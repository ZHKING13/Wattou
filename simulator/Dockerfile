FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY . .
RUN uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:$PATH"
# Simule un ménage en temps réel (vitesse 1) pour le foyer WATTOU_SIM_FOYER.
CMD ["sh", "-c", "python -m wattou_sim --foyer \"$WATTOU_SIM_FOYER\" --host \"$MQTT_HOST\" --port \"${MQTT_PORT:-1883}\" --user device --password \"$MQTT_DEVICE_PASSWORD\" --backfill-days \"${WATTOU_SIM_BACKFILL_DAYS:-0}\" --start \"$(date -u -d \"-${WATTOU_SIM_BACKFILL_DAYS:-0} days\" +%Y-%m-%dT%H:%M:%SZ)\""]
