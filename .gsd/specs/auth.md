# Spec: Authentication

## Overview

Users can register an account, log in, and log out.
Authentication uses JWT stored in an httpOnly cookie.
All protected routes require a valid JWT to proceed.

---

## Endpoints

### POST /auth/register

**Purpose:** Create a new user account

**Request body:**

```json
{
  "email": "user@example.com",
  "password": "StrongPass123",
  "full_name": "John Doe"
}
```

**Validation rules:**

- `email` — valid email format, max 255 chars, must be unique in DB
- `password` — min 8 chars, at least one uppercase, one number
- `full_name` — min 2 chars, max 255 chars, required

**Success response: 201**

```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "created_at": "2025-01-01T00:00:00Z"
}
```

**Error cases:**

- 422 — validation failure (Pydantic handles this automatically)
- 409 — email already registered

---

### POST /auth/login

**Purpose:** Authenticate a user and set JWT cookie

**Request body:**

```json
{
  "email": "user@example.com",
  "password": "StrongPass123"
}
```

**Success response: 200**

```json
{
  "message": "Login successful",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "John Doe"
  }
}
```

Sets cookie: `access_token` — httpOnly, Secure (prod only), SameSite=Lax, max_age = ACCESS_TOKEN_EXPIRE_MINUTES \* 60

**Error cases:**

- 401 — invalid credentials (same message for wrong email OR wrong password — never reveal which)

---

### POST /auth/logout

**Purpose:** Clear the auth cookie

**Auth required:** Yes

**Success response: 200**

```json
{
  "message": "Logged out successfully"
}
```

Clears cookie: `access_token` by setting it with max_age=0

---

### GET /auth/me

**Purpose:** Return the currently authenticated user's profile

**Auth required:** Yes

**Success response: 200**

```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "created_at": "2025-01-01T00:00:00Z"
}
```

**Error cases:**

- 401 — no cookie or invalid/expired JWT

---

## Data model

### User (SQLAlchemy model)

```
id            UUID, primary key, server default uuid_generate_v4()
email         VARCHAR(255), unique, indexed, not null
hashed_password  VARCHAR(255), not null
full_name     VARCHAR(255), not null
is_active     BOOLEAN, default true
created_at    TIMESTAMP, server default now()
updated_at    TIMESTAMP, auto-updated on change
```

---

## Security rules

- Passwords hashed with bcrypt (passlib), never stored plain
- JWT payload contains only: `sub` (user_id as string), `exp` (expiry timestamp)
- JWT secret loaded from env `SECRET_KEY` — never hardcoded
- Cookie flags: httpOnly=True, samesite="lax", secure=True in production only
- Login error message is always "Invalid credentials" regardless of which field is wrong
- Inactive users (`is_active=False`) are rejected at login with 401

---

## Dependencies (Depends)

### get_db

Yields an async SQLAlchemy session. Used in every route that touches the DB.

### get_current_user

- Reads `access_token` cookie
- Decodes JWT with python-jose
- Fetches user from DB by `sub` claim
- Raises 401 if cookie missing, JWT invalid/expired, or user not found
- Returns the User ORM object
- Used in: /auth/logout, /auth/me, and all protected routes in other modules
