# Backend Test Suite

This directory contains unit and integration tests for the Skolist backend.

## Quick Start

### Run Unit Tests (No External Dependencies)

```bash
# All unit tests
pytest tests/unit/ -v

# Specific test file
pytest tests/unit/test_question_generator.py -v

# Specific test function
pytest tests/unit/test_question_generator.py::test_batch_building -v
```

### Run Integration Tests (Requires Supabase)

Integration tests require a running Supabase instance. You have two options:

#### Option A: Use CI (Recommended for quick feedback)

Push to GitHub and let CI run tests with local Supabase automatically.

#### Option B: Run Locally with Local Supabase

1. **Start local Supabase** (requires Docker):
   ```bash
   # Clone skolist-db if you haven't
   cd ../skolist-db  # or wherever your skolist-db repo is
   
   # Start Supabase
   supabase start
   
   # Note the output - you'll need the URLs and keys
   ```

2. **Create test environment file**:
   ```bash
   cd backend
   cp .env.test.example .env.test
   # Edit .env.test with values from supabase start output
   ```

3. **Seed test users**:
   ```bash
   cd ../skolist-db
   pip install -r requirements.txt
   python seed_users.py
   ```

4. **Run integration tests**:
   ```bash
   cd backend
   pytest tests/integration/ -v
   ```

5. **Stop Supabase when done**:
   ```bash
   cd ../skolist-db
   supabase stop
   ```

## Test Structure

```
tests/
├── conftest.py              # Root config: CLI options, env loading
├── utils/
│   ├── __init__.py
│   ├── mock_gemini.py       # Shared Gemini mock implementation
│   └── factories.py         # Test data factories
├── unit/                    # Pure logic tests (mocked dependencies)
│   ├── conftest.py          # Unit test fixtures
│   └── test_*.py            # Unit tests
└── integration/             # API endpoint tests (requires Supabase)
    ├── conftest.py          # Integration fixtures, auth setup
    └── test_*_api.py        # API endpoint tests
```

## CLI Options

| Flag | Description |
|------|-------------|
| `--gemini-live` | Use real Gemini API instead of mocks (costs money!) |
| `-m unit` | Run only unit tests |
| `-m integration` | Run only integration tests |
| `-m 'not slow'` | Skip slow tests |

### Examples

```bash
# Run all tests
pytest

# Run only unit tests
pytest -m unit

# Run only integration tests (requires Supabase)
pytest -m integration

# Run with real Gemini API (for validation)
pytest tests/unit/ --gemini-live

# Run fast tests only
pytest -m 'not slow'

# Run specific marker combination
pytest -m 'integration and qgen'

# Stop on first failure
pytest -x

# Re-run only failed tests
pytest --lf

# With coverage
pytest --cov=api --cov-report=html
```

## Environment Files

| File | Purpose |
|------|---------|
| `.env.test.example` | Template for local test config |
| `.env.test` | Your local test config (gitignored) |
| `.env` | Production/default config |

The test suite loads `.env.test` if it exists, otherwise falls back to `.env`.

## Gemini Mocking

By default, all tests use a mock Gemini client that returns realistic question structures. This ensures:
- Tests are fast and deterministic
- No API costs during testing
- Tests work offline

To test with the real Gemini API:
```bash
# Set API key in .env.test
GEMINI_API_KEY=your-key-here

# Run with live API
pytest tests/unit/test_question_generator.py --gemini-live
```

## Adding New Tests

### Unit Test Template

```python
# tests/unit/test_my_feature.py
import pytest
from tests.utils.factories import create_test_concept

class TestMyFeature:
    def test_basic_case(self, gemini_client):
        # gemini_client is mocked by default
        result = do_something(gemini_client)
        assert result is not None
    
    @pytest.mark.slow
    def test_slow_operation(self):
        # This test is skipped with -m 'not slow'
        pass
```

### Integration Test Template

```python
# tests/integration/test_my_endpoint_api.py
import pytest
from fastapi.testclient import TestClient

class TestMyEndpoint:
    def test_requires_auth(self, unauthenticated_test_client: TestClient):
        response = unauthenticated_test_client.post("/api/v1/my-endpoint")
        assert response.status_code == 401
    
    def test_happy_path(
        self,
        test_client: TestClient,  # Already authenticated
        test_concepts,            # Auto-cleanup test data
    ):
        response = test_client.post("/api/v1/my-endpoint", json={...})
        assert response.status_code == 200
```

## Troubleshooting

### Integration tests skip with "Missing env vars"

Your Supabase credentials aren't available. Either:
- Start local Supabase and create `.env.test`
- Push to GitHub and let CI run the tests

### Tests fail with "Connection refused"

Local Supabase isn't running. Start it with:
```bash
cd ../skolist-db && supabase start
```

### Mock responses don't match expected structure

Update the mock factories in `tests/utils/mock_gemini.py` to match the current API response structure.
