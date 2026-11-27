# Image « tout-en-un » pour Railway (contexte = racine du dépôt) :
# serveur (API, ingestion, analyse), Mosquitto et le simulateur pour la démo.
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends mosquitto \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv
WORKDIR /app
COPY server/pyproject.toml server/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY server/ .
RUN uv sync --frozen --no-dev
# le simulateur n'a besoin que de pydantic et aiomqtt, déjà présents dans l'environnement du serveur
COPY simulator/src/wattou_sim /app/simulateur/wattou_sim
ENV PATH="/app/.venv/bin:$PATH" PYTHONPATH="/app/simulateur"
CMD ["bash", "/app/demarrer.sh"]
