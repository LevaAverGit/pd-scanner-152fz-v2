# Developer Guide

## Repository Structure

```
pd-scanner-152fz/
├── backend/
│   ├── app/
│   │   ├── main.py                      FastAPI app factory, router mounts, lifespan
│   │   ├── api/
│   │   │   ├── routes_scan.py           POST /api/scan, GET /api/scan/{id}, diff
│   │   │   └── routes_history.py        GET /api/history, DELETE /api/history/{id}
│   │   ├── core/
│   │   │   ├── config.py                pydantic-settings (PD_ env vars)
│   │   │   └── logging.py               Structured JSON logger config
│   │   ├── models/
│   │   │   ├── schemas.py               All Pydantic v2 models (ScanRequest, ScanResult, ...)
│   │   │   └── db.py                    aiosqlite pool, init_db, auto-migration
│   │   ├── services/
│   │   │   ├── scanner_service.py       Full pipeline orchestrator
│   │   │   ├── crawler_service.py       Playwright BFS crawler
│   │   │   ├── classifier_service.py    PD field classification
│   │   │   ├── consent_detection_service.py   Consent signals
│   │   │   ├── vendor_classification_service.py  Vendor types + processor map
│   │   │   ├── policy_parser_service.py      Policy page routing
│   │   │   ├── document_extraction_service.py   PDF (PyMuPDF) + DOCX (python-docx)
│   │   │   ├── synthetic_submission_service.py  Controlled form submission
│   │   │   ├── integration_audit_service.py     Processor inference
│   │   │   ├── fz152_assessment_service.py      152-FZ evidence builder
│   │   │   ├── report_service.py               JSON + Markdown export
│   │   │   ├── scan_diff_service.py            Compare two scan results
│   │   │   └── url_validation.py               SSRF guard + scheme check
│   │   └── utils/
│   │       ├── pd_dictionary.py         PD_CATEGORIES keyword dictionary
│   │       ├── patterns.py              Compiled regex patterns
│   │       └── normalization.py         Field signal extraction utilities
│   ├── tests/
│   │   ├── fixtures/
│   │   │   └── form_server.py           FastAPI fixture server for Playwright tests
│   │   └── test_*.py                   303 tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx                      Router, layout
│   │   ├── pages/
│   │   │   ├── DashboardPage.tsx
│   │   │   └── ScanDetailsPage.tsx
│   │   └── components/                  Panel components (FZ152, Policy, Vendors, ...)
│   ├── package.json
│   └── tsconfig.json
├── docs/
│   ├── ARCHITECTURE.md                  System architecture diagram
│   ├── ARCHITECTURE_DECISIONS.md        Design rationale
│   ├── THREAT_MODEL.md                  Trust boundaries, SSRF, safety design
│   ├── API_OVERVIEW.md                  Endpoints, request/response, lifecycle
│   ├── DATA_FLOW.md                     Full pipeline data flow
│   ├── EXTENDING_SCANNER.md            How to add categories, vendors, sections
│   ├── QUALITY_ASSURANCE.md            Test strategy and patterns
│   ├── 152FZ_CHECKLIST.md              152-FZ signal checklist
│   ├── EVIDENCE_MODEL.md               Evidence types and confidence
│   ├── PRIVACY_AUDIT_MAPPING.md        Compliance audit methodology mapping
│   └── RISK_SCORING.md                 Heuristic risk scoring model
├── sample_reports/
├── labs/enterprise_demo_site/           Local demo target site for development
├── Makefile
├── pytest.ini
├── pyproject.toml
└── CONTRIBUTING.md
```

---

## Setup

```bash
make install    # venv + backend deps + Playwright + frontend deps
```

---

## Common Commands

```bash
make dev-backend    # FastAPI on port 8000 with hot reload
make dev-frontend   # Vite dev server on port 5173

make test           # 303 backend tests
make type-check     # TypeScript strict check
make build          # Frontend production build
make verify         # all three in sequence

make format         # black + isort on backend/app/
```

---

## Adding a New Feature (Backend)

1. Add Pydantic model to `backend/app/models/schemas.py`
2. Add service function to `backend/app/services/`
3. Wire into `scanner_service.py` if part of the scan pipeline
4. Add API route to `backend/app/api/routes_scan.py` if exposed via API
5. Write tests using `ASGITransport` pattern
6. Run `make verify`

---

## Debugging

Run a scan against the local demo site:

```bash
# Terminal 1: start demo site
cd labs/enterprise_demo_site && python3 -m uvicorn backend.app.main:app --port 3001

# Terminal 2: start scanner backend (with local targets allowed)
PD_ALLOW_LOCAL_TEST_TARGETS=true make dev-backend

# Submit scan via API
curl -s -X POST http://localhost:8000/api/scan \
  -H "Content-Type: application/json" \
  -d '{"url": "http://localhost:3001/register"}' | python3 -m json.tool
```

Run a specific test with verbose output:

```bash
.venv/bin/pytest backend/tests/test_classifier.py -v
.venv/bin/pytest backend/tests/test_api.py::TestScanAPI::test_ssrf_blocked -v
```

---

## Module Relationships

```
routes_scan.py
  ↓ calls
  scanner_service.py              ← pipeline orchestrator
    ├── crawler_service.py        ← Playwright BFS
    │   ├── dom_parser.py
    │   └── network_capture.py
    ├── classifier_service.py     ← PD category detection
    │   └── pd_dictionary.py
    ├── consent_detection_service.py
    ├── vendor_classification_service.py
    ├── policy_parser_service.py
    │   └── document_extraction_service.py
    ├── integration_audit_service.py
    ├── fz152_assessment_service.py  ← synthesises all findings
    ├── screenshot_service.py
    └── report_service.py

models/db.py      ← SQLite persistence, used by routes and scanner
models/schemas.py ← shared by all services
core/config.py    ← settings, used by db.py and scanner_service.py
```
