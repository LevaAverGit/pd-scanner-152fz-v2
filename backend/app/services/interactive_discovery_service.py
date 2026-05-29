"""
interactive_discovery_service.py — bounded, safe interactive reveal pass.

Opens hidden/modal/accordion content by clicking CTA-like elements that are
publicly visible. Does NOT submit forms, enter real personal data, bypass auth
or CAPTCHAs, or navigate to other domains.

Safety limits:
  - max 8 interactions per page
  - 3 second timeout per click
  - URL guard: go back if navigation leaves the same host
  - skip all submit-typed elements and elements with submit-like text
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from backend.app.utils.patterns import (
    INTERACTIVE_CTA_PATTERNS,
    INTERACTIVE_EXPAND_PATTERNS,
    CONSENT_BUNDLED_KEYWORDS,
    CONSENT_PRIVACY_KEYWORDS,
    CONSENT_MARKETING_KEYWORDS,
)

logger = logging.getLogger(__name__)

MAX_INTERACTIONS_PER_PAGE: int = 8
CLICK_TIMEOUT_MS: int = 3_000
POST_CLICK_WAIT_MS: int = 1_500

# Text patterns that indicate a "submit" element — skip these
_SKIP_TEXT_PATTERNS: list[str] = [
    "submit", "send", "отправить", "войти", "вход", "login", "log in",
    "sign in", "signin", "авторизоваться", "войти в",
]

_FIND_INTERACTIVE_JS = """
(function([ctaPatterns, expandPatterns, skipPatterns]) {
    const allPatterns = ctaPatterns.concat(expandPatterns);
    const candidates = Array.from(document.querySelectorAll(
        'button, a, [role="button"], [role="tab"], .btn, .button, ' +
        '[class*="btn"], [class*="button"], [class*="cta"]'
    ));

    function normText(el) {
        return (el.innerText || el.textContent || el.getAttribute('aria-label') || '').trim().toLowerCase();
    }

    function isVisible(el) {
        const r = el.getBoundingClientRect();
        return r.width > 0 && r.height > 0 && window.getComputedStyle(el).display !== 'none';
    }

    function isSkip(text) {
        return skipPatterns.some(p => text.includes(p));
    }

    function isMatch(text) {
        return allPatterns.some(p => text.includes(p));
    }

    function isSubmitType(el) {
        // Only skip elements with an EXPLICIT type=submit attribute
        // (a plain <button> without type has el.type='submit' by default but is NOT necessarily a submit button)
        return el.getAttribute('type') === 'submit' || el.getAttribute('type') === 'button' && el.form && el.type === 'submit';
    }

    function isExternalHref(el) {
        const href = el.getAttribute('href') || '';
        if (!href || href.startsWith('#') || href.startsWith('javascript')
            || href.startsWith('/') || href.startsWith('./')) return false;
        try {
            const u = new URL(href, window.location.href);
            return u.hostname !== window.location.hostname;
        } catch { return false; }
    }

    const results = [];
    for (const el of candidates) {
        const text = normText(el);
        if (!text || isSubmitType(el) || isSkip(text) || isExternalHref(el)) continue;
        if (!isVisible(el)) continue;
        if (!isMatch(text)) continue;
        const tag = el.tagName.toLowerCase();
        results.push({ text: el.innerText.trim().slice(0, 80), tag });
        if (results.length >= 20) break;  // gather up to 20 candidates, caller picks max
    }
    return results;
})
"""

_DETECT_MODAL_JS = """
(function() {
    const selectors = [
        '[role="dialog"]', 'dialog[open]', '.modal.show', '.modal-open .modal',
        '.modal[style*="display: block"]', '.modal[style*="display:block"]',
        '[class*="modal"][class*="open"]', '[class*="popup"][class*="open"]',
        '[class*="overlay"][class*="active"]',
    ];
    for (const sel of selectors) {
        const el = document.querySelector(sel);
        if (el) {
            const r = el.getBoundingClientRect();
            if (r.width > 0 && r.height > 0) return true;
        }
    }
    return false;
})()
"""

_EXTRACT_VISIBLE_TEXT_JS = """
(function(keywords) {
    const body = document.body.innerText || '';
    const lower = body.toLowerCase();
    const signals = [];
    for (const kw of keywords) {
        if (lower.includes(kw)) {
            const idx = lower.indexOf(kw);
            const snippet = body.slice(Math.max(0, idx - 20), idx + kw.length + 60).replace(/\\s+/g, ' ').trim();
            signals.push(snippet.slice(0, 120));
        }
    }
    return signals;
})
"""


async def run_interactive_discovery(page: Page, page_url: str) -> dict:
    """
    Perform bounded interactive reveal on an already-loaded page.
    Returns a dict with interactive discovery results.
    """
    result = _empty_result()
    base_host = urlparse(page_url).netloc.lower()

    # Snapshot: forms before any interaction
    try:
        forms_before = await page.locator("form").count()
    except Exception:
        forms_before = 0

    # Find candidate CTA elements
    try:
        candidates: list[dict] = await page.evaluate(
            _FIND_INTERACTIVE_JS,
            [INTERACTIVE_CTA_PATTERNS, INTERACTIVE_EXPAND_PATTERNS, _SKIP_TEXT_PATTERNS],
        )
    except Exception as exc:
        logger.debug("interactive_discovery: candidate search failed: %s", exc)
        return result

    if not candidates:
        return result

    interactions_done = 0

    for candidate in candidates:
        if interactions_done >= MAX_INTERACTIONS_PER_PAGE:
            break

        cand_text = candidate.get("text", "")
        cand_tag = candidate.get("tag", "?")

        try:
            # Re-find element by text (DOM may have changed between iterations)
            selector = _build_selector(cand_text, cand_tag)
            element = page.locator(selector).first
            if not await element.is_visible(timeout=1000):
                continue

            current_url = page.url
            forms_snap = await page.locator("form").count()

            # Click
            await element.click(timeout=CLICK_TIMEOUT_MS)
            interactions_done += 1
            result["interactions_performed"].append(
                f"Clicked: '{cand_text[:60]}' ({cand_tag})"
            )

            # Wait for DOM to settle
            try:
                await page.wait_for_timeout(POST_CLICK_WAIT_MS)
            except Exception:
                pass

            # Guard: if navigated away from same host, go back
            new_url = page.url
            if urlparse(new_url).netloc.lower() != base_host:
                logger.debug("interactive_discovery: navigated away to %s — going back", new_url)
                try:
                    await page.go_back(timeout=5000, wait_until="domcontentloaded")
                except Exception:
                    pass
                continue

            # Check for new forms
            try:
                forms_after = await page.locator("form").count()
                if forms_after > forms_snap:
                    result["hidden_forms_revealed"] += (forms_after - forms_snap)
            except Exception:
                pass

            # Check for modal
            try:
                modal_visible: bool = await page.evaluate(_DETECT_MODAL_JS)
                if modal_visible:
                    result["modal_forms_found"] += 1
            except Exception:
                pass

            # Detect dynamic consent signals in newly visible text
            try:
                all_consent_kws = (
                    list(CONSENT_PRIVACY_KEYWORDS)
                    + list(CONSENT_MARKETING_KEYWORDS)
                    + list(CONSENT_BUNDLED_KEYWORDS)
                )
                signals: list[str] = await page.evaluate(_EXTRACT_VISIBLE_TEXT_JS, all_consent_kws)
                for sig in signals:
                    if sig not in result["dynamic_consent_signals"]:
                        result["dynamic_consent_signals"].append(sig)
            except Exception:
                pass

        except PlaywrightTimeout:
            logger.debug("interactive_discovery: click timeout on '%s'", cand_text[:40])
        except Exception as exc:
            logger.debug("interactive_discovery: click error on '%s': %s", cand_text[:40], exc)

    result["hidden_forms_revealed"] = max(0, result["hidden_forms_revealed"])
    # Clamp dynamic_consent_signals
    result["dynamic_consent_signals"] = result["dynamic_consent_signals"][:20]
    return result


def _build_selector(text: str, tag: str) -> str:
    """Build a Playwright CSS/text selector for an element by its visible text."""
    safe = re.sub(r'["\\]', " ", text.strip()[:50])
    if tag in ("button", "a"):
        return f'{tag}:has-text("{safe}")'
    return f':has-text("{safe}")'


def _empty_result() -> dict:
    return {
        "hidden_forms_revealed": 0,
        "interactions_performed": [],
        "dynamic_consent_signals": [],
        "modal_forms_found": 0,
    }
