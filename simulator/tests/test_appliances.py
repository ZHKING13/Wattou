from datetime import datetime, time, timedelta, timezone

from wattou_sim.appliances import Bursty, Constant, Cyclic, Scheduled

DAY = datetime(2026, 11, 2, tzinfo=timezone.utc)


def seconds(day=DAY, step=1):
    for s in range(0, 86400, step):
        yield day + timedelta(seconds=s)


def test_cyclic_duty_cycle():
    fridge = Cyclic("frigo", on_w=120, on_s=15 * 60, off_s=25 * 60, pf=0.8)
    values = [fridge.power_w(t) for t in seconds()]
    on = [v for v in values if v > 0]
    assert set(on) == {120}
    assert abs(len(on) / len(values) - 15 / 40) < 0.02


def test_scheduled_off_outside_windows():
    clim = Scheduled("clim", on_w=1100, windows=[(time(19), time(23, 30))], pf=0.9, jitter_min=0)
    assert clim.power_w(DAY.replace(hour=10)) == 0
    assert clim.power_w(DAY.replace(hour=21)) == 1100


def test_scheduled_window_crossing_midnight():
    fan = Scheduled("ventilo", on_w=60, windows=[(time(21), time(6))], pf=0.95, jitter_min=0)
    assert fan.power_w(DAY.replace(hour=2)) == 60
    assert fan.power_w(DAY.replace(hour=23)) == 60
    assert fan.power_w(DAY.replace(hour=12)) == 0


def test_bursty_energy():
    iron = Bursty("fer", on_w=1000, bursts_per_day=2, burst_s=8 * 60,
                  active_hours=[(time(6), time(8)), (time(18), time(20))], pf=1.0, seed=3)
    kwh = sum(iron.power_w(t) for t in seconds()) / 3600 / 1000
    assert abs(kwh - 0.267) / 0.267 < 0.10


def test_constant():
    assert Constant("fond", 25, pf=0.6).power_w(DAY) == 25
