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

## Lancer la démo sur données simulées

```bash
make app     # + API (port 8000), ingestion et analyse dans Docker
curl -s -X POST localhost:8000/api/v1/auth/register -H 'content-type: application/json' \
  -d '{"phone":"+2250700000000","password":"secret1","foyer_name":"Démo"}'
cd simulator && uv run python -m wattou_sim --foyer <foyer_id> --backfill-days 7 --speed 60
```

`--scenario neighbor_tap@<début>/<fin>`, `fridge_stuck@<début>`, `outage@…/…`, `netcut@…/…`
injectent un branchement sauvage, un frigo bloqué, un délestage ou une coupure internet.

## Test d'acceptation

`make e2e` rejoue 14 jours simulés à travers MQTT, l'ingestion, l'analyse et l'API, et vérifie
les critères de réussite de la spec (≈ 15 min).

## Application mobile

Voir [`mobile/README.md`](mobile/README.md). `make mobile-test` lance ses tests ;
`make mobile-integration` vérifie le client contre l'API réelle.
