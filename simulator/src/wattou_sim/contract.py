"""Contrat MQTT Wattou (copie conforme côté serveur : server/src/wattou/contract.py)."""

from typing import Literal

from pydantic import BaseModel, Field

PREFIX = "wattou"


def topic(foyer_id: str, device_id: str, leaf: str) -> str:
    return f"{PREFIX}/{foyer_id}/{device_id}/{leaf}"


class Meta(BaseModel):
    kind: Literal["meter", "plug", "ir_ac"]
    name: str
    essential: bool = False


class MeterState(BaseModel):
    ts: str
    p_w: float
    v: float
    i_a: float
    pf: float
    e_kwh: float


class PlugState(BaseModel):
    ts: str
    p_w: float
    on: bool


class AcState(BaseModel):
    ts: str
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
