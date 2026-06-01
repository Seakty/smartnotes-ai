from fastapi import APIRouter, Depends, Query, Response, status

from app.database import get_db
from app.models.user import User
from app.routes.auth import get_current_user
from app.schemas.note import NoteCreateRequest, NoteResponse, NoteUpdateRequest, PaginatedNotesResponse
from app.services.note_service import note_service
from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("", response_model=PaginatedNotesResponse)
async def list_notes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    pinned: bool | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedNotesResponse:
    return await note_service.get_notes(db, current_user.id, page, page_size, pinned)


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    payload: NoteCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NoteResponse:
    note = await note_service.create_note(db, current_user.id, payload)
    return NoteResponse.model_validate(note)


@router.get("/search", response_model=PaginatedNotesResponse)
async def search_notes(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedNotesResponse:
    return await note_service.search_notes(db, current_user.id, q, page, page_size)


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NoteResponse:
    note = await note_service.get_note(db, note_id, current_user.id)
    return NoteResponse.model_validate(note)


@router.patch("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: str,
    payload: NoteUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NoteResponse:
    note = await note_service.update_note(db, note_id, current_user.id, payload)
    return NoteResponse.model_validate(note)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await note_service.delete_note(db, note_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
