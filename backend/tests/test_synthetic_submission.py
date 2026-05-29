"""
Controlled Synthetic Submission Mode — test suite.
"""
from __future__ import annotations

import pytest
import pytest_asyncio

from backend.app.models.schemas import (
    ScanRequest,
    SyntheticSubmissionSummary,
    VisitedPageItem,
)
from backend.app.services.synthetic_submission_service import (
    MAX_SUBMISSIONS_PER_PAGE,
    MAX_SUBMISSIONS_PER_SCAN,
    SYNTHETIC_FIELD_VALUES,
    _SENSITIVE_PATTERNS,
    _classify_target,
    _infer_capture_tool,
)


# ---------------------------------------------------------------------------
# Pure-unit tests (no browser required)
# ---------------------------------------------------------------------------

def test_classify_target_first_party():
    result = _classify_target("http://example.com/submit", "http://example.com/contact")
    assert result == "first_party"


def test_classify_target_third_party():
    result = _classify_target("https://forms.hubspot.com/submit", "http://example.com/contact")
    assert result == "third_party"


def test_classify_target_relative():
    result = _classify_target("/submit", "http://example.com/contact")
    assert result == "relative"


def test_classify_target_unknown():
    result = _classify_target("", "http://example.com/contact")
    assert result == "unknown"


def test_infer_capture_tool_hubspot():
    tool, _ = _infer_capture_tool("https://forms.hubspot.com/submissions/v3/public/single", [])
    assert tool == "HubSpot"


def test_infer_capture_tool_formspree():
    tool, _ = _infer_capture_tool("https://formspree.io/f/abc123", [])
    assert tool == "Formspree"


def test_infer_capture_tool_none():
    tool, hint = _infer_capture_tool("https://randomdomain.example/page", [])
    assert tool is None


def test_synthetic_field_values_no_real_pii():
    """Verify the synthetic values are clearly fake — not real-looking PII."""
    email = SYNTHETIC_FIELD_VALUES["email"]
    assert "@gmail.com" not in email
    assert "@mail.ru" not in email
    assert ".invalid" in email or "example" in email

    phone = SYNTHETIC_FIELD_VALUES["phone"]
    # Should not look like a real Russian mobile (which starts +7[3-9]xx)
    assert phone == "+70000000000" or "0000000" in phone


def test_max_submissions_constants():
    assert MAX_SUBMISSIONS_PER_PAGE == 1
    assert MAX_SUBMISSIONS_PER_SCAN == 3


def test_sensitive_patterns_present():
    """Key sensitive patterns must be present."""
    required = ["passport", "snils", "inn", "card", "cvv", "ssn", "medical", "birth"]
    for pattern in required:
        assert pattern in _SENSITIVE_PATTERNS, f"Missing sensitive pattern: {pattern}"


def test_schema_scan_request_defaults():
    req = ScanRequest(url="https://example.com")
    assert req.enable_synthetic_submission is False


def test_schema_visited_page_defaults():
    page = VisitedPageItem(url="https://example.com")
    assert page.synthetic_submission_attempted is False
    assert page.synthetic_submission_status == "not_attempted"
    assert page.observed_submit_url is None
    assert page.observed_submit_method is None
    assert page.observed_submit_target_type == "unknown"
    assert page.observed_follow_on_hosts == []
    assert page.observed_submission_evidence == []
    assert page.observed_capture_tool is None
    assert page.observed_webhook_or_api_hint is None


def test_schema_summary_defaults():
    summary = SyntheticSubmissionSummary()
    assert summary.pages_attempted == 0
    assert summary.successful_submissions == 0
    assert summary.third_party_submissions == 0
    assert summary.first_party_submissions == 0
    assert summary.blocked_or_failed == 0


# ---------------------------------------------------------------------------
# Playwright-based live tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_live_synthetic_submission():
    """
    Start a local HTTP server with a real form and verify the full
    synthetic submission flow using Playwright.
    """
    from playwright.async_api import async_playwright
    from backend.app.services.synthetic_submission_service import run_synthetic_submission
    from backend.tests.fixtures.form_server import FormFixtureServer

    server = FormFixtureServer()
    server.start()
    base_url = server.base_url
    form_url = f"{base_url}/"

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(form_url, timeout=15000)

            result = await run_synthetic_submission(page, form_url, base_url, submissions_count=0)

            await context.close()
            await browser.close()
    finally:
        server.stop()

    assert result["synthetic_submission_attempted"] is True, f"Expected attempted=True, got: {result}"
    assert result["synthetic_submission_status"] == "submitted", (
        f"Expected status='submitted', got '{result['synthetic_submission_status']}'. "
        f"Evidence: {result['observed_submission_evidence']}"
    )
    assert result["observed_submit_url"] is not None
    assert result["observed_submit_url"].endswith("/submit"), (
        f"Expected URL ending with '/submit', got: {result['observed_submit_url']}"
    )
    assert result["observed_submit_method"] == "POST"
    assert result["observed_submit_target_type"] == "first_party"
    assert len(result["observed_submission_evidence"]) > 0

    # Verify no request bodies or field values in evidence strings
    for ev_str in result["observed_submission_evidence"]:
        # Evidence must be brief metadata, not raw form data
        assert len(ev_str) < 200, f"Evidence string too long (may contain body data): {ev_str!r}"
        # Should not contain our synthetic values literally
        assert "test@example.invalid" not in ev_str.lower(), (
            f"Evidence contains synthetic email value (should not log field values): {ev_str!r}"
        )
        assert "test user" not in ev_str.lower(), (
            f"Evidence contains synthetic name value: {ev_str!r}"
        )


@pytest.mark.asyncio
async def test_captcha_blocks_submission():
    """
    The /blocked page has a g-recaptcha element — submission must be blocked.
    """
    from playwright.async_api import async_playwright
    from backend.app.services.synthetic_submission_service import run_synthetic_submission
    from backend.tests.fixtures.form_server import FormFixtureServer

    server = FormFixtureServer()
    server.start()
    base_url = server.base_url
    blocked_url = f"{base_url}/blocked"

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(blocked_url, timeout=15000)

            result = await run_synthetic_submission(page, blocked_url, base_url, submissions_count=0)

            await context.close()
            await browser.close()
    finally:
        server.stop()

    assert result["synthetic_submission_status"] == "blocked", (
        f"Expected status='blocked', got: {result['synthetic_submission_status']}"
    )
    evidence_text = " ".join(result["observed_submission_evidence"]).lower()
    assert "captcha" in evidence_text, (
        f"Expected 'captcha' in evidence, got: {result['observed_submission_evidence']}"
    )
