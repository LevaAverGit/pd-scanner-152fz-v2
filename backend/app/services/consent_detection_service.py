"""
Consent and privacy-policy signal detector for the PD Scanner.

For each visited page, heuristically detects the presence of:
  - Privacy policy links (by link text and href)
  - Terms of service links (by link text and href)
  - Consent checkboxes (agree to terms / privacy) — including ARIA roles
  - Marketing / newsletter consent checkboxes
  - Custom toggle/switch elements suggesting consent
  - Bundled consent text near submit controls

Detection is purely heuristic — no AI, no form submission.
Results should be treated as evidence indicators, not legal conclusions.
All text matching is case-insensitive.
"""

import logging

from backend.app.utils.patterns import (
    CONSENT_BUNDLED_KEYWORDS,
    CONSENT_MARKETING_KEYWORDS,
    CONSENT_PRIVACY_KEYWORDS,
    CONSENT_TERMS_KEYWORDS,
)

logger = logging.getLogger(__name__)

# JS snippet that runs entirely client-side; receives keyword lists as arguments.
# Returns a plain dict serialisable back to Python via page.evaluate().
_DETECTION_JS = """
(function([privacyKws, termsKws, marketingKws, bundledKws]) {
    const signals = [];
    const lower = s => (s || '').toLowerCase();

    // Helper: text of element including aria-label
    function elText(el) {
        return lower(el.innerText || el.textContent || el.getAttribute('aria-label') || '');
    }

    // ---- Privacy link ----
    let hasPrivacyLink = false;
    for (const a of Array.from(document.querySelectorAll('a'))) {
        const t = elText(a) + ' ' + lower(a.href || '');
        if (privacyKws.some(k => t.includes(k))) {
            hasPrivacyLink = true;
            signals.push('Privacy link: ' + (a.innerText || a.href || '').trim().slice(0, 80));
            break;
        }
    }

    // ---- Terms link ----
    let hasTermsLink = false;
    for (const a of Array.from(document.querySelectorAll('a'))) {
        const t = elText(a) + ' ' + lower(a.href || '');
        if (termsKws.some(k => t.includes(k))) {
            hasTermsLink = true;
            signals.push('Terms link: ' + (a.innerText || a.href || '').trim().slice(0, 80));
            break;
        }
    }

    // ---- Standard checkboxes + ARIA roles ----
    let hasConsentCheckbox = false;
    let hasMarketingConsent = false;

    const checkboxLike = Array.from(document.querySelectorAll(
        'input[type=checkbox], [role=checkbox], [role=switch]'
    ));

    // Also find aria-checked elements
    const ariaChecked = Array.from(document.querySelectorAll('[aria-checked]'));
    const allCheckLike = [...new Set([...checkboxLike, ...ariaChecked])];

    for (const cb of allCheckLike) {
        // Label from: for=id, aria-label, aria-labelledby, ancestor label, parent text
        let labelText = '';
        const id = cb.id;
        if (id) {
            const lbl = document.querySelector('label[for="' + id + '"]');
            if (lbl) labelText += ' ' + lower(lbl.innerText || '');
        }
        const ariaLabel = cb.getAttribute('aria-label') || '';
        const ariaLabelledBy = cb.getAttribute('aria-labelledby') || '';
        if (ariaLabel) labelText += ' ' + lower(ariaLabel);
        if (ariaLabelledBy) {
            const lbl2 = document.getElementById(ariaLabelledBy);
            if (lbl2) labelText += ' ' + lower(lbl2.innerText || '');
        }
        // parent/ancestor text (up to 3 levels)
        let parent = cb.parentElement;
        for (let i = 0; i < 3 && parent; i++, parent = parent.parentElement) {
            labelText += ' ' + lower(parent.innerText || '').slice(0, 200);
        }

        const isPrivacy = privacyKws.some(k => labelText.includes(k));
        const isMarketing = marketingKws.some(k => labelText.includes(k));

        if (isPrivacy) {
            hasConsentCheckbox = true;
            signals.push('Consent checkbox: ' + labelText.trim().slice(0, 120));
        }
        if (isMarketing) {
            hasMarketingConsent = true;
            signals.push('Marketing consent checkbox: ' + labelText.trim().slice(0, 120));
        }
    }

    // ---- Custom toggle/switch divs ----
    const customToggles = Array.from(document.querySelectorAll(
        '[class*="toggle"], [class*="switch"], [class*="consent"], [class*="agree"]'
    ));
    for (const toggle of customToggles) {
        const t = elText(toggle);
        if (privacyKws.some(k => t.includes(k))) {
            hasConsentCheckbox = true;
            signals.push('Custom toggle suggests consent: ' + t.slice(0, 80));
            break;
        }
        if (marketingKws.some(k => t.includes(k))) {
            hasMarketingConsent = true;
            signals.push('Custom toggle suggests marketing consent: ' + t.slice(0, 80));
            break;
        }
    }

    // ---- Bundled consent text near submit controls ----
    let hasBundledConsentText = false;
    const bundledSnippets = [];

    // Look for submit buttons and check surrounding text
    const submitEls = Array.from(document.querySelectorAll(
        'button[type=submit], input[type=submit], button:not([type]), [role=button]'
    ));
    for (const btn of submitEls) {
        // Check parent form or nearest block ancestor (up to 4 levels)
        let el = btn.parentElement;
        for (let i = 0; i < 4 && el; i++, el = el.parentElement) {
            const t = lower(el.innerText || '').slice(0, 500);
            if (bundledKws.some(k => t.includes(k))) {
                hasBundledConsentText = true;
                const idx = bundledKws.findIndex(k => t.includes(k));
                const pos = t.indexOf(bundledKws[idx]);
                const snippet = (el.innerText || '').slice(
                    Math.max(0, pos - 30), pos + bundledKws[idx].length + 100
                ).replace(/\\s+/g, ' ').trim().slice(0, 150);
                bundledSnippets.push('Near-submit consent: ' + snippet);
                break;
            }
        }
        if (hasBundledConsentText) break;
    }

    // Also check full page text for bundled keywords if no submit button found nearby
    if (!hasBundledConsentText) {
        const bodyText = lower(document.body.innerText || '');
        for (const kw of bundledKws) {
            if (bodyText.includes(kw)) {
                hasBundledConsentText = true;
                const pos = bodyText.indexOf(kw);
                const fullText = document.body.innerText || '';
                const snippet = fullText.slice(
                    Math.max(0, pos - 20), pos + kw.length + 100
                ).replace(/\\s+/g, ' ').trim().slice(0, 150);
                bundledSnippets.push('Bundled consent text: ' + snippet);
                break;
            }
        }
    }

    if (bundledSnippets.length) {
        signals.push(...bundledSnippets);
    }

    return {
        hasPrivacyLink, hasTermsLink, hasConsentCheckbox,
        hasMarketingConsent, hasBundledConsentText,
        signals,
    };
})
"""


async def detect_consent_signals(page) -> dict:
    """
    Scan a loaded Playwright page for consent/privacy indicators.

    Runs purely client-side JavaScript — no navigation, no network requests.

    Returns
    -------
    dict with keys:
        has_privacy_link: bool
        has_terms_link: bool
        has_consent_checkbox: bool
        has_marketing_consent: bool
        has_bundled_consent_text: bool
        consent_signals: list[str]  — human-readable evidence strings
    """
    result: dict = {
        "has_privacy_link": False,
        "has_terms_link": False,
        "has_consent_checkbox": False,
        "has_marketing_consent": False,
        "has_bundled_consent_text": False,
        "consent_signals": [],
    }

    try:
        raw = await page.evaluate(
            _DETECTION_JS,
            [
                list(CONSENT_PRIVACY_KEYWORDS),
                list(CONSENT_TERMS_KEYWORDS),
                list(CONSENT_MARKETING_KEYWORDS),
                list(CONSENT_BUNDLED_KEYWORDS),
            ],
        )
        result["has_privacy_link"] = bool(raw.get("hasPrivacyLink"))
        result["has_terms_link"] = bool(raw.get("hasTermsLink"))
        result["has_consent_checkbox"] = bool(raw.get("hasConsentCheckbox"))
        result["has_marketing_consent"] = bool(raw.get("hasMarketingConsent"))
        result["has_bundled_consent_text"] = bool(raw.get("hasBundledConsentText"))
        result["consent_signals"] = raw.get("signals", [])
    except Exception as exc:
        logger.debug("consent_detection: evaluation failed: %s", exc)

    return result
