FROM python:3.12-slim
# Mosquitto : utilisé seulement avec WATTOU_ROLE=tout (un seul service pour tout le serveur)
RUN apt-get update && apt-get install -y --no-install-recommends mosquitto \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY . .
RUN uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:$PATH"
# Rôle choisi par WATTOU_ROLE (api, ingest, worker) : voir demarrer.sh.
CMD ["bash", "/app/demarrer.sh"]
