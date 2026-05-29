# Extending the Scanner

This guide covers the four most common extension points.

---

## Adding a New Personal Data Category

Personal data categories are defined in `backend/app/utils/pd_dictionary.py`.

**Step 1 — Add the category:**

```python
PD_CATEGORIES: dict[str, dict] = {
    ...
    "biometric": {
        "description": "Biometric data: fingerprint, facial recognition, retina scan.",
        "gdpr_article": "Art.9(1)",
        "keywords": [
            "fingerprint", "biometric", "facial", "face_id",
            "retina", "voice_id",
        ],
    },
}
```

Field guidance:
- `description` — human-readable, used in reports
- `gdpr_article` — GDPR or 152-FZ reference
- `keywords` — lowercase, match against field `name`, `id`, `label`, `placeholder`, `aria-label`

**Step 2 — Mark as high-risk if applicable:**

```python
HIGH_RISK_CATEGORIES: frozenset[str] = frozenset({
    "health", "financial", "national_id", "gender",
    "biometric",  # add here
})
```

**Step 3 — Write a test:**

In `backend/tests/test_classifier.py`:

```python
def test_biometric_field_classified():
    field = {"name": "fingerprint", "id": "", "label": "", "placeholder": "", "aria_label": ""}
    result = classify_field(field)
    assert result is not None
    assert result.category == "biometric"
    assert result.confidence == 1.0
```

**Step 4 — Update `docs/152FZ_CHECKLIST.md`** with the new category and its regulatory basis.

---

## Adding a Vendor Signature

Vendor classification lives in `backend/app/services/vendor_classification_service.py`.

**Step 1 — Find the vendor lookup table** in the file (a dict mapping hostname substrings to
vendor name + class):

```python
KNOWN_VENDORS: dict[str, dict] = {
    ...
    "my-analytics.com": {
        "vendor_name": "My Analytics",
        "vendor_class": "analytics",
    },
}
```

Vendor classes: `analytics`, `ad_tech`, `CDN`, `payment`, `CRM`, `social`, `tracking`, `unknown`.

**Step 2 — Write a test:**

In `backend/tests/test_vendor_classification.py`:

```python
def test_my_analytics_classified():
    vendors = classify_vendors(["my-analytics.com"])
    assert vendors[0].vendor_name == "My Analytics"
    assert vendors[0].vendor_class == "analytics"
```

---

## Adding a Policy Section

Policy section detection is done by keyword matching in `backend/app/services/policy_parser_service.py`.
The result is stored in a boolean flag on `PolicyAnalysis` / `FZ152Assessment`.

**Step 1 — Add a boolean flag to `PolicyAnalysis` in `backend/app/models/schemas.py`:**

```python
class PolicyAnalysis(BaseModel):
    ...
    has_cookie_policy_section: bool = False
```

**Step 2 — Add to `FZ152Assessment` and the assessment builder** in `fz152_assessment_service.py`:

```python
class FZ152Assessment(BaseModel):
    ...
    policy_has_cookie_policy_section: bool = False
```

**Step 3 — Add keyword detection** in `policy_parser_service.py`:

```python
SECTION_KEYWORDS = {
    ...
    "has_cookie_policy_section": [
        "cookie policy", "cookies", "политика куки", "куки",
    ],
}
```

**Step 4 — Add a gap rule** if the section is required:

In `fz152_assessment_service.py` → `_derive_potential_gaps()`:

```python
if not assessment.policy_has_cookie_policy_section:
    gaps.append(
        "Cookie policy section not publicly evidenced — manual review recommended."
    )
```

**Step 5 — Write a test** in `backend/tests/test_policy_parser.py`.

**Step 6 — Update `docs/152FZ_CHECKLIST.md`** with the new section.

---

## Adding a New Report Field

Report generation is in `backend/app/services/report_service.py`.

**Step 1 — Add the field to the appropriate Pydantic model** in `schemas.py`.

**Step 2 — Populate the field** in the relevant service (e.g., `fz152_assessment_service.py`).

**Step 3 — Include in the Markdown template** in `report_service.py`:

```python
def _render_fz152_section(assessment: FZ152Assessment) -> str:
    ...
    lines.append(f"- Cookie policy section: {'Yes' if assessment.policy_has_cookie_policy_section else 'No'}")
    ...
```

**Step 4 — Include in the JSON output** — Pydantic's `.model_dump()` picks up new fields automatically.

**Step 5 — Write a test** verifying the field appears in both Markdown and JSON output.

---

## Adding Tests for a New Rule

See the [Testing Strategy](QUALITY_ASSURANCE.md) and examples in:
- `backend/tests/test_classifier.py` — classifier tests with field dict inputs
- `backend/tests/test_fz152_assessment.py` — assessment builder tests
- `backend/tests/test_vendor_classification.py` — vendor lookup tests

### Async API test pattern

```python
import pytest
from httpx import ASGITransport, AsyncClient
from backend.app.main import app

@pytest.mark.asyncio
async def test_my_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/health")
    assert resp.status_code == 200
```

For tests that need the database, use the `_init_db` fixture pattern from `test_api.py`:

```python
import pytest_asyncio
from unittest.mock import patch
from backend.app.models.db import init_db

@pytest.mark.asyncio
class TestMyEndpoint:
    @pytest_asyncio.fixture(autouse=True)
    async def _init_db(self, tmp_path):
        path = str(tmp_path / "test.db")
        await init_db(path)
        with patch("backend.app.core.config.settings.db_path", path):
            yield
```
