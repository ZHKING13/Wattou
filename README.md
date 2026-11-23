# Wattou

POC de suivi et de pilotage de la consommation électrique des ménages ivoiriens.
Conception : `docs/superpowers/specs/2026-11-23-wattou-poc-design.md`.

## Démarrage

Prérequis : Docker, [uv](https://docs.astral.sh/uv/).

```bash
make up      # PostgreSQL/TimescaleDB + Mosquitto
make test    # tests serveur et simulateur
```

Utilisateurs MQTT de développement : `server`/`server` et `device`/`device`.
