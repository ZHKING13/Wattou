# Déploiement Railway

Un projet Railway « wattou », environnement `production`, avec :

| Service | Dossier racine | Fichier de config | Variables |
|---|---|---|---|
| Postgres | (base gérée Railway) | — | — |
| mqtt | `/infra/mosquitto` | `/infra/railway/mqtt.json` | `MQTT_SERVER_PASSWORD`, `MQTT_DEVICE_PASSWORD` (générés) ; proxy TCP sur 1883 pour les vrais kits |
| api | `/server` | `/infra/railway/api.json` | communes ci-dessous ; domaine public HTTPS |
| ingest | `/server` | `/infra/railway/ingest.json` | communes |
| worker | `/server` | `/infra/railway/worker.json` | communes |
| simulateur (facultatif) | `/simulator` | `/infra/railway/simulateur.json` | `WATTOU_SIM_FOYER`, `MQTT_HOST=mqtt.railway.internal`, `MQTT_DEVICE_PASSWORD` |

Variables communes (api, ingest, worker) :

```
WATTOU_DATABASE_URL=${{Postgres.DATABASE_URL}}
WATTOU_MQTT_HOST=mqtt.railway.internal
WATTOU_MQTT_PASSWORD=${{mqtt.MQTT_SERVER_PASSWORD}}
WATTOU_JWT_SECRET=<64 caractères aléatoires>
TARIF_FCFA_KWH_DEFAUT=110
```

La base PostgreSQL de Railway n'a pas TimescaleDB : la migration le détecte et crée des tables
ordinaires (testé sur PostgreSQL 16 simple). Les migrations sont lancées au démarrage de l'API.

Les notifications push demandent en plus `WATTOU_EXPO_PUSH_ENABLED=true` et une clé FCM
enregistrée dans le projet EAS.
