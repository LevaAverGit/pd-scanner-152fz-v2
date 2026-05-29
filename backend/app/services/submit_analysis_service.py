"""
submit_analysis_service.py — passive form submission target inference.

Inspects the live DOM (via page.evaluate) and static script/iframe references to
infer *where* a form would send data and *which platform* is likely handling
submission.  No form is ever submitted; no extra network requests are made.
"""

from __future__ import annotations

from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Script-src platform fingerprints
# Each entry: (substring_to_match_in_src, platform_label, category)
# category: "form_platform" | "crm_or_lead_capture"
# ---------------------------------------------------------------------------
_SCRIPT_PLATFORM_RULES: list[tuple[str, str, str]] = [
    # Form platforms
    ("js.hsforms.net", "HubSpot Forms", "form_platform"),
    ("embed.typeform.com", "Typeform", "form_platform"),
    ("form.jotform.com", "JotForm", "form_platform"),
    ("tildacdn.com", "Tilda", "form_platform"),
    ("forms.fillout.com", "Fillout", "form_platform"),
    ("paperform.co", "Paperform", "form_platform"),
    ("wufoo.com", "Wufoo", "form_platform"),
    ("formstack.com", "Formstack", "form_platform"),
    ("cognito", "Cognito Forms", "form_platform"),
    ("formassembly.com", "FormAssembly", "form_platform"),
    ("getform.io", "Getform", "form_platform"),
    ("formspree.io", "Formspree", "form_platform"),
    ("123formbuilder.com", "123FormBuilder", "form_platform"),
    ("formsite.com", "Formsite", "form_platform"),
    # CRM / lead capture
    ("amocrm.ru", "amoCRM", "crm_or_lead_capture"),
    ("kommo.com", "Kommo (amoCRM)", "crm_or_lead_capture"),
    ("bitrix24.ru", "Bitrix24", "crm_or_lead_capture"),
    ("bitrix24.com", "Bitrix24", "crm_or_lead_capture"),
    ("calltouch.ru", "Calltouch", "crm_or_lead_capture"),
    ("roistat.com", "Roistat", "crm_or_lead_capture"),
    ("yclients.com", "YCLIENTS", "crm_or_lead_capture"),
    ("retail-rocket.ru", "Retail Rocket", "crm_or_lead_capture"),
    ("insales.ru", "InSales", "crm_or_lead_capture"),
    ("salesforce.com", "Salesforce", "crm_or_lead_capture"),
    ("pardot.com", "Salesforce Pardot", "crm_or_lead_capture"),
    ("marketo.com", "Marketo", "crm_or_lead_capture"),
    ("eloqua.com", "Oracle Eloqua", "crm_or_lead_capture"),
    ("activehosted.com", "ActiveCampaign", "crm_or_lead_capture"),
    ("klaviyo.com", "Klaviyo", "crm_or_lead_capture"),
    ("intercom.io", "Intercom", "crm_or_lead_capture"),
    ("zendesk.com", "Zendesk", "crm_or_lead_capture"),
    ("freshworks.com", "Freshworks CRM", "crm_or_lead_capture"),
    ("pipedrive.com", "Pipedrive", "crm_or_lead_capture"),
]

# ---------------------------------------------------------------------------
# Hidden-input name fingerprints
# ---------------------------------------------------------------------------
_HIDDEN_INPUT_RULES: list[tuple[str, str, str]] = [
    # (hidden input name substring, platform_label, category)
    ("_wpcf7", "Contact Form 7", "form_platform"),
    ("hs_context", "HubSpot", "form_platform"),
    ("portalId", "HubSpot", "form_platform"),
    ("tilda-page", "Tilda", "form_platform"),
    ("oid", "Salesforce Web-to-Lead", "crm_or_lead_capture"),
    ("retURL", "Salesforce Web-to-Lead", "crm_or_lead_capture"),
    ("FORMTYPE", "Bitrix24", "crm_or_lead_capture"),
    ("web_form_id", "Bitrix24", "crm_or_lead_capture"),
    ("ctw_", "Calltouch", "crm_or_lead_capture"),
    ("roistat", "Roistat", "crm_or_lead_capture"),
    ("gform_unique_id", "Gravity Forms", "form_platform"),
    ("ninja_forms_field", "Ninja Forms", "form_platform"),
    ("forminator", "Forminator", "form_platform"),
    ("wdform", "WDForm", "form_platform"),
    ("mautic", "Mautic", "crm_or_lead_capture"),
]

# ---------------------------------------------------------------------------
# DOM inspection JS — run in page context, no network side-effects
# ---------------------------------------------------------------------------
_INSPECT_JS = """
(function() {
    const MAX_SCRIPTS = 40;
    const MAX_IFRAMES = 5;
    const MAX_HIDDEN  = 30;

    // sensitive hidden-input name fragments we should NOT collect
    const SKIP_HIDDEN = ['csrf', 'token', 'nonce', 'password', 'secret', 'key',
                         'captcha', 'recaptcha', '_wpnonce'];

    function skipHidden(name) {
        const n = name.toLowerCase();
        return SKIP_HIDDEN.some(s => n.includes(s));
    }

    // 1. Form metadata
    const forms = Array.from(document.querySelectorAll('form')).map(f => ({
        action: f.getAttribute('action') || '',
        method: (f.getAttribute('method') || 'get').toLowerCase(),
        dataAttrs: Object.fromEntries(
            Array.from(f.attributes)
                .filter(a => a.name.startsWith('data-'))
                .map(a => [a.name, a.value])
        ),
        hiddenInputNames: Array.from(f.querySelectorAll('input[type=hidden]'))
            .map(i => i.getAttribute('name') || '')
            .filter(n => n && !skipHidden(n))
            .slice(0, MAX_HIDDEN),
    }));

    // 2. All script srcs (external only)
    const scriptSrcs = Array.from(document.querySelectorAll('script[src]'))
        .map(s => s.getAttribute('src') || '')
        .filter(Boolean)
        .slice(0, MAX_SCRIPTS);

    // 3. Iframe srcs
    const iframeSrcs = Array.from(document.querySelectorAll('iframe[src]'))
        .map(f => f.getAttribute('src') || '')
        .filter(Boolean)
        .slice(0, MAX_IFRAMES);

    return { forms, scriptSrcs, iframeSrcs };
})()
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _classify_action(action: str, page_url: str) -> tuple[str | None, str]:
    """
    Given a form action and the page url, return
    (probable_submission_target, submission_target_type).
    target_type: "first_party" | "third_party" | "relative" | "unknown"
    """
    if not action or action.startswith("#"):
        return None, "unknown"

    # Resolve relative paths against page origin
    if action.startswith("/") or not action.startswith("http"):
        return None, "relative"  # same-site form post

    try:
        action_host = urlparse(action).netloc.lower()
        page_host = urlparse(page_url).netloc.lower()
    except Exception:
        return action, "unknown"

    if not action_host:
        return None, "relative"

    # Strip www. for comparison
    def _strip_www(h: str) -> str:
        return h.removeprefix("www.")

    if _strip_www(action_host) == _strip_www(page_host):
        return action, "first_party"
    return action, "third_party"


def _detect_platform_from_scripts(
    script_srcs: list[str],
) -> tuple[str | None, str | None]:
    """Returns (form_platform, crm_or_lead_capture) labels inferred from script urls."""
    form_platform: str | None = None
    crm_tool: str | None = None
    for src in script_srcs:
        src_lower = src.lower()
        for fragment, label, category in _SCRIPT_PLATFORM_RULES:
            if fragment in src_lower:
                if category == "form_platform" and form_platform is None:
                    form_platform = label
                elif category == "crm_or_lead_capture" and crm_tool is None:
                    crm_tool = label
    return form_platform, crm_tool


def _detect_platform_from_hidden_inputs(
    hidden_names: list[str],
) -> tuple[str | None, str | None]:
    """Returns (form_platform, crm_or_lead_capture) labels inferred from hidden input names."""
    form_platform: str | None = None
    crm_tool: str | None = None
    for name in hidden_names:
        name_lower = name.lower()
        for fragment, label, category in _HIDDEN_INPUT_RULES:
            if fragment.lower() in name_lower:
                if category == "form_platform" and form_platform is None:
                    form_platform = label
                elif category == "crm_or_lead_capture" and crm_tool is None:
                    crm_tool = label
    return form_platform, crm_tool


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def analyse_submit_targets(page, page_url: str) -> dict:
    """
    Passively inspect a Playwright page for form submission clues.

    Returns a dict with keys matching the VisitedPageItem submit-analysis fields:
        has_first_party_submission_hint   bool
        has_third_party_submission_hint   bool
        probable_form_platform            str | None
        probable_crm_or_capture_tool      str | None
        probable_submission_target        str | None
        submission_method                 str | None
        submission_target_type            str  ("first_party"|"third_party"|"relative"|"unknown")
        submission_evidence               list[str]
    """
    try:
        raw: dict = await page.evaluate(_INSPECT_JS)
    except Exception:
        return _empty_result()

    forms: list[dict] = raw.get("forms", [])
    script_srcs: list[str] = raw.get("scriptSrcs", [])
    iframe_srcs: list[str] = raw.get("iframeSrcs", [])

    evidence: list[str] = []
    first_party = False
    third_party = False
    probable_target: str | None = None
    probable_method: str | None = None
    target_type: str = "unknown"

    # Collect all hidden input names across all forms
    all_hidden_names: list[str] = []
    for form in forms:
        all_hidden_names.extend(form.get("hiddenInputNames", []))

    # Determine target from form actions (first actionable form wins)
    for form in forms:
        action = form.get("action", "")
        method = form.get("method", "get")
        t, t_type = _classify_action(action, page_url)

        if t_type == "first_party":
            first_party = True
            if probable_target is None:
                probable_target = t
                probable_method = method
                target_type = "first_party"
                evidence.append(f"Form action submits to first-party endpoint: {action[:80]}")
        elif t_type == "third_party":
            third_party = True
            if probable_target is None:
                probable_target = t
                probable_method = method
                target_type = "third_party"
                evidence.append(f"Form action submits to third-party host: {urlparse(action).netloc}")
        elif t_type == "relative":
            first_party = True
            if probable_target is None:
                probable_method = method
                target_type = "relative"
                evidence.append(f"Form posts to relative path: {action or '(same page)'}")

        # Data attributes can hint at form platform (e.g. data-form-id for HubSpot)
        for attr, val in form.get("dataAttrs", {}).items():
            if any(kw in attr for kw in ["hubspot", "pardot", "marketo", "klaviyo",
                                          "hs-", "typeform", "jotform"]):
                evidence.append(f"Form data attribute suggests platform: {attr}={val[:40]}")

    # Platform detection from scripts
    fp_script, crm_script = _detect_platform_from_scripts(script_srcs)
    if fp_script:
        evidence.append(f"Script src suggests form platform: {fp_script}")
    if crm_script:
        evidence.append(f"Script src suggests CRM/capture tool: {crm_script}")

    # Platform detection from hidden inputs
    fp_hidden, crm_hidden = _detect_platform_from_hidden_inputs(all_hidden_names)
    if fp_hidden:
        evidence.append(f"Hidden input names suggest form platform: {fp_hidden}")
    if crm_hidden:
        evidence.append(f"Hidden input names suggest CRM/capture tool: {crm_hidden}")

    # Iframe platform hints (e.g. embedded Typeform or JotForm)
    for src in iframe_srcs:
        src_lower = src.lower()
        for fragment, label, category in _SCRIPT_PLATFORM_RULES:
            if fragment in src_lower:
                hint = f"Embedded iframe suggests {label}"
                if hint not in evidence:
                    evidence.append(hint)
                if category == "form_platform" and fp_script is None and fp_hidden is None:
                    fp_script = label
                elif category == "crm_or_lead_capture" and crm_script is None and crm_hidden is None:
                    crm_script = label
                break

    form_platform = fp_script or fp_hidden
    crm_tool = crm_script or crm_hidden

    # If a known third-party form platform is embedded, flag third_party hint
    if form_platform and target_type in ("unknown", "relative"):
        third_party = True

    return {
        "has_first_party_submission_hint": first_party,
        "has_third_party_submission_hint": third_party,
        "probable_form_platform": form_platform,
        "probable_crm_or_capture_tool": crm_tool,
        "probable_submission_target": probable_target,
        "submission_method": probable_method,
        "submission_target_type": target_type,
        "submission_evidence": evidence,
    }


def _empty_result() -> dict:
    return {
        "has_first_party_submission_hint": False,
        "has_third_party_submission_hint": False,
        "probable_form_platform": None,
        "probable_crm_or_capture_tool": None,
        "probable_submission_target": None,
        "submission_method": None,
        "submission_target_type": "unknown",
        "submission_evidence": [],
    }
