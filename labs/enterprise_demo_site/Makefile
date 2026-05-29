VENV := ../../.venv
PYTHON := $(VENV)/bin/python3
UVICORN := $(VENV)/bin/uvicorn
PYTEST := $(VENV)/bin/pytest
PORT := 8001

install:
	$(VENV)/bin/pip install -r requirements.txt

run:
	cd backend && $(UVICORN) app.main:app --host 0.0.0.0 --port $(PORT) --reload

test:
	$(PYTEST) tests/ -v

profile-good:
	curl -s -X POST http://localhost:$(PORT)/api/profile/good_compliance

profile-mixed:
	curl -s -X POST http://localhost:$(PORT)/api/profile/mixed_compliance

profile-bad:
	curl -s -X POST http://localhost:$(PORT)/api/profile/bad_compliance

generate-policies:
	cd backend && $(PYTHON) -c "from app.policy_generator import generate_all; generate_all(); print('Policies generated.')"

status:
	curl -s http://localhost:$(PORT)/api/status | python3 -m json.tool

.PHONY: install run test profile-good profile-mixed profile-bad generate-policies status
