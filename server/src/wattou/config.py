from functools import lru_cache

from pydantic import AliasChoices, Field
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
