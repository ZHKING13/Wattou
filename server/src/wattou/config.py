from functools import lru_cache

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WATTOU_", extra="ignore")

    database_url: str
    mqtt_host: str
    mqtt_port: int = 1883
    mqtt_user: str = "server"
    mqtt_password: str = "server"
    jwt_secret: str
    tarif_fcfa_kwh_defaut: float = Field(
        default=110.0, validation_alias=AliasChoices("TARIF_FCFA_KWH_DEFAUT")
    )
    expo_push_enabled: bool = False
    # port HTTP de l'API : Railway le fournit dans PORT
    port: int = Field(default=8000, validation_alias=AliasChoices("PORT", "WATTOU_PORT"))
    worker_interval_s: float = 60
    # rejette les mesures datées de plus de N h dans le futur (horloge murale). 0 = désactivé,
    # nécessaire pour le simulateur accéléré ; à activer en phase 2 avec le vrai kit.
    max_future_h: float = 0


    @field_validator("database_url")
    @classmethod
    def _pilote_async(cls, v: str) -> str:
        """Railway (et la plupart des hébergeurs) donnent postgresql:// : on force le pilote asyncpg."""
        for prefixe in ("postgresql://", "postgres://"):
            if v.startswith(prefixe):
                return "postgresql+asyncpg://" + v[len(prefixe):]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
