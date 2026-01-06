# Skolist Backend – Intern Guide

Welcome!
This repository contains the **backend API** for Skolist, built using **FastAPI** and **Supabase authentication**.

Please read this before starting work.

---

## What is this service?

This backend:
- exposes REST APIs used by frontend apps
- verifies users using **Supabase Auth**
- runs on **Google Cloud Run** in production

You will mostly:
- add new API endpoints
- modify business logic
- write or update tests

You should **not**:
- change authentication logic
- expose Supabase service keys
- bypass existing security patterns

---

## Project Structure (Important Files)

```
backend/
├── app.py              → FastAPI app factory
├── main.py             → Entry point (used by Uvicorn & Docker)
│
├── api/
│   └── v1/
│       ├── router.py   → Main v1 router (auth enforced here)
│       ├── auth.py     → Supabase JWT verification
│       └── *.py        → Feature-specific routes
│
├── config/
│   └── settings.py     → Environment variable loader
│
├── tests/
│   └── integration/    → Integration tests (real Supabase auth)
│
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```

---

## Requirements

- Python **3.11**
- Test user credentials (provided by seniors)

If you don't have something, **ask before guessing**.

---

## Environment Variables

Create a `.env` file:

```bash
cp .env.example .env
```

Fill the required values (ask seniors for secrets).

### Required

| Variable                | Description                    |
| ----------------------- | ------------------------------ |
| `SUPABASE_URL`          | Supabase project URL           |
| `SUPABASE_SERVICE_KEY`  | Server-side service key        |
| `SUPABASE_ANON_KEY`     | Public anonymous key           |
| `TEST_USER_EMAIL`       | Test account email             |
| `TEST_USER_PASSWORD`    | Test account password          |

### Optional

| Variable          | Description                        |
| ----------------- | ---------------------------------- |
| `PRODUCTION`      | Controls CORS behavior             |
| `GEMINI_API_KEY`  | Used for AI-related features       |
| `OPENAI_API_KEY`  | Used for AI-related features       |

⚠️ **Security Rule**
- `SUPABASE_SERVICE_KEY` is **server-only**
- Never expose it in frontend code
- Never commit `.env` files

---

## Local Setup

### Create virtual environment

```bash
python -m venv venv
source venv/bin/activate
```

---

### Install dependencies

```bash
pip install -r requirements-dev.txt
```

---

### Run the API locally

```bash
uvicorn main:app --reload --port 8080
```

Test it:

```bash
GET http://127.0.0.1:8080/
```

Expected response:

```json
{ "message": "Welcome to My FastAPI Application!" }
```

---

## Authentication (Very Important)

All API routes under:

```
/api/v1/*
```

are **protected by Supabase authentication**.

### How auth works

1. Frontend sends:
   ```
   Authorization: Bearer <JWT>
   ```
2. Backend verifies JWT using Supabase SDK
3. If token is invalid → request is rejected
---

### Quick manual test

If you already have a valid Supabase JWT:

```bash
curl -H "Authorization: Bearer <JWT>" \
  http://127.0.0.1:8080/api/v1/hello
```

Expected:
- No token → `401 Unauthorized`
- Valid token → `200 OK`

---

## Adding New API Endpoints

### Rule: always add routes under `/api/v1`

This ensures authentication is enforced automatically.

### Option 1: Add directly to router

Edit:

```
api/v1/router.py
```

---

### Option 2: Create a feature router (preferred)

Example:

```
api/v1/users.py
```

Then include it inside `api/v1/router.py`.

You **do not** need to add auth checks — they are already applied at the router level.

---

## Running Tests

This project uses **pytest**.

Run all tests:

```bash
pytest
```

Run only integration tests:

```bash
pytest tests/integration/
```

### Notes on tests

- Integration tests:
  - log in to Supabase using test credentials
  - call protected endpoints
- If required env vars are missing:
  - the test will be skipped automatically

Do not hardcode secrets inside tests.

---

## Docker (Optional)

### Build image

```bash
docker build -t skolist-backend .
```

---

### Run container

```bash
docker run --rm -p 8080:8080 --env-file .env skolist-backend
```

The server will be available at:

```
http://localhost:8080
```

---

## Git Workflow (VERY IMPORTANT)

We follow a **strict Git workflow**.
Breaking it can block the whole team.

---

### Branch Rules

| Branch      | Who can push | Purpose    |
| ----------- | ------------ | ---------- |
| `main`      | Seniors only | Production |
| `stage`     | Seniors only | Staging    |
| `feature/*` | Everyone     | Your work  |
| `bugs/*`    | Everyone     | Bug fixes  |

❌ Never push to `main`
❌ Never push to `stage`

---

## Step-by-Step: How You Should Work

### 1️⃣ Start from `stage`

Always sync first:

```bash
git checkout stage
git pull origin stage
```

---

### 2️⃣ Create your own branch

For features:

```bash
git checkout -b feature/<short-name>
```

For bugs:

```bash
git checkout -b bugs/<short-name>
```

Examples:
- `feature/add-login-ui`
- `bugs/fix-navbar-overflow`

---

### 3️⃣ Make changes and commit

```bash
git add .
git commit -m "Clear description of what you changed"
```

Bad message ❌: `fix`, `update`, `changes`
Good message ✅: `Fix redirect after login`

---

### 4️⃣ Push your branch

```bash
git push -u origin feature/<short-name>
```

---

### 5️⃣ Open a Pull Request (PR)

After pushing, GitHub will show **"Compare & pull request"**.

Make sure:
- **Base branch** → `stage`
- **Compare branch** → your branch

Explain:
- what you changed
- why you changed it

If there is an issue number, mention it:

```
Fixes #123
```

---

### 6️⃣ Review & Merge

- Seniors will review your PR
- You may be asked to update code
- Once approved, it will be merged into `stage`
- Staging is auto-deployed on Vercel

❌ Do NOT merge your own PR
❌ Do NOT open PRs to `main`

---

---

## General Rules

- Keep endpoints small and focused
- Do not mix multiple features in one PR
- Prefer explicit schemas (Pydantic)
- Avoid "quick hacks" — ask if unsure
- If auth fails unexpectedly, **stop and ask**

---

## Final Note

This backend is security-sensitive.
If you are unsure about:
- authentication
- permissions
- database access

**Ask before implementing.**

Breaking auth can affect all users.
