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

# Démo : WATTOU_SIM_CIBLE = « dernier » (dernier foyer créé) ou un numéro +225… Le simulateur reprend
# à la dernière mesure du foyer (ou WATTOU_SIM_JOURS jours en arrière, 3 par défaut, s'il n'en a
# aucune), comble le trou en accéléré, puis continue en temps réel.
lancer_simulateur() {
  [ -n "${WATTOU_SIM_CIBLE:-}" ] || return 0
  local cible foyer derniere debut jours
  cible=$(python -m wattou.demo "$WATTOU_SIM_CIBLE" || true)
  if [ -z "$cible" ]; then
    echo "simulateur : aucun foyer pour « $WATTOU_SIM_CIBLE », pas de simulation" >&2
    return 0
  fi
  read -r foyer derniere <<< "$cible"
  if [ "$derniere" = "-" ]; then
    debut=$(date -u -d "-${WATTOU_SIM_JOURS:-3} days" +%Y-%m-%dT%H:%M:%SZ)
  else
    debut=$(date -u -d "$derniere + 1 second" +%Y-%m-%dT%H:%M:%SZ)
  fi
  jours=$(python -c "from datetime import datetime,timezone as t;import sys;d=datetime.fromisoformat(sys.argv[1].replace('Z','+00:00'));print(max(0,(datetime.now(t.utc)-d).total_seconds()/86400))" "$debut")
  echo "simulateur : foyer $foyer, reprise à $debut ($jours jour(s) à combler) puis temps réel"
  python -m wattou_sim --foyer "$foyer" --host 127.0.0.1 --user device --password "$MQTT_DEVICE_PASSWORD" \
    --start "$debut" --backfill-days "$jours" --speed 1 &
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
    lancer_simulateur
    uvicorn wattou.api.app:create_app --factory --host 0.0.0.0 --port "${PORT:-8000}" &
    wait -n
    echo "un processus s'est arrêté : redémarrage du conteneur" >&2
    exit 1 ;;
  *) echo "WATTOU_ROLE inconnu : ${WATTOU_ROLE}" >&2; exit 1 ;;
esac
