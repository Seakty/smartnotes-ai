# Spec: Notes CRUD

## Overview
Authenticated users can create, read, update, delete, and search their own notes.
Every note belongs to exactly one user. Users can never see or modify other users' notes.
Notes support rich text content, tags, and a pinned flag.

---

## Endpoints

### GET /notes
**Purpose:** List all notes for the current user (paginated)

**Auth required:** Yes

**Query parameters:**
- `page` — integer, default 1, min 1
- `page_size` — integer, default 20, min 1, max 100
- `pinned` — optional boolean, filter by pinned status

**Success response: 200**
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "My note",
      "content": "<p>Rich text content</p>",
      "summary": null,
      "tags": ["work", "ideas"],
      "is_pinned": false,
      "created_at": "2025-01-01T00:00:00Z",
      "updated_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20,
  "total_pages": 3
}
```

**Ordering:** pinned notes first, then by `updated_at` descending

---

### POST /notes
**Purpose:** Create a new note

**Auth required:** Yes

**Request body:**
```json
{
  "title": "My note",
  "content": "<p>Rich text content</p>",
  "tags": ["work", "ideas"],
  "is_pinned": false
}
```

**Validation rules:**
- `title` — required, min 1 char, max 500 chars
- `content` — required, min 1 char, no max (rich text HTML)
- `tags` — optional, default empty list, max 10 tags, each tag max 50 chars
- `is_pinned` — optional, default false

**Success response: 201**
```json
{
  "id": "uuid",
  "title": "My note",
  "content": "<p>Rich text content</p>",
  "summary": null,
  "tags": ["work", "ideas"],
  "is_pinned": false,
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

---

### GET /notes/{note_id}
**Purpose:** Get a single note by ID

**Auth required:** Yes

**Success response: 200** — same shape as single item above

**Error cases:**
- 404 — note not found
- 403 — note exists but belongs to another user

---

### PATCH /notes/{note_id}
**Purpose:** Partially update a note

**Auth required:** Yes

**Request body:** all fields optional
```json
{
  "title": "Updated title",
  "content": "<p>Updated content</p>",
  "tags": ["updated"],
  "is_pinned": true
}
```

**Rules:**
- Only update fields that are present in the request body
- `updated_at` must be refreshed automatically on every update
- User can only update their own notes

**Success response: 200** — full updated note

**Error cases:**
- 404 — note not found
- 403 — note belongs to another user

---

### DELETE /notes/{note_id}
**Purpose:** Delete a note permanently

**Auth required:** Yes

**Success response: 204** — no body

**Error cases:**
- 404 — note not found
- 403 — note belongs to another user

---

### GET /notes/search
**Purpose:** Full-text search across title and content

**Auth required:** Yes

**Query parameters:**
- `q` — required, search query string, min 1 char
- `page` — integer, default 1
- `page_size` — integer, default 20, max 100

**Success response: 200** — same paginated shape as GET /notes

**Search behaviour:**
- Case insensitive
- Searches both title and content fields
- Results ordered by relevance (most recent match first)
- Only searches the current user's notes

---

## Data model

### Note (SQLAlchemy model)
```
id          UUID, primary key, default uuid4
user_id     UUID, foreign key → users.id, indexed, CASCADE DELETE, not null
title       VARCHAR(500), not null
content     TEXT, not null
summary     TEXT, nullable (filled by AI in Phase 3)
tags        ARRAY(VARCHAR(50)), default empty array, not null
is_pinned   BOOLEAN, default false, not null
created_at  TIMESTAMP, default now(), not null
updated_at  TIMESTAMP, default now(), auto-updated, not null
```

**Relationships:**
- `Note.user_id` → `User.id` (many notes to one user)
- When a user is deleted, all their notes are deleted (CASCADE)

---

## Schemas

### NoteCreateRequest
- title: str (min 1, max 500)
- content: str (min 1)
- tags: list[str] = [] (max 10 items, each max 50 chars)
- is_pinned: bool = False

### NoteUpdateRequest
- title: str | None = None
- content: str | None = None
- tags: list[str] | None = None
- is_pinned: bool | None = None

### NoteResponse
- id: UUID
- title: str
- content: str
- summary: str | None
- tags: list[str]
- is_pinned: bool
- created_at: datetime
- updated_at: datetime
- model_config from_attributes = True

### PaginatedNotesResponse
- items: list[NoteResponse]
- total: int
- page: int
- page_size: int
- total_pages: int

---

## Service layer rules

### Ownership check pattern
Every service method that fetches a note must:
1. Fetch the note by ID first
2. If not found → raise 404
3. If found but `note.user_id != current_user.id` → raise 403
4. Never combine steps 2 and 3 into one query — always check existence first

### Update pattern (PATCH)
Use `model_dump(exclude_unset=True)` on the request payload to get only
the fields the client actually sent. Loop over those fields and set them
on the ORM object. Never overwrite fields the client didn't include.

### Pagination pattern
```python
offset = (page - 1) * page_size
total = await db.scalar(select(func.count()).where(Note.user_id == user_id))
notes = await db.execute(
    select(Note)
    .where(Note.user_id == user_id)
    .order_by(Note.is_pinned.desc(), Note.updated_at.desc())
    .offset(offset)
    .limit(page_size)
)
total_pages = ceil(total / page_size)
```

---

## Security rules
- Every route requires `get_current_user` dependency
- Ownership enforced at service layer — never trust the client to send the right user_id
- Search only queries notes where `user_id = current_user.id`
- Tags are stored and returned as-is — no server-side normalisation needed