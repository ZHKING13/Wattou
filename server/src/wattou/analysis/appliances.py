"""Regroupement des activations en appareils et répartition de l'énergie (kWh)."""

from dataclasses import replace
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from .types import Activation, ApplianceSig, Sample

PROMOTE_AFTER = 3


def assign(activations: list[Activation], sigs: list[ApplianceSig], tol: float = 0.15,
           pf_tol: float = 0.15) -> tuple[list[tuple[Activation, UUID]], list[ApplianceSig]]:
    sigs = [replace(s) for s in sigs]
    out: list[tuple[Activation, UUID]] = []
    for a in activations:
        best, best_err = None, None
        for s in sigs:
            if s.delta_w <= 0:
                continue
            err = abs(a.delta_w - s.delta_w) / s.delta_w
            pf_ok = s.device_id is not None or abs(a.pf - s.pf) <= pf_tol
            if err <= tol and pf_ok and (best_err is None or err < best_err):
                best, best_err = s, err
        if best is None:
            best = ApplianceSig(uuid4(), None, a.delta_w, a.pf, 0)
            sigs.append(best)
        best.delta_w = (best.delta_w * best.n_obs + a.delta_w) / (best.n_obs + 1)
        best.pf = (best.pf * best.n_obs + a.pf) / (best.n_obs + 1)
        best.n_obs += 1
        out.append((a, best.id))
    return out, sigs


def visible(sigs: list[ApplianceSig]) -> list[ApplianceSig]:
    """Signaux montrés à l'utilisateur (« appareil inconnu à nommer » après 3 observations)."""
    return [s for s in sigs if s.n_obs >= PROMOTE_AFTER or s.label or s.device_id]


def _overlap_h(a: Activation, start: datetime, end: datetime) -> float:
    s, e = max(a.start, start), min(a.end or end, end)
    return max(0.0, (e - s).total_seconds() / 3600)


def _percentile(values: list[float], q: float) -> float:
    v = sorted(values)
    return v[min(len(v) - 1, int(q * len(v)))] if v else 0.0


def attribute(samples: list[Sample], assigned: list[tuple[Activation, UUID]],
              sigs: list[ApplianceSig], plug_energy: dict[str, float]) -> dict[str, float]:
    """kWh par clé (id d'appareil en str, "fond", "autres") ; la somme = énergie totale mesurée."""
    if not samples:
        return {}
    start, end = samples[0].ts, samples[-1].ts + timedelta(seconds=1)  # 1 mesure = 1 s
    total = sum(s.p_w for s in samples) / 3_600_000
    night = [s.p_w for s in samples if s.ts.hour < 5] or [s.p_w for s in samples]
    return attribute_totals(total, len(samples) / 3600, _percentile(night, 0.05), assigned, sigs,
                            plug_energy, start, end)


def attribute_totals(total_kwh: float, hours_measured: float, baseline_w: float,
                     assigned: list[tuple[Activation, UUID]], sigs: list[ApplianceSig],
                     plug_energy: dict[str, float], start: datetime, end: datetime) -> dict[str, float]:
    """Même répartition qu'`attribute`, à partir d'agrégats (longues périodes, côté API)."""
    by_id = {s.id: s for s in sigs}
    out: dict[str, float] = {}
    for s in sigs:
        if s.device_id:
            out[str(s.id)] = plug_energy.get(s.device_id, 0.0)
    for a, sid in assigned:
        sig = by_id.get(sid)
        if sig is None or sig.device_id:
            continue
        out[str(sid)] = out.get(str(sid), 0.0) + a.delta_w * _overlap_h(a, start, end) / 1000
    used = sum(out.values())
    if used > total_kwh and used > 0:
        out = {k: v * total_kwh / used for k, v in out.items()}
        used = total_kwh
    out["fond"] = max(0.0, min(baseline_w * hours_measured / 1000, total_kwh - used))
    out["autres"] = max(0.0, total_kwh - used - out["fond"])
    return out
