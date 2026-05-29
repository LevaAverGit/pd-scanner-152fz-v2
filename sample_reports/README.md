# Sample Reports

This directory contains synthetic, redacted example outputs from PD Scanner.

All data here is **entirely fabricated** — the company names, URLs, contact details,
INN numbers, and all other specifics are fictional and do not represent any real
organisation or scan result.

These examples exist to:
1. Show the structure and depth of PD Scanner outputs without exposing real scan data
2. Demonstrate the export format to potential clients or evaluators

---

## Files

| File | Description |
|---|---|
| `example_report.md` | Synthetic Markdown export — full-featured scan of a fictional registration page |
| `example_result.json` | Synthetic JSON export — same scan as above, machine-readable format |

---

## How Real Reports Are Generated

When a scan completes, PD Scanner automatically exports:
- `exports/{scan_id}.json` — full structured result (all fields, all phases)
- `exports/{scan_id}.md` — human-readable Markdown report

These are also downloadable from the web UI on the scan details page.

The Markdown report includes sections for:
1. Scan metadata
2. Detected personal data categories (with confidence and matched signals)
3. Site summary (pages scanned, forms found, consent signals)
4. Third-party network observations
5. Vendor classification (analytics, ad-tech, CRM, etc.)
6. Policy / privacy page analysis (8-section table, document type, parse status)
7. Downstream processor map (with source labels: observed / inferred / operator-supplied)
8. 152-FZ public evidence summary (risk badge, gaps, manual validation checklist)
9. Synthetic submission findings (if mode was enabled)
10. Recommended manual follow-up
