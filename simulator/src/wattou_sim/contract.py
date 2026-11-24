"""Contrat MQTT Wattou (copie conforme côté serveur : server/src/wattou/contract.py)."""

from typing import Literal

from datetime import UTC, datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

PREFIX = "wattou"
MIN_TS = datetime(2024, 1, 1, tzinfo=UTC)  # avant : horloge non synchronisée (NTP)


def topic(foyer_id: str, device_id: str, leaf: str) -> str:
    return f"{PREFIX}/{foyer_id}/{device_id}/{leaf}"


class Meta(BaseModel):
    kind: Literal["meter", "plug", "ir_ac"]
    name: str
    essential: bool = False


class _State(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    ts: AwareDatetime

    @field_validator("ts")
    @classmethod
    def _synced_clock(cls, v: datetime) -> datetime:
        if v < MIN_TS:
            raise ValueError("horodatage antérieur à 2024 (horloge non synchronisée)")
        return v


class MeterState(_State):
    p_w: float
    v: float
    i_a: float
    pf: float
    e_kwh: float


class PlugState(_State):
    p_w: float
    on: bool


class AcState(_State):
    mode: Literal["off", "cool", "fan"]
    setpoint_c: int


class PlugCmd(BaseModel):
    on: bool


class AcCmd(BaseModel):
    mode: Literal["off", "cool", "fan"] | None = None
    setpoint_c: int | None = Field(default=None, ge=16, le=30)


class ScheduleSlot(BaseModel):
    at: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    days: list[int] = Field(default_factory=lambda: list(range(7)))
    action: dict


class Schedule(BaseModel):
    slots: list[ScheduleSlot] = Field(default_factory=list)
