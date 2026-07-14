# PD Scanner

[![CI](https://github.com/LevaAverGit/pd-scanner-152fz-v2/actions/workflows/ci.yml/badge.svg)](https://github.com/LevaAverGit/pd-scanner-152fz-v2/actions/workflows/ci.yml)

A local-first web application for privacy compliance pre-analysis of public websites.
Given a URL, PD Scanner launches a headless browser, crawls the site, classifies
personal data collection points, and produces structured evidence reports aligned with
Russian Federal Law 152-FZ "On Personal Data" and general data protection principles.

All analysis runs locally. No data leaves your machine.

---

## What PD Scanner Does

- **Crawls** up to 20 pages of a public site (bounded same-site BFS)
- **Detects** form fields collecting personal data and classifies them into 12 categories
- **Observes** outbound network requests and classifies third-party hosts by vendor type
- **Detects** privacy links, consent checkboxes, marketing consent, and bundled consent text
- **Parses** linked policy pages — HTML, PDF, and DOCX — for 8 standard policy sections
- **Infers** downstream data processors from form action URLs, scripts, and network patterns
- **Builds** a structured 152-FZ evidence layer: risk level, policy gaps, manual validation targets
- **Exports** full findings as JSON and Markdown reports
- **Screenshots** the seed URL for visual record

---

## What PD Scanner Does NOT Do

| Boundary | Why |
|---|---|
| Does not submit real personal data into forms | Safety by design — only synthetic placeholder values are used when synthetic mode is explicitly enabled |
| Does not bypass CAPTCHA | Never attempts any CAPTCHA circumvention |
| Does not bypass authentication | Login-gated pages are out of scope |
| Does not follow external links | Same-host only; no cross-domain crawling |
| Does not claim definitive legal compliance | All findings are heuristic public-signal observations; legal conclusions require expert analysis |
| Rule-based heuristic classification | No external LLM or AI API dependency; all classification is deterministic and auditable |
| Does not store data remotely | SQLite database is local-only |
| Does not scan private IP ranges | SSRF guard blocks all private/loopback/link-local addresses |

---

## Why Observed / Inferred / Operator-Supplied Separation Matters

Every finding in PD Scanner is clearly labelled by its epistemic status:

- **`observed`** — directly seen by the scanner (e.g., a network request to `analytics.google.com`, a form action pointing to HubSpot)
- **`inferred`** — derived from public signals with stated confidence (e.g., a hidden form field with `portalId` suggests HubSpot even if not confirmed)
- **`operator_supplied`** — provided by the operator (e.g., `integration_evidence.crm_destination = "Bitrix24"`)

This separation matters because:
1. It makes the provenance of every claim transparent and auditable
2. It prevents conflating speculation with observation in audit reports
3. It allows operator-supplied context to enrich findings without being confused with scanner observations

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, Playwright (async), aiosqlite |
| Data models | Pydantic v2 |
| PDF extraction | PyMuPDF (fitz) |
| DOCX extraction | python-docx |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Database | SQLite (local file, auto-migrated) |
| Tests | pytest-asyncio, httpx ASGITransport |

---

## Engineering Highlights

- **Async pipeline** — FastAPI + Playwright + aiosqlite; scan runs as a background task so the API returns immediately; no blocking I/O in the event loop
- **Bounded BFS crawler** — same-host only, max 20 pages; SSRF guard resolves hostnames and blocks RFC1918, loopback, and link-local before any outbound request
- **Layered analysis** — DOM classification → vendor detection → consent signals → policy parsing (HTML + PDF + DOCX) → 152-FZ evidence synthesis; each layer is independently testable
- **Epistemic labelling** — every finding is tagged `observed`, `inferred`, or `operator_supplied`; provenance is preserved through the full data model and reports
- **Pydantic v2 throughout** — all API inputs/outputs, database models, and inter-service data pass through Pydantic validation; no stringly-typed result handling
- **303 tests, 0 warnings** — in-process HTTP via `httpx.ASGITransport`; per-test DB isolation via `tmp_path` + `patch`; no real network calls in tests

## Backend Architecture

```
POST /api/scan
  ↓
URL Validation (SSRF guard, scheme check)
  ↓
Scan record persisted (status=pending) → HTTP 200 returned
  ↓ [background task]
Playwright BFS crawler (up to 20 pages, same-host)
  │
  ├── DOM Parser → form fields, links
  ├── PD Classifier → DataCategoryItem list
  ├── Consent Detector → checkbox / bundled text / absent
  ├── Vendor Classifier → VendorSummaryItem list
  └── Network Capture → third-party hosts
  ↓
Policy Parser (HTML/PDF/DOCX) → PolicyAnalysis
  ↓
Integration Audit → ProcessorMapItem list
  ↓
152-FZ Assessment → FZ152Assessment (risk level, gaps, targets)
  ↓
Screenshot + Report export (JSON + Markdown)
  ↓
Scan record updated (status=complete)
```

## API and Data Flow

| Endpoint | Method | Description |
|---|---|---|
| `/api/scan` | POST | Submit URL; returns `scan_id` immediately |
| `/api/scan/{id}` | GET | Poll for results; returns full `ScanResult` when complete |
| `/api/scan/diff` | POST | Compare two completed scans |
| `/api/history` | GET | Paginated scan history |
| `/api/history/{id}` | DELETE | Delete scan record and files |
| `/api/health` | GET | Liveness check |

See `docs/API_OVERVIEW.md` for request/response examples and error handling.
See `docs/DATA_FLOW.md` for the full stage-by-stage pipeline breakdown.

## Testing Strategy

```bash
make test        # 303 backend tests
make type-check  # TypeScript strict check
make verify      # both + frontend build
```

All backend tests use `httpx.ASGITransport` (no real server) and isolated
SQLite databases via `tmp_path` + `unittest.mock.patch`. The 2 Playwright tests
use a local fixture server.

See `docs/QUALITY_ASSURANCE.md` for the full test strategy and patterns.

## Why This Project Matters for Developer Roles

- **Full-stack implementation**: async Python API + React TypeScript frontend + SQLite
- **Non-trivial backend pipeline**: multi-stage async processing with distinct service boundaries
- **Production-oriented design decisions**: SSRF guard, local-only storage, epistemic labelling,
  safety gates — each documented with rationale in `docs/ARCHITECTURE_DECISIONS.md`
- **Test discipline**: 303 tests, in-process HTTP testing, per-test DB isolation — testable
  architecture, not just coverage numbers
- **Domain understanding**: 152-FZ requirements translated into detectable signals with
  explicit limitations — shows the ability to scope and build a tool that is honest
  about what it can and cannot do

---

## Prerequisites

| Dependency | Version | Install |
|---|---|---|
| Python | 3.11+ | `brew install python@3.11` or [python.org](https://www.python.org/) |
| Node.js | 18+ | `brew install node` or [nodejs.org](https://nodejs.org/) |
| make | any | pre-installed on macOS / Linux |

---

## Setup

> **Python 3.11+ is required.** The codebase uses `str | None` union syntax and other Python 3.10+ features. Running with Python 3.9 or earlier will fail at import time.
>
> If you use pyenv:
> ```bash
> pyenv install 3.11
> pyenv local 3.11
> python -m venv .venv
> ```

```bash
# Create Python venv, install all backend deps,
# install Playwright Chromium, install frontend deps
make install
```

---

## Run

**Terminal 1 — backend** (FastAPI on port 8000):
```bash
make dev-backend
```

**Terminal 2 — frontend** (Vite dev server on port 5173):
```bash
make dev-frontend
```

Open **http://localhost:5173** in your browser.

---

## Demo Flow

1. Start backend + frontend
2. Open http://localhost:5173
3. Paste a public registration page URL (e.g. a company's `/register` or `/signup` page)
4. Click **Scan**
5. Wait 10–30 seconds for the crawler to finish
6. View: detected data categories, vendor observations, policy analysis, 152-FZ risk assessment
7. Download JSON or Markdown report from the Export section

---

## Tests

```bash
make test          # backend tests (303 tests)
make type-check    # frontend TypeScript strict check
make build         # frontend production build
make verify        # all three in sequence — full clean check
```

**Current status: 303 tests, 0 warnings.**

Coverage:
- **API**: health, scan create/get, history, delete, SSRF URL validation (loopback, RFC1918, link-local all blocked)
- **Classifier**: 12 data categories, confidence scoring, false-positive guard
- **Page classifier**: registration relevance, page-type detection
- **Vendor classification**: analytics, ad-tech, CDN, payment, tracker patterns
- **Policy parser**: section detection, operator name / contact extraction
- **Synthetic submission**: safety gates (CAPTCHA block, max-submissions cap, sensitive field detection)
- **Downstream processor inference**: operator evidence schema, processor map building
- **152-FZ assessment**: consent mechanism typing, risk scoring, gap generation
- **Document parsing**: PDF / DOCX type detection, text extraction, parse-status propagation

---

## Configuration

Backend settings via environment variables (all optional, prefix `PD_`):

| Variable | Default | Description |
|---|---|---|
| `PD_DB_PATH` | `pd_scanner.db` | SQLite database file path |
| `PD_CORS_ORIGINS` | `["http://localhost:5173"]` | Allowed CORS origins |
| `PD_LOG_LEVEL` | `INFO` | Logging level |
| `PD_ALLOW_LOCAL_TEST_TARGETS` | `false` | Allow localhost / 127.x — **local fixture testing only, never in production** |

---

## API Reference

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/scan` | Submit URL for scanning |
| `GET` | `/api/scan/{scan_id}` | Poll for results |
| `GET` | `/api/history` | Paginated scan history (`limit`, `offset`) |
| `DELETE` | `/api/history/{scan_id}` | Delete a scan record |
| `GET` | `/api/health` | Liveness check → `{"status": "ok"}` |

`POST /api/scan` request body:
```json
{
  "url": "https://example.com/register",
  "notes": "optional free-text notes",
  "enable_synthetic_submission": false,
  "integration_evidence": null,
  "operator_metadata": null
}
```

`integration_evidence` and `operator_metadata` accept operator-supplied context
(CRM platform, webhook URLs, legal name, INN) that is clearly labelled
`operator_supplied` in all outputs — never mixed with scanner observations.

---

## Project Structure

```
pd-scanner-152fz/
├── backend/
│   ├── app/
│   │   ├── main.py                           FastAPI app factory
│   │   ├── api/routes_scan.py                Scan endpoints
│   │   ├── api/routes_history.py             History endpoints
│   │   ├── core/config.py                    pydantic-settings (PD_ prefix)
│   │   ├── models/schemas.py                 All Pydantic v2 models
│   │   ├── models/db.py                      aiosqlite + auto-migration
│   │   └── services/
│   │       ├── scanner_service.py            Full pipeline orchestrator
│   │       ├── crawler_service.py            Bounded BFS crawler
│   │       ├── classifier_service.py         PD field classifier
│   │       ├── consent_detection_service.py  Consent signals
│   │       ├── vendor_classification_service.py  Vendor types
│   │       ├── policy_parser_service.py      Policy page + doc routing
│   │       ├── document_extraction_service.py   PDF / DOCX extraction
│   │       ├── synthetic_submission_service.py  Controlled form submission
│   │       ├── integration_audit_service.py  Processor inference
│   │       ├── fz152_assessment_service.py   152-FZ evidence builder
│   │       └── report_service.py             JSON + Markdown export
│   ├── tests/                                303 tests, 0 warnings
│   └── requirements.txt
├── frontend/
│   ├── src/pages/DashboardPage.tsx
│   ├── src/pages/ScanDetailsPage.tsx
│   ├── src/components/                       PolicyAnalysisPanel, FZ152AssessmentPanel, …
│   └── package.json
├── docs/
│   ├── ARCHITECTURE.md
│   ├── THREAT_MODEL.md
│   ├── PRD.md
│   ├── 152FZ_CHECKLIST.md
│   ├── EVIDENCE_MODEL.md
│   ├── PRIVACY_AUDIT_MAPPING.md
│   └── RISK_SCORING.md
├── sample_reports/
│   ├── example_report.md
│   └── example_result.json
├── pytest.ini
├── Makefile
└── README.md
```

---

## Documentation

| Document | Description |
|---|---|
| [`docs/API_OVERVIEW.md`](docs/API_OVERVIEW.md) | Endpoints, request/response examples, async scan lifecycle, error handling |
| [`docs/DATA_FLOW.md`](docs/DATA_FLOW.md) | Full stage-by-stage pipeline: URL → crawler → classification → export |
| [`docs/EXTENDING_SCANNER.md`](docs/EXTENDING_SCANNER.md) | How to add PD categories, vendor signatures, policy sections, tests |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System architecture, component breakdown, pipeline diagram |
| [`docs/ARCHITECTURE_DECISIONS.md`](docs/ARCHITECTURE_DECISIONS.md) | Why the architecture was designed this way (async, Playwright, SQLite, rule-based) |
| [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md) | Trust boundaries, SSRF guard, synthetic submission safety |
| [`docs/QUALITY_ASSURANCE.md`](docs/QUALITY_ASSURANCE.md) | Test strategy, patterns, DB isolation, manual validation checklist |
| [`docs/152FZ_CHECKLIST.md`](docs/152FZ_CHECKLIST.md) | 152-FZ signal checklist with article mapping and limitations |
| [`docs/EVIDENCE_MODEL.md`](docs/EVIDENCE_MODEL.md) | Evidence types, confidence model, and what each finding represents |
| [`docs/PRIVACY_AUDIT_MAPPING.md`](docs/PRIVACY_AUDIT_MAPPING.md) | How scanner output maps to structured privacy audit phases |
| [`docs/RISK_SCORING.md`](docs/RISK_SCORING.md) | Heuristic risk scoring: factors, weights, thresholds |
| [`docs/INTERVIEW_NOTES.md`](docs/INTERVIEW_NOTES.md) | Interview pitch and Q&A with strict scope/limitations framing |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Setup, running tests, adding categories/vendors/sections |

---

## Use Case

PD Scanner automates the public-site evidence collection phase of a 152-FZ or GDPR
pre-audit. An analyst can scan a client's registration flow in under a minute and receive
a structured report showing: what personal data is collected, via which forms, routed to
which third parties, with what consent mechanism, against what published policy.

The 152-FZ assessment layer highlights potential gaps for manual follow-up — replacing
30–60 minutes of manual browser inspection per site.

---

## How This Maps to Real Privacy Compliance Work

Privacy compliance under 152-FZ requires evidence collection, gap analysis, and
structured reporting. This tool automates the evidence collection phase against the
publicly observable layer of a website.

| This tool | Real compliance workflow |
|---|---|
| Bounded BFS crawler | Evidence gathering scope (in-scope URLs) |
| PD category classifier | PD inventory — what data is collected and where |
| Consent signal detection | Consent mechanism review |
| Policy section flags | Privacy policy adequacy review |
| Vendor / processor map | Third-party and processor register (Art. 6(4)) |
| 152-FZ gap list | Preliminary gap analysis for legal review |
| `manual_validation_targets` | Audit findings requiring specialist follow-up |
| JSON / Markdown export | Audit evidence package |

See [`docs/PRIVACY_AUDIT_MAPPING.md`](docs/PRIVACY_AUDIT_MAPPING.md) for a
full phase-by-phase breakdown.

---

## What This Project Demonstrates for Security Roles

- Practical 152-FZ knowledge: Articles 6, 9, 12, 14, 18.1, 21 translated into
  heuristic detection logic
- Privacy-by-design principles: SSRF guard, no real data submission, local-only storage,
  epistemic labelling of findings
- Evidence model design: observed vs. inferred vs. operator-supplied distinction
  maintained throughout the data model
- Full-stack implementation: async Python pipeline + React TypeScript UI + SQLite
- Test discipline: 303 tests with async fixtures, DB isolation via tmp_path + patch,
  comprehensive coverage of all detection layers
- Structured reporting: compliance-oriented output for both technical and non-technical audiences

---

## Known Limitations

- BFS crawler is bounded at 20 pages / depth 2 — deep sites are partially covered
- JavaScript-heavy SPAs requiring interaction to reveal forms may not be fully captured
- Classifier relies on field `name`, `id`, `label`, `placeholder`, `aria-label`; obfuscated attributes reduce accuracy
- PDF / DOCX policy parsing requires a text layer; image-only scanned PDFs return `unreadable` status
- Synthetic submission is off by default; when enabled, only clearly synthetic values are submitted with strict safety gates
- No rate limiting, multi-user support, or remote deployment hardening
- DNS rebinding is not defended against (post-resolution host validation is deferred)

---

## Safety Disclaimer

PD Scanner is a **read-only analysis tool** by default:

- Analyses only URLs you explicitly provide
- Never submits real personal data
- Never bypasses authentication or CAPTCHA
- Never follows links to external domains
- Stores all output locally on your machine
- Intended for use on publicly accessible pages only

When `enable_synthetic_submission: true` is set, only clearly synthetic placeholder
values are used (e.g. `test@example.invalid`), submissions are blocked on CAPTCHA /
payment / sensitive-field pages, and only request metadata (no bodies, no cookies) is
captured.

---

## Legal / Compliance Disclaimer

This tool performs **heuristic technical analysis only**.

- It does **not** determine legal compliance with 152-FZ or any other regulation.
- It does **not** replace a legal, DPO, or professional compliance audit.
- All findings are potential risk indicators that require manual validation.
- No output constitutes a legal opinion or a guarantee of regulatory conformance.
- The tool is intended for educational, portfolio, and pre-audit assistance purposes.
