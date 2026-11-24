from datetime import date, datetime, timedelta, timezone

from wattou.analysis.credit import (
    depletion,
    forecast_daily_kwh,
    price_per_kwh,
    remaining_kwh,
    validate_reading,
)
from wattou.analysis.types import CreditEntry

T0 = datetime(2026, 11, 2, tzinfo=timezone.utc)
FLAT = [1 / 24] * 24


def reading(kwh, h=0):
    return CreditEntry(T0 + timedelta(hours=h), "reading", kwh)


def recharge(kwh, fcfa, h=0):
    return CreditEntry(T0 + timedelta(hours=h), "recharge", kwh, fcfa)


def test_price_weighted():
    assert price_per_kwh([recharge(40, 5000), recharge(80, 10000, 1)], 110) == 125


def test_price_uses_last_three_recharges():
    entries = [recharge(10, 9999, 0)] + [recharge(10, 1000, h) for h in (1, 2, 3)]
    assert price_per_kwh(entries, 110) == 100


def test_price_default():
    assert price_per_kwh([reading(50)], 110) == 110


def test_remaining_after_consumption():
    assert remaining_kwh([reading(50)], lambda since: 12.0) == 38


def test_remaining_with_recharge():
    assert remaining_kwh([reading(50), recharge(40, 5000, 1)], lambda since: 12.0) == 78


def test_remaining_floor_zero():
    assert remaining_kwh([reading(5)], lambda since: 12.0) == 0


def test_remaining_none_without_reading():
    assert remaining_kwh([], lambda since: 0) is None
    assert remaining_kwh([recharge(40, 5000)], lambda since: 0) is None


def test_validate_reading_rejects_increase():
    entries = [reading(50)]
    assert validate_reading(entries, 60, measured_since_last=3) is not None
    assert validate_reading(entries, 46, measured_since_last=3) is None
    assert validate_reading(entries + [recharge(40, 5000, 1)], 85, measured_since_last=3) is None
    assert validate_reading([], 85, measured_since_last=0) is None


def test_forecast_constant():
    daily = [(date(2026, 11, d), 8.0) for d in range(1, 8)]
    assert forecast_daily_kwh(daily, date(2026, 11, 8)) == 8


def test_forecast_blends_same_weekday():
    daily = [(date(2026, 10, 12) + timedelta(days=i), 12.0 if i % 7 == 6 else 8.0) for i in range(28)]
    # cible = dimanche 8 novembre 2026 ; dimanches passés à 12 kWh, moyenne 7 j = 8,571
    f = forecast_daily_kwh(daily, date(2026, 11, 8))
    assert abs(f - (12 + (8 * 6 + 12) / 7) / 2) < 1e-9


def test_depletion_days():
    days, when = depletion(38, T0, 8, FLAT)
    assert abs(days - 4.75) < 1e-9
    assert when == T0 + timedelta(days=4, hours=18)


def test_depletion_zero_forecast():
    assert depletion(38, T0, 0, FLAT) is None
