"""
Integration audit service — downstream routing inference and processor map building.

Infers downstream processor type, name, confidence level, and routing signals
from existing per-page passive + synthetic-submission evidence.
Does NOT make network requests. All inference is heuristic and evidence-based.

Sources distinguished:
- observed_submit: confirmed by actual network request in synthetic mode
- inferred_public_signal: inferred from DOM, scripts, or follow-on hosts
- operator_supplied: operator-provided (clearly labelled, not scanner-observed)
"""
from __future__ import annotations

import logging
from urllib.parse import urlparse

from backend.app.models.schemas import (
    OperatorIntegrationEvidence, ProcessorMapItem, VisitedPageItem, VendorSummaryItem,
)

logger = logging.getLogger(__name__)

# Known platform URL fragments → (fragment, processor_name, processor_type)
_ACTION_URL_SIGNATURES: list[tuple[str, str, str]] = [
    ("forms.hscollect.net", "HubSpot", "crm_or_lead_capture"),
    ("forms.hubspot.com", "HubSpot", "crm_or_lead_capture"),
    ("api.hsforms.com", "HubSpot", "crm_or_lead_capture"),
    ("tildaforms.com", "Tilda", "form_platform"),
    ("formspree.io", "Formspree", "form_platform"),
    ("getform.io", "Getform", "form_platform"),
    ("api.typeform.com", "Typeform", "form_platform"),
    ("submit.jotform.com", "JotForm", "form_platform"),
    ("salesforce.com", "Salesforce", "crm_or_lead_capture"),
    ("pardot.com", "Salesforce Pardot", "crm_or_lead_capture"),
    ("amocrm.ru", "amoCRM", "crm_or_lead_capture"),
    ("kommo.com", "Kommo (amoCRM)", "crm_or_lead_capture"),
    ("bitrix24.ru", "Bitrix24", "crm_or_lead_capture"),
    ("bitrix24.com", "Bitrix24", "crm_or_lead_capture"),
    ("mailchimp.com", "Mailchimp", "crm_or_lead_capture"),
    ("list-manage.com", "Mailchimp", "crm_or_lead_capture"),
    ("glueup.com", "GlueUp", "crm_or_lead_capture"),
    ("calltouch.ru", "Calltouch", "crm_or_lead_capture"),
    ("roistat.com", "Roistat", "crm_or_lead_capture"),
    ("docs.google.com/forms", "Google Forms", "form_platform"),
    ("forms.gle", "Google Forms", "form_platform"),
    ("marketo.com", "Marketo", "crm_or_lead_capture"),
    ("mktoforms", "Marketo", "crm_or_lead_capture"),
    ("klaviyo.com", "Klaviyo", "crm_or_lead_capture"),
    ("activehosted.com", "ActiveCampaign", "crm_or_lead_capture"),
    ("mailerlite.com", "MailerLite", "crm_or_lead_capture"),
    ("sendinblue.com", "Brevo (Sendinblue)", "crm_or_lead_capture"),
    ("brevo.com", "Brevo", "crm_or_lead_capture"),
]

_WEBHOOK_PATH_PATTERNS: list[str] = [
    "/api/lead", "/api/leads", "/api/contact", "/api/contacts",
    "/api/form", "/api/forms", "/api/submit", "/api/intake",
    "/webhook", "/webhooks", "/hook/", "/hooks/",
    "/integrations/", "/capture", "/lead-capture",
]


def infer_downstream_routing(page: VisitedPageItem) -> dict:
    """
    Infer downstream processor type/name/confidence for a single visited page.

    Evidence priority (highest to lowest confidence):
    1. observed_submit_url + status==submitted -> high if matches known platform
    2. probable_form_platform / probable_crm_or_capture_tool (passive DOM analysis) -> medium
    3. observed_capture_tool / observed_webhook_or_api_hint (synthetic submission) -> medium
    4. follow-on hosts (synthetic submission) -> low-medium
    5. submission_evidence strings -> low

    Returns a routing inference dict.
    """
    signals: list[str] = []
    processor_type: str | None = None
    processor_name: str | None = None
    confidence_level = 0  # 0=none, 1=low, 2=medium, 3=high

    # 1. Highest confidence: observed actual submit URL (synthetic submission)
    if page.observed_submit_url and page.synthetic_submission_status == "submitted":
        url_lower = page.observed_submit_url.lower()
        matched = False
        for fragment, name, ptype in _ACTION_URL_SIGNATURES:
            if fragment in url_lower:
                processor_name = name
                processor_type = ptype
                confidence_level = max(confidence_level, 3)
                signals.append(f"Observed submit to known platform: {name} ({page.observed_submit_url[:80]})")
                matched = True
                break
        if not matched:
            # Check for webhook-like path
            try:
                path = urlparse(page.observed_submit_url).path.lower()
            except Exception:
                path = ""
            if any(p in path for p in _WEBHOOK_PATH_PATTERNS):
                processor_type = "webhook_or_api"
                confidence_level = max(confidence_level, 2)
                signals.append(f"Observed submit to webhook-like path: {path[:60]}")
            elif page.observed_submit_target_type == "third_party":
                processor_type = "unknown"
                confidence_level = max(confidence_level, 2)
                try:
                    host = urlparse(page.observed_submit_url).netloc
                except Exception:
                    host = page.observed_submit_url[:40]
                signals.append(f"Observed submit to third-party host: {host}")
            elif page.observed_submit_target_type in ("first_party", "relative"):
                processor_type = "webhook_or_api"
                confidence_level = max(confidence_level, 2)
                signals.append(f"Observed first-party submit: {page.observed_submit_url[:80]}")

    # 2. Passive DOM analysis
    if page.probable_form_platform:
        if not processor_name:
            processor_name = page.probable_form_platform
            processor_type = "form_platform"
        confidence_level = max(confidence_level, 2)
        signals.append(f"Passive signal: form platform detected — {page.probable_form_platform}")

    if page.probable_crm_or_capture_tool:
        if not processor_name:
            processor_name = page.probable_crm_or_capture_tool
            processor_type = "crm_or_lead_capture"
        confidence_level = max(confidence_level, 2)
        signals.append(f"Passive signal: CRM/capture tool — {page.probable_crm_or_capture_tool}")

    # 3. Capture tool / webhook hint (synthetic submission)
    if page.observed_capture_tool:
        if not processor_name:
            processor_name = page.observed_capture_tool
        confidence_level = max(confidence_level, 2)
        signals.append(f"Capture tool observed post-submit: {page.observed_capture_tool}")

    if page.observed_webhook_or_api_hint:
        if processor_type is None:
            processor_type = "webhook_or_api"
        confidence_level = max(confidence_level, 1)
        signals.append(f"Webhook/API hint: {str(page.observed_webhook_or_api_hint)[:80]}")

    # 4. Follow-on hosts (synthetic submission)
    for host in page.observed_follow_on_hosts:
        host_lower = host.lower()
        matched_vendor = False
        for fragment, name, ptype in _ACTION_URL_SIGNATURES:
            if fragment in host_lower:
                if not processor_name:
                    processor_name = name
                    processor_type = ptype
                confidence_level = max(confidence_level, 2)
                signals.append(f"Follow-on host suggests {name}: {host}")
                matched_vendor = True
                break
        if not matched_vendor:
            confidence_level = max(confidence_level, 1)
            signals.append(f"Follow-on host observed: {host}")

    conf_map = {0: "low", 1: "low", 2: "medium", 3: "high"}
    return {
        "downstream_processor_type": processor_type,
        "downstream_processor_name": processor_name,
        "downstream_routing_confidence": conf_map[confidence_level],
        "downstream_routing_signals": signals,
    }


def build_processor_map(
    visited_pages: list[VisitedPageItem],
    vendor_summary: list[VendorSummaryItem],
    operator_evidence: OperatorIntegrationEvidence | None,
) -> list[ProcessorMapItem]:
    """
    Build the site-level consolidated processor map.
    Sources clearly labelled: observed_submit | inferred_public_signal | operator_supplied.
    """
    items: list[ProcessorMapItem] = []
    seen: dict[str, ProcessorMapItem] = {}

    conf_order = {"low": 0, "medium": 1, "high": 2}

    def _upsert(key: str, new_item: ProcessorMapItem, page_url: str | None = None) -> None:
        if key in seen:
            existing = seen[key]
            if page_url and page_url not in existing.related_pages:
                existing.related_pages.append(page_url)
            if conf_order.get(new_item.confidence, 0) > conf_order.get(existing.confidence, 0):
                existing.confidence = new_item.confidence
            for ev in new_item.evidence:
                if ev not in existing.evidence:
                    existing.evidence.append(ev)
            for h in new_item.related_hosts:
                if h not in existing.related_hosts:
                    existing.related_hosts.append(h)
        else:
            seen[key] = new_item
            items.append(new_item)

    # From per-page downstream routing
    for page in visited_pages:
        name = page.downstream_processor_name
        ptype = page.downstream_processor_type
        if not name and not ptype:
            continue
        key = (name or ptype or "unknown").lower()
        source = (
            "observed_submit"
            if page.synthetic_submission_status == "submitted"
            else "inferred_public_signal"
        )
        related_hosts: list[str] = []
        if page.observed_submit_url:
            try:
                h = urlparse(page.observed_submit_url).netloc
                if h:
                    related_hosts.append(h)
            except Exception:
                pass
        related_hosts.extend(page.observed_follow_on_hosts)

        new_item = ProcessorMapItem(
            processor_name=name,
            processor_type=ptype or "unknown",
            source=source,
            related_hosts=related_hosts,
            related_pages=[page.url],
            confidence=page.downstream_routing_confidence,
            evidence=list(page.downstream_routing_signals[:5]),
        )
        _upsert(key, new_item, page.url)

    # From vendor summary (observed network hosts)
    _SKIP_VENDOR_CLASSES = {"analytics", "cdn", "unknown", "font", "utility"}
    for vendor in vendor_summary:
        if vendor.vendor_class in _SKIP_VENDOR_CLASSES:
            continue
        vname = vendor.vendor_name or vendor.host
        key = vname.lower()
        related_pages = [vendor.first_seen_on] if vendor.first_seen_on else []
        new_item = ProcessorMapItem(
            processor_name=vname,
            processor_type=vendor.vendor_class,
            source="inferred_public_signal",
            related_hosts=[vendor.host],
            related_pages=related_pages,
            confidence="low",
            evidence=[f"Third-party network request to {vendor.host}"],
        )
        _upsert(key, new_item)

    # From operator-supplied evidence
    if operator_evidence:
        if operator_evidence.form_platform:
            key = operator_evidence.form_platform.lower()
            new_item = ProcessorMapItem(
                processor_name=operator_evidence.form_platform,
                processor_type="form_platform",
                source="operator_supplied",
                confidence="high",
                evidence=["Operator-supplied evidence: form platform"],
            )
            _upsert(key, new_item)

        if operator_evidence.crm_destination:
            key = operator_evidence.crm_destination.lower()
            new_item = ProcessorMapItem(
                processor_name=operator_evidence.crm_destination,
                processor_type="crm_or_lead_capture",
                source="operator_supplied",
                confidence="high",
                evidence=["Operator-supplied evidence: CRM destination"],
            )
            _upsert(key, new_item)

        for wh in operator_evidence.webhook_urls:
            key = wh.lower()[:60]
            try:
                host = urlparse(wh).netloc or wh[:40]
            except Exception:
                host = wh[:40]
            new_item = ProcessorMapItem(
                processor_name=None,
                processor_type="webhook_or_api",
                source="operator_supplied",
                related_hosts=[host],
                confidence="high",
                evidence=["Operator-supplied evidence: webhook destination"],
            )
            _upsert(key, new_item)

        for note in operator_evidence.notes[:3]:
            items.append(ProcessorMapItem(
                processor_name=None,
                processor_type="unknown",
                source="operator_supplied",
                confidence="low",
                evidence=[f"Operator note: {note[:120]}"],
            ))

    # Sort: observed_submit first, then inferred, then operator; by confidence desc within group
    source_order = {"observed_submit": 0, "inferred_public_signal": 1, "operator_supplied": 2}
    items.sort(key=lambda i: (source_order.get(i.source, 3), -conf_order.get(i.confidence, 0)))
    return items
