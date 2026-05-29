"""Tests for Integration Audit Mode."""
import pytest

from backend.app.models.schemas import (
    OperatorIntegrationEvidence,
    ProcessorMapItem,
    ScanRequest,
    ScanResult,
    VisitedPageItem,
    VendorSummaryItem,
)
from backend.app.services.integration_audit_service import (
    _ACTION_URL_SIGNATURES,
    build_processor_map,
    infer_downstream_routing,
)


def _make_page(**kwargs) -> VisitedPageItem:
    """Helper: construct VisitedPageItem with all defaults."""
    defaults = dict(
        url="https://example.com/",
        page_title=None,
        registration_relevance=None,
        detected_categories=[],
        fields_count=0,
        forms_found=0,
        notes=[],
        has_privacy_link=False,
        has_terms_link=False,
        has_consent_checkbox=False,
        has_marketing_consent=False,
        consent_signals=[],
        has_first_party_submission_hint=False,
        has_third_party_submission_hint=False,
        probable_form_platform=None,
        probable_crm_or_capture_tool=None,
        probable_submission_target=None,
        submission_method=None,
        submission_target_type="unknown",
        submission_evidence=[],
        hidden_forms_revealed=0,
        interactions_performed=[],
        dynamic_consent_signals=[],
        modal_forms_found=0,
        has_bundled_consent_text=False,
        synthetic_submission_attempted=False,
        synthetic_submission_status="not_attempted",
        observed_submit_url=None,
        observed_submit_method=None,
        observed_submit_target_type="unknown",
        observed_follow_on_hosts=[],
        observed_submission_evidence=[],
        observed_capture_tool=None,
        observed_webhook_or_api_hint=None,
    )
    defaults.update(kwargs)
    return VisitedPageItem(**defaults)


class TestInferDownstreamRouting:
    def test_infers_from_observed_submit_url_hubspot(self):
        page = _make_page(
            observed_submit_url="https://forms.hscollect.net/submit",
            synthetic_submission_status="submitted",
            observed_submit_target_type="third_party",
        )
        result = infer_downstream_routing(page)
        assert result["downstream_processor_name"] == "HubSpot"
        assert result["downstream_processor_type"] == "crm_or_lead_capture"
        assert result["downstream_routing_confidence"] == "high"
        assert result["downstream_routing_signals"]

    def test_infers_from_observed_submit_url_formspree(self):
        page = _make_page(
            observed_submit_url="https://formspree.io/f/abc123",
            synthetic_submission_status="submitted",
            observed_submit_target_type="third_party",
        )
        result = infer_downstream_routing(page)
        assert result["downstream_processor_name"] == "Formspree"
        assert result["downstream_routing_confidence"] == "high"

    def test_infers_webhook_path(self):
        page = _make_page(
            observed_submit_url="https://example.com/api/lead",
            synthetic_submission_status="submitted",
            observed_submit_target_type="first_party",
        )
        result = infer_downstream_routing(page)
        assert result["downstream_processor_type"] == "webhook_or_api"
        assert result["downstream_routing_confidence"] in ("medium", "high")

    def test_infers_from_probable_form_platform(self):
        page = _make_page(probable_form_platform="Tilda")
        result = infer_downstream_routing(page)
        assert result["downstream_processor_name"] == "Tilda"
        assert result["downstream_processor_type"] == "form_platform"
        assert result["downstream_routing_confidence"] == "medium"

    def test_infers_from_probable_crm(self):
        page = _make_page(probable_crm_or_capture_tool="amoCRM")
        result = infer_downstream_routing(page)
        assert result["downstream_processor_name"] == "amoCRM"
        assert result["downstream_routing_confidence"] == "medium"

    def test_returns_low_confidence_for_empty_page(self):
        page = _make_page()
        result = infer_downstream_routing(page)
        assert result["downstream_routing_confidence"] == "low"
        assert result["downstream_processor_type"] is None

    def test_signals_non_empty_when_evidence_present(self):
        page = _make_page(probable_form_platform="Typeform")
        result = infer_downstream_routing(page)
        assert len(result["downstream_routing_signals"]) > 0

    def test_does_not_infer_when_submission_not_submitted(self):
        # observed_submit_url present but status is not 'submitted' -> no high confidence
        page = _make_page(
            observed_submit_url="https://forms.hscollect.net/submit",
            synthetic_submission_status="blocked",
            observed_submit_target_type="third_party",
        )
        result = infer_downstream_routing(page)
        # Not from observed submit — may still infer from other signals but not high
        assert result["downstream_routing_confidence"] != "high"


class TestBuildProcessorMap:
    def test_map_includes_observed_submit_item(self):
        page = _make_page(
            url="https://example.com/contact",
            observed_submit_url="https://formspree.io/f/abc",
            synthetic_submission_status="submitted",
            observed_submit_target_type="third_party",
            downstream_processor_name="Formspree",
            downstream_processor_type="form_platform",
            downstream_routing_confidence="high",
            downstream_routing_signals=["Observed submit to known platform: Formspree"],
        )
        pm = build_processor_map([page], [], None)
        assert any(item.processor_name == "Formspree" for item in pm)
        formspree = next(i for i in pm if i.processor_name == "Formspree")
        assert formspree.source == "observed_submit"

    def test_map_includes_inferred_item(self):
        page = _make_page(
            url="https://example.com/form",
            probable_form_platform="Tilda",
            downstream_processor_name="Tilda",
            downstream_processor_type="form_platform",
            downstream_routing_confidence="medium",
            downstream_routing_signals=["Passive signal: form platform detected — Tilda"],
        )
        pm = build_processor_map([page], [], None)
        assert any(item.processor_name == "Tilda" for item in pm)
        tilda = next(i for i in pm if i.processor_name == "Tilda")
        assert tilda.source == "inferred_public_signal"

    def test_map_operator_evidence_labelled(self):
        oe = OperatorIntegrationEvidence(form_platform="Typeform", crm_destination="Salesforce CRM")
        pm = build_processor_map([], [], oe)
        sources = [item.source for item in pm]
        assert "operator_supplied" in sources
        typeform = next((i for i in pm if i.processor_name == "Typeform"), None)
        assert typeform is not None
        assert typeform.source == "operator_supplied"

    def test_map_deduplicates_same_processor(self):
        page1 = _make_page(
            url="https://example.com/p1",
            downstream_processor_name="HubSpot",
            downstream_processor_type="crm_or_lead_capture",
            downstream_routing_confidence="medium",
            downstream_routing_signals=["sig1"],
        )
        page2 = _make_page(
            url="https://example.com/p2",
            downstream_processor_name="HubSpot",
            downstream_processor_type="crm_or_lead_capture",
            downstream_routing_confidence="medium",
            downstream_routing_signals=["sig2"],
        )
        pm = build_processor_map([page1, page2], [], None)
        hubspot_items = [i for i in pm if i.processor_name == "HubSpot"]
        assert len(hubspot_items) == 1
        assert "https://example.com/p1" in hubspot_items[0].related_pages
        assert "https://example.com/p2" in hubspot_items[0].related_pages

    def test_map_excludes_analytics_vendors(self):
        vendor = VendorSummaryItem(
            host="google-analytics.com",
            vendor_class="analytics",
            vendor_name="Google Analytics",
        )
        pm = build_processor_map([], [vendor], None)
        assert not any(item.processor_name == "Google Analytics" for item in pm)

    def test_map_vendor_crm_included(self):
        vendor = VendorSummaryItem(
            host="amocrm.ru",
            vendor_class="crm_or_lead_capture",
            vendor_name="amoCRM",
        )
        pm = build_processor_map([], [vendor], None)
        assert any(item.processor_name == "amoCRM" for item in pm)

    def test_empty_inputs_return_empty_map(self):
        pm = build_processor_map([], [], None)
        assert pm == []


class TestOperatorEvidenceSchema:
    def test_defaults_all_optional(self):
        oe = OperatorIntegrationEvidence()
        assert oe.source is None
        assert oe.form_platform is None
        assert oe.crm_destination is None
        assert oe.webhook_urls == []
        assert oe.notification_targets == []
        assert oe.notes == []

    def test_full_construction(self):
        oe = OperatorIntegrationEvidence(
            source="manual",
            form_platform="HubSpot",
            crm_destination="Salesforce",
            webhook_urls=["https://hooks.zapier.com/abc"],
            notification_targets=["team@example.com"],
            notes=["Confirmed by IT"],
        )
        assert oe.form_platform == "HubSpot"
        assert len(oe.webhook_urls) == 1

    def test_scan_request_accepts_integration_evidence(self):
        req = ScanRequest(
            url="https://example.com",
            integration_evidence={"form_platform": "HubSpot", "crm_destination": "Salesforce"},
        )
        assert req.integration_evidence == {"form_platform": "HubSpot", "crm_destination": "Salesforce"}

    def test_scan_request_integration_evidence_defaults_none(self):
        req = ScanRequest(url="https://example.com")
        assert req.integration_evidence is None

    def test_scan_result_has_processor_map(self):
        # Just check the field exists with correct default
        fields = ScanResult.model_fields
        assert "processor_map" in fields
        assert "operator_integration_evidence" in fields

    def test_processor_map_item_defaults(self):
        item = ProcessorMapItem()
        assert item.processor_name is None
        assert item.processor_type == "unknown"
        assert item.source == "inferred_public_signal"
        assert item.confidence == "low"
        assert item.evidence == []

    def test_visited_page_has_routing_fields(self):
        page = _make_page()
        assert page.downstream_processor_type is None
        assert page.downstream_processor_name is None
        assert page.downstream_routing_confidence == "low"
        assert page.downstream_routing_signals == []


class TestActionUrlSignatures:
    def test_signatures_not_empty(self):
        assert len(_ACTION_URL_SIGNATURES) > 0

    def test_covers_hubspot(self):
        urls = [s[0] for s in _ACTION_URL_SIGNATURES]
        assert any("hubspot" in u for u in urls)

    def test_covers_formspree(self):
        urls = [s[0] for s in _ACTION_URL_SIGNATURES]
        assert any("formspree" in u for u in urls)
