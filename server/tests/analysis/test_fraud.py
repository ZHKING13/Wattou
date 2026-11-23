from datetime import datetime, timedelta, timezone
from uuid import uuid4

from wattou.analysis.fraud import check_absence, check_meter_gap, check_night_unknown
from wattou.analysis.types import Activation, ApplianceSig, CreditEntry

T0 = datetime(2026, 11, 2, 2, tzinfo=timezone.utc)
FRIDGE = ApplianceSig(uuid4(), "frigo", 120, 0.8, 50, essential=True)


NOW = T0 + timedelta(minutes=20)


def test_absence_tap_detected_within_15_min():
    tap = Activation(T0 + timedelta(minutes=5), None, 400, 0.9)
    alert = check_absence([tap], [FRIDGE], absence_since=T0, now=NOW)
    assert alert is not None and alert.kind == "absence_load"
    assert alert.ts == T0 + timedelta(minutes=15)
    assert "400 W" in alert.message


def test_absence_not_yet_ten_minutes():
    tap = Activation(T0 + timedelta(minutes=5), None, 400, 0.9)
    assert check_absence([tap], [FRIDGE], absence_since=T0, now=T0 + timedelta(minutes=14)) is None


def test_absence_short_load_ignored():
    short = Activation(T0 + timedelta(minutes=5), T0 + timedelta(minutes=13), 400, 0.9)
    assert check_absence([short], [FRIDGE], absence_since=T0, now=NOW) is None


def test_absence_known_or_small_loads_not_flagged():
    fridge = Activation(T0 - timedelta(minutes=1), None, 120, 0.8)
    clim = Activation(T0, None, 1100, 0.9)
    sigs = [FRIDGE, ApplianceSig(uuid4(), "Clim", 1100, 0.9, 20)]
    small = Activation(T0, None, 200, 0.9)
    assert check_absence([fridge, clim, small], sigs, absence_since=T0, now=NOW) is None


def test_absence_ignores_loads_started_before_leaving():
    before = Activation(T0 - timedelta(minutes=30), None, 400, 0.9)
    assert check_absence([before], [FRIDGE], absence_since=T0, now=NOW) is None


def test_no_alert_when_present():
    tap = Activation(T0 + timedelta(minutes=5), None, 400, 0.9)
    assert check_absence([tap], [FRIDGE], absence_since=None, now=NOW) is None


def entries(*readings, recharge_at=None):
    out = [CreditEntry(T0 + timedelta(days=i), "reading", kwh) for i, kwh in enumerate(readings)]
    if recharge_at is not None:
        out.append(CreditEntry(T0 + timedelta(days=recharge_at, hours=1), "recharge", 40, 5000))
    return out


def test_meter_gap_two_intervals():
    # le compteur décompte 10 kWh/jour, le capteur n'en voit que 8
    alert = check_meter_gap(entries(50, 40, 30), lambda a, b: 8.0)
    assert alert is not None and alert.kind == "meter_gap"
    assert "10.0 kWh" in alert.message and "8.0" in alert.message


def test_meter_gap_single_interval_ignored():
    measured = {0: 10.0, 1: 8.0}
    f = lambda a, b: measured[(a - T0).days]  # noqa: E731
    assert check_meter_gap(entries(50, 40, 30), f) is None


def test_meter_gap_accounts_for_recharge():
    assert check_meter_gap(entries(50, 80, 70, recharge_at=0), lambda a, b: 10.0) is None


def test_night_unknown_three_nights():
    unknown = ApplianceSig(uuid4(), None, 400, 0.9, 5)
    history_start = T0 - timedelta(days=30)
    acts = [Activation(T0 + timedelta(days=d), T0 + timedelta(days=d, hours=1), 400, 0.9)
            for d in range(3)]
    now = T0 + timedelta(days=3)
    [alert] = check_night_unknown({unknown.id: acts}, [unknown], now, history_start)
    assert alert.kind == "night_unknown"
    assert check_night_unknown({unknown.id: acts[:2]}, [unknown], now, history_start) == []
    labeled = ApplianceSig(unknown.id, "clim", 400, 0.9, 5)
    assert check_night_unknown({unknown.id: acts}, [labeled], now, history_start) == []


def test_night_habit_since_installation_not_fraud():
    """Un appareil nocturne présent dès l'installation (clim, congélateur) n'est pas suspect."""
    sig = ApplianceSig(uuid4(), None, 1100, 0.9, 40)
    acts = [Activation(T0 + timedelta(days=d), T0 + timedelta(days=d, hours=3), 1100, 0.9)
            for d in range(-20, 3)]
    now = T0 + timedelta(days=3)
    assert check_night_unknown({sig.id: acts}, [sig], now, history_start=T0 - timedelta(days=20)) == []


def test_night_unknown_needs_a_week_of_history():
    sig = ApplianceSig(uuid4(), None, 400, 0.9, 5)
    acts = [Activation(T0 + timedelta(days=d), T0 + timedelta(days=d, hours=1), 400, 0.9)
            for d in range(3)]
    now = T0 + timedelta(days=3)
    assert check_night_unknown({sig.id: acts}, [sig], now, history_start=T0 - timedelta(days=1)) == []
