# Data Flow

This document traces the path of data from URL input to the final
`ScanResult` object returned by the API.

---

## Full Pipeline

```
User submits URL
       │
       ▼
[1] URL Validation        (url_validation.py)
    SSRF guard, scheme check, hostname resolution
       │
       ▼
[2] Scan Record Created   (db.py)
    status = "pending"
       │
       ▼
[3] Background Task       (scanner_service.py)
    status = "running"
       │
       ▼
[4] BFS Crawler           (crawler_service.py)
    Playwright/Chromium, up to 20 pages, same-host only
    → List[VisitedPageItem] (per page: forms, fields, links, consent signals)
    → network_capture: third-party hostnames
       │
       ├──── [5a] DOM Parser (dom_parser.py)
       │     Extract form fields: name, id, label, placeholder, aria-label, autocomplete
       │
       ├──── [5b] Classifier (classifier_service.py + pd_dictionary.py)
       │     Match fields against PD_CATEGORIES keyword dict
       │     → List[DataCategoryItem] with confidence scores
       │
       ├──── [5c] Consent Detection (consent_detection_service.py)
       │     Detect: privacy link, consent checkbox, marketing checkbox,
       │     bundled consent text
       │     → per-page consent signal booleans
       │
       ├──── [5d] Page Classifier (page_classifier_service.py)
       │     Classify page type: registration, login, contact, other
       │     → registration_relevance per page
       │
       └──── [5e] Vendor Classification (vendor_classification_service.py)
             Third-party script hosts → VendorSummaryItem list
             → processor_map (inferred processors with confidence)
       │
       ▼
[6] Policy Parser         (policy_parser_service.py)
    Follow privacy/terms links found during crawl
    → Fetch HTML, PDF, or DOCX
    → document_extraction_service.py (PDF: PyMuPDF; DOCX: python-docx)
    → Keyword matching for 8 policy sections
    → PolicyAnalysis with per-section boolean flags
       │
       ▼
[7] Integration Audit     (integration_audit_service.py)
    Combine vendor signals, form action analysis, operator-supplied evidence
    → Refined processor_map with confidence levels and source labels
       │
       ▼
[8] 152-FZ Assessment     (fz152_assessment_service.py)
    Synthesise all findings into FZ152Assessment:
    → consent_mechanism_type classification
    → policy section coverage flags
    → potential_gaps list (heuristic)
    → manual_validation_targets
    → overall_public_risk_level (low/medium/high)
       │
       ▼
[9] Site Summary          (scanner_service.py)
    Aggregate: pages_scanned, pages_with_forms, unique_categories_found,
    top_third_party_hosts
       │
       ▼
[10] Screenshot           (screenshot_service.py)
    Take screenshot of seed URL → saves to exports/{scan_id}.png
       │
       ▼
[11] Report Export        (report_service.py)
    Generate JSON report → exports/{scan_id}.json
    Generate Markdown report → exports/{scan_id}.md
       │
       ▼
[12] Persist Full Result  (db.py)
    Serialise ScanResult to JSON → store in SQLite scans table
    status = "complete"
       │
       ▼
GET /api/scan/{scan_id}
    → Deserialise from SQLite
    → Return ScanResult to frontend
```

---

## Key Data Models

### ScanResult (the full output model)

```python
class ScanResult(BaseModel):
    scan_id: str
    url: str
    status: ScanStatus              # pending / running / complete / failed
    data_categories: List[DataCategoryItem]
    vendor_summary: List[VendorSummaryItem]
    processor_map: List[ProcessorMapItem]
    fz152_assessment: FZ152Assessment | None
    site_summary: SiteSummary | None
    registration_relevance: str | None
    created_at: str
    completed_at: str | None
```

### DataCategoryItem

```python
class DataCategoryItem(BaseModel):
    category: str            # e.g. "email", "phone", "national_id"
    confidence: float        # 1.0 (2+ signals) or 0.7 (1 signal)
    matched_signals: List[str]  # which field attributes triggered the match
    explanation: str
```

### FZ152Assessment

```python
class FZ152Assessment(BaseModel):
    overall_public_risk_level: str          # low / medium / high
    consent_mechanism_type: str             # explicit_checkbox / bundled_text / ...
    policy_publicly_available: bool
    policy_has_purpose_section: bool
    policy_has_categories_section: bool
    policy_has_legal_basis_section: bool
    policy_has_processor_or_third_party_section: bool
    policy_has_cross_border_section: bool
    policy_has_subject_rights_section: bool
    policy_has_retention_or_destruction_section: bool
    policy_has_localization_statement: bool
    potential_gaps: List[str]
    manual_validation_targets: List[str]
```

---

## Operator-Supplied Evidence

When the request body includes `integration_evidence` or `operator_metadata`,
this data is:
- Stored in the scan record with source label `operator_supplied`
- Passed to `integration_audit_service.py` for processor inference
- **Never mixed with scanner observations** — always tagged separately in output

This separation is maintained throughout the data model so reports always
show the provenance of each piece of information.

---

## Database Persistence

`ScanResult` is serialised to JSON and stored in a single `TEXT` column in SQLite.
Auto-migration in `db.py` handles schema evolution — new columns use `ALTER TABLE`
wrapped in `try/except OperationalError` to be idempotent across existing databases.
