# Architecture Decisions

This document records the key design choices and the reasoning behind them.

---

## Why FastAPI + Async

**Decision:** FastAPI backend with `async def` endpoints and `aiosqlite` for database access.

**Rationale:**
- The crawler is I/O-bound (HTTP requests, DOM evaluation via Playwright) — async
  allows efficient use of a single thread while waiting on network I/O
- FastAPI provides automatic request/response validation via Pydantic v2
- Background tasks (`fastapi.BackgroundTasks`) allow the scan to run after the
  HTTP response has been returned — scans can take 15–60 seconds, so the API
  must be non-blocking
- `aiosqlite` ensures database writes from the background task don't block the
  event loop

---

## Why Playwright for Crawling

**Decision:** Use Playwright (headless Chromium) rather than `requests` + BeautifulSoup.

**Rationale:**
- Modern registration pages are heavily JavaScript-driven — form fields are often
  injected by JS frameworks after page load; `requests` would miss them
- Playwright provides DOM access after JavaScript execution, capturing dynamically
  rendered forms, consent dialogs, and third-party script loads
- Network interception captures outbound requests to third-party hosts —
  critical for vendor detection

**Trade-off:** Playwright adds ~100MB of Chromium binaries and is slower than
a raw HTTP crawler. Justified by the significantly higher recall for JS-heavy sites.

---

## Why Bounded BFS (Max 20 Pages)

**Decision:** Crawl up to 20 pages using breadth-first search, same-host only.

**Rationale:**
- Registration forms are typically in the first 3–5 pages (homepage, /register, /login, /contact)
- A hard limit prevents the crawler from running indefinitely on large sites
- Same-host constraint prevents cross-site data leakage and unintended crawling of CDN URLs

**Trade-off:** Deep sites or apps that gate forms behind navigation will not be
fully covered. Accepted — the 20-page limit is clearly documented.

---

## Why SQLite (Not PostgreSQL)

**Decision:** `aiosqlite` with a local file, not a hosted database.

**Rationale:**
- Local-only tool — no server, no credentials, no network database required
- Single user, low write volume (one scan at a time) — SQLite is more than adequate
- `pd_scanner.db` is created automatically on first run, no setup required
- Auto-migration in `db.py` handles schema evolution idempotently

**Trade-off:** Not suitable for multi-user or multi-process deployment.
Acceptable for the intended use case (local analysis tool).

---

## Why Pydantic v2

**Decision:** All API models use Pydantic v2 (`BaseModel` with strict type annotations).

**Rationale:**
- Automatic request body validation at the API boundary — no manual `if not field` checks
- Serialisation to/from JSON for database storage is trivial (`model_dump()`, `model_validate()`)
- Type errors caught at startup (field type mismatches) rather than at runtime
- Pydantic v2 is significantly faster than v1 for validation-heavy applications

---

## Why Epistemic Labelling (Observed / Inferred / Operator-Supplied)

**Decision:** Every finding in the output is tagged with its provenance:
`observed`, `inferred`, or `operator_supplied`.

**Rationale:**
- The scanner makes claims of different confidence levels — a directly observed
  network request is different from a processor inferred from a form field pattern
- Conflating these would make the report misleading
- The label lets the analyst immediately know how much trust to place in a finding
- It is a standard practice in security and compliance evidence collection:
  "chain of custody" for each piece of evidence

---

## Why Rule-Based Classification (No LLM / AI)

**Decision:** All field classification, vendor detection, and policy section
analysis uses keyword matching and pattern rules, not ML or LLM inference.

**Rationale:**
- Deterministic — same URL always produces the same result; easy to test
- Auditable — every classification can be traced to a specific keyword match
- No external API dependency — tool works offline, no API keys, no costs
- Explainable to users — "Matched 'email' in field name attribute" is a clear
  justification

**Trade-off:** Lower recall for unusual field naming patterns and non-English
policy text. Keyword lists must be manually maintained.

---

## Known Limitations

- No rate limiting or request queuing — only one scan runs at a time in the current implementation
- No authentication — the API is localhost-only by design; adding auth would require
  additional session management
- DNS rebinding protection is partially deferred — host is validated at request time
  but not re-validated after DNS resolution
- Frontend TypeScript strict check passes, but some components use broad types
  that could be narrowed with more effort
