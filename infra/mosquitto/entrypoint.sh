#!/bin/sh
set -eu
: "${MQTT_SERVER_PASSWORD:?MQTT_SERVER_PASSWORD manquant}"
: "${MQTT_DEVICE_PASSWORD:?MQTT_DEVICE_PASSWORD manquant}"
mkdir -p /mosquitto/data
rm -f /mosquitto/data/passwd
touch /mosquitto/data/passwd
chmod 0700 /mosquitto/data/passwd
mosquitto_passwd -b /mosquitto/data/passwd server "$MQTT_SERVER_PASSWORD"
mosquitto_passwd -b /mosquitto/data/passwd device "$MQTT_DEVICE_PASSWORD"
chown -R mosquitto:mosquitto /mosquitto/data
exec mosquitto -c /mosquitto/config/mosquitto.conf
