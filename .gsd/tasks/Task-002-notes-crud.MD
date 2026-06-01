# Task 002 — Notes CRUD API

**Phase:** 2
**Spec reference:** `.gsd/specs/notes-crud.md`
**Depends on:** Task 001 (auth backend complete)
**Output:** Full notes REST API with list, create, get, update, delete, and search

---

## Context to load before starting
```
@.gsd/project.md
@.gsd/conventions.md
@.gsd/specs/notes-crud.md
```

---

## Step 1 — Note model (models/note.py)

Create `backend/app/models/note.py`:
- Import UUID from sqlalchemy.dialects.postgresql
- Import ARRAY, String, Text, Boolean, DateTime, ForeignKey from sqlalchemy
- id: UUID primary key, default uuid4
- user_id: UUID, ForeignKey("users.id"), indexed, nullable=False
  - Add cascade delete: ForeignKey("users.id", ondelete="CASCADE")
- title: VARCHAR(500), nullable=False
- content: TEXT, nullable=False
- summary: TEXT, nullable=True
- tags: ARRAY(String(50)), default=[], nullable=False
  - Use: mapped_column(ARRAY(String(50)), default=list, nullable=False)
- is_pinned: Boolean, default=False, nullable=False
- created_at: DateTime, default=datetime.utcnow, nullable=False
- updated_at: DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
- Add relationship to User: user = relationship("User", back_populates="notes")
- Add __tablename__ = "notes"

Also update models/user.py to add:
- notes = relationship("Note", back_populates="user", cascade="all, delete-orphan")

Update models/__init__.py to export both User and Note.

---

## Step 2 — Note schemas (schemas/note.py)

Create `backend/app/schemas/note.py` with these exact schemas:

**NoteCreateRequest:**
- title: str with Field(min_length=1, max_length=500)
- content: str with Field(min_length=1)
- tags: list[str] = Field(default_factory=list, max_length=10)
- is_pinned: bool = False
- Add field_validator for tags: each tag max 50 chars, strip whitespace

**NoteUpdateRequest:**
- title: str | None = None with Field(max_length=500)
- content: str | None = None
- tags: list[str] | None = None
- is_pinned: bool | None = None
- All fields optional — use model_config = ConfigDict(extra="ignore")

**NoteResponse:**
- id: UUID
- title: str
- content: str
- summary: str | None
- tags: list[str]
- is_pinned: bool
- created_at: datetime
- updated_at: datetime
- model_config = ConfigDict(from_attributes=True)

**PaginatedNotesResponse:**
- items: list[NoteResponse]
- total: int
- page: int
- page_size: int
- total_pages: int

---

## Step 3 — Note service (services/note_service.py)

Create `backend/app/services/note_service.py` with class `NoteService`:

**get_note_or_raise(db, note_id, user_id) → Note** (private helper)
- Fetch note by id
- If not found → raise HTTPException 404 "Note not found"
- If note.user_id != user_id → raise HTTPException 403 "Not authorised"
- Return note

**get_notes(db, user_id, page, page_size, pinned) → PaginatedNotesResponse**
- Build base query: select(Note).where(Note.user_id == user_id)
- If pinned is not None: add .where(Note.is_pinned == pinned)
- Count total with select(func.count()).select_from(subquery)
- Fetch paginated: .order_by(Note.is_pinned.desc(), Note.updated_at.desc()).offset().limit()
- Calculate total_pages with ceil(total / page_size)
- Return PaginatedNotesResponse

**create_note(db, user_id, payload: NoteCreateRequest) → Note**
- Create Note ORM object with all payload fields + user_id
- db.add(note), await db.flush(), await db.refresh(note)
- Return note

**get_note(db, note_id, user_id) → Note**
- Call get_note_or_raise and return result

**update_note(db, note_id, user_id, payload: NoteUpdateRequest) → Note**
- Call get_note_or_raise
- Use payload.model_dump(exclude_unset=True) to get only sent fields
- Loop over fields and setattr(note, field, value)
- await db.flush(), await db.refresh(note)
- Return note

**delete_note(db, note_id, user_id) → None**
- Call get_note_or_raise
- await db.delete(note)
- await db.flush()

**search_notes(db, user_id, q, page, page_size) → PaginatedNotesResponse**
- Use ilike for case insensitive search on both title and content
- Condition: or_(Note.title.ilike(f"%{q}%"), Note.content.ilike(f"%{q}%"))
- Add .where(Note.user_id == user_id) always
- Same pagination pattern as get_notes
- Order by updated_at descending

Add singleton at bottom: note_service = NoteService()

---

## Step 4 — Note routes (routes/notes.py)

Create `backend/app/routes/notes.py`:
- APIRouter(prefix="/notes", tags=["notes"])
- Import get_current_user from routes/auth.py
- All routes require current_user via Depends(get_current_user)

**GET /** → list notes
- Query params: page=1, page_size=20, pinned: bool | None = None
- Returns PaginatedNotesResponse

**POST /** → create note
- Body: NoteCreateRequest
- Returns NoteResponse, status 201

**GET /search** → search notes
- IMPORTANT: define this route BEFORE GET /{note_id}
- Query params: q (required), page=1, page_size=20
- Returns PaginatedNotesResponse

**GET /{note_id}** → get single note
- Returns NoteResponse

**PATCH /{note_id}** → update note
- Body: NoteUpdateRequest
- Returns NoteResponse

**DELETE /{note_id}** → delete note
- Returns Response with status 204
- Use: return Response(status_code=204)

---

## Step 5 — Register routes in main.py

Update `backend/app/main.py`:
- Import notes router: from app.routes import auth, notes
- Add: app.include_router(notes.router)

---

## Step 6 — Alembic migration

Run:
```bash
alembic revision --autogenerate -m "create notes table"
alembic upgrade head
```

Verify the migration file was created in alembic/versions/
Verify the notes table exists in the database after upgrade

---

## Step 7 — Smoke test via /docs

Open http://localhost:8000/docs and test in this order:

1. POST /auth/register — create a test user
2. POST /auth/login — login (sets cookie)
3. POST /notes — create a note with title, content, tags
4. GET /notes — should return paginated list with your note
5. GET /notes/{id} — get the note by ID from step 3
6. PATCH /notes/{id} — update the title
7. GET /notes/search?q=your_search_term — should return matching notes
8. DELETE /notes/{id} — delete the note
9. GET /notes — should return empty list

---

## Definition of done
- [ ] All 6 endpoints return correct status codes
- [ ] Pagination works correctly — total, total_pages calculated right
- [ ] PATCH only updates sent fields, leaves others unchanged
- [ ] DELETE returns 204 with no body
- [ ] Search is case insensitive and searches both title and content
- [ ] Ownership enforced — 403 when accessing another user's note
- [ ] GET /notes/search route defined BEFORE GET /{note_id}
- [ ] Alembic migration runs cleanly
- [ ] notes table visible in database