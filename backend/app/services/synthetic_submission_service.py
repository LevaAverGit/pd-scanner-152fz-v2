"""
Controlled synthetic form submission service.

Fills form fields with clearly synthetic placeholder values and performs
one controlled submission per page (max 3 per scan). Captures only request
metadata — not request bodies, response bodies, or cookies.

Safety constraints (enforced, not configurable):
- Only runs when explicitly enabled in the scan request
- max 1 submission per page, max 3 per scan
- Never submits real personal data
- Skips payment, CAPTCHA, auth, file-upload, sensitive-field forms
- Does not persist request bodies, response bodies, or cookies
"""
from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)

MAX_SUBMISSIONS_PER_PAGE: int = 1
MAX_SUBMISSIONS_PER_SCAN: int = 3
FILL_TIMEOUT_MS: int = 2_000
SUBMIT_WAIT_MS: int = 3_000
POST_SUBMIT_WAIT_MS: int = 2_000

# Synthetic values — clearly fake, not real PII
SYNTHETIC_FIELD_VALUES: dict[str, str] = {
    "email": "test@example.invalid",
    "phone": "+70000000000",
    "tel": "+70000000000",
    "mobile": "+70000000000",
    "name": "Test User",
    "fullname": "Test User",
    "full_name": "Test User",
    "firstname": "Test",
    "first_name": "Test",
    "fname": "Test",
    "lastname": "User",
    "last_name": "User",
    "lname": "User",
    "company": "Test Company",
    "organization": "Test Company",
    "org": "Test Company",
    "message": "Synthetic compliance test",
    "comment": "Synthetic compliance test",
    "text": "Synthetic test",
    "city": "Test",
    "address": "Test",
    "street": "Test",
    "zip": "000000",
    "postal": "000000",
    "password": "TestPassword123!",
    "subject": "Synthetic compliance test",
    "question": "Synthetic compliance test",
}

# Patterns in field name/type/label that indicate sensitive categories — skip entire form
_SENSITIVE_PATTERNS: list[str] = [
    "passport", "snils", "inn", "card", "cvv", "cvc",
    "account", "routing", "iban", "swift", "bic",
    "medical", "health", "diagnosis", "prescription",
    "ssn", "tax_id", "social_security", "national_id",
    "birth", "dob", "date_of_birth",
]

# Page-level keywords suggesting payment checkout
_PAYMENT_KEYWORDS: list[str] = [
    "checkout", "payment", "billing", "card number",
    "credit card", "bank transfer", "оплата", "оплатить",
    "номер карты", "cvv", "cvc",
]

# Form-level keywords suggesting auth-only (login / sign-in, no registration)
_AUTH_KEYWORDS: list[str] = [
    "sign in", "signin", "log in", "login", "вход", "войти",
    "authenticate", "авторизация",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _classify_target(observed_url: str, base_url: str) -> str:
    """Return 'first_party' | 'third_party' | 'relative' | 'unknown'."""
    if not observed_url:
        return "unknown"
    if observed_url.startswith("/") or observed_url.startswith("./") or not observed_url.startswith("http"):
        return "relative"
    try:
        obs_host = urlparse(observed_url).netloc.lower().lstrip("www.")
        base_host = urlparse(base_url).netloc.lower().lstrip("www.")
        return "first_party" if obs_host == base_host else "third_party"
    except Exception:
        return "unknown"


def _infer_capture_tool(url: str, evidence: list[str]) -> tuple[str | None, str | None]:
    """
    Detect known form platforms / CRMs from URL patterns.
    Returns (capture_tool_name, webhook_or_api_hint).
    """
    if not url:
        return None, None

    url_lower = url.lower()
    capture_tool: str | None = None
    webhook_hint: str | None = None

    # Known form platforms / CRMs
    _PLATFORM_PATTERNS: list[tuple[str, str]] = [
        ("forms.hscollect.net", "HubSpot"),
        ("forms.hubspot.com", "HubSpot"),
        ("salesforce.com", "Salesforce"),
        ("pardot.com", "Salesforce Pardot"),
        ("tildaforms.com", "Tilda Forms"),
        ("getform.io", "Getform"),
        ("formspree.io", "Formspree"),
    ]
    for pattern, name in _PLATFORM_PATTERNS:
        if pattern in url_lower:
            capture_tool = name
            break

    # Webhook / API hints from path
    _WEBHOOK_PATHS: list[str] = ["/api/", "/webhook", "/hook", "/submit", "/lead"]
    for path_hint in _WEBHOOK_PATHS:
        if path_hint in url_lower:
            webhook_hint = f"Path contains '{path_hint}'"
            break

    return capture_tool, webhook_hint


async def _has_captcha(page: Page) -> bool:
    """Check for common CAPTCHA indicators in the page DOM."""
    try:
        return await page.evaluate("""
(function() {
    return !!(
        document.querySelector('.g-recaptcha, .cf-turnstile, [data-sitekey], #recaptcha, .h-captcha, iframe[src*="recaptcha"]')
    );
})()
""")
    except Exception:
        return False


async def _has_file_upload(page: Page, form_selector: str) -> bool:
    """Check if the form contains a file upload input."""
    try:
        count = await page.locator(f"{form_selector} input[type=file]").count()
        return count > 0
    except Exception:
        return False


async def _has_sensitive_fields(page: Page, form_selector: str) -> tuple[bool, str]:
    """
    Check all input names/ids/labels within the form against _SENSITIVE_PATTERNS.
    Returns (found: bool, reason: str).
    """
    try:
        field_data: list[dict] = await page.evaluate(
            """
(function(formSel) {
    const form = document.querySelector(formSel);
    if (!form) return [];
    const inputs = Array.from(form.querySelectorAll('input, textarea, select'));
    return inputs.map(el => ({
        name: (el.getAttribute('name') || '').toLowerCase(),
        id: (el.getAttribute('id') || '').toLowerCase(),
        type: (el.getAttribute('type') || '').toLowerCase(),
    }));
})
""",
            form_selector,
        )
        # Also try to get label texts near the form
        label_texts: list[str] = await page.evaluate(
            """
(function(formSel) {
    const form = document.querySelector(formSel);
    if (!form) return [];
    return Array.from(form.querySelectorAll('label')).map(l =>
        (l.innerText || l.textContent || '').toLowerCase()
    );
})
""",
            form_selector,
        )
    except Exception:
        return False, ""

    for field in field_data:
        for pattern in _SENSITIVE_PATTERNS:
            if (
                pattern in field.get("name", "")
                or pattern in field.get("id", "")
                or pattern in field.get("type", "")
            ):
                return True, f"Sensitive field detected: pattern='{pattern}' in field name/id/type"

    for label in label_texts:
        for pattern in _SENSITIVE_PATTERNS:
            if pattern in label:
                return True, f"Sensitive label text detected: pattern='{pattern}'"

    return False, ""


async def _is_payment_page(page: Page) -> bool:
    """Check page body text for payment-related keywords."""
    try:
        body_text: str = await page.evaluate(
            "(function() { return (document.body.innerText || document.body.textContent || '').toLowerCase(); })()"
        )
        return any(kw in body_text for kw in _PAYMENT_KEYWORDS)
    except Exception:
        return False


async def _is_auth_only_form(page: Page, form_selector: str) -> bool:
    """
    Check form visible text for auth keywords AND no name/email-only registration fields.
    Returns True only for pure login forms (has password + no name field).
    """
    try:
        form_text: str = await page.evaluate(
            """
(function(formSel) {
    const form = document.querySelector(formSel);
    if (!form) return '';
    return (form.innerText || form.textContent || '').toLowerCase();
})
""",
            form_selector,
        )
        has_auth_keyword = any(kw in form_text for kw in _AUTH_KEYWORDS)
        if not has_auth_keyword:
            return False

        # Check if it has a password field but no name field (pure login)
        field_data: list[dict] = await page.evaluate(
            """
(function(formSel) {
    const form = document.querySelector(formSel);
    if (!form) return [];
    return Array.from(form.querySelectorAll('input')).map(el => ({
        name: (el.getAttribute('name') || '').toLowerCase(),
        type: (el.getAttribute('type') || '').toLowerCase(),
    }));
})
""",
            form_selector,
        )
        has_password = any(f.get("type") == "password" for f in field_data)
        has_name_field = any(
            "name" in f.get("name", "") or "fname" in f.get("name", "")
            for f in field_data
        )
        # Pure login = has password but no name registration field
        return has_password and not has_name_field
    except Exception:
        return False


async def _fill_form(page: Page, form_selector: str) -> list[str]:
    """
    Find all visible input fields in the form and fill with synthetic values.
    Returns list of filled field descriptions (no actual values logged).
    DO NOT fill: hidden, submit, reset, button, checkbox, radio, file inputs.
    For select: pick first non-empty option.
    For textarea: fill with SYNTHETIC_FIELD_VALUES['message'].
    """
    filled: list[str] = []
    _SKIP_TYPES = {"hidden", "submit", "reset", "button", "checkbox", "radio", "file", "image"}

    def _synthetic_value_for(name: str, field_type: str) -> str:
        name_lower = name.lower()
        # Try exact match first
        if name_lower in SYNTHETIC_FIELD_VALUES:
            return SYNTHETIC_FIELD_VALUES[name_lower]
        # Try partial match
        for key, val in SYNTHETIC_FIELD_VALUES.items():
            if key in name_lower or name_lower in key:
                return val
        # Fall back by type
        type_lower = field_type.lower()
        if type_lower in SYNTHETIC_FIELD_VALUES:
            return SYNTHETIC_FIELD_VALUES[type_lower]
        if type_lower == "number":
            return "1"
        if type_lower == "url":
            return "https://example.invalid"
        if type_lower == "date":
            return "2000-01-01"
        return "Test"

    try:
        # Fill text-like inputs
        inputs = page.locator(f"{form_selector} input")
        count = await inputs.count()
        for i in range(count):
            el = inputs.nth(i)
            try:
                field_type = (await el.get_attribute("type") or "text").lower()
                if field_type in _SKIP_TYPES:
                    continue
                is_visible = await el.is_visible()
                if not is_visible:
                    continue
                name = await el.get_attribute("name") or await el.get_attribute("id") or ""
                value = _synthetic_value_for(name, field_type)
                await el.fill(value, timeout=FILL_TIMEOUT_MS)
                filled.append(f"input[name={name or '?'}][type={field_type}] filled")
            except Exception:
                pass

        # Fill textareas
        textareas = page.locator(f"{form_selector} textarea")
        ta_count = await textareas.count()
        for i in range(ta_count):
            el = textareas.nth(i)
            try:
                is_visible = await el.is_visible()
                if not is_visible:
                    continue
                name = await el.get_attribute("name") or await el.get_attribute("id") or ""
                await el.fill(SYNTHETIC_FIELD_VALUES["message"], timeout=FILL_TIMEOUT_MS)
                filled.append(f"textarea[name={name or '?'}] filled")
            except Exception:
                pass

        # Select first non-empty option in selects
        selects = page.locator(f"{form_selector} select")
        sel_count = await selects.count()
        for i in range(sel_count):
            el = selects.nth(i)
            try:
                is_visible = await el.is_visible()
                if not is_visible:
                    continue
                name = await el.get_attribute("name") or await el.get_attribute("id") or ""
                # Pick the first non-empty option value
                option_val: str | None = await el.evaluate(
                    "(sel) => { const opts = Array.from(sel.options).filter(o => o.value); return opts.length ? opts[0].value : null; }"
                )
                if option_val:
                    await el.select_option(option_val, timeout=FILL_TIMEOUT_MS)
                    filled.append(f"select[name={name or '?'}] option selected")
            except Exception:
                pass

    except Exception as exc:
        logger.debug("synthetic_submission: _fill_form error: %s", exc)

    return filled


def _blocked_result(reason: str) -> dict:
    return {
        "synthetic_submission_attempted": True,
        "synthetic_submission_status": "blocked",
        "observed_submit_url": None,
        "observed_submit_method": None,
        "observed_submit_target_type": "unknown",
        "observed_follow_on_hosts": [],
        "observed_submission_evidence": [reason],
        "observed_capture_tool": None,
        "observed_webhook_or_api_hint": None,
    }


def _not_attempted_result() -> dict:
    return {
        "synthetic_submission_attempted": False,
        "synthetic_submission_status": "not_attempted",
        "observed_submit_url": None,
        "observed_submit_method": None,
        "observed_submit_target_type": "unknown",
        "observed_follow_on_hosts": [],
        "observed_submission_evidence": [],
        "observed_capture_tool": None,
        "observed_webhook_or_api_hint": None,
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def run_synthetic_submission(
    page: Page,
    page_url: str,
    base_url: str,
    submissions_count: int,
) -> dict:
    """
    Attempt a single controlled synthetic form submission on the given page.

    Safety gates (in order):
      1. Global submission cap
      2. Payment page detection
      3. No form found / not visible
      4. CAPTCHA detection
      5. File upload detection
      6. Sensitive field detection
      7. Auth-only form detection

    Returns a dict with all synthetic submission VisitedPageItem fields.
    """
    # Gate 1: global submission cap
    if submissions_count >= MAX_SUBMISSIONS_PER_SCAN:
        return _not_attempted_result()

    # Gate 2: payment page
    try:
        if await _is_payment_page(page):
            return _blocked_result("Skipped: payment/checkout page detected")
    except Exception:
        pass

    # Find primary form
    form_selector = "form"
    try:
        form_count = await page.locator(form_selector).count()
        if form_count == 0:
            return _not_attempted_result()
        # Use CSS :first-of-type — locate the first visible form
        first_form = page.locator(form_selector).first
        is_visible = await first_form.is_visible()
        if not is_visible:
            return _not_attempted_result()
    except Exception:
        return _not_attempted_result()

    # Use nth-form selector for safety checks — default to first form
    form_nth_selector = "form:first-of-type"

    # Gate 3: CAPTCHA
    try:
        if await _has_captcha(page):
            return _blocked_result("Skipped: CAPTCHA detected on page")
    except Exception:
        pass

    # Gate 4: file upload
    try:
        if await _has_file_upload(page, form_selector):
            return _blocked_result("Skipped: file upload form detected")
    except Exception:
        pass

    # Gate 5: sensitive fields
    try:
        has_sensitive, sensitive_reason = await _has_sensitive_fields(page, form_selector)
        if has_sensitive:
            return _blocked_result(f"Skipped: {sensitive_reason}")
    except Exception:
        pass

    # Gate 6: auth-only form
    try:
        if await _is_auth_only_form(page, form_selector):
            return _blocked_result("Skipped: auth-only (login) form detected")
    except Exception:
        pass

    # All gates passed — proceed with filling and submitting
    evidence: list[str] = []
    captured_requests: list[dict] = []

    def on_request(req):
        if req.method in ("POST", "GET") and req.resource_type in ("fetch", "xhr", "document"):
            captured_requests.append({
                "url": req.url,
                "method": req.method,
                "resource_type": req.resource_type,
            })

    page.on("request", on_request)

    try:
        # Fill the form
        filled_fields = await _fill_form(page, form_selector)
        evidence.append(f"Filled {len(filled_fields)} field(s) with synthetic values")

        # Find and click submit button
        submit_clicked = False
        submit_selectors = [
            f"{form_selector} button[type=submit]",
            f"{form_selector} input[type=submit]",
            f"{form_selector} button:not([type=button]):not([type=reset])",
        ]
        for sel in submit_selectors:
            try:
                btn = page.locator(sel).first
                btn_count = await page.locator(sel).count()
                if btn_count > 0 and await btn.is_visible():
                    await btn.click(timeout=SUBMIT_WAIT_MS)
                    submit_clicked = True
                    evidence.append(f"Submit button clicked (selector: {sel})")
                    break
            except Exception:
                pass

        if not submit_clicked:
            # Try pressing Enter on the last filled input
            try:
                await page.keyboard.press("Enter")
                submit_clicked = True
                evidence.append("Submit triggered via keyboard Enter")
            except Exception:
                pass

        # Wait for network activity to settle
        try:
            await page.wait_for_timeout(POST_SUBMIT_WAIT_MS)
        except Exception:
            pass

    except Exception as exc:
        page.remove_listener("request", on_request)
        return {
            "synthetic_submission_attempted": True,
            "synthetic_submission_status": "indeterminate",
            "observed_submit_url": None,
            "observed_submit_method": None,
            "observed_submit_target_type": "unknown",
            "observed_follow_on_hosts": [],
            "observed_submission_evidence": [f"Exception during submission: {type(exc).__name__}"],
            "observed_capture_tool": None,
            "observed_webhook_or_api_hint": None,
        }
    finally:
        try:
            page.remove_listener("request", on_request)
        except Exception:
            pass

    # Analyse captured requests
    observed_submit_url: str | None = None
    observed_submit_method: str | None = None

    # Identify primary submit request: first POST, or fallback to first document navigation
    for req in captured_requests:
        if req["method"] == "POST":
            observed_submit_url = req["url"]
            observed_submit_method = "POST"
            evidence.append(f"POST request captured to: {req['url'][:80]}")
            break

    if observed_submit_url is None:
        for req in captured_requests:
            if req["resource_type"] == "document":
                observed_submit_url = req["url"]
                observed_submit_method = req["method"]
                evidence.append(f"Navigation request captured: {req['method']} {req['url'][:80]}")
                break

    # Follow-on hosts: check current page URL and all captured request hosts
    follow_on_hosts: list[str] = []
    current_url = page.url
    if current_url and current_url != page_url:
        try:
            current_host = urlparse(current_url).netloc.lower()
            base_host = urlparse(base_url).netloc.lower()
            if current_host and current_host != base_host:
                follow_on_hosts.append(current_host)
        except Exception:
            pass

    for req in captured_requests:
        try:
            req_host = urlparse(req["url"]).netloc.lower()
            base_host = urlparse(base_url).netloc.lower()
            if req_host and req_host != base_host and req_host not in follow_on_hosts:
                follow_on_hosts.append(req_host)
        except Exception:
            pass

    # Classify submission status
    if observed_submit_url:
        status = "submitted"
    elif captured_requests:
        status = "indeterminate"
    else:
        status = "validation_failed"
        evidence.append("No network request captured — JS validation may have prevented submit")

    # Classify target type
    target_type = _classify_target(observed_submit_url or "", base_url)

    # Infer capture tool
    capture_tool, webhook_hint = _infer_capture_tool(observed_submit_url or "", evidence)

    return {
        "synthetic_submission_attempted": True,
        "synthetic_submission_status": status,
        "observed_submit_url": observed_submit_url,
        "observed_submit_method": observed_submit_method,
        "observed_submit_target_type": target_type,
        "observed_follow_on_hosts": follow_on_hosts,
        "observed_submission_evidence": evidence,
        "observed_capture_tool": capture_tool,
        "observed_webhook_or_api_hint": webhook_hint,
    }
