"""Envoi des notifications push (Expo) ; LogNotifier pour le développement."""

import logging
from typing import Protocol

import httpx

log = logging.getLogger("wattou.notify")
EXPO_URL = "https://exp.host/--/api/v2/push/send"


class Notifier(Protocol):
    async def send(self, tokens: list[str], title: str, body: str) -> None: ...


class LogNotifier:
    def __init__(self):
        self.sent: list[tuple[list[str], str, str]] = []

    async def send(self, tokens: list[str], title: str, body: str) -> None:
        self.sent.append((tokens, title, body))
        log.info("push %s: %s — %s", tokens, title, body)


class ExpoNotifier:
    def __init__(self, client: httpx.AsyncClient | None = None):
        self.client = client or httpx.AsyncClient(timeout=10)

    async def send(self, tokens: list[str], title: str, body: str) -> None:
        if not tokens:
            return
        # canal Android « alertes » créé par l'app (importance haute : son + bannière)
        msgs = [{"to": t, "title": title, "body": body, "sound": "default", "channelId": "alertes",
                 "priority": "high"} for t in tokens]
        try:
            r = await self.client.post(EXPO_URL, json=msgs)
            r.raise_for_status()
        except httpx.HTTPError as e:
            log.warning("échec de l'envoi push: %s", e)
