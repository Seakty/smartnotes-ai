# Spec: AI Features

## Overview
Two AI-powered features built on top of the notes system:
1. **Summariser** — generates a concise summary of a note's content
2. **Smart Tagger** — suggests up to 5 relevant tags for a note

Both features call the OPENAI API from the backend.
Both are triggered manually by the user — never automatically.
Both update the note in the database and return the updated note.

---

## Endpoints

### POST /ai/summarise/{note_id}
**Purpose:** Generate a summary of a note using OPENAI and save it

**Auth required:** Yes

**Path parameter:**
- `note_id` — UUID of the note to summarise

**Request body:** none

**Success response: 200**
```json
{
  "id": "uuid",
  "title": "My note",
  "content": "<p>Rich text content</p>",
  "summary": "A concise 2-3 sentence summary of the note.",
  "tags": ["work"],
  "is_pinned": false,
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

**Error cases:**
- 404 — note not found
- 403 — note belongs to another user
- 422 — note content is empty or too short (less than 50 chars)
- 429 — rate limit exceeded (max 10 AI requests per user per minute)

---

### POST /ai/suggest-tags/{note_id}
**Purpose:** Suggest relevant tags for a note using OPENAI and save them

**Auth required:** Yes

**Path parameter:**
- `note_id` — UUID of the note to tag

**Request body:** none

**Success response: 200** — same NoteResponse shape as above
- `tags` field will be updated with suggested tags merged with existing tags

**Error cases:**
- 404 — note not found
- 403 — note belongs to another user
- 422 — note content is empty or too short (less than 50 chars)
- 429 — rate limit exceeded (max 10 AI requests per user per minute)

---

## OPENAI API integration

### Model
Always use: `gpt-4o-mini`

### Summariser prompt
```
System: You are a helpful assistant that summarises personal notes concisely.
        Write a summary in 2-3 sentences maximum.
        Focus on the key points and main ideas.
        Write in plain text — no markdown, no bullet points.
        Respond with only the summary, nothing else.

User: [note content with HTML tags stripped]
```

### Smart tagger prompt
```
System: You are a helpful assistant that suggests relevant tags for personal notes.
        Suggest between 3 and 5 short, lowercase tags.
        Tags should be single words or short hyphenated phrases.
        Respond with ONLY a JSON object containing a single key "tags" mapped to an array of strings.
        Example response: {"tags": ["productivity", "work", "meeting-notes"]}
        Do not include any other text, explanation, or markdown.

User: Title: [note title]
      Content: [note content with HTML tags stripped]
```

### HTML stripping
Note content is stored as rich text HTML from TipTap.
Before sending to OPENAI, strip all HTML tags to plain text.
Use Python's built-in `html.parser` via `BeautifulSoup` or simple regex.
Simple regex approach:
```python
import re
plain_text = re.sub(r'<[^>]+>', '', html_content).strip()
```

---

## Rate limiting

Use Redis to enforce per-user rate limits on AI endpoints.

### Pattern
```python
key = f"rate:ai:{user_id}"

async with redis.pipeline(transaction=True) as pipe:
    pipe.incr(key)
    pipe.expire(key, 60, nx=True)  
    results = await pipe.execute()

current = results[0]

if current > 10:
    raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again in a minute.")
```

### Redis connection
Create a Redis client in `app/database.py`:
```python
from redis.asyncio import Redis

redis_client: Redis | None = None

async def get_redis() -> Redis:
    global redis_client
    if redis_client is None:
        redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    return redis_client
```

---

## Service layer rules

### AI service pattern
```python
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=settings.openai_api_key)

response = await client.chat.completions.create(
    model="gpt-4o-mini",
    max_tokens=512,
    messages=[
        {"role": "system", "content": "You are a helpful assistant..."}, 
        {"role": "user", "content": plain_text}
    ],
    response_format={ "type": "json_object" }
)
```

### Tag parsing
OpenAI is prompted to return a JSON object. Ensure the response_format is forced to JSON in the API call for the tagger:
```python
import json

try:
    parsed_data = json.loads(response_text)
    tags = parsed_data.get("tags", [])
    if not isinstance(tags, list):
        tags = []
    tags = [str(t).lower().strip() for t in tags if t][:5]
    
except json.JSONDecodeError:
    tags = []
```

### Merging tags
When saving suggested tags — merge with existing tags, deduplicate:
```python
merged = list(dict.fromkeys(note.tags + suggested_tags))[:10]
```

### Minimum content check
Before calling OPENAI, check stripped plain text length:
```python
if len(plain_text) < 50:
    raise HTTPException(status_code=422, detail="Note content is too short to process")
```

---

## File structure additions
```
backend/app/
├── services/
│   └── ai_service.py     ← new
└── routes/
    └── ai.py             ← new
```

---

## Security rules
- Rate limit ALL AI endpoints per user via Redis
- Never expose the OpenAI API key in responses or logs
- Always verify note ownership before calling OPENAI
- Strip HTML before sending to OPENAI — never send raw HTML
- If OPENAI returns unexpected output, fail gracefully — don't crash