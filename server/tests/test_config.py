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


def test_database_url_railway_normalisee(monkeypatch):
    """Railway fournit postgresql:// (ou postgres://) ; SQLAlchemy async veut postgresql+asyncpg://."""
    monkeypatch.setenv("WATTOU_MQTT_HOST", "x")
    monkeypatch.setenv("WATTOU_JWT_SECRET", "x")
    for brute in ("postgresql://u:p@h:5432/railway", "postgres://u:p@h:5432/railway"):
        monkeypatch.setenv("WATTOU_DATABASE_URL", brute)
        assert Settings().database_url == "postgresql+asyncpg://u:p@h:5432/railway"
    monkeypatch.setenv("WATTOU_DATABASE_URL", "postgresql+asyncpg://u:p@h/db")
    assert Settings().database_url == "postgresql+asyncpg://u:p@h/db"


def test_port_http_railway(monkeypatch):
    monkeypatch.setenv("WATTOU_DATABASE_URL", "x")
    monkeypatch.setenv("WATTOU_MQTT_HOST", "x")
    monkeypatch.setenv("WATTOU_JWT_SECRET", "x")
    monkeypatch.setenv("PORT", "4321")
    assert Settings().port == 4321
