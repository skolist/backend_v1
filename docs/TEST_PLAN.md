# Backend Test Suite Plan

## Overview

This document outlines the modular test suite architecture for the Skolist backend. The test suite is designed to handle two key external dependencies:
1. **Supabase** - Database and authentication
2. **Gemini AI** - Question generation, correction, and regeneration

---

## Test Architecture

```
tests/
├── conftest.py                 # Root config: --gemini-live, --supabase-local flags
├── unit/                       # Pure logic tests (mocked dependencies)
│   ├── conftest.py            # Unit test fixtures, mock Gemini client
│   ├── test_*.py              # Unit tests for individual functions
│   └── fixtures/              # Shared test data fixtures
├── integration/                # API endpoint tests
│   ├── conftest.py            # Integration fixtures, TestClient, auth
│   └── test_*_api.py          # API endpoint integration tests
├── e2e/                        # End-to-end tests (optional, for CI)
│   └── test_*.py              # Full workflow tests
└── utils/                      # Shared test utilities
    ├── __init__.py
    ├── factories.py           # Test data factories
    ├── mock_gemini.py         # Shared Gemini mock implementation
    ├── supabase_helpers.py    # Supabase test utilities
    └── response_recorder.py   # VCR-style response recording (optional)
```

---

## Dependency Strategy

### 1. Supabase Strategy

| Test Type | Supabase Approach |
|-----------|-------------------|
| **Unit Tests** | Mock `get_supabase_client()` using `unittest.mock` |
| **Integration Tests** | Use **local Supabase** (recommended) or production test account |
| **CI Pipeline** | Local Supabase via Docker (see setup below) |

#### Local Supabase Setup

The `skolist-db` directory contains the Supabase project with migrations and seeds.

```bash
# Start local Supabase (from skolist-db directory)
cd ../skolist-db
supabase start

# Output provides:
# - SUPABASE_URL: http://127.0.0.1:54321
# - SUPABASE_ANON_KEY: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
# - SUPABASE_SERVICE_KEY: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Create test users
python seed_users.py

# Reset database (re-runs migrations + seeds)
supabase db reset

# Stop when done
supabase stop
```

#### Environment Configuration for Tests

Create a `.env.test` file for local testing:

```dotenv
# Local Supabase
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_ANON_KEY=<from supabase start output>
SUPABASE_SERVICE_KEY=<from supabase start output>

# Test user credentials
TEST_USER_EMAIL=test@example.com
TEST_USER_PASSWORD=testpassword123

# Gemini (optional - for live tests only)
GEMINI_API_KEY=<your-api-key>

DEPLOYMENT_ENV=LOCAL
```

### 2. Gemini AI Strategy

| Test Type | Gemini Approach |
|-----------|-----------------|
| **Unit Tests** | **Always mock** - deterministic, fast, free |
| **Integration Tests** | **Mock by default**, `--gemini-live` for real API |
| **Validation Tests** | Live API with recorded responses comparison |

#### Mock Implementation (Default)

The mock Gemini client is already implemented in:
- `tests/unit/conftest.py`
- `tests/integration/conftest.py`

Key features:
- Returns realistic question structures
- Respects question types based on content analysis
- No API calls = no costs

#### Live Gemini Testing

Use the `--gemini-live` flag for real API testing:

```bash
# Run with real Gemini API
pytest tests/integration/ --gemini-live

# Run specific test with live API
pytest tests/integration/test_generate_questions_api.py -k "test_basic_generation" --gemini-live
```

#### Response Recording (VCR Pattern) - Optional

For deterministic CI tests without mocking:

```python
# Record responses
pytest tests/integration/ --gemini-live --record-responses

# Replay recorded responses (no API calls)
pytest tests/integration/ --replay-responses
```

---

## Test Categories

### Unit Tests (`tests/unit/`)

**Purpose**: Test pure business logic in isolation.

**What to test**:
- Batchification logic (`build_batches_end_to_end`, `_chunk_questions`)
- Prompt generation functions
- Data validation and transformation
- Credits calculation
- Request/response parsing
- PDF/DOCX generation logic

**Running**:
```bash
# All unit tests (fast, no external deps)
pytest tests/unit/ -v

# Specific module
pytest tests/unit/test_question_generator.py -v

# With coverage
pytest tests/unit/ --cov=api --cov-report=html
```

### Integration Tests (`tests/integration/`)

**Purpose**: Test API endpoints with real HTTP calls.

**What to test**:
- Authentication flows (valid/invalid tokens)
- Request validation (400 errors)
- Authorization (401/403 errors)
- Happy path responses
- Database interactions (via local Supabase)

**Running**:
```bash
# Start local Supabase first
cd ../skolist-db && supabase start && cd ../backend

# Run integration tests (mocked Gemini)
pytest tests/integration/ -v

# Run with live Gemini (uses API credits)
pytest tests/integration/ --gemini-live -v

# Single test
pytest tests/integration/test_generate_questions_api.py::TestGenerateQuestionsAuth -v
```

### E2E Tests (`tests/e2e/`) - Future

**Purpose**: Full workflow validation.

**What to test**:
- Complete user journeys
- Multi-endpoint workflows
- Performance benchmarks

---

## Test Markers

Available pytest markers:

```python
@pytest.mark.slow           # Skip with -m 'not slow'
@pytest.mark.integration    # Integration tests only
@pytest.mark.unit          # Unit tests only
@pytest.mark.live_gemini   # Requires --gemini-live flag
@pytest.mark.auth          # Authentication tests
```

**Usage**:
```bash
# Run only fast tests
pytest -m 'not slow'

# Run only unit tests
pytest -m unit

# Run integration tests requiring live Gemini
pytest -m live_gemini --gemini-live
```

---

## CI Pipeline Configuration

### GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements-dev.txt
      - run: pytest tests/unit/ -v --cov=api --cov-report=xml
      
  integration-tests:
    runs-on: ubuntu-latest
    services:
      # Supabase requires Docker Compose, use action
    steps:
      - uses: actions/checkout@v4
      - uses: supabase/setup-cli@v1
      - run: |
          cd ../skolist-db
          supabase start
      - run: pytest tests/integration/ -v
```

---

## Quick Reference

### Daily Development

```bash
# Quick unit test run
pytest tests/unit/ -v --tb=short

# Test specific functionality
pytest tests/unit/test_question_generator.py -v -k "batch"
```

### Before PR

```bash
# Full test suite with mocked dependencies
pytest tests/ -v --tb=short

# With coverage report
pytest tests/ --cov=api --cov=ai --cov-report=term-missing
```

### Debugging

```bash
# Single test with full output
pytest tests/unit/test_question_generator.py::test_specific -v -s

# Stop on first failure
pytest tests/ -x

# Last failed only
pytest tests/ --lf
```

---

## Endpoint Coverage Matrix

| Endpoint | Unit Tests | Integration Tests | Status |
|----------|------------|-------------------|--------|
| `/qgen/generate_questions` | ✅ | ✅ | Complete |
| `/qgen/auto_correct_question` | ✅ | ✅ | Complete |
| `/qgen/regenerate_question` | ✅ | ✅ | Complete |
| `/qgen/regenerate_question_with_prompt` | ✅ | ✅ | Complete |
| `/qgen/extract_questions` | ⬜ | ⬜ | TODO |
| `/qgen/edit_svg` | ⬜ | ⬜ | TODO |
| `/qgen/get_feedback` | ⬜ | ⬜ | TODO |
| `/qgen/download_pdf` | ✅ | ⬜ | Partial |
| `/qgen/download_docx` | ✅ | ⬜ | Partial |
| `/bank/list` | ⬜ | ⬜ | TODO |
| `/bank/*` | ⬜ | ⬜ | TODO |
| Auth endpoints | ⬜ | ✅ | Partial |

---

## Next Steps

1. **Immediate**: Run existing tests with local Supabase
2. **This Week**: Add missing endpoint tests
3. **Next Sprint**: Set up CI with automated Supabase
4. **Future**: Consider response recording for deterministic CI

See `tests/README.md` for detailed setup instructions.
