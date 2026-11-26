#!/bin/sh
# Point d'entrée de l'image serveur : WATTOU_ROLE = api (défaut) | ingest | worker.
set -eu
case "${WATTOU_ROLE:-api}" in
  api)
    alembic upgrade head
    exec uvicorn wattou.api.app:create_app --factory --host :: --port "${PORT:-8000}" ;;
  ingest) exec python -m wattou.ingest ;;
  worker) exec python -m wattou.worker ;;
  *) echo "WATTOU_ROLE inconnu : ${WATTOU_ROLE}" >&2; exit 1 ;;
esac
