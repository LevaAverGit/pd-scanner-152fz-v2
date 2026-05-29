# Quality Assurance

## Test Strategy

303 backend tests, 0 warnings. All tests run without a live server, without
network access, and without launching Playwright.

```bash
make test              # backend: 303 tests
make type-check        # frontend TypeScript strict check
make build             # frontend production build
make verify            # all three in sequence
```

---

## Test Structure

| Test file | What is covered |
|---|---|
| `test_api.py` | Scan create/get/delete, history pagination, SSRF URL validation, health endpoint |
| `test_classifier.py` | All 12 PD categories, confidence scoring, false-positive guard, multi-field dedup |
| `test_vendor_classification.py` | Analytics, ad-tech, CDN, payment, tracker patterns |
| `test_policy_parser.py` | Section detection keywords, operator name/contact extraction |
| `test_fz152_assessment.py` | Consent mechanism typing, risk scoring, gap generation, manual validation targets |
| `test_document_extraction.py` | PDF/DOCX type detection, text extraction, parse-status propagation |
| `test_integration_audit.py` | Downstream processor inference, operator evidence schema |
| `test_synthetic_submission.py` | Safety gates: CAPTCHA block, max-submissions cap, sensitive field detection |
| `test_scan_diff.py` | Diff computation: added/removed categories, vendors, processors, policy changes |
| `test_page_classifier.py` | Registration relevance scoring, page-type detection |

---

## Key Test Patterns

### In-process HTTP testing (ASGITransport)

```python
from httpx import ASGITransport, AsyncClient
from backend.app.main import app

async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/health")
    assert resp.status_code == 200
```

No real server is started — the ASGI app is called in-process.

### Database isolation per test class

```python
@pytest_asyncio.fixture(autouse=True)
async def _init_db(self, tmp_path):
    path = str(tmp_path / "test.db")
    await init_db(path)
    with patch("backend.app.core.config.settings.db_path", path):
        yield
```

Each test class gets a fresh SQLite database in a temporary directory.
The `patch` replaces the config setting so the app uses the temp DB.

### Classifier unit test pattern

```python
def test_email_field_classified():
    field = {
        "name": "email", "id": "email", "label": "Email address",
        "placeholder": "", "aria_label": "", "autocomplete": "email",
    }
    result = classify_field(field)
    assert result.category == "email"
    assert result.confidence == 1.0
    assert "email" in result.matched_signals
```

---

## What Is Intentionally Not Tested

- **Live crawling** — Playwright tests run against a local fixture server
  (`tests/fixtures/form_server.py`) but the actual internet crawling is not
  unit-tested; validated manually against example sites
- **PDF/DOCX content** — extraction is tested with minimal synthetic inputs;
  real-world documents are validated manually
- **Frontend component behavior** — TypeScript strict check ensures type
  correctness; visual behavior is verified manually

---

## Two Playwright Tests in CI

`test_synthetic_submission.py` contains 2 tests that actually launch Chromium
via `async_playwright()`. These run in CI via:
```yaml
- name: Install Playwright browser
  run: playwright install chromium --with-deps
```

All other tests use `httpx.ASGITransport` and do not require a browser.

---

## Manual Validation Checklist

Before major feature changes:

- [ ] `make test` passes: 303 passed, 0 warnings
- [ ] `make type-check` passes: 0 TypeScript errors
- [ ] `make build` succeeds: frontend bundle builds without errors
- [ ] Start stack (`make dev-backend` + `make dev-frontend`), scan one public URL
- [ ] Verify scan completes and shows categories, vendors, 152-FZ assessment
- [ ] Download JSON and Markdown exports — verify content
- [ ] Check CI badge in README shows green after push

---

## CI

GitHub Actions CI (`ci.yml`) runs on every push and PR to `main`:
- Python 3.11
- Install backend deps from `backend/requirements.txt`
- Install Playwright Chromium with system deps
- Run `python -m pytest backend/tests/ -q`

Frontend type-check and build are not in CI (requires Node.js setup); run manually.
