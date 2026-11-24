from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from .. import repo
from .deps import current_foyer, get_session

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("")
async def list_alerts(unread: bool = False, foyer: UUID = Depends(current_foyer),
                      s: AsyncSession = Depends(get_session)):
    return [{k: a[k] for k in ("id", "ts", "kind", "message", "read")}
            for a in await repo.list_alerts(s, foyer, unread)]


@router.post("/{alert_id}/read")
async def read(alert_id: int, foyer: UUID = Depends(current_foyer),
               s: AsyncSession = Depends(get_session)):
    if not await repo.mark_alert_read(s, foyer, alert_id):
        raise HTTPException(404, "Alerte introuvable.")
    await s.commit()
    return {"ok": True}
