"""Tests for the 152-FZ Evidence Layer."""
import pytest

from backend.app.models.schemas import (
    FZ152Assessment,
    OperatorIntegrationEvidence,
    OperatorMetadata,
    PolicyAnalysis,
    ProcessorMapItem,
    ScanRequest,
    ScanResult,
    VisitedPageItem,
    VendorSummaryItem,
)
from backend.app.services.fz152_assessment_service import (
    _derive_consent_mechanism_type,
    _derive_potential_gaps,
    _derive_manual_validation_targets,
    _derive_risk_level,
    build_fz152_assessment,
)


def _make_page(**kwargs) -> VisitedPageItem:
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
        downstream_processor_type=None,
        downstream_processor_name=None,
        downstream_routing_confidence="low",
        downstream_routing_signals=[],
    )
    defaults.update(kwargs)
    return VisitedPageItem(**defaults)


class TestConsentMechanismType:
    def test_explicit_checkbox(self):
        pages = [_make_page(has_consent_checkbox=True, forms_found=1)]
        assert _derive_consent_mechanism_type(pages) == "explicit_checkbox"

    def test_bundled_text(self):
        pages = [_make_page(has_bundled_consent_text=True, forms_found=1)]
        assert _derive_consent_mechanism_type(pages) == "bundled_text"

    def test_mixed(self):
        pages = [
            _make_page(has_consent_checkbox=True, forms_found=1),
            _make_page(has_bundled_consent_text=True, forms_found=1),
        ]
        assert _derive_consent_mechanism_type(pages) == "mixed"

    def test_weak_or_absent(self):
        pages = [_make_page(forms_found=1, fields_count=2)]
        assert _derive_consent_mechanism_type(pages) == "weak_or_absent"

    def test_unknown_when_no_forms(self):
        pages = [_make_page()]
        assert _derive_consent_mechanism_type(pages) == "unknown"


class TestPotentialGaps:
    def _base_assessment(self, **kwargs):
        defaults = dict(
            policy_publicly_available=True,
            consent_mechanism_type="explicit_checkbox",
            third_party_routing_present=False,
            processor_map_present=False,
            metrics_or_tracking_present=False,
            forms_collecting_pd=1,
            detected_pd_categories=[],
            policy_has_purpose_section=True,
            policy_has_categories_section=True,
            policy_has_legal_basis_section=True,
            policy_has_processor_or_third_party_section=True,
            policy_has_cross_border_section=False,
            policy_has_subject_rights_section=True,
            policy_has_retention_or_destruction_section=True,
            policy_has_localization_statement=True,
            operator_name=None,
            operator_contacts=[],
            privacy_links_found=1,
            observed_submit_present=False,
            operator_supplied_evidence_present=False,
            potential_gaps=[],
            manual_validation_targets=[],
            overall_public_risk_level="medium",
        )
        defaults.update(kwargs)
        return FZ152Assessment(**defaults)

    def test_no_policy_generates_gap(self):
        a = self._base_assessment(policy_publicly_available=False)
        gaps = _derive_potential_gaps(a, None, [], [])
        assert any("policy" in g.lower() for g in gaps)

    def test_weak_consent_generates_gap(self):
        a = self._base_assessment(consent_mechanism_type="weak_or_absent")
        gaps = _derive_potential_gaps(a, None, [], [])
        assert any("consent" in g.lower() for g in gaps)

    def test_bundled_consent_generates_gap(self):
        a = self._base_assessment(consent_mechanism_type="bundled_text")
        gaps = _derive_potential_gaps(a, None, [], [])
        assert any("bundled" in g.lower() or "implied" in g.lower() or "explicit" in g.lower() for g in gaps)

    def test_third_party_no_disclosure_generates_gap(self):
        a = self._base_assessment(
            third_party_routing_present=True,
            policy_has_processor_or_third_party_section=False,
        )
        gaps = _derive_potential_gaps(a, None, [], [])
        assert any("third-party" in g.lower() or "processor" in g.lower() for g in gaps)

    def test_metrics_tracking_generates_gap(self):
        a = self._base_assessment(metrics_or_tracking_present=True)
        gaps = _derive_potential_gaps(a, None, [], [])
        assert any("metrics" in g.lower() or "tracking" in g.lower() or "analytic" in g.lower() or "cookie" in g.lower() for g in gaps)

    def test_no_gaps_for_clean_site(self):
        a = self._base_assessment()
        gaps = _derive_potential_gaps(a, None, [], [])
        assert len(gaps) == 0


class TestManualValidationTargets:
    def _base_assessment(self, **kwargs):
        defaults = dict(
            policy_publicly_available=True,
            consent_mechanism_type="explicit_checkbox",
            third_party_routing_present=False,
            processor_map_present=False,
            metrics_or_tracking_present=False,
            forms_collecting_pd=1,
            detected_pd_categories=[],
            policy_has_purpose_section=True,
            policy_has_categories_section=True,
            policy_has_legal_basis_section=True,
            policy_has_processor_or_third_party_section=True,
            policy_has_cross_border_section=True,
            policy_has_subject_rights_section=True,
            policy_has_retention_or_destruction_section=True,
            policy_has_localization_statement=True,
            operator_name=None,
            operator_contacts=[],
            privacy_links_found=1,
            observed_submit_present=False,
            operator_supplied_evidence_present=False,
            potential_gaps=[],
            manual_validation_targets=[],
            overall_public_risk_level="low",
        )
        defaults.update(kwargs)
        return FZ152Assessment(**defaults)

    def test_always_includes_operator_identity_check(self):
        a = self._base_assessment()
        targets = _derive_manual_validation_targets(a)
        assert any("operator" in t.lower() or "legal" in t.lower() for t in targets)

    def test_includes_consent_review_for_bundled(self):
        a = self._base_assessment(consent_mechanism_type="bundled_text")
        targets = _derive_manual_validation_targets(a)
        assert any("consent" in t.lower() for t in targets)

    def test_includes_dpa_review_for_third_party(self):
        a = self._base_assessment(third_party_routing_present=True, processor_map_present=True)
        targets = _derive_manual_validation_targets(a)
        assert any("processor" in t.lower() or "dpa" in t.lower() or "agreement" in t.lower() for t in targets)


class TestRiskLevel:
    def _base_assessment(self, **kwargs):
        defaults = dict(
            policy_publicly_available=True,
            consent_mechanism_type="explicit_checkbox",
            third_party_routing_present=False,
            policy_has_processor_or_third_party_section=True,
            policy_has_cross_border_section=True,
            policy_has_legal_basis_section=True,
            policy_has_subject_rights_section=True,
            policy_has_retention_or_destruction_section=True,
            metrics_or_tracking_present=False,
            potential_gaps=[],
        )
        defaults.update(kwargs)
        return FZ152Assessment(**defaults)

    def test_no_policy_is_high_risk(self):
        a = self._base_assessment(policy_publicly_available=False)
        assert _derive_risk_level(a) == "high"

    def test_weak_consent_is_high_risk(self):
        a = self._base_assessment(consent_mechanism_type="weak_or_absent")
        assert _derive_risk_level(a) == "high"

    def test_clean_site_is_low_risk(self):
        a = self._base_assessment()
        assert _derive_risk_level(a) == "low"

    def test_bundled_consent_is_at_least_medium(self):
        a = self._base_assessment(consent_mechanism_type="bundled_text")
        assert _derive_risk_level(a) in ("medium", "high")


class TestOperatorMetadataSchema:
    def test_defaults(self):
        om = OperatorMetadata()
        assert om.legal_name is None
        assert om.inn is None
        assert om.ogrn is None
        assert om.notes == []

    def test_full_construction(self):
        om = OperatorMetadata(legal_name="ООО Тест", inn="1234567890", ogrn="1231234567890", notes=["note"])
        assert om.legal_name == "ООО Тест"
        assert om.inn == "1234567890"

    def test_scan_request_accepts_operator_metadata(self):
        req = ScanRequest(url="https://example.com", operator_metadata={"legal_name": "ООО Тест"})
        assert req.operator_metadata == {"legal_name": "ООО Тест"}

    def test_scan_result_has_fz152_field(self):
        fields = ScanResult.model_fields
        assert "fz152_assessment" in fields
        assert "operator_metadata" in fields


class TestBuildFZ152Assessment:
    def test_builds_successfully_with_minimal_input(self):
        result = build_fz152_assessment([], None, None, [], [], None, None)
        assert isinstance(result, FZ152Assessment)
        assert result.overall_public_risk_level in ("low", "medium", "high")

    def test_privacy_link_detected(self):
        pages = [_make_page(has_privacy_link=True)]
        result = build_fz152_assessment(pages, None, None, [], [], None, None)
        assert result.policy_publicly_available is True
        assert result.privacy_links_found == 1

    def test_operator_metadata_name_used(self):
        om = OperatorMetadata(legal_name="ООО Тест")
        result = build_fz152_assessment([], None, None, [], [], None, om)
        assert result.operator_name == "ООО Тест"

    def test_policy_analysis_sections_mapped(self):
        policy = PolicyAnalysis(
            url="https://example.com/policy",
            has_purpose_section=True,
            has_legal_basis_section=True,
            has_subject_rights_section=True,
        )
        result = build_fz152_assessment([], policy, None, [], [], None, None)
        assert result.policy_has_purpose_section is True
        assert result.policy_has_legal_basis_section is True
        assert result.policy_has_subject_rights_section is True

    def test_tracking_vendor_detected(self):
        vendor = VendorSummaryItem(host="google-analytics.com", vendor_class="analytics")
        result = build_fz152_assessment([], None, None, [vendor], [], None, None)
        assert result.metrics_or_tracking_present is True

    def test_potential_gaps_generated(self):
        # No policy, weak consent → gaps
        pages = [_make_page(forms_found=1, fields_count=2)]
        result = build_fz152_assessment(pages, None, None, [], [], None, None)
        assert len(result.potential_gaps) > 0

    def test_manual_validation_targets_generated(self):
        result = build_fz152_assessment([], None, None, [], [], None, None)
        assert len(result.manual_validation_targets) > 0

    def test_disclaimer_present(self):
        result = build_fz152_assessment([], None, None, [], [], None, None)
        assert "152-FZ" in result.disclaimer or "heuristic" in result.disclaimer.lower()
