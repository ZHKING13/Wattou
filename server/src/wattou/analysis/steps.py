"""Détection de paliers de puissance (allumages/extinctions) et appariement."""

from datetime import datetime, timedelta
from statistics import median

from .types import Activation, Sample, Step

__all__ = ["Activation", "Step", "detect_steps", "pair_steps", "segments", "track"]


def segments(samples: list[Sample], max_gap_s: int = 120) -> list[list[Sample]]:
    out: list[list[Sample]] = []
    for s in samples:
        if out and (s.ts - out[-1][-1].ts).total_seconds() <= max_gap_s:
            out[-1].append(s)
        else:
            out.append([s])
    return out


def _detect(seg: list[Sample], min_delta_w: float, settle_s: int) -> list[Step]:
    p = [s.p_w for s in seg]
    steps: list[Step] = []
    group: list[tuple[int, float]] = []

    def close_group():
        if group:
            delta = max((d for _, d in group), key=abs)
            i = max((i for i, _ in group), key=lambda i: abs(p[i] - p[i - 1]))
            pf = median(s.pf for s in seg[i:i + settle_s])
            steps.append(Step(seg[i].ts, delta, pf))
            group.clear()

    for i in range(settle_s, len(p) - settle_s + 1):
        d = median(p[i:i + settle_s]) - median(p[i - settle_s:i])
        if abs(d) >= min_delta_w and (not group or (d > 0) == (group[-1][1] > 0)) \
                and (not group or group[-1][0] == i - 1):
            group.append((i, d))
        else:
            close_group()
            if abs(d) >= min_delta_w:
                group.append((i, d))
    close_group()
    return steps


def detect_steps(samples: list[Sample], min_delta_w: float = 80, settle_s: int = 3,
                 max_gap_s: int = 120) -> list[Step]:
    out: list[Step] = []
    for seg in segments(samples, max_gap_s):
        out.extend(_detect(seg, min_delta_w, settle_s))
    return out


def pair_steps(steps: list[Step], open_: list[Activation],
               tol: float = 0.15) -> tuple[list[Activation], list[Activation]]:
    still_open = list(open_)
    closed: list[Activation] = []
    for st in steps:
        if st.delta_w > 0:
            still_open.append(Activation(st.ts, None, st.delta_w, st.pf))
            continue
        for a in reversed(still_open):
            if abs(a.delta_w + st.delta_w) <= tol * a.delta_w:
                still_open.remove(a)
                a.end = st.ts
                closed.append(a)
                break
    return closed, still_open


MAX_OPEN = timedelta(hours=24)


def track(samples: list[Sample], open_: list[Activation], last_ts: datetime, boundary: datetime,
          max_gap_s: int = 120) -> tuple[list[Activation], list[Activation]]:
    """Paliers de (last_ts, boundary] appariés segment par segment.

    Un trou de données (délestage, coupure) ferme les activations ouvertes au dernier
    échantillon avant le trou : sans mesure, on ne leur attribue pas d'énergie. Une activation
    ouverte depuis plus de 24 h (palier d'extinction manqué) est abandonnée.
    """
    closed: list[Activation] = []
    segs = segments(samples, max_gap_s)
    for i, seg in enumerate(segs):
        steps = [st for st in _detect(seg, 80, 3) if last_ts < st.ts <= boundary]
        done, open_ = pair_steps(steps, open_)
        closed += done
        if i + 1 < len(segs) and segs[i + 1][0].ts > last_ts:
            for a in open_:
                a.end = max(a.start, seg[-1].ts)
            closed += open_
            open_ = []
    now = samples[-1].ts if samples else boundary
    return closed, [a for a in open_ if now - a.start <= MAX_OPEN]
