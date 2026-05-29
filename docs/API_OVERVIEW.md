# API Overview

The backend exposes a REST API on `http://localhost:8000`.
All endpoints return JSON. The frontend communicates exclusively with this API.

---

## Endpoints

### POST /api/scan

Submit a URL for scanning. Returns immediately with a `scan_id`. The scan
runs as a FastAPI background task.

**Request body:**
```json
{
  "url": "https://example.com/register",
  "notes": "optional free-text notes",
  "enable_synthetic_submission": false,
  "integration_evidence": null,
  "operator_metadata": null
}
```

**Response:**
```json
{
  "scan_id": "abc123",
  "url": "https://example.com/register",
  "status": "pending",
  "created_at": "2026-05-25T10:00:00Z"
}
```

**Status codes:**
- `200` — scan accepted and started
- `422` — validation error (bad URL, unsafe target, missing field)

---

### GET /api/scan/{scan_id}

Poll for scan results. Call repeatedly until `status` is `complete` or `failed`.

**Response (pending):**
```json
{
  "scan_id": "abc123",
  "status": "running",
  "url": "https://example.com/register"
}
```

**Response (complete):**
```json
{
  "scan_id": "abc123",
  "status": "complete",
  "url": "https://example.com/register",
  "created_at": "2026-05-25T10:00:00Z",
  "completed_at": "2026-05-25T10:00:22Z",
  "data_categories": [...],
  "vendor_summary": [...],
  "processor_map": [...],
  "fz152_assessment": {...},
  "site_summary": {...},
  "registration_relevance": "medium"
}
```

**Status codes:**
- `200` — scan found
- `404` — scan ID not found

---

### GET /api/history

Paginated list of past scans.

**Query parameters:**
- `limit` (int, default 20) — number of results
- `offset` (int, default 0) — pagination offset

**Response:**
```json
{
  "items": [
    {
      "scan_id": "abc123",
      "url": "https://example.com",
      "status": "complete",
      "created_at": "..."
    }
  ],
  "total": 42
}
```

---

### DELETE /api/history/{scan_id}

Delete a scan record and its associated files (screenshot, exports).

**Status codes:**
- `200` — deleted
- `404` — not found

---

### POST /api/scan/diff

Compare two completed scans.

**Request body:**
```json
{
  "base_scan_id": "abc123",
  "compare_scan_id": "def456"
}
```

**Response:** `ScanDiffResult` with `added_categories`, `removed_categories`,
`added_vendors`, `removed_vendors`, `changed_items`, `summary_lines`.

**Status codes:**
- `200` — diff computed
- `404` — base or compare scan not found
- `422` — validation error

---

### GET /api/health

Liveness check.

**Response:** `{"status": "ok"}`

---

## Async Scan Lifecycle

```
POST /api/scan
  → validate URL (SSRF guard, scheme check)
  → persist scan record with status="pending"
  → start background task (scanner_service.run_scan)
  → return scan_id immediately

Background task:
  → set status="running"
  → crawl (BFS, up to 20 pages, Playwright)
  → classify fields, detect consent signals
  → detect vendors, infer processors
  → parse policy document
  → build 152-FZ assessment
  → take screenshot
  → generate exports (JSON + Markdown)
  → set status="complete" and persist full result

GET /api/scan/{scan_id}
  → read from SQLite
  → return current state
```

The frontend polls `GET /api/scan/{scan_id}` on a 2-second interval until
status is `complete` or `failed`.

---

## Error Handling

| Scenario | HTTP status | `detail` field |
|---|---|---|
| URL blocked by SSRF guard | 422 | `"URL targets a private or loopback address"` |
| Non-HTTP(S) scheme | 422 | `"URL must use http or https scheme"` |
| Scan ID not found | 404 | `"Scan {id} not found"` |
| Scanner internal error | 500 (logged) | Scan status set to `failed` with error message |
| Missing required field | 422 | Standard Pydantic validation error |

---

## URL Validation

All submitted URLs are validated by `backend/app/services/url_validation.py`:
- Must use `http` or `https` scheme
- Hostname must not resolve to RFC1918, loopback (127.x, ::1), or link-local addresses
- This guard prevents SSRF — the backend never makes outbound requests to internal networks

---

## Static File Mounts

The FastAPI app mounts two static directories:
- `/screenshots/{scan_id}.png` — screenshot taken at scan time
- `/exports/{scan_id}.{md|json}` — generated report files

These are served directly from the filesystem, not via API routes.
