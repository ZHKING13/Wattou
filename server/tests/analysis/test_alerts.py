from datetime import datetime, timedelta, timezone
from uuid import uuid4

from wattou.analysis.alerts import (
    check_credit,
    check_outage,
    check_peak,
    check_plug_stuck,
    check_stuck,
    check_voltage,
)
from wattou.analysis.types import Activation, ApplianceSig, Sample

T0 = datetime(2026, 11, 2, 12, tzinfo=timezone.utc)


def test_check_credit():
    a = check_credit(1.5, 2, T0 + timedelta(hours=36), T0)
    assert a.kind == "credit_low" and "1,5 jours" in a.message and "04/11" in a.message
    assert check_credit(3, 2, T0 + timedelta(days=3), T0) is None
    assert check_credit(None, 2, None, T0) is None


def test_check_peak():
    avg = [0.4] * 24
    today = [0.4] * 24
    today[11] = 1.0
    a = check_peak(today, avg, T0)  # heure écoulée = 11h
    assert a is not None and a.kind == "peak"
    today[11] = 0.45
    assert check_peak(today, avg, T0) is None
    small = [0.1] * 24
    assert check_peak([0.3] * 24, small, T0) is None  # < 0,5 kWh


def test_check_stuck():
    fridge = ApplianceSig(uuid4(), "Frigo", 120, 0.8, 30, essential=True)
    opened = [Activation(T0 - timedelta(hours=4), None, 118, 0.8)]
    [a] = check_stuck(opened, [fridge], T0)
    assert a.kind == "stuck" and "Frigo" in a.message
    assert check_stuck([Activation(T0 - timedelta(hours=1), None, 118, 0.8)], [fridge], T0) == []


def test_check_outage():
    s = [Sample(T0 + timedelta(seconds=i), 100) for i in range(60)]
    s += [Sample(T0 + timedelta(minutes=31, seconds=i), 100) for i in range(60)]
    [a] = check_outage(s)
    assert a.kind == "outage" and "30 min" in a.message
    assert check_outage(s[:60]) == []


def test_check_voltage():
    ok = [Sample(T0 + timedelta(seconds=i), 100, 1, 228) for i in range(30)]
    low = [Sample(T0 + timedelta(seconds=30 + i), 100, 1, 170) for i in range(12)]
    a = check_voltage(ok + low)
    assert a is not None and a.kind == "voltage" and "170 V" in a.message
    assert check_voltage(ok + low[:5]) is None


def test_check_stuck_ignores_plug_backed_appliances():
    plug_fridge = ApplianceSig(uuid4(), "prise-frigo", 120, 0.8, 30, device_id="prise-frigo", essential=True)
    opened = [Activation(T0 - timedelta(hours=9), None, 120, 0.95)]
    assert check_stuck(opened, [plug_fridge], T0) == []


def test_check_plug_stuck():
    readings = [(T0 - timedelta(hours=3) + timedelta(seconds=10 * i), 120.0) for i in range(1081)]
    [a] = check_plug_stuck("prise-frigo", "Prise frigo", readings, T0)
    assert a.kind == "stuck" and "Prise frigo" in a.message
    cycling = [(t, 0.0 if i % 200 < 80 else 120.0) for i, (t, _) in enumerate(readings)]
    assert check_plug_stuck("prise-frigo", "Prise frigo", cycling, T0) == []
    assert check_plug_stuck("prise-frigo", "Prise frigo", readings[-100:], T0) == []
