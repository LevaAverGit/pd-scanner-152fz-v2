# PD Scanner — Architecture

## Overview

```
User (browser)
    |
    | HTTP (localhost:5173)
    v
React Frontend (Vite dev server)
    |
    | HTTP/JSON → /api/*           (proxied to localhost:8000)
    | Static    → /screenshots/*   (proxied to localhost:8000)
    | Static    → /exports/*       (proxied to localhost:8000)
    v
FastAPI Backend (localhost:8000)
    |                    \
    v                     v
Scanner Engine         SQLite (pd_scanner.db, local file)
(Playwright/Chromium)
    |
    v
Target URL (public internet — outbound only, read-only)
```

The backend is the only process that makes outbound requests to external URLs.
The frontend communicates exclusively with the local backend.
No data leaves the machine.

---

## Components

### FastAPI Backend (`backend/app/`)
Receives scan requests, validates input (URL scheme + SSRF guard), persists scan records
to SQLite, launches the scanner pipeline as a FastAPI background task, and serves the
REST API plus static file mounts for screenshots and exports.

Entry point: `backend/app/main.py`

### Scanner Pipeline (`backend/app/services/scanner_service.py`)
Orchestrates the full 10-step scan pipeline as a FastAPI background task:

1. URL validation (second pass inside the worker)
2. Mark scan as `processing`
3. Launch headless Chromium via Playwright async API
4. BFS crawl — up to 20 pages, depth 2, same-host only
5. Parse linked policy pages (HTML, PDF, DOCX)
6. Screenshot of seed URL
7. Aggregate data categories across all pages
8. Classify vendors; build processor map; build 152-FZ assessment
9. Persist results to SQLite
10. Export JSON + Markdown reports

### BFS Crawler (`backend/app/services/crawler_service.py`)
Bounded same-site BFS crawler. Navigates pages, extracts links, respects
`MAX_PAGES=20` and `MAX_DEPTH=2`. Runs interactive discovery to reveal
hidden forms. After each page, runs `infer_downstream_routing()` to patch the
`VisitedPageItem` with processor inference signals.

### PD Field Classifier (`backend/app/services/classifier_service.py`)
Rules-based keyword matching using `pd_dictionary.py`. For each extracted field,
signals (`name`, `id`, `label`, `placeholder`, `aria-label`, `autocomplete`) are
checked against 12 category keyword lists using word-boundary-aware regex (`\bkeyword\b`).
Returns `DataCategoryItem` with category, confidence, matched signals, and explanation.

### Consent Detection (`backend/app/services/consent_detection_service.py`)
Detects privacy links, terms links, consent checkboxes (explicit opt-in),
marketing consent checkboxes, and bundled/implied consent text via JavaScript execution
in the Playwright page context.

### Vendor Classification (`backend/app/services/vendor_classification_service.py`)
Maps third-party hosts to vendor classes:
`analytics`, `ad_tech`, `tracking`, `cdn`, `payment`, `crm`, `email_marketing`,
`retargeting`, `marketing_automation`, `form_platform`, `customer_support`.
Uses signature matching against a curated host-to-vendor dictionary.

### Policy Parser (`backend/app/services/policy_parser_service.py`)
Phases 11 + 15. Analyses linked policy pages for 8 standard sections:
purpose, data categories, legal basis, third-party processors, cross-border transfers,
subject rights, retention/destruction, and data localisation (152-FZ specific).

Routing logic:
- `.pdf` URL → download via httpx → extract with PyMuPDF
- `.docx` URL → download via httpx → extract with python-docx
- `.doc` URL → record as `unsupported`
- other → load in Playwright, extract `innerText`

The keyword analysis (`_analyse_text()`) is a pure Python function shared by all paths.

### Document Extraction (`backend/app/services/document_extraction_service.py`)
Downloads policy documents via httpx (10 MB cap, 30 s timeout), extracts
plain text from PDF (PyMuPDF) or DOCX (python-docx), returns `(text, status)` where
status is `parsed | unreadable | failed`. No OCR is performed.

### Synthetic Submission (`backend/app/services/synthetic_submission_service.py`)
Off by default. When explicitly enabled:
- Fills forms with clearly synthetic placeholder values (`test@example.invalid`, etc.)
- Blocks on CAPTCHA, payment fields, file uploads, sensitive fields (passport, SSN, etc.)
- Maximum 1 submission per page, 3 per scan
- Captures only POST request metadata (URL, method) — no bodies, no cookies

### Integration Audit (`backend/app/services/integration_audit_service.py`)
Infers downstream processors from form action URLs, hidden field signatures,
and network observations. Merges with operator-supplied `integration_evidence`.
Produces a `processor_map: list[ProcessorMapItem]` with explicit source labels:
`observed_submit | inferred_public_signal | operator_supplied`.

### 152-FZ Assessment (`backend/app/services/fz152_assessment_service.py`)
Synthesises all prior findings into a `FZ152Assessment`:
- Derives consent mechanism type (`explicit_checkbox | bundled_text | weak_or_absent | mixed | unknown`)
- Generates potential gaps list (heuristic, not legal conclusions)
- Generates manual validation checklist
- Scores overall public risk level (`low | medium | high`)
- Accepts optional `operator_metadata` (legal name, INN, OGRN)

All language uses careful wording: "potential gap", "public evidence suggests",
"manual validation required" — never "violation" or "non-compliant".

### Storage (`backend/app/models/db.py`, `backend/app/services/storage_service.py`)
Single-file local SQLite database using aiosqlite (raw SQL, no ORM).
`init_db()` runs on startup and applies auto-migrations via `ALTER TABLE IF NOT EXISTS`
for columns added in later phases. All complex fields are stored as serialised JSON.

### React Frontend (`frontend/`)
React 18 + TypeScript + Vite + Tailwind CSS. Two pages:
- `DashboardPage` — URL input + paginated scan history
- `ScanDetailsPage` — full result view with polling, all panels

Key display components:
- `PolicyAnalysisPanel` — 8-section table, operator name, contacts, document type badge
- `FZ152AssessmentPanel` — risk badge, policy coverage, gaps, manual checklist, disclaimer
- `SyntheticSubmissionPanel` — shown only when synthetic mode was enabled

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/scan` | Submit URL; returns `scan_id` + `status: pending` |
| GET | `/api/scan/{scan_id}` | Retrieve current status and results |
| GET | `/api/history` | Paginated list (`limit`, `offset`) |
| DELETE | `/api/history/{scan_id}` | Delete a scan record |
| GET | `/api/health` | Liveness check |

Static mounts (FastAPI `StaticFiles`):
- `GET /screenshots/{filename}` — scan screenshots
- `GET /exports/{filename}` — JSON and Markdown reports

---

## Scan Lifecycle

```
POST /api/scan
    → URL validated (scheme + SSRF guard)
    → DB record created: status=pending
    → background task enqueued
    → scan_id returned immediately

Background task (scanner_service.run_scan):
    status → processing
    Playwright → headless Chromium launched
    BFS crawl (≤20 pages, depth ≤2, same-host)
      Per page: DOM extraction, field classification, consent signals,
                form detection, interactive discovery, downstream routing inference
    Policy page parsing (HTML / PDF / DOCX)
    Screenshot of seed URL
    Aggregate categories across pages
    Vendor classification
    Processor map construction
    152-FZ assessment build
    Persist to SQLite: status=complete, all results
    Export: {scan_id}.json, {scan_id}.md

GET /api/scan/{scan_id}
    → client polls until status=complete or status=failed
```

---

## Data Models (Key)

```
ScanResult
  ├── scan_id, url, status, created_at, completed_at
  ├── data_categories: list[DataCategoryItem]
  ├── network_observations: list[NetworkObservation]
  ├── visited_pages: list[VisitedPageItem]
  ├── site_summary: SiteSummary
  ├── vendor_summary: list[VendorSummaryItem]
  ├── policy_analysis: PolicyAnalysis | None
  │     ├── url, operator_name, operator_contacts
  │     ├── has_*_section: bool (×8)
  │     ├── policy_signals: list[str]
  │     ├── policy_document_type: html | pdf | docx | doc
  │     └── policy_parse_status: parsed | unreadable | unsupported | failed
  ├── processor_map: list[ProcessorMapItem]
  │     └── source: observed_submit | inferred_public_signal | operator_supplied
  ├── fz152_assessment: FZ152Assessment | None
  │     ├── consent_mechanism_type, overall_public_risk_level
  │     ├── potential_gaps: list[str]
  │     └── manual_validation_targets: list[str]
  ├── synthetic_submission_summary: SyntheticSubmissionSummary | None
  ├── operator_integration_evidence: OperatorIntegrationEvidence | None
  └── operator_metadata: OperatorMetadata | None
```

---

## Security Properties

| Property | Implementation |
|---|---|
| SSRF prevention | `url_validation.py`: scheme allowlist, loopback / RFC1918 / link-local blocklist |
| No PII in logs | Logs only scan_id, URL, status transitions, error messages |
| No PII in exports | Only classification metadata; raw HTML and response bodies never stored |
| Same-host crawl only | Cross-domain links are never followed |
| Clean browser context | New context per scan; no persistent cookies or storage |
| UUID-only filenames | Screenshots / exports use server-generated scan_id |
| CORS lockdown | Explicit origin list (default: `localhost:5173`); no wildcard |
| Document download cap | 10 MB hard limit; 30 s timeout |

See `docs/THREAT_MODEL.md` for full threat analysis.
