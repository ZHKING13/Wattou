"""Types partagés par l'analyse (indépendants de la base)."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class Sample:
    ts: datetime
    p_w: float
    pf: float = 1.0
    v: float = 230.0


@dataclass(frozen=True)
class CreditEntry:
    ts: datetime
    kind: str  # "reading" | "recharge"
    kwh: float
    amount_fcfa: int | None = None


@dataclass(frozen=True)
class DeviceView:
    id: str
    kind: str
    essential: bool
    last_state: dict = field(default_factory=dict)
    name: str = ""  # nom lisible (« Prise fer à repasser ») pour les messages


@dataclass(frozen=True)
class Step:
    ts: datetime
    delta_w: float
    pf: float


@dataclass
class Activation:
    start: datetime
    end: datetime | None
    delta_w: float
    pf: float


@dataclass
class ApplianceSig:
    id: UUID
    label: str | None
    delta_w: float
    pf: float
    n_obs: int
    device_id: str | None = None
    essential: bool = False


@dataclass(frozen=True)
class Alert:
    kind: str
    ts: datetime
    message: str
    dedup_key: str
