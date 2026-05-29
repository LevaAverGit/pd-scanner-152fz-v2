.PHONY: install dev-backend dev-frontend test type-check build verify format lint help

help:
	@echo "Available targets:"
	@echo "  install      — create venv, install backend deps, Playwright, frontend deps"
	@echo "  dev-backend  — FastAPI on port 8000 with hot reload"
	@echo "  dev-frontend — Vite dev server on port 5173"
	@echo "  test         — run backend pytest (303 tests)"
	@echo "  type-check   — frontend TypeScript strict check"
	@echo "  build        — frontend production build"
	@echo "  verify       — test + type-check + build in sequence"
	@echo "  lint         — ruff linter (non-blocking)"
	@echo "  format       — black + isort on backend/app/"

# Detect node binary: prefer system PATH, fall back to Homebrew locations.
NODE_BIN ?= $(shell which node 2>/dev/null || echo /opt/homebrew/opt/node/bin/node)
NODE_PATH := $(dir $(NODE_BIN))

install:
	python3.11 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt
	.venv/bin/playwright install chromium
	cd frontend && PATH="$(NODE_PATH):$$PATH" npm install

dev-backend:
	.venv/bin/uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && PATH="$(NODE_PATH):$$PATH" npm run dev

test:
	.venv/bin/pytest backend/tests/ -v

type-check:
	cd frontend && PATH="$(NODE_PATH):$$PATH" node_modules/.bin/tsc --noEmit

build:
	cd frontend && PATH="$(NODE_PATH):$$PATH" node_modules/.bin/vite build

# Run backend tests + frontend type-check + frontend build in sequence.
# All three must pass for a clean verification.
verify: test type-check build
	@echo ""
	@echo "✓ backend tests passed"
	@echo "✓ frontend type-check passed"
	@echo "✓ frontend build passed"

lint:
	.venv/bin/ruff check backend/app/ backend/tests/ || true

format:
	.venv/bin/black backend/app/ && .venv/bin/isort backend/app/
