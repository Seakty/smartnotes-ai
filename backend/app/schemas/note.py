from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NoteCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list, max_length=10)
    is_pinned: bool = False

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        validated = []
        for tag in v:
            if len(tag) > 50:
                raise ValueError("Each tag must be at most 50 characters")
            validated.append(tag.strip())
        return validated


class NoteUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str | None = Field(None, max_length=500)
    content: str | None = None
    tags: list[str] | None = None
    is_pinned: bool | None = None


class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    content: str
    summary: str | None
    tags: list[str]
    is_pinned: bool
    created_at: datetime
    updated_at: datetime


class PaginatedNotesResponse(BaseModel):
    items: list[NoteResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
