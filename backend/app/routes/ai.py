from fastapi import APIRouter, Depends

from app.database import get_db, get_redis
from app.models.user import User
from app.routes.auth import get_current_user
from app.schemas.note import NoteResponse
from app.services.ai_service import ai_service
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/summarise/{note_id}", response_model=NoteResponse)
async def summarise_note(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> NoteResponse:
    note = await ai_service.summarise_note(db, redis, note_id, current_user.id)
    return NoteResponse.model_validate(note)


@router.post("/suggest-tags/{note_id}", response_model=NoteResponse)
async def suggest_tags(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> NoteResponse:
    note = await ai_service.suggest_tags(db, redis, note_id, current_user.id)
    return NoteResponse.model_validate(note)
