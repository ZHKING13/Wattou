from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from ..control import Publisher
from ..db import sessionmaker
from .auth import foyer_from_token

_bearer = HTTPBearer(auto_error=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with sessionmaker()() as s:
        yield s


def get_publisher(request: Request) -> Publisher:
    pub = getattr(request.app.state, "publisher", None)
    if pub is None:
        raise HTTPException(503, "Pilotage indisponible : serveur MQTT non connecté.")
    return pub


async def current_foyer(cred: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> UUID:
    foyer = foyer_from_token(cred.credentials) if cred else None
    if foyer is None:
        raise HTTPException(401, "Connexion requise.")
    return foyer
