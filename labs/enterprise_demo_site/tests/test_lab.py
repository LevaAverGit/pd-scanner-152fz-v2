"""
Comprehensive tests for the Enterprise Demo Lab.
Run from ./:
    .venv/bin/pytest labs/enterprise_demo_site/tests/ -v
"""
import sys
import asyncio
import tempfile
from pathlib import Path

# Ensure the backend package is importable
LAB_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(LAB_ROOT))

import pytest
import httpx
import aiosqlite

# Set up temp dirs BEFORE importing app modules so patches take effect
_tmp_dir = tempfile.mkdtemp()
_tmp_db = Path(_tmp_dir) / "test_lab.db"
_tmp_policies = Path(_tmp_dir) / "generated_policies"
_tmp_profile = Path(_tmp_dir) / "profile.json"

# Monkey-patch paths before importing app modules
import backend.app.database as _db_module
import backend.app.policy_generator as _pg_module
import backend.app.profile as _profile_module

_db_module.DB_PATH = _tmp_db
_pg_module.POLICY_DIR = _tmp_policies
_profile_module.PROFILE_FILE = _tmp_profile

from backend.app.main import app
from backend.app.database import DB_PATH, init_db
from backend.app.policy_generator import generate_all
from backend.app.profile import get_profile, set_profile


# ============================================================
# Session-scoped setup: init DB + generate policies once
# ============================================================

@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module", autouse=True)
async def setup_lab():
    """Initialize DB and generate policies before any test runs."""
    await init_db()
    generate_all()
    yield


@pytest.fixture(scope="module")
async def client():
    """Shared async HTTP client (no lifespan needed — we called init manually)."""
    # Use app directly without lifespan to avoid double-init
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


# ============================================================
# 1. TestPublicPages
# ============================================================
class TestPublicPages:
    public_routes = [
        "/",
        "/about",
        "/services",
        "/pricing",
        "/request-demo",
        "/contact",
        "/webinar",
        "/careers",
        "/privacy",
        "/terms",
        "/cookies",
    ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", public_routes)
    async def test_page_returns_200(self, client, path):
        resp = await client.get(path)
        assert resp.status_code == 200, f"Expected 200 for {path}, got {resp.status_code}"

    @pytest.mark.asyncio
    async def test_pages_contain_html(self, client):
        resp = await client.get("/")
        assert "text/html" in resp.headers["content-type"]
        assert b"<html" in resp.content.lower()

    @pytest.mark.asyncio
    async def test_analytics_script_on_homepage(self, client):
        resp = await client.get("/")
        assert b"/mock/analytics.js" in resp.content

    @pytest.mark.asyncio
    async def test_lab_mode_indicator_visible(self, client):
        resp = await client.get("/")
        assert b"Lab mode:" in resp.content


# ============================================================
# 2. TestFormSubmission
# ============================================================
class TestFormSubmission:
    @pytest.mark.asyncio
    async def test_submit_form_returns_200(self, client):
        resp = await client.post("/submit", data={
            "name": "Иван Петров",
            "email": "ivan@test.ru",
            "phone": "+7 999 000 00 00",
            "company": "ООО Тест",
            "message": "Тестовое сообщение",
            "form_type": "contact",
            "source_page": "/contact",
        })
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_submit_stores_email(self, client):
        unique_email = "unique_test_submission@example.com"
        await client.post("/submit", data={
            "name": "Test User",
            "email": unique_email,
            "phone": "",
            "company": "TestCo",
            "message": "",
            "form_type": "demo_request",
            "source_page": "/request-demo",
        })
        async with aiosqlite.connect(str(DB_PATH)) as db:
            cursor = await db.execute("SELECT email FROM submissions WHERE email = ?", (unique_email,))
            row = await cursor.fetchone()
        assert row is not None, "Submission was not stored in DB"
        assert row[0] == unique_email

    @pytest.mark.asyncio
    async def test_api_lead_json_endpoint(self, client):
        resp = await client.post("/api/lead", json={
            "name": "API Lead",
            "email": "apilead@example.com",
            "company": "ApiCo",
            "source_page": "/",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "submission_id" in body
        assert isinstance(body["submission_id"], int)


# ============================================================
# 3. TestDBWrites
# ============================================================
class TestDBWrites:
    @pytest.mark.asyncio
    async def test_submission_creates_routing_event(self, client):
        unique_email = "routing_test@example.com"
        await client.post("/submit", data={
            "name": "Routing Test",
            "email": unique_email,
            "form_type": "contact",
            "source_page": "/contact",
        })
        async with aiosqlite.connect(str(DB_PATH)) as db:
            cursor = await db.execute(
                "SELECT r.* FROM routing_events r "
                "JOIN submissions s ON r.submission_id = s.id "
                "WHERE s.email = ?", (unique_email,)
            )
            rows = await cursor.fetchall()
        assert len(rows) >= 1, "No routing events found for submission"

    @pytest.mark.asyncio
    async def test_submission_creates_processor_event(self, client):
        unique_email = "processor_test@example.com"
        await client.post("/submit", data={
            "name": "Processor Test",
            "email": unique_email,
            "form_type": "contact",
            "source_page": "/contact",
        })
        async with aiosqlite.connect(str(DB_PATH)) as db:
            cursor = await db.execute(
                "SELECT p.* FROM processor_events p "
                "JOIN submissions s ON p.submission_id = s.id "
                "WHERE s.email = ?", (unique_email,)
            )
            rows = await cursor.fetchall()
        assert len(rows) >= 1, "No processor events found for submission"

    @pytest.mark.asyncio
    async def test_submission_creates_consent_event(self, client):
        unique_email = "consent_test@example.com"
        await client.post("/submit", data={
            "name": "Consent Test",
            "email": unique_email,
            "form_type": "contact",
            "source_page": "/contact",
        })
        async with aiosqlite.connect(str(DB_PATH)) as db:
            cursor = await db.execute(
                "SELECT c.* FROM consent_events c "
                "JOIN submissions s ON c.submission_id = s.id "
                "WHERE s.email = ?", (unique_email,)
            )
            rows = await cursor.fetchall()
        assert len(rows) >= 1, "No consent events found for submission"

    @pytest.mark.asyncio
    async def test_all_four_tables_populated(self, client):
        """Verify all 4 core tables have data after submissions above."""
        async with aiosqlite.connect(str(DB_PATH)) as db:
            for table in ("submissions", "routing_events", "processor_events", "consent_events"):
                cursor = await db.execute(f"SELECT COUNT(*) FROM {table}")
                count = (await cursor.fetchone())[0]
                assert count > 0, f"Table {table} is empty"


# ============================================================
# 4. TestProfileSwitching
# ============================================================
class TestProfileSwitching:
    @pytest.mark.asyncio
    async def test_set_profile_good(self, client):
        resp = await client.post("/api/profile/good_compliance")
        assert resp.status_code == 200
        assert resp.json()["profile"] == "good_compliance"

    @pytest.mark.asyncio
    async def test_set_profile_mixed(self, client):
        resp = await client.post("/api/profile/mixed_compliance")
        assert resp.status_code == 200
        assert resp.json()["profile"] == "mixed_compliance"

    @pytest.mark.asyncio
    async def test_set_profile_bad(self, client):
        resp = await client.post("/api/profile/bad_compliance")
        assert resp.status_code == 200
        assert resp.json()["profile"] == "bad_compliance"

    @pytest.mark.asyncio
    async def test_invalid_profile_returns_400(self, client):
        resp = await client.post("/api/profile/nonexistent_profile")
        assert resp.status_code == 400
        assert "error" in resp.json()

    @pytest.mark.asyncio
    async def test_good_compliance_shows_consent_checkbox(self, client):
        await client.post("/api/profile/good_compliance")
        resp = await client.get("/request-demo")
        assert b'type="checkbox"' in resp.content
        assert b'consent' in resp.content

    @pytest.mark.asyncio
    async def test_bad_compliance_page_renders(self, client):
        await client.post("/api/profile/bad_compliance")
        resp = await client.get("/request-demo")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_good_compliance_consent_type_stored(self, client):
        await client.post("/api/profile/good_compliance")
        unique_email = "good_consent@example.com"
        await client.post("/submit", data={
            "name": "Good User",
            "email": unique_email,
            "consent": "1",
            "form_type": "contact",
            "source_page": "/contact",
        })
        async with aiosqlite.connect(str(DB_PATH)) as db:
            cursor = await db.execute(
                "SELECT consent_type FROM submissions WHERE email = ?", (unique_email,)
            )
            row = await cursor.fetchone()
        assert row is not None
        assert row[0] == "explicit_checkbox"

    @pytest.mark.asyncio
    async def test_bad_compliance_consent_type_absent(self, client):
        await client.post("/api/profile/bad_compliance")
        unique_email = "bad_consent@example.com"
        await client.post("/submit", data={
            "name": "Bad User",
            "email": unique_email,
            "form_type": "contact",
            "source_page": "/contact",
        })
        async with aiosqlite.connect(str(DB_PATH)) as db:
            cursor = await db.execute(
                "SELECT consent_type FROM submissions WHERE email = ?", (unique_email,)
            )
            row = await cursor.fetchone()
        assert row is not None
        assert row[0] == "absent"


# ============================================================
# 5. TestPolicyFiles
# ============================================================
class TestPolicyFiles:
    @pytest.mark.asyncio
    async def test_privacy_page_200(self, client):
        await client.post("/api/profile/good_compliance")
        resp = await client.get("/privacy")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_privacy_pdf_200(self, client):
        resp = await client.get("/privacy.pdf")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"

    @pytest.mark.asyncio
    async def test_privacy_docx_200(self, client):
        resp = await client.get("/privacy.docx")
        assert resp.status_code == 200
        assert "wordprocessingml" in resp.headers["content-type"]

    @pytest.mark.asyncio
    async def test_good_compliance_policy_has_key_content(self, client):
        await client.post("/api/profile/good_compliance")
        resp = await client.get("/privacy")
        content = resp.content
        assert b"152" in content
        assert b"privacy@democorp.local" in content

    @pytest.mark.asyncio
    async def test_bad_compliance_page_renders(self, client):
        await client.post("/api/profile/bad_compliance")
        resp = await client.get("/")
        assert resp.status_code == 200
        assert b"bad_compliance" in resp.content


# ============================================================
# 6. TestMockServices
# ============================================================
class TestMockServices:
    @pytest.mark.asyncio
    async def test_analytics_js_returns_javascript(self, client):
        resp = await client.get("/mock/analytics.js")
        assert resp.status_code == 200
        assert "javascript" in resp.headers["content-type"]
        assert b"__labAnalytics" in resp.content

    @pytest.mark.asyncio
    async def test_pixel_gif_returns_image(self, client):
        resp = await client.get("/mock/pixel.gif")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/gif"
        assert len(resp.content) > 0

    @pytest.mark.asyncio
    async def test_crm_js_returns_javascript(self, client):
        resp = await client.get("/mock/crm.js")
        assert resp.status_code == 200
        assert "javascript" in resp.headers["content-type"]
        assert b"__labCRM" in resp.content

    @pytest.mark.asyncio
    async def test_analytics_collect_post(self, client):
        resp = await client.post("/mock/analytics/collect", json={"event": "pageview"})
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    @pytest.mark.asyncio
    async def test_bad_compliance_includes_tracking_pixel(self, client):
        await client.post("/api/profile/bad_compliance")
        resp = await client.get("/")
        assert b"/mock/pixel.gif" in resp.content

    @pytest.mark.asyncio
    async def test_good_compliance_no_tracking_pixel(self, client):
        await client.post("/api/profile/good_compliance")
        resp = await client.get("/")
        assert b"/mock/pixel.gif" not in resp.content


# ============================================================
# 7. TestAdminPages
# ============================================================
class TestAdminPages:
    @pytest.mark.asyncio
    async def test_admin_login_page_200(self, client):
        resp = await client.get("/admin/login")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_unauthenticated_submissions_redirects(self):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
            follow_redirects=False
        ) as fresh_client:
            resp = await fresh_client.get("/admin/submissions")
        assert resp.status_code in (302, 307)

    @pytest.mark.asyncio
    async def test_admin_login_with_correct_password(self, client):
        resp = await client.post(
            "/admin/login",
            data={"password": "demo-lab-only"},
            follow_redirects=False
        )
        assert resp.status_code in (302, 307)
        assert "lab_admin_session" in resp.cookies

    @pytest.mark.asyncio
    async def test_admin_login_wrong_password(self, client):
        resp = await client.post(
            "/admin/login",
            data={"password": "wrongpassword"},
        )
        assert resp.status_code == 200
        assert b"Invalid password" in resp.content

    @pytest.mark.asyncio
    async def test_authenticated_admin_can_view_submissions(self, client):
        await client.post(
            "/admin/login",
            data={"password": "demo-lab-only"},
            follow_redirects=True
        )
        resp = await client.get("/admin/submissions")
        assert resp.status_code == 200


# ============================================================
# 8. TestAPIEndpoints
# ============================================================
class TestAPIEndpoints:
    @pytest.mark.asyncio
    async def test_api_status(self, client):
        resp = await client.get("/api/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["lab"] == "enterprise_demo_site"
        assert "profile" in body

    @pytest.mark.asyncio
    async def test_api_get_profile(self, client):
        resp = await client.get("/api/profile")
        assert resp.status_code == 200
        assert "profile" in resp.json()

    @pytest.mark.asyncio
    async def test_api_set_profile_and_verify(self, client):
        await client.post("/api/profile/good_compliance")
        resp = await client.get("/api/profile")
        assert resp.json()["profile"] == "good_compliance"


# ============================================================
# 9. TestWebhookRouting
# ============================================================
class TestWebhookRouting:
    @pytest.mark.asyncio
    async def test_bad_compliance_routes_to_crm(self, client):
        await client.post("/api/profile/bad_compliance")
        unique_email = "crm_routing_test@example.com"
        await client.post("/submit", data={
            "name": "CRM Routing Test",
            "email": unique_email,
            "form_type": "demo_request",
            "source_page": "/request-demo",
        })
        async with aiosqlite.connect(str(DB_PATH)) as db:
            cursor = await db.execute(
                "SELECT r.route_type, r.destination FROM routing_events r "
                "JOIN submissions s ON r.submission_id = s.id "
                "WHERE s.email = ?", (unique_email,)
            )
            rows = await cursor.fetchall()
        route_types = [r[0] for r in rows]
        destinations = [r[1] for r in rows]
        assert "third_party_crm" in route_types, f"Expected third_party_crm route, got: {route_types}"
        assert any("crm" in d for d in destinations), f"Expected CRM destination, got: {destinations}"

    @pytest.mark.asyncio
    async def test_mixed_compliance_routes_to_webhook(self, client):
        await client.post("/api/profile/mixed_compliance")
        unique_email = "webhook_routing_test@example.com"
        await client.post("/submit", data={
            "name": "Webhook Routing Test",
            "email": unique_email,
            "form_type": "demo_request",
            "source_page": "/request-demo",
        })
        async with aiosqlite.connect(str(DB_PATH)) as db:
            cursor = await db.execute(
                "SELECT r.route_type FROM routing_events r "
                "JOIN submissions s ON r.submission_id = s.id "
                "WHERE s.email = ?", (unique_email,)
            )
            rows = await cursor.fetchall()
        route_types = [r[0] for r in rows]
        assert "webhook" in route_types, f"Expected webhook route, got: {route_types}"

    @pytest.mark.asyncio
    async def test_good_compliance_only_first_party_routing(self, client):
        await client.post("/api/profile/good_compliance")
        unique_email = "first_party_only_test@example.com"
        await client.post("/submit", data={
            "name": "First Party Test",
            "email": unique_email,
            "consent": "1",
            "form_type": "demo_request",
            "source_page": "/request-demo",
        })
        async with aiosqlite.connect(str(DB_PATH)) as db:
            cursor = await db.execute(
                "SELECT r.route_type FROM routing_events r "
                "JOIN submissions s ON r.submission_id = s.id "
                "WHERE s.email = ?", (unique_email,)
            )
            rows = await cursor.fetchall()
        route_types = [r[0] for r in rows]
        assert all(rt == "first_party" for rt in route_types), \
            f"Expected only first_party routes, got: {route_types}"

    @pytest.mark.asyncio
    async def test_webhook_mock_endpoint_accepts_post(self, client):
        resp = await client.post("/webhook/mock", content=b'{"test": "data"}')
        assert resp.status_code == 200
        assert resp.json()["status"] == "received"

    @pytest.mark.asyncio
    async def test_crm_mock_endpoint_accepts_post(self, client):
        resp = await client.post("/crm/mock", content=b'{"lead": "data"}')
        assert resp.status_code == 200
        assert resp.json()["status"] == "lead_created"
        assert resp.json()["crm"] == "MockCRM"
