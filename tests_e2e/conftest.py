"""Scénario d'acceptation : 14 jours simulés traversent MQTT, l'ingestion, l'analyse et l'API.

Prérequis : `make up` (PostgreSQL + Mosquitto). Lancer avec `make e2e`.
"""

import csv
import os
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulator" / "src"))
UTC = timezone.utc
API = "http://127.0.0.1:8765/api/v1"
DB = "wattou_e2e"
TAP = (datetime(2026, 11, 13, 1, tzinfo=UTC), datetime(2026, 11, 13, 3, tzinfo=UTC))
END = datetime(2026, 11, 14, tzinfo=UTC)
LOGS = ROOT / ".superpowers" / "e2e-logs"


def dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def psql(sql: str, db: str = DB) -> str:
    return subprocess.run(["docker", "exec", "wattou-db-1", "psql", "-U", "wattou", "-d", db, "-tAc", sql],
                          check=True, capture_output=True, text=True).stdout.strip()


def wait(cond, timeout: float, what: str, every: float = 2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if cond():
            return
        time.sleep(every)
    raise TimeoutError(what)


class Scenario:
    def __init__(self):
        LOGS.mkdir(parents=True, exist_ok=True)
        self.env = {**os.environ,
                    "WATTOU_DATABASE_URL": f"postgresql+asyncpg://wattou:wattou@localhost:5432/{DB}",
                    "WATTOU_MQTT_HOST": "localhost",
                    "WATTOU_JWT_SECRET": "e2e-secret-e2e-secret-e2e-secret-0123",
                    "WATTOU_WORKER_INTERVAL_S": "2"}
        self.procs: list[subprocess.Popen] = []
        self.truth: dict[str, dict[datetime, float]] = defaultdict(dict)  # appareil -> minute -> W

    # --- infrastructure -------------------------------------------------------
    def start(self):
        psql(f"DROP DATABASE IF EXISTS {DB} WITH (FORCE)", db="wattou")
        psql(f"CREATE DATABASE {DB}", db="wattou")
        subprocess.run(["uv", "run", "alembic", "upgrade", "head"], cwd=ROOT / "server", env=self.env,
                       check=True, capture_output=True)
        for name, cmd in {
            "ingest": ["uv", "run", "python", "-m", "wattou.ingest"],
            "worker": ["uv", "run", "python", "-m", "wattou.worker"],
            "api": ["uv", "run", "uvicorn", "wattou.api.app:create_app", "--factory", "--port", "8765"],
        }.items():
            log = open(LOGS / f"{name}.log", "w")
            self.procs.append(subprocess.Popen(cmd, cwd=ROOT / "server", env=self.env, stdout=log,
                                               stderr=subprocess.STDOUT))
        wait(lambda: self._ok("http://127.0.0.1:8765/health"), 60, "API")
        r = httpx.post(f"{API}/auth/register", json={"phone": "+2250700000099", "password": "secret1",
                                                       "foyer_name": "E2E"})
        r.raise_for_status()
        self.foyer = r.json()["foyer_id"]
        self.h = {"Authorization": f"Bearer {r.json()['token']}"}

    def stop(self):
        for p in self.procs:
            p.terminate()
        for p in self.procs:
            p.wait(timeout=20)

    @staticmethod
    def _ok(url):
        try:
            return httpx.get(url, timeout=2).status_code == 200
        except httpx.HTTPError:
            return False

    # --- pilotage du scénario --------------------------------------------------
    def simulate(self, start: datetime, end: datetime, *scenarios: str):
        truth = LOGS / f"truth-{start:%m%d}.csv"
        days = (end - start).total_seconds() / 86400
        cmd = ["uv", "run", "python", "-m", "wattou_sim", "--foyer", self.foyer,
               "--start", start.isoformat(), "--backfill-days", str(days), "--until", end.isoformat(),
               "--truth", str(truth)]
        for s in scenarios:
            cmd += ["--scenario", s]
        with open(LOGS / "sim.log", "a") as log:
            subprocess.run(cmd, cwd=ROOT / "simulator", check=True, stdout=log, stderr=subprocess.STDOUT)
        for row in csv.DictReader(open(truth)):
            self.truth[row["appareil"]][dt(row["ts"])] = float(row["p_w"])
        last = end - timedelta(seconds=1)
        wait(lambda: self.summary()["data_until"] and dt(self.summary()["data_until"]) >= last,
             600, f"ingestion jusqu'à {last}")
        wait(lambda: self.analysed_until() >= last - timedelta(seconds=10), 900, "analyse")

    def analysed_until(self) -> datetime:
        v = psql(f"SELECT last_ts FROM analysis_state WHERE foyer_id = '{self.foyer}'")
        return dt(v.replace(" ", "T")) if v else datetime.min.replace(tzinfo=UTC)

    def summary(self) -> dict:
        return httpx.get(f"{API}/foyer/summary", headers=self.h).json()

    def get(self, path, **params):
        r = httpx.get(f"{API}{path}", headers=self.h, params=params, timeout=60)
        r.raise_for_status()
        return r.json()

    def send(self, method, path, body):
        r = httpx.request(method, f"{API}{path}", headers=self.h, json=body, timeout=30)
        assert r.status_code < 300, r.text
        return r

    def truth_kwh(self, appareil: str, start: datetime, end: datetime) -> float:
        return sum(w for t, w in self.truth.get(appareil, {}).items() if start <= t < end) / 60 / 1000

    def truth_total(self, start: datetime, end: datetime) -> float:
        return sum(self.truth_kwh(a, start, end) for a in self.truth)


@pytest.fixture(scope="session")
def sc():
    s = Scenario()
    s.start()
    try:
        d = lambda day: datetime(2026, 11, day, tzinfo=UTC)  # noqa: E731
        s.simulate(d(1), d(8))
        s.send("POST", "/foyer/credit", {"kind": "reading", "kwh": 60})
        s.simulate(d(8), d(11))
        s.send("POST", "/foyer/credit", {"kind": "recharge", "kwh": 80, "amount_fcfa": 10000})
        s.simulate(d(11), d(13))
        # l'utilisateur nomme ses deux gros appareils puis part (mode absence)
        week = s.get("/foyer/appliances", period="week")
        s.labeled = {}
        for name, watts in (("Clim", 1100), ("Congélateur", 150)):
            cands = [a for a in week if a["power_w"] and abs(a["power_w"] - watts) <= 0.15 * watts
                     and not a["device_id"]]
            best = max(cands, key=lambda a: a["kwh"])
            s.send("PATCH", f"/appliances/{best['id']}", {"label": name})
            s.labeled[name] = best["id"]
        s.send("PUT", "/foyer/absence", {"enabled": True})
        s.simulate(d(13), END, f"neighbor_tap@{TAP[0].isoformat()}/{TAP[1].isoformat()}")
        # dernier relevé du compteur : il reste 1,5 jour de consommation
        s.daily = s.truth_total(d(13), END)
        s.r14 = round(1.5 * s.daily, 1)
        sub = subprocess.Popen(["docker", "exec", "wattou-mqtt-1", "mosquitto_sub", "-u", "server",
                                "-P", "server", "-t", f"wattou/{s.foyer}/+/cmd", "-v", "-W", "30"],
                               stdout=subprocess.PIPE, text=True)
        time.sleep(1)
        s.send("POST", "/foyer/credit", {"kind": "reading", "kwh": s.r14})
        s.commands = sub.communicate(timeout=60)[0].splitlines()
        s.summary_end = s.summary()
        yield s
    finally:
        s.stop()
