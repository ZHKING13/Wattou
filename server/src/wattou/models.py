from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    PrimaryKeyConstraint,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

metadata = MetaData()
TS = DateTime(timezone=True)

foyers = Table(
    "foyers", metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    Column("name", Text, nullable=False),
    Column("absence_mode", Boolean, nullable=False, server_default="false"),
    Column("absence_since", TS),
    Column("low_credit_days", Float, nullable=False, server_default="2"),
    Column("low_credit_active", Boolean, nullable=False, server_default="false"),
    Column("created_at", TS, nullable=False, server_default=func.now()),
)
users = Table(
    "users", metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()),
    Column("phone", Text, nullable=False, unique=True),
    Column("password_hash", Text, nullable=False),
    Column("foyer_id", UUID(as_uuid=True), ForeignKey("foyers.id"), nullable=False),
)
devices = Table(
    "devices", metadata,
    Column("foyer_id", UUID(as_uuid=True), ForeignKey("foyers.id"), nullable=False),
    Column("id", Text, nullable=False),
    Column("kind", Text, nullable=False),
    Column("name", Text, nullable=False),
    Column("essential", Boolean, nullable=False, server_default="false"),
    Column("last_state", JSONB, nullable=False, server_default="{}"),
    Column("schedule", JSONB, nullable=False, server_default='{"slots": []}'),
    PrimaryKeyConstraint("foyer_id", "id"),
)
meter_readings = Table(
    "meter_readings", metadata,
    Column("foyer_id", UUID(as_uuid=True), nullable=False),
    Column("ts", TS, nullable=False),
    Column("p_w", Float, nullable=False),
    Column("v", Float, nullable=False),
    Column("i_a", Float, nullable=False),
    Column("pf", Float, nullable=False),
    Column("e_kwh", Float, nullable=False),
    PrimaryKeyConstraint("foyer_id", "ts"),
)
plug_readings = Table(
    "plug_readings", metadata,
    Column("foyer_id", UUID(as_uuid=True), nullable=False),
    Column("device_id", Text, nullable=False),
    Column("ts", TS, nullable=False),
    Column("p_w", Float, nullable=False),
    Column("on", Boolean, nullable=False),
    PrimaryKeyConstraint("foyer_id", "device_id", "ts"),
)
appliances = Table(
    "appliances", metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("foyer_id", UUID(as_uuid=True), ForeignKey("foyers.id"), nullable=False),
    Column("label", Text),
    Column("delta_w", Float, nullable=False),
    Column("pf", Float, nullable=False),
    Column("n_obs", Integer, nullable=False),
    Column("device_id", Text),
    Column("essential", Boolean, nullable=False, server_default="false"),
)
activations = Table(
    "activations", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("foyer_id", UUID(as_uuid=True), nullable=False, index=True),
    Column("appliance_id", UUID(as_uuid=True), ForeignKey("appliances.id"), nullable=False),
    Column("start_ts", TS, nullable=False),
    Column("end_ts", TS),
    Column("delta_w", Float, nullable=False),
)
credit_entries = Table(
    "credit_entries", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("foyer_id", UUID(as_uuid=True), ForeignKey("foyers.id"), nullable=False),
    Column("ts", TS, nullable=False),
    Column("kind", Text, nullable=False),
    Column("kwh", Float, nullable=False),
    Column("amount_fcfa", Integer),
)
alerts = Table(
    "alerts", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("foyer_id", UUID(as_uuid=True), ForeignKey("foyers.id"), nullable=False),
    Column("ts", TS, nullable=False),
    Column("kind", Text, nullable=False),
    Column("message", Text, nullable=False),
    Column("read", Boolean, nullable=False, server_default="false"),
    Column("dedup_key", Text, nullable=False),
    UniqueConstraint("foyer_id", "dedup_key"),
)
push_tokens = Table(
    "push_tokens", metadata,
    Column("foyer_id", UUID(as_uuid=True), ForeignKey("foyers.id"), nullable=False),
    Column("token", Text, nullable=False),
    PrimaryKeyConstraint("foyer_id", "token"),
)
analysis_state = Table(
    "analysis_state", metadata,
    Column("foyer_id", UUID(as_uuid=True), ForeignKey("foyers.id"), primary_key=True),
    Column("last_ts", TS),
    Column("open_json", JSONB, nullable=False, server_default="[]"),
)
