import random
from datetime import datetime, timedelta, timezone

from wattou.analysis.steps import detect_steps, pair_steps
from wattou.analysis.types import Sample

T0 = datetime(2026, 11, 2, tzinfo=timezone.utc)


def series(levels: list[tuple[int, float]], start=T0, noise=0.0, seed=1):
    """levels: [(durée_s, puissance)] -> échantillons 1 Hz."""
    rng = random.Random(seed)
    out, t = [], start
    for dur, p in levels:
        for _ in range(dur):
            out.append(Sample(t, p + rng.uniform(-noise, noise), 0.9))
            t += timedelta(seconds=1)
    return out


def test_single_on_off():
    steps = detect_steps(series([(60, 50), (120, 1150), (60, 50)]))
    assert [round(s.delta_w) for s in steps] == [1100, -1100]
    assert steps[0].ts == T0 + timedelta(seconds=60)


def test_noise_below_threshold_ignored():
    assert detect_steps(series([(600, 300)], noise=30)) == []


def test_overlapping_appliances_paired():
    s = series([(60, 50), (60, 1150), (60, 1270), (60, 1150), (60, 50)])
    closed, still_open = pair_steps(detect_steps(s), [])
    deltas = sorted(round(a.delta_w) for a in closed)
    assert deltas == [120, 1100] and still_open == []
    fridge = next(a for a in closed if round(a.delta_w) == 120)
    assert (fridge.end - fridge.start).total_seconds() == 60


def test_unmatched_on_stays_open():
    closed, still_open = pair_steps(detect_steps(series([(60, 50), (60, 1150)])), [])
    assert closed == [] and len(still_open) == 1


def test_gap_creates_no_step():
    a = series([(60, 0)])
    b = series([(60, 1000)], start=T0 + timedelta(minutes=11))
    assert detect_steps(a + b) == []


def test_track_closes_open_activation_at_gap():
    from wattou.analysis.steps import track

    before = series([(30, 50), (270, 1150)])  # clim allumée à +30 s, puis délestage
    after = series([(600, 50)], start=T0 + timedelta(hours=3))
    closed, still_open = track(before + after, [], T0 - timedelta(seconds=1), after[-1].ts)
    assert still_open == []
    [a] = closed
    assert a.start == T0 + timedelta(seconds=30) and a.end == before[-1].ts


def test_track_drops_activation_open_more_than_a_day():
    from wattou.analysis.steps import track
    from wattou.analysis.types import Activation

    old = Activation(T0 - timedelta(hours=25), None, 300, 0.9)
    s = series([(60, 350)])
    closed, still_open = track(s, [old], T0 - timedelta(seconds=1), s[-1].ts)
    assert closed == [] and still_open == []
