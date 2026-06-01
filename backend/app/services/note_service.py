from math import ceil

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.note import Note
from app.schemas.note import NoteCreateRequest, NoteUpdateRequest, PaginatedNotesResponse, NoteResponse


class NoteService:
    @staticmethod
    async def _get_note_or_raise(db: AsyncSession, note_id: str, user_id: str) -> Note:
        result = await db.execute(select(Note).where(Note.id == note_id))
        note = result.scalar_one_or_none()
        if not note:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
        if note.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorised")
        return note

    @staticmethod
    async def get_notes(
        db: AsyncSession,
        user_id: str,
        page: int,
        page_size: int,
        pinned: bool | None = None,
    ) -> PaginatedNotesResponse:
        query = select(Note).where(Note.user_id == user_id)
        if pinned is not None:
            query = query.where(Note.is_pinned == pinned)

        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query)

        offset = (page - 1) * page_size
        notes_result = await db.execute(
            query.order_by(Note.is_pinned.desc(), Note.updated_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        notes = notes_result.scalars().all()

        total_pages = ceil(total / page_size)

        return PaginatedNotesResponse(
            items=[NoteResponse.model_validate(note) for note in notes],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @staticmethod
    async def create_note(
        db: AsyncSession,
        user_id: str,
        payload: NoteCreateRequest,
    ) -> Note:
        note = Note(
            user_id=user_id,
            title=payload.title,
            content=payload.content,
            tags=payload.tags,
            is_pinned=payload.is_pinned,
        )
        db.add(note)
        await db.flush()
        await db.refresh(note)
        return note

    @staticmethod
    async def get_note(db: AsyncSession, note_id: str, user_id: str) -> Note:
        return await NoteService._get_note_or_raise(db, note_id, user_id)

    @staticmethod
    async def update_note(
        db: AsyncSession,
        note_id: str,
        user_id: str,
        payload: NoteUpdateRequest,
    ) -> Note:
        note = await NoteService._get_note_or_raise(db, note_id, user_id)
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(note, field, value)
        await db.flush()
        await db.refresh(note)
        return note

    @staticmethod
    async def delete_note(db: AsyncSession, note_id: str, user_id: str) -> None:
        note = await NoteService._get_note_or_raise(db, note_id, user_id)
        await db.delete(note)
        await db.flush()

    @staticmethod
    async def search_notes(
        db: AsyncSession,
        user_id: str,
        q: str,
        page: int,
        page_size: int,
    ) -> PaginatedNotesResponse:
        from sqlalchemy import or_

        query = select(Note).where(
            Note.user_id == user_id,
            or_(Note.title.ilike(f"%{q}%"), Note.content.ilike(f"%{q}%")),
        )

        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query)

        offset = (page - 1) * page_size
        notes_result = await db.execute(
            query.order_by(Note.updated_at.desc()).offset(offset).limit(page_size)
        )
        notes = notes_result.scalars().all()

        total_pages = ceil(total / page_size)

        return PaginatedNotesResponse(
            items=[NoteResponse.model_validate(note) for note in notes],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


note_service = NoteService()
