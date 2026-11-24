from wattou.config import Settings


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("WATTOU_DATABASE_URL", "postgresql+asyncpg://u:p@h/db")
    monkeypatch.setenv("WATTOU_MQTT_HOST", "mqtt.local")
    monkeypatch.setenv("WATTOU_JWT_SECRET", "s3cret")
    monkeypatch.delenv("TARIF_FCFA_KWH_DEFAUT", raising=False)
    s = Settings()
    assert s.database_url == "postgresql+asyncpg://u:p@h/db"
    assert s.mqtt_host == "mqtt.local"
    assert s.mqtt_port == 1883
    assert s.jwt_secret == "s3cret"
    assert s.tarif_fcfa_kwh_defaut == 110.0
    assert s.worker_interval_s == 60


def test_tarif_override(monkeypatch):
    monkeypatch.setenv("WATTOU_DATABASE_URL", "x")
    monkeypatch.setenv("WATTOU_MQTT_HOST", "x")
    monkeypatch.setenv("WATTOU_JWT_SECRET", "x")
    monkeypatch.setenv("TARIF_FCFA_KWH_DEFAUT", "95.5")
    assert Settings().tarif_fcfa_kwh_defaut == 95.5
