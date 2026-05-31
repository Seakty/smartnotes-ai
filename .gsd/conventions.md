# SmartNotes AI — Conventions

> This file defines all naming, structure, and style rules for this project.
> The AI assistant must follow every rule here without exception.
> If a rule conflicts with a library's default, this file wins.

---

## General rules

- All code comments are in English
- No commented-out dead code — delete it, Git remembers it
- No magic numbers — use named constants or config values
- Prefer explicit over implicit — clarity beats cleverness
- Every function does ONE thing — if you need "and" to describe it, split it

---

## Python (backend)

### Naming

| Thing               | Convention            | Example                             |
| ------------------- | --------------------- | ----------------------------------- |
| Files / modules     | `snake_case`          | `note_service.py`                   |
| Classes             | `PascalCase`          | `NoteService`                       |
| Functions / methods | `snake_case`          | `get_note_by_id()`                  |
| Variables           | `snake_case`          | `current_user`                      |
| Constants           | `UPPER_SNAKE_CASE`    | `MAX_NOTE_LENGTH`                   |
| Pydantic schemas    | `PascalCase` + suffix | `NoteCreateRequest`, `NoteResponse` |
| SQLAlchemy models   | `PascalCase`          | `Note`, `User`                      |
| Route files         | `snake_case`          | `notes.py`, `auth.py`               |

### File structure rules

- **models/** — only SQLAlchemy table definitions, no logic
- **schemas/** — only Pydantic models for request/response validation
- **routes/** — only HTTP handling: parse request → call service → return response
- **services/** — all business logic lives here; services call models, never routes
- **database.py** — only DB session and connection setup

### FastAPI patterns

```python
# Route handler pattern — always this shape
@router.post("/notes", response_model=NoteResponse, status_code=201)
async def create_note(
    payload: NoteCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NoteResponse:
    return await note_service.create_note(db, current_user.id, payload)
```

- Routes are thin — one line of logic max, everything else in the service
- Always declare `response_model` on every route
- Use `Depends()` for DB sessions and auth — never instantiate manually in routes
- Use `status_code` explicitly on POST (201), DELETE (204)
- Group related routes in an `APIRouter` with a prefix: `router = APIRouter(prefix="/notes", tags=["notes"])`

### Error handling

```python
# Always raise HTTPException with a clear detail string
raise HTTPException(status_code=404, detail="Note not found")
raise HTTPException(status_code=403, detail="You do not own this note")
raise HTTPException(status_code=422, detail="Note content cannot be empty")
```

- Never let raw exceptions bubble up to the client
- Use 404 for not found, 403 for forbidden (not 401), 422 for validation failures beyond Pydantic

### Async rules

- All route handlers: `async def`
- All service functions that touch the DB: `async def`
- All DB queries use `await`
- Never use synchronous `session.query()` — always use `select()` with `await session.execute()`

### Imports order (enforced by isort)

1. Standard library
2. Third-party (fastapi, sqlalchemy, pydantic…)
3. Local app imports (`from app.models import…`)

---

## TypeScript / React (frontend)

### Naming

| Thing                 | Convention                                                            | Example                         |
| --------------------- | --------------------------------------------------------------------- | ------------------------------- |
| Files (components)    | `PascalCase.tsx`                                                      | `NoteCard.tsx`                  |
| Files (non-component) | `camelCase.ts`                                                        | `noteApi.ts`, `useNoteStore.ts` |
| React components      | `PascalCase`                                                          | `NoteCard`, `AISidebar`         |
| Hooks                 | `camelCase` + `use` prefix                                            | `useNoteStore`, `useAuth`       |
| Types / interfaces    | `PascalCase`                                                          | `Note`, `User`, `ApiError`      |
| Variables / functions | `camelCase`                                                           | `fetchNotes`, `currentUser`     |
| Constants             | `UPPER_SNAKE_CASE`                                                    | `API_BASE_URL`                  |
| CSS classes           | TailwindCSS utilities only — no custom class names unless unavoidable |

### Component structure (always in this order)

```tsx
// 1. Imports
import { useState } from "react";
import type { Note } from "@/types";

// 2. Type definitions local to this file
interface Props {
  note: Note;
  onDelete: (id: string) => void;
}

// 3. Component — named export, never default export for components
export function NoteCard({ note, onDelete }: Props) {
  // 4. Hooks first
  const [isExpanded, setIsExpanded] = useState(false);

  // 5. Derived values / handlers
  const handleDelete = () => onDelete(note.id);

  // 6. JSX return
  return <div className="...">...</div>;
}
```

- **No default exports** for components — named exports only
- **No inline anonymous functions** in JSX props — extract to a named handler
- **No `any` type** — ever. Use `unknown` and narrow it if needed
- Props interface defined in same file as the component, named `Props`

### API call pattern

```ts
// api/noteApi.ts
import { apiClient } from "./client";
import type { Note, NoteCreateRequest } from "@/types";

export const noteApi = {
  getAll: () => apiClient.get<Note[]>("/notes").then((r) => r.data),

  create: (payload: NoteCreateRequest) =>
    apiClient.post<Note>("/notes", payload).then((r) => r.data),

  delete: (id: string) => apiClient.delete(`/notes/${id}`),
};
```

- All API calls live in `src/api/` — never inline fetch/axios in a component
- Always type the response generic: `apiClient.get<Note[]>`

### State (Zustand)

```ts
// store/useNoteStore.ts
import { create } from "zustand";

interface NoteStore {
  notes: Note[];
  isLoading: boolean;
  fetchNotes: () => Promise<void>;
}

export const useNoteStore = create<NoteStore>((set) => ({
  notes: [],
  isLoading: false,
  fetchNotes: async () => {
    set({ isLoading: true });
    const notes = await noteApi.getAll();
    set({ notes, isLoading: false });
  },
}));
```

- One store file per domain: `useNoteStore.ts`, `useAuthStore.ts`
- Store files always named `use{Domain}Store.ts`

---

## Git conventions

### Branch naming

```
feature/phase-1-auth-backend
feature/phase-2-notes-crud
fix/jwt-expiry-bug
chore/update-dependencies
```

### Commit messages (Conventional Commits)

```
feat: add JWT authentication endpoint
feat(ai): integrate Claude summariser service
fix: resolve note ownership check in delete route
chore: add Docker configuration
docs: update README with setup instructions
test: add unit tests for note service
```

- Subject line max 72 characters
- Use imperative mood: "add" not "added" or "adds"
- Never commit `.env` files — ever

---

## Environment variables

### Backend `.env` pattern

```
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/smartnotes
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ANTHROPIC_API_KEY=sk-ant-...
ENVIRONMENT=development
```

### Frontend `.env` pattern

```
VITE_API_BASE_URL=http://localhost:8000
```

- All Vite env vars must be prefixed `VITE_`
- Backend reads env via `pydantic-settings` Settings class — never `os.environ` directly

---

## Testing conventions

- Test files: `test_{module_name}.py` in `backend/tests/`
- Test functions: `test_{what_it_does}_{expected_outcome}`
  - Example: `test_create_note_returns_201`
  - Example: `test_delete_note_returns_403_if_not_owner`
- Use `pytest` + `httpx.AsyncClient` for route tests
- Each test is independent — no shared mutable state between tests
