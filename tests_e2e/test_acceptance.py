"""Critères de réussite de la spec, mesurés sur le simulateur."""

from datetime import datetime, timedelta, timezone

from wattou_sim.household import abidjan_household

from .conftest import END, TAP, dt

UTC = timezone.utc


def test_daily_cost_within_10pct(sc):
    days = sc.get("/foyer/history", **{"from": "2026-11-08T00:00:00Z", "to": END.isoformat(), "step": "day"})
    assert len(days) == 6
    for d in days:
        start = dt(d["ts"])
        truth = sc.truth_total(start, start + timedelta(days=1))
        assert abs(d["kwh"] - truth) / truth <= 0.10, (start, d["kwh"], truth)


def test_four_appliances_recognized(sc):
    week = {a["label"]: a["kwh"] for a in sc.get("/foyer/appliances", period="week")}
    start = END - timedelta(days=7)
    pairs = {"Clim": "clim", "Congélateur": "congelateur", "prise-fer": "fer",
             "prise-tv": "tv", "prise-frigo": "frigo"}
    ok = []
    for label, appareil in pairs.items():
        truth = sc.truth_kwh(appareil, start, END)
        got = week.get(label, 0.0)
        if truth and abs(got - truth) / truth <= 0.25:
            ok.append(label)
        print(f"{label}: api={got:.2f} kWh vérité={truth:.2f} kWh")
    assert len(ok) >= 4, ok
    # les prises mesurent directement ; la reconnaissance par désagrégation (NILM) est jugée à part
    assert {"Clim", "Congélateur"} <= set(ok), ok


def test_no_false_fraud_alert_on_normal_weeks(sc):
    alerts = sc.get("/alerts")
    assert not [a for a in alerts if a["kind"] == "night_unknown"], alerts
    for a in alerts:
        if a["kind"] == "absence_load":
            assert TAP[0] <= dt(a["ts"]) <= TAP[1], a
    assert not [a for a in alerts if a["kind"] == "stuck"], alerts


def test_depletion_within_one_day(sc):
    predicted = sc.summary_end["days_left"]
    assert predicted is not None
    h, t, used = abidjan_household(seed=1), END, 0.0
    while used < sc.r14:
        used += h.total(t)[0] / 3_600_000
        t += timedelta(seconds=1)
    real = (t - END).total_seconds() / 86400
    print(f"prévu {predicted:.2f} j, réel {real:.2f} j")
    assert abs(predicted - real) <= 1.0


def test_tap_alert_within_15_min(sc):
    alerts = [a for a in sc.get("/alerts") if a["kind"] == "absence_load"]
    assert alerts, sc.get("/alerts")
    delay = dt(alerts[-1]["ts"]) - TAP[0]
    assert timedelta(0) <= delay < timedelta(minutes=15), delay


def test_low_credit_rule_cuts_iron(sc):
    assert sc.summary_end["days_left"] < 2
    assert any(line.endswith('/prise-fer/cmd {"on":false}') for line in sc.commands), sc.commands
    assert not any("/prise-frigo/cmd" in line for line in sc.commands)
    assert [a for a in sc.get("/alerts") if a["kind"] == "low_credit_rule"]
