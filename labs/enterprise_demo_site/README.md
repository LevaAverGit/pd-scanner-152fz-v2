# Enterprise Demo Lab — ДемоКорп

Controlled local test-lab website for PD Scanner privacy compliance scanning.

## Quick Start

```bash
cd labs/enterprise_demo_site

# Install dependencies (if not already in venv)
make install

# Start on port 8001
make run
```

Open: http://localhost:8001

Admin panel: http://localhost:8001/admin/login (password set via `LAB_ADMIN_PASSWORD` env var, default: `demo-lab-only`)

## Profile Modes

Switch profile via API (while server is running):

```bash
# Good compliance — explicit consent, full policy, first-party only
make profile-good

# Mixed compliance — bundled consent, partial policy, webhook routing
make profile-mixed

# Bad compliance — no consent, no privacy link on forms, CRM routing
make profile-bad
```

Or directly:
```bash
curl -X POST http://localhost:8001/api/profile/good_compliance
```

## Run Tests

```bash
# From labs/enterprise_demo_site/
make test
# or
../../.venv/bin/pytest tests/ -v
```

## Architecture

- FastAPI + Jinja2 + SQLite (aiosqlite)
- Port: **8001** (main PD Scanner app runs on 8000)
- DB: `backend/data/lab.db`
- Profile config: `backend/data/profile.json`
- Generated policy files: `backend/generated_policies/`
