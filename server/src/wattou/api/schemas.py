from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Register(BaseModel):
    phone: str = Field(min_length=1, max_length=20)
    password: str = Field(min_length=6)
    foyer_name: str = Field(min_length=1, max_length=80)


class Login(BaseModel):
    phone: str
    password: str


class TokenOut(BaseModel):
    token: str
    foyer_id: str


class Summary(BaseModel):
    power_w: float
    today_kwh: float
    today_fcfa: float
    price_fcfa_kwh: float
    credit_kwh: float | None
    credit_fcfa: float | None
    days_left: float | None
    depletion_at: datetime | None
    month_forecast_fcfa: float
    absence_mode: bool
    low_credit_days: float
    data_until: datetime | None


class ApplianceOut(BaseModel):
    id: str
    label: str | None
    kwh: float
    fcfa: float
    share: float
    estimated: bool = True
    essential: bool = False
    device_id: str | None = None


class AppliancePatch(BaseModel):
    label: str | None = Field(default=None, max_length=60)
    essential: bool | None = None


class HistoryPoint(BaseModel):
    ts: datetime
    kwh: float


class CreditIn(BaseModel):
    kind: Literal["reading", "recharge"]
    kwh: float = Field(gt=0, le=10000)
    amount_fcfa: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def recharge_has_amount(self):
        if self.kind == "recharge" and self.amount_fcfa is None:
            raise ValueError("Indiquez le montant payé (FCFA) pour une recharge.")
        return self


class AbsenceIn(BaseModel):
    enabled: bool


class RulesIn(BaseModel):
    low_credit_days: float = Field(ge=0.5, le=10)


class PushTokenIn(BaseModel):
    token: str = Field(min_length=1, max_length=200)
