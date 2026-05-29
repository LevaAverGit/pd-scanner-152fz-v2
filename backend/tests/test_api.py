"""
API integration tests for PD Scanner.

Uses httpx.AsyncClient with ASGITransport against the real FastAPI app.
Each test gets a fresh temporary SQLite database via a pytest fixture so
tests are fully isolated and do not touch the development database.

The Playwright background scanner is patched out — these tests cover the
HTTP API layer and storage layer only, not the scan pipeline itself.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.models.db import init_db
from backend.app.services.url_validation import validate_url, URLValidationError, MAX_URL_LENGTH


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db_path(tmp_path):
    """Create an isolated temporary SQLite database for each test."""
    path = str(tmp_path / "test.db")
    await init_db(path)
    return path


@pytest_asyncio.fixture
async def client(db_path):
    """
    Async HTTP client wired to the FastAPI app with a per-test DB path.
    The background scanner (run_scan) is patched to a no-op so tests
    complete instantly without launching Playwright.
    """
    with patch("backend.app.core.config.settings.db_path", db_path), \
         patch("backend.app.api.routes_scan.run_scan", new_callable=AsyncMock):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestHealth:
    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client):
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /api/scan
# ---------------------------------------------------------------------------

class TestCreateScan:
    @pytest.mark.asyncio
    async def test_create_scan_success(self, client):
        resp = await client.post(
            "/api/scan", json={"url": "https://example.com/register"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "scan_id" in body
        assert body["status"] == "pending"
        assert body["url"] == "https://example.com/register"
        assert body["data_categories"] == []

    @pytest.mark.asyncio
    async def test_create_scan_returns_scan_id(self, client):
        resp = await client.post(
            "/api/scan", json={"url": "https://example.com/register"}
        )
        assert resp.status_code == 200
        scan_id = resp.json()["scan_id"]
        assert isinstance(scan_id, str)
        assert len(scan_id) == 36  # UUID4 format

    @pytest.mark.asyncio
    async def test_create_scan_rejects_non_http_scheme(self, client):
        resp = await client.post(
            "/api/scan", json={"url": "ftp://example.com/page"}
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_scan_rejects_localhost(self, client):
        with patch("backend.app.api.routes_scan.settings.allow_local_test_targets", False):
            resp = await client.post(
                "/api/scan", json={"url": "http://localhost/admin"}
            )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_scan_rejects_loopback(self, client):
        with patch("backend.app.api.routes_scan.settings.allow_local_test_targets", False):
            resp = await client.post(
                "/api/scan", json={"url": "http://127.0.0.1/"}
            )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_scan_rejects_loopback_range(self, client):
        # 127.0.0.0/8 — not just 127.0.0.1
        with patch("backend.app.api.routes_scan.settings.allow_local_test_targets", False):
            resp = await client.post(
                "/api/scan", json={"url": "http://127.0.0.2/"}
            )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_scan_rejects_link_local(self, client):
        # 169.254.169.254 is the AWS EC2 metadata endpoint
        resp = await client.post(
            "/api/scan", json={"url": "http://169.254.169.254/latest/meta-data/"}
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_scan_rejects_private_range(self, client):
        resp = await client.post(
            "/api/scan", json={"url": "http://192.168.1.1/"}
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_scan_accepts_optional_notes(self, client):
        resp = await client.post(
            "/api/scan",
            json={"url": "https://example.com/register", "notes": "test run"},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/scan/{scan_id}
# ---------------------------------------------------------------------------

class TestGetScan:
    @pytest.mark.asyncio
    async def test_get_existing_scan(self, client):
        create = await client.post(
            "/api/scan", json={"url": "https://example.com/register"}
        )
        scan_id = create.json()["scan_id"]

        resp = await client.get(f"/api/scan/{scan_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["scan_id"] == scan_id
        assert body["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_nonexistent_scan_returns_404(self, client):
        resp = await client.get("/api/scan/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/history
# ---------------------------------------------------------------------------

class TestGetHistory:
    @pytest.mark.asyncio
    async def test_history_empty_on_fresh_db(self, client):
        resp = await client.get("/api/history")
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0

    @pytest.mark.asyncio
    async def test_history_contains_created_scans(self, client):
        await client.post("/api/scan", json={"url": "https://example.com/a"})
        await client.post("/api/scan", json={"url": "https://example.com/b"})

        resp = await client.get("/api/history")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert len(body["items"]) == 2

    @pytest.mark.asyncio
    async def test_history_pagination(self, client):
        for i in range(5):
            await client.post(
                "/api/scan", json={"url": f"https://example.com/page{i}"}
            )

        resp = await client.get("/api/history?limit=2&offset=0")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 2
        assert body["total"] == 5


# ---------------------------------------------------------------------------
# DELETE /api/history/{scan_id}
# ---------------------------------------------------------------------------

class TestDeleteScan:
    @pytest.mark.asyncio
    async def test_delete_existing_scan(self, client):
        create = await client.post(
            "/api/scan", json={"url": "https://example.com/register"}
        )
        scan_id = create.json()["scan_id"]

        resp = await client.delete(f"/api/history/{scan_id}")
        assert resp.status_code == 200
        assert resp.json()["deleted"] == scan_id

    @pytest.mark.asyncio
    async def test_deleted_scan_no_longer_in_history(self, client):
        create = await client.post(
            "/api/scan", json={"url": "https://example.com/register"}
        )
        scan_id = create.json()["scan_id"]
        await client.delete(f"/api/history/{scan_id}")

        history = await client.get("/api/history")
        ids = [item["scan_id"] for item in history.json()["items"]]
        assert scan_id not in ids

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_404(self, client):
        resp = await client.delete(
            "/api/history/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_after_delete_returns_404(self, client):
        create = await client.post(
            "/api/scan", json={"url": "https://example.com/register"}
        )
        scan_id = create.json()["scan_id"]
        await client.delete(f"/api/history/{scan_id}")

        resp = await client.get(f"/api/scan/{scan_id}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# URL validation unit tests (SSRF hardening)
# ---------------------------------------------------------------------------

class TestURLValidation:
    def test_accepts_https(self):
        assert validate_url("https://example.com/register") == "https://example.com/register"

    def test_accepts_http(self):
        assert validate_url("http://example.com/page") == "http://example.com/page"

    def test_rejects_ftp_scheme(self):
        with pytest.raises(URLValidationError):
            validate_url("ftp://example.com/file")

    def test_rejects_file_scheme(self):
        with pytest.raises(URLValidationError):
            validate_url("file:///etc/passwd")

    def test_rejects_localhost(self):
        with pytest.raises(URLValidationError):
            validate_url("http://localhost/admin")

    def test_rejects_127_0_0_1(self):
        with pytest.raises(URLValidationError):
            validate_url("http://127.0.0.1/")

    def test_rejects_127_0_0_2(self):
        # Full 127.0.0.0/8 loopback range — not just 127.0.0.1
        with pytest.raises(URLValidationError):
            validate_url("http://127.0.0.2/")

    def test_rejects_127_x_range(self):
        with pytest.raises(URLValidationError):
            validate_url("http://127.100.200.1/")

    def test_rejects_link_local_metadata(self):
        # AWS EC2 / cloud metadata endpoint
        with pytest.raises(URLValidationError):
            validate_url("http://169.254.169.254/latest/meta-data/")

    def test_rejects_link_local_range(self):
        with pytest.raises(URLValidationError):
            validate_url("http://169.254.1.1/")

    def test_rejects_rfc1918_10(self):
        with pytest.raises(URLValidationError):
            validate_url("http://10.0.0.1/")

    def test_rejects_rfc1918_172(self):
        with pytest.raises(URLValidationError):
            validate_url("http://172.16.0.1/")

    def test_rejects_rfc1918_192_168(self):
        with pytest.raises(URLValidationError):
            validate_url("http://192.168.1.1/")

    def test_rejects_url_exceeding_max_length(self):
        long_url = "https://example.com/" + "a" * MAX_URL_LENGTH
        with pytest.raises(URLValidationError, match="maximum allowed length"):
            validate_url(long_url)

    def test_accepts_url_at_max_length(self):
        # A URL exactly at the limit should pass (if otherwise valid)
        path = "a" * (MAX_URL_LENGTH - len("https://example.com/"))
        url = "https://example.com/" + path
        assert len(url) <= MAX_URL_LENGTH
        result = validate_url(url)
        assert result == url


class TestAllowLocalFlag:
    """allow_local=True exempts localhost/127.x only; all other blocks remain."""

    def test_default_rejects_localhost(self):
        with pytest.raises(URLValidationError):
            validate_url("http://localhost/")

    def test_default_rejects_127_0_0_1(self):
        with pytest.raises(URLValidationError):
            validate_url("http://127.0.0.1/")

    def test_allow_local_accepts_localhost(self):
        result = validate_url("http://localhost/", allow_local=True)
        assert result == "http://localhost/"

    def test_allow_local_accepts_127_0_0_1(self):
        result = validate_url("http://127.0.0.1:8080/", allow_local=True)
        assert result == "http://127.0.0.1:8080/"

    def test_allow_local_accepts_127_x_range(self):
        result = validate_url("http://127.0.0.2/", allow_local=True)
        assert result == "http://127.0.0.2/"

    def test_allow_local_still_rejects_link_local(self):
        # 169.254.x must still be blocked even with allow_local
        with pytest.raises(URLValidationError):
            validate_url("http://169.254.169.254/", allow_local=True)

    def test_allow_local_still_rejects_rfc1918_10(self):
        with pytest.raises(URLValidationError):
            validate_url("http://10.0.0.1/", allow_local=True)

    def test_allow_local_still_rejects_rfc1918_192_168(self):
        with pytest.raises(URLValidationError):
            validate_url("http://192.168.1.1/", allow_local=True)

    def test_allow_local_still_rejects_ftp(self):
        with pytest.raises(URLValidationError):
            validate_url("ftp://localhost/", allow_local=True)
