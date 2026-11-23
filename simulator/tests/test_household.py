from datetime import datetime, timedelta, timezone

from wattou_sim.household import NeighborTap, abidjan_household

DAY = datetime(2026, 11, 2, tzinfo=timezone.utc)


def test_household_breakdown_sums_to_total():
    h = abidjan_household(seed=1)
    for i in range(100):
        t = DAY + timedelta(seconds=i * 863)
        total, pf = h.total(t)
        assert abs(sum(h.breakdown(t).values()) - total) < 1e-6
        assert 0 < pf <= 1


def test_neighbor_tap_adds_power():
    h = abidjan_household(seed=1)
    t = DAY.replace(hour=2)
    before = h.total(t)[0]
    h.add_scenario(NeighborTap(start=DAY.replace(hour=1), end=DAY.replace(hour=3), w=400))
    assert abs(h.total(t)[0] - before - 400) < 1e-6
    assert h.breakdown(t)["voisin"] == 400


def test_deterministic():
    a, b = abidjan_household(seed=7), abidjan_household(seed=7)
    for i in range(200):
        t = DAY + timedelta(seconds=i * 431)
        assert a.total(t) == b.total(t)
