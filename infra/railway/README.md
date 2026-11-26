# Déploiement Railway

## Déploiement actuel (offre gratuite) : un seul service

L'offre gratuite limite le nombre de services. Le projet `wattou` contient donc :

- **Postgres** (base gérée Railway) ;
- **wattou** (dossier `/server`) avec `WATTOU_ROLE=tout` : Mosquitto, ingestion, analyse et API dans
  le même conteneur. Variables : `WATTOU_ROLE=tout`, `WATTOU_DATABASE_URL=${{Postgres.DATABASE_URL}}`,
  `WATTOU_JWT_SECRET`, `MQTT_SERVER_PASSWORD`, `MQTT_DEVICE_PASSWORD` (aléatoires), `TARIF_FCFA_KWH_DEFAUT=110`.
  Domaine public HTTPS pour l'API ; un proxy TCP sur 1883 sera nécessaire pour les vrais kits.

## Déploiement séparé (offre payante)

Un projet Railway « wattou », environnement `production`, avec :

| Service | Dossier racine | Fichier de config | Variables |
|---|---|---|---|
| Postgres | (base gérée Railway) | — | — |
| mqtt | `/infra/mosquitto` | `infra/mosquitto/railway.json` | `MQTT_SERVER_PASSWORD`, `MQTT_DEVICE_PASSWORD` (générés) ; proxy TCP sur 1883 pour les vrais kits |
| api | `/server` | — | communes + `WATTOU_ROLE=api` ; domaine public HTTPS |
| ingest | `/server` | — | communes + `WATTOU_ROLE=ingest` |
| worker | `/server` | — | communes + `WATTOU_ROLE=worker` |
| simulateur (facultatif) | `/simulator` | `simulator/railway.json` | `WATTOU_SIM_FOYER`, `MQTT_HOST=mqtt.railway.internal`, `MQTT_DEVICE_PASSWORD` |

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
