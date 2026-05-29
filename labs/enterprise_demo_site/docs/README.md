# Enterprise Demo Lab — Documentation

## Purpose

This lab provides a realistic Russian B2B enterprise website that PD Scanner can be run against.
It simulates three compliance states (good / mixed / bad) controlled by a profile mode.

## Install & Run

```bash
cd labs/enterprise_demo_site
make install        # install deps into shared venv
make run            # start on port 8001
make test           # run pytest suite
```

## PD Scanner Scenarios

### Scenario A — Good Compliance (good_compliance)
1. `curl -X POST http://localhost:8001/api/profile/good_compliance`
2. Run PD Scanner against http://localhost:8001
3. Expected findings: explicit consent checkboxes present, privacy policy accessible (HTML/PDF/DOCX), all 8 sections present, first-party routing only, no tracking pixel.

### Scenario B — Mixed Compliance (mixed_compliance)
1. `curl -X POST http://localhost:8001/api/profile/mixed_compliance`
2. Run PD Scanner against http://localhost:8001
3. Expected findings: bundled consent text (no checkbox), policy partially complete (missing sections 5, 7, 8), webhook routing to secondary endpoint.

### Scenario C — Bad Compliance (bad_compliance)
1. `curl -X POST http://localhost:8001/api/profile/bad_compliance`
2. Run PD Scanner against http://localhost:8001
3. Expected findings: no consent mechanism, no privacy link on forms, privacy policy missing from footer, CRM third-party routing, tracking pixel present.

## Admin Panel

URL: http://localhost:8001/admin/login
Password: set via `LAB_ADMIN_PASSWORD` env var (default for local lab: `demo-lab-only`)

Pages:
- `/admin/submissions` — all form submissions with consent/profile info
- `/admin/routing-log` — data routing events per submission
- `/admin/consent-log` — consent capture events
- `/admin/processors` — processor/vendor events
