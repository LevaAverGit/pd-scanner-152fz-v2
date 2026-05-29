# PD Scanner — Threat Model

## Scope

PD Scanner is a local-first tool designed for use by a single trusted operator on their
own workstation. It is not exposed to the internet. The backend binds to `0.0.0.0`
(configurable) but is intended for localhost use only. The attack surface is: URLs
submitted by the operator, the local file system (SQLite, screenshots, exports), the
headless browser subprocess, and downloaded policy documents.

This threat model covers the local deployment scenario only. Network-exposed or
multi-user deployments are explicitly out of scope and unsupported.

---

## Threats and Mitigations

### SSRF (Server-Side Request Forgery)

**Description:** The backend accepts a user-supplied URL and instructs Playwright to
fetch it. Without validation, an attacker could submit URLs pointing to internal network
services, cloud metadata endpoints, or `localhost` ports.

**Mitigations applied (Phases 2–6):**
- `url_validation.py` enforces scheme allowlist (`http`, `https` only) — rejects `file://`, `ftp://`, etc.
- Blocks loopback hosts: `localhost`, `0.0.0.0`, `::1`
- Blocks full `127.0.0.0/8` loopback range (all `127.x.x.x`, not just `127.0.0.1`)
- Blocks link-local range `169.254.0.0/16` — covers AWS/GCP/Azure metadata endpoints (`169.254.169.254`)
- Blocks RFC1918 private ranges: `10.x`, `172.16–31.x`, `192.168.x`
- Validation runs before the DB record is created — blocked URLs never reach Playwright
- Returns HTTP 422 with a descriptive error on blocked input
- `PD_ALLOW_LOCAL_TEST_TARGETS=true` exempts only `localhost` and `127.x` (for local fixture testing); link-local and RFC1918 remain blocked unconditionally

**Residual risk:**
- DNS rebinding: a hostname that resolves to a public IP at validation time but later
  resolves to a private IP is not defended against. Post-resolution host validation
  would require intercepting Playwright's DNS resolution — deferred.

---

### Path Traversal

**Description:** When saving screenshots or exports, paths derived from scan IDs could
theoretically allow writes outside the intended output directory.

**Mitigations applied:**
- Output filenames are constructed exclusively from server-generated UUIDs
  (`{scan_id}.png`, `{scan_id}.json`, `{scan_id}.md`)
- No user-supplied string is used as any part of a filename
- Output directories (`screenshots/`, `exports/`) are constants

**Residual risk:** Output directories are relative to the server's working directory.
If the server is started from an unexpected working directory, output goes there.
Absolute path enforcement via `Path(__file__).parent` is deferred.

---

### Unsafe Browser Automation

**Description:** A headless Chromium process executing arbitrary JavaScript from an
attacker-controlled page could attempt to exfiltrate local data.

**Design constraints (by design, Phases 3+):**
- No form submission is performed by default
- No credentials or personal data are entered into any field
- No stealth or anti-detection techniques are used
- No CAPTCHA bypass is attempted
- Same-host only — cross-domain links are never followed
- A clean browser context is created per scan (no persistent cookies or local storage)
- Page navigation timeout is capped at 20 seconds

**Synthetic submission mode:**
- Only clearly synthetic placeholder values are submitted
- Submission is blocked on CAPTCHA, payment fields, file uploads, sensitive data patterns
- Maximum 1 submission per page, 3 per scan
- Only POST request metadata (URL, method) is captured — no response bodies, no cookies

---

### Document Download Safety

**Description:** Downloading and processing third-party PDF or DOCX files introduces
a parsing attack surface.

**Mitigations applied:**
- Downloads are bounded at 10 MB — oversized documents are rejected
- Downloads use a 30-second timeout
- Only text content is extracted; no macros are executed, no scripts are evaluated
- PyMuPDF (`fitz`) opens PDFs in a read-only text extraction mode; no form fields are filled
- python-docx opens DOCX in a read-only paragraph/table traversal mode
- Document URLs are subject to the same SSRF validator as scan URLs (same-host enforcement in `parse_policy_page`)

---

### Over-collection of Network Metadata

**Description:** Network request observation could capture sensitive data in request
headers, cookies, or POST bodies from background requests made by the scanned page.

**Mitigations applied:**
- `network_capture.py` collects only: host, resource_type, method, is_third_party
- Request and response bodies are never captured
- Query strings are not stored
- Observation count is capped at 50 per scan
- Collected via Playwright's request event listener (read-only, no interception)

---

### Sensitive Data in Logs

**Description:** Debug logging of raw HTML, page source, or field values could write
personal-data-adjacent content to log files.

**Mitigations applied:**
- Raw HTML is not stored in the database and not logged at any level
- Extracted field label text is not persisted to SQLite (only classification metadata)
- Log level defaults to `INFO`; `DEBUG` does not include page content
- `scanner_service.py` logs only scan_id, URL, status transitions, and error messages

---

### CORS Misconfiguration

**Description:** A wildcard CORS policy would allow any web page visited by the operator
to make credentialed requests to the local API.

**Mitigations applied:**
- CORS is configured with an explicit origin list: `["http://localhost:5173"]` (default)
- Configurable via `PD_CORS_ORIGINS` environment variable
- Wildcard origin is never set as a default

**Residual risk:** The explicit origins list is not validated for safety at startup — a
user could set `PD_CORS_ORIGINS=["*"]` via env var. Startup validation is deferred.

---

## Summary Table

| Threat | Status |
|---|---|
| SSRF — scheme allowlist | **Applied** |
| SSRF — loopback block (full 127.0.0.0/8) | **Applied** |
| SSRF — RFC1918 private range block | **Applied** |
| SSRF — link-local / metadata endpoint block (169.254.x) | **Applied** |
| SSRF — DNS rebinding | **Residual** (deferred) |
| Path traversal — UUID-only filenames | **Applied** |
| Path traversal — absolute output paths | **Residual** (deferred) |
| Unsafe browser automation — no credentials, no submission | **Applied** (by design) |
| Synthetic submission safety gates | **Applied** |
| Document download — size cap + no macro execution | **Applied** |
| Over-collection of network metadata | **Applied** |
| Sensitive data in logs | **Applied** |
| CORS misconfiguration | **Applied** |
| CORS env-var wildcard regression | **Residual** (deferred) |
