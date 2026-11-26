FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY . .
RUN uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:$PATH"
# Par défaut : l'API (migrations puis serveur HTTP sur $PORT, fourni par Railway).
# Les services « ingest » et « worker » remplacent cette commande (infra/railway/*.json).
CMD ["sh", "-c", "alembic upgrade head && uvicorn wattou.api.app:create_app --factory --host 0.0.0.0 --port ${PORT:-8000}"]
