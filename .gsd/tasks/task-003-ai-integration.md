# Task 003 — AI Integration (OpenAI API)

**Phase:** 3
**Spec reference:** `.gsd/specs/ai-features.md`
**Depends on:** Task 001 (auth), Task 002 (notes CRUD)
**Output:** Two AI endpoints — summariser and smart tagger — powered by OpenAI API

---

## Context to load before starting

```
@.gsd/project.md
@.gsd/conventions.md
@.gsd/specs/ai-features.md
```

---

## Step 1 — Add Redis client to `database.py`

Update `backend/app/database.py`.

Add import:

```python
from redis.asyncio import Redis
```

Add after the existing SQLAlchemy setup:

```python
redis_client: Redis | None = None

async def get_redis() -> Redis:
    global redis_client
    if redis_client is None:
        redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    return redis_client
```

---

## Step 2 — Create AI service (`services/ai_service.py`)

Create `backend/app/services/ai_service.py`.

**Imports:**

```python
import json
from bs4 import BeautifulSoup
from openai import AsyncOpenAI
from fastapi import HTTPException
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.models.note import Note
from app.services.note_service import note_service
```

**OpenAI client:**

```python
openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
```

**Class `AIService` with these methods:**

### `_strip_html(html_content: str) -> str`

Use BeautifulSoup to safely strip all HTML tags and return plain text:

```python
return BeautifulSoup(html_content, "html.parser").get_text(separator=" ", strip=True)
```

### `_check_rate_limit(redis, user_id) -> None`

Use a Redis pipeline for atomicity — increment and set expiry in one transaction:

```python
key = f"rate:ai:{user_id}"
async with redis.pipeline(transaction=True) as pipe:
    pipe.incr(key)
    pipe.expire(key, 60, nx=True)
    results = await pipe.execute()
current = results[0]
if current > 10:
    raise HTTPException(429, "Rate limit exceeded. Try again in a minute.")
```

### `_check_content_length(plain_text: str) -> None`

```python
if len(plain_text) < 50:
    raise HTTPException(422, "Note content is too short to process")
```

### `summarise_note(db, redis, note_id, user_id) -> Note`

1. Call `note_service.get_note()` for ownership check
2. Call `_check_rate_limit(redis, user_id)`
3. Strip HTML: `plain_text = self._strip_html(note.content)`
4. Call `_check_content_length(plain_text)`
5. Call OpenAI API:

```python
response = await openai_client.chat.completions.create(
    model="gpt-4o-mini",
    max_tokens=512,
    messages=[
        {
            "role": "system",
            "content": (
                "You are a helpful assistant that summarises personal notes concisely. "
                "Write a summary in 2-3 sentences maximum. Focus on the key points and "
                "main ideas. Write in plain text — no markdown, no bullet points. "
                "Respond with only the summary, nothing else."
            ),
        },
        {"role": "user", "content": plain_text},
    ],
)
```

6. Extract summary: `summary = response.choices[0].message.content.strip()`
7. Set `note.summary = summary`
8. `await db.flush()`, `await db.refresh(note)`
9. Return `note`

### `suggest_tags(db, redis, note_id, user_id) -> Note`

1. Call `note_service.get_note()` for ownership check
2. Call `_check_rate_limit(redis, user_id)`
3. Strip HTML: `plain_text = self._strip_html(note.content)`
4. Call `_check_content_length(plain_text)`
5. Call OpenAI API with `response_format={"type": "json_object"}`:

```python
response = await openai_client.chat.completions.create(
    model="gpt-4o-mini",
    max_tokens=256,
    response_format={"type": "json_object"},
    messages=[
        {
            "role": "system",
            "content": (
                "You are a helpful assistant that suggests relevant tags for personal notes. "
                "Suggest between 3 and 5 short, lowercase tags. Tags should be single words "
                'or short hyphenated phrases. Respond with ONLY a JSON object containing a '
                'single key \'tags\' mapped to an array of strings. '
                'Example: {"tags": ["productivity", "work", "meeting-notes"]}. '
                "Do not include any other text or markdown."
            ),
        },
        {"role": "user", "content": f"Title: {note.title}\nContent: {plain_text}"},
    ],
)
```

6. Parse response safely:

```python
try:
    parsed_data = json.loads(response.choices[0].message.content)
    tags = parsed_data.get("tags", [])
    if not isinstance(tags, list):
        tags = []
    tags = [str(t).lower().strip() for t in tags if t][:5]
except json.JSONDecodeError:
    tags = []
```

7. Merge with existing tags (preserve order, deduplicate, cap at 10):

```python
merged = list(dict.fromkeys(note.tags + tags))[:10]
```

8. Set `note.tags = merged`
9. `await db.flush()`, `await db.refresh(note)`
10. Return `note`

**Singleton at module level:**

```python
ai_service = AIService()
```

---

## Step 3 — Create AI routes (`routes/ai.py`)

Create `backend/app/routes/ai.py`:

```python
from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, get_redis
from app.models.user import User
from app.routes.auth import get_current_user
from app.schemas.note import NoteResponse
from app.services.ai_service import ai_service

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/summarise/{note_id}", response_model=NoteResponse)
async def summarise_note(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> NoteResponse:
    note = await ai_service.summarise_note(db, redis, note_id, str(current_user.id))
    return NoteResponse.model_validate(note)


@router.post("/suggest-tags/{note_id}", response_model=NoteResponse)
async def suggest_tags(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> NoteResponse:
    note = await ai_service.suggest_tags(db, redis, note_id, str(current_user.id))
    return NoteResponse.model_validate(note)
```

---

## Step 4 — Register AI router in `main.py`

Update `backend/app/main.py`:

```python
from app.routes import auth, notes, ai

# ...

app.include_router(ai.router)
```

---

## Step 5 — Add `openai_api_key` to `.env`

Make sure `backend/.env` has a real OpenAI API key:

```
openai_api_key=sk-proj-your-real-key-here
```

Without this, the AI endpoints will crash on startup. Get a key from [platform.openai.com](https://platform.openai.com) if you don't have one.

Also verify that `beautifulsoup4` and `openai` are in your `requirements.txt` or `pyproject.toml`.

---

## Step 6 — Smoke test via `/docs`

Open `http://localhost:8000/docs` and run through these in order:

1. `POST /auth/login` — log in first to get a token
2. `POST /notes` — create a note with at least 50 chars of content
3. `POST /ai/summarise/{note_id}` — should return the note with `summary` filled
4. `POST /ai/suggest-tags/{note_id}` — should return the note with `tags` updated
5. `GET /notes/{note_id}` — verify `summary` and `tags` are persisted in the DB
6. **Rate limit test** — call summarise 11 times quickly; the 11th should return `429`

---

## Definition of done

- [ ] Summarise endpoint returns note with `summary` field filled
- [ ] Suggest tags endpoint returns note with `tags` field updated
- [ ] HTML is stripped using BeautifulSoup before sending to OpenAI
- [ ] Content shorter than 50 chars returns `422`
- [ ] Rate limit returns `429` after 10 requests per minute (enforced via Redis pipeline)
- [ ] Tags are parsed from a JSON object (`{"tags": [...]}`) not a bare array
- [ ] Tags are merged with existing tags, not replaced; capped at 10 total
- [ ] If OpenAI returns invalid JSON, endpoint defaults to empty array and does not crash
- [ ] AI router registered in `main.py`