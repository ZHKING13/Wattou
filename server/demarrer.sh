#!/bin/bash
# Point d'entrée de l'image serveur : WATTOU_ROLE = api (défaut) | ingest | worker | tout.
# « tout » (hébergement à un seul service, ex. offre gratuite Railway) : Mosquitto, ingestion,
# analyse et API dans le même conteneur ; si l'un s'arrête, le conteneur s'arrête et redémarre.
set -euo pipefail

lancer_mosquitto() {
  : "${MQTT_SERVER_PASSWORD:?MQTT_SERVER_PASSWORD manquant}"
  : "${MQTT_DEVICE_PASSWORD:?MQTT_DEVICE_PASSWORD manquant}"
  mkdir -p /tmp/mosquitto
  rm -f /tmp/mosquitto/passwd
  touch /tmp/mosquitto/passwd && chmod 0600 /tmp/mosquitto/passwd
  mosquitto_passwd -b /tmp/mosquitto/passwd server "$MQTT_SERVER_PASSWORD"
  mosquitto_passwd -b /tmp/mosquitto/passwd device "$MQTT_DEVICE_PASSWORD"
  cat > /tmp/mosquitto/mosquitto.conf <<CONF
listener 1883
allow_anonymous false
password_file /tmp/mosquitto/passwd
persistence false
max_queued_messages 0
max_inflight_messages 0
CONF
  # Mosquitto abandonne root pour l'utilisateur « mosquitto » : il doit pouvoir lire ses fichiers
  chown -R mosquitto:mosquitto /tmp/mosquitto
  mosquitto -c /tmp/mosquitto/mosquitto.conf &
}

api() {
  alembic upgrade head
  exec uvicorn wattou.api.app:create_app --factory --host 0.0.0.0 --port "${PORT:-8000}"
}

case "${WATTOU_ROLE:-api}" in
  api) api ;;
  ingest) exec python -m wattou.ingest ;;
  worker) exec python -m wattou.worker ;;
  tout)
    export WATTOU_MQTT_HOST=127.0.0.1 WATTOU_MQTT_USER=server WATTOU_MQTT_PASSWORD="$MQTT_SERVER_PASSWORD"
    lancer_mosquitto
    alembic upgrade head
    sleep 1
    python -m wattou.ingest &
    python -m wattou.worker &
    uvicorn wattou.api.app:create_app --factory --host 0.0.0.0 --port "${PORT:-8000}" &
    wait -n
    echo "un processus s'est arrêté : redémarrage du conteneur" >&2
    exit 1 ;;
  *) echo "WATTOU_ROLE inconnu : ${WATTOU_ROLE}" >&2; exit 1 ;;
esac
