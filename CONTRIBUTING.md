# Contributing

## Local Setup

```bash
git clone https://github.com/LevaAverGit/pd-scanner-152fz.git
cd pd-scanner-152fz

make install   # creates .venv, installs backend deps, Playwright Chromium, frontend deps
```

Or manually:
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
playwright install chromium
cd frontend && npm install && cd ..
```

## Running the Development Stack

```bash
# Terminal 1 — FastAPI backend on port 8000
make dev-backend

# Terminal 2 — Vite dev server on port 5173
make dev-frontend
```

Open http://localhost:5173.

## Running Tests

```bash
make test           # backend pytest (303 tests)
make type-check     # frontend TypeScript strict check
make build          # frontend production build
make verify         # all three in sequence
```

Tests run without a running server, network access, or Playwright.
All async tests use `httpx.ASGITransport` for in-process HTTP.

## Code Style

- Python 3.11+, type hints on all public functions
- Pydantic v2 models for all API inputs/outputs
- `ruff` for linting: `ruff check backend/app/` (future)
- No bare `except:` — always catch specific exceptions
- All service functions are `async def`; no synchronous IO in the hot path

## Adding a New Personal Data Category

1. Add to `PD_CATEGORIES` in `backend/app/utils/pd_dictionary.py`:
   ```python
   "my_category": {
       "description": "What this category is.",
       "gdpr_article": "Art.4(1)",
       "keywords": ["keyword1", "keyword2"],
   }
   ```
2. Add to `HIGH_RISK_CATEGORIES` if applicable
3. Write a test in `backend/tests/test_classifier.py`

See `docs/EXTENDING_SCANNER.md` for the full guide.

## Adding a Vendor Signature

1. Add to the vendor lookup table in `backend/app/services/vendor_classification_service.py`
2. Write a test in `backend/tests/test_vendor_classification.py`

## Database Migrations

The database uses `aiosqlite` with an auto-migration system in `backend/app/models/db.py`.
When adding a new column to the `scans` table:
1. Add the SQL `ALTER TABLE` statement to `_run_migrations()` in `db.py`
2. Wrap in a `try/except OperationalError` to make it idempotent (column already exists)
3. Add the field to the Pydantic model in `backend/app/models/schemas.py`

## Branch and Commit Convention

- Branch: `feature/<short-name>`, `fix/<short-name>`, `docs/<short-name>`
- Commit: imperative present tense — `Add national ID classifier`, `Fix SSRF guard for IPv6`
- Keep backend and frontend changes in separate commits when possible

## Frontend

- React 18 + TypeScript + Vite + Tailwind CSS
- Components in `frontend/src/components/`
- Type-check: `make type-check` — must pass before any PR

## Limitations

- Backend requires Python 3.11+ (uses `str | None` union syntax throughout)
- Frontend dev server requires Node.js 18+
- Playwright tests require Chromium — installed via `make install` or `playwright install chromium`
- No rate limiting, authentication, or multi-user support in the current implementation
- DNS rebinding protection is deferred (post-resolution host validation not implemented)
