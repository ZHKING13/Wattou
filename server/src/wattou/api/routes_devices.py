from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from .. import repo
from ..contract import AcCmd, PlugCmd, Schedule
from ..control import Publisher, send_command, set_schedule
from .deps import current_foyer, get_publisher, get_session

router = APIRouter(prefix="/devices", tags=["devices"])
CMD = {"plug": PlugCmd, "ir_ac": AcCmd}


async def _device(s: AsyncSession, foyer: UUID, device_id: str) -> dict:
    d = await repo.get_device(s, foyer, device_id)
    if d is None:
        raise HTTPException(404, "Appareil introuvable.")
    return d


@router.get("")
async def list_devices(foyer: UUID = Depends(current_foyer), s: AsyncSession = Depends(get_session)):
    return [{k: d[k] for k in ("id", "kind", "name", "essential", "last_state", "schedule")}
            for d in await repo.list_devices(s, foyer)]


@router.post("/{device_id}/command", status_code=202)
async def command(device_id: str, body: dict = Body(...), foyer: UUID = Depends(current_foyer),
                  s: AsyncSession = Depends(get_session), pub: Publisher = Depends(get_publisher)):
    d = await _device(s, foyer, device_id)
    model = CMD.get(d["kind"])
    if model is None:
        raise HTTPException(422, "Cet appareil ne se pilote pas.")
    try:
        cmd = model(**body)
    except ValidationError as e:
        raise HTTPException(422, "Commande invalide pour cet appareil.") from e
    await send_command(pub, foyer, device_id, cmd)
    return {"ok": True}


@router.get("/{device_id}/schedule", response_model=Schedule)
async def get_schedule(device_id: str, foyer: UUID = Depends(current_foyer),
                       s: AsyncSession = Depends(get_session)):
    return Schedule(**(await _device(s, foyer, device_id))["schedule"])


@router.put("/{device_id}/schedule", response_model=Schedule)
async def put_schedule(device_id: str, body: Schedule, foyer: UUID = Depends(current_foyer),
                       s: AsyncSession = Depends(get_session), pub: Publisher = Depends(get_publisher)):
    d = await _device(s, foyer, device_id)
    model = CMD.get(d["kind"])
    if model is None:
        raise HTTPException(422, "Cet appareil ne se programme pas.")
    for slot in body.slots:
        try:
            model(**slot.action)
        except ValidationError as e:
            raise HTTPException(422, f"Action invalide à {slot.at}.") from e
    await repo.set_schedule(s, foyer, device_id, body.model_dump())
    await set_schedule(pub, foyer, device_id, body)
    await s.commit()
    return body
