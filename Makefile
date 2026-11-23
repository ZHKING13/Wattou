COMPOSE = docker compose -f infra/docker-compose.yml

up:
	docker run --rm -v $(CURDIR)/infra/mosquitto:/m eclipse-mosquitto:2 sh -c 'chown 1883:1883 /m/passwd && chmod 0700 /m/passwd'
	$(COMPOSE) up -d --wait db mqtt

down:
	$(COMPOSE) down

test:
	cd server && uv run pytest -q
	cd simulator && uv run pytest -q

lint:
	cd server && uv run ruff check .
	cd simulator && uv run ruff check .

.PHONY: up down test lint
