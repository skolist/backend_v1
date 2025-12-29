# Backend (FastAPI)

Developer notes and setup instructions for this backend service.

## What’s in here

- FastAPI app factory: [app.py](app.py)
- ASGI entrypoint for Uvicorn/Docker: [main.py](main.py)
- API v1 router (Supabase auth enforced): [api/v1/router.py](api/v1/router.py)
- Supabase JWT verification dependency: [api/v1/auth.py](api/v1/auth.py)
- Settings loader (reads `.env`): [config/settings.py](config/settings.py)
- Tests:
  - Supabase auth + hello endpoint integration test: [tests/integration/test_supabase_auth_hello.py](tests/integration/test_supabase_auth_hello.py)

## Requirements

- Python 3.11
- A Supabase project
- A test user in Supabase Auth (email/password) for the integration test

## Environment variables

Copy `.env.example` to `.env` and fill values:

- `SUPABASE_URL` (required)
- `SUPABASE_SERVICE_KEY` (required for server-side token verification)
- `SUPABASE_ANON_KEY` (required for the integration test to sign-in)
- `TEST_USER_EMAIL`, `TEST_USER_PASSWORD` (required for the integration test)
- `PRODUCTION` (optional; controls CORS behavior)
- `GEMINI_API_KEY`, `OPENAI_API_KEY` (optional; used by `ai/` code when applicable)

Security note:
- `SUPABASE_SERVICE_KEY` is a **service role key**. Keep it server-side only. Do not ship it to browsers/mobile apps.

## Local setup

Create a virtual environment and install dependencies:

- `python -m venv venv`
- `source venv/bin/activate`
- `pip install -r requirements.txt`

Run the API:

- `uvicorn main:app --reload --port 8080`

The root endpoint should respond:

- `GET http://127.0.0.1:8080/` → `{ "message": "Welcome to My FastAPI Application!" }`

## Supabase authentication

All `/api/v1/*` routes require a valid JWT in the request header:

- `Authorization: Bearer <jwt>`

Verification is performed via the Supabase Python SDK (`supabase.auth.get_user(token)`). No manual JWT decoding is done in this service.

### Quick manual auth test

If you already have a valid Supabase access token (JWT):

- `curl -H "Authorization: Bearer <JWT>" http://127.0.0.1:8080/api/v1/hello`

Expected:
- Without header → `401`
- With valid token → `200` and a JSON payload containing `authenticated: true`

## Running tests

This repo currently uses Python’s built-in `unittest`.

Run all tests:

- `python -m unittest discover -s tests -p 'test_*.py'`

Notes:
- The integration test signs in to Supabase using `SUPABASE_ANON_KEY` + `TEST_USER_EMAIL`/`TEST_USER_PASSWORD`, then calls `/api/v1/hello` with the returned JWT.
- If required env vars are missing, the integration test will be skipped.

## Docker

Build:

- `docker build -t platform-backend .`

Run (using your local `.env`):

- `docker run --rm -p 8080:8080 --env-file .env platform-backend`

The container runs:

- `uvicorn main:app --host 0.0.0.0 --port 8080`

## Adding new routes (v1)

Add endpoints under the v1 router so they automatically inherit Supabase auth:

- Register routes in [api/v1/router.py](api/v1/router.py) directly, or
- Create feature routers (e.g. `api/v1/users.py`) and include them from [api/v1/router.py](api/v1/router.py)

Because the v1 router is created with `dependencies=[Depends(require_supabase_user)]`, everything under `/api/v1/*` is protected by default.
