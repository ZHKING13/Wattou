from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .. import repo
from .auth import hash_password, make_token, verify_password
from .deps import get_session
from .schemas import Login, Register, TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201, response_model=TokenOut)
async def register(body: Register, s: AsyncSession = Depends(get_session)):
    if await repo.get_user_by_phone(s, body.phone):
        raise HTTPException(409, "Ce numéro a déjà un compte.")
    foyer = await repo.create_foyer(s, body.foyer_name)
    try:
        user = await repo.create_user(s, body.phone, hash_password(body.password), foyer)
    except IntegrityError as e:
        raise HTTPException(409, "Ce numéro a déjà un compte.") from e
    await s.commit()
    return TokenOut(token=make_token(user, foyer), foyer_id=str(foyer))


@router.post("/login", response_model=TokenOut)
async def login(body: Login, s: AsyncSession = Depends(get_session)):
    u = await repo.get_user_by_phone(s, body.phone)
    if not u or not verify_password(u["password_hash"], body.password):
        raise HTTPException(401, "Numéro ou mot de passe incorrect.")
    return TokenOut(token=make_token(u["id"], u["foyer_id"]), foyer_id=str(u["foyer_id"]))
