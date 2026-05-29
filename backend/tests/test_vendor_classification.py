"""
Unit tests for vendor_classification_service and submit_analysis_service.
"""

import pytest

from backend.app.models.schemas import NetworkObservation
from backend.app.services.vendor_classification_service import (
    classify_vendors,
    vendor_class_description,
)
from backend.app.services.submit_analysis_service import (
    _classify_action,
    _detect_platform_from_scripts,
    _detect_platform_from_hidden_inputs,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _obs(host: str, is_third_party: bool = True) -> NetworkObservation:
    return NetworkObservation(
        host=host,
        resource_type="script",
        is_third_party=is_third_party,
        method="GET",
    )


# ---------------------------------------------------------------------------
# vendor_classification_service — classify_vendors
# ---------------------------------------------------------------------------

class TestClassifyVendors:
    def test_known_analytics_vendor(self):
        obs = [_obs("www.google-analytics.com")]
        result = classify_vendors(obs)
        assert len(result) == 1
        assert result[0].vendor_class == "analytics"
        assert result[0].vendor_name is not None

    def test_known_tag_manager(self):
        obs = [_obs("www.googletagmanager.com")]
        result = classify_vendors(obs)
        assert any(v.vendor_class == "tag_manager" for v in result)

    def test_known_advertising_vendor(self):
        obs = [_obs("connect.facebook.net")]
        result = classify_vendors(obs)
        assert any(v.vendor_class == "advertising" for v in result)

    def test_known_form_platform(self):
        obs = [_obs("js.hsforms.net")]
        result = classify_vendors(obs)
        assert any(v.vendor_class == "form_platform" for v in result)
        assert any(v.vendor_name == "HubSpot Forms" for v in result)

    def test_known_payment_vendor(self):
        obs = [_obs("js.stripe.com")]
        result = classify_vendors(obs)
        assert any(v.vendor_class == "payment" for v in result)

    def test_first_party_excluded(self):
        obs = [_obs("example.com", is_third_party=False)]
        result = classify_vendors(obs)
        assert len(result) == 0

    def test_unknown_vendor_classified(self):
        obs = [_obs("some-unknown-tracker.io")]
        result = classify_vendors(obs)
        assert len(result) == 1
        assert result[0].vendor_class == "unknown"
        assert result[0].vendor_name is None

    def test_deduplication(self):
        # Same host appearing twice → only one entry
        obs = [_obs("www.google-analytics.com"), _obs("www.google-analytics.com")]
        result = classify_vendors(obs)
        assert len(result) == 1

    def test_high_interest_classes_sorted_first(self):
        obs = [
            _obs("fonts.googleapis.com"),           # fonts (low-interest)
            _obs("js.hsforms.net"),                  # form_platform (high-interest)
            _obs("connect.facebook.net"),            # advertising (high-interest)
        ]
        result = classify_vendors(obs)
        classes = [v.vendor_class for v in result]
        # All high-interest classes must appear before 'fonts'
        high_interest = {"form_platform", "crm_or_lead_capture", "call_tracking",
                         "advertising", "tag_manager"}
        font_idx = next(i for i, v in enumerate(result) if v.vendor_class == "fonts")
        for i, v in enumerate(result):
            if v.vendor_class in high_interest:
                assert i < font_idx, f"{v.vendor_class} should appear before fonts"

    def test_first_seen_on_populated(self):
        obs = [_obs("www.google-analytics.com")]
        first_seen = {"www.google-analytics.com": "https://example.com/about"}
        result = classify_vendors(obs, host_first_seen=first_seen)
        assert result[0].first_seen_on == "https://example.com/about"

    def test_first_seen_on_none_when_not_provided(self):
        obs = [_obs("www.google-analytics.com")]
        result = classify_vendors(obs)
        assert result[0].first_seen_on is None

    def test_notes_populated_for_high_interest(self):
        obs = [_obs("js.hsforms.net")]
        result = classify_vendors(obs)
        assert result[0].notes  # should have at least one note

    def test_cdn_vendor_classified(self):
        obs = [_obs("cdn.jsdelivr.net")]
        result = classify_vendors(obs)
        assert any(v.vendor_class == "cdn_or_static" for v in result)

    def test_social_vendor_classified(self):
        obs = [_obs("platform.twitter.com")]
        result = classify_vendors(obs)
        assert any(v.vendor_class == "social" for v in result)


# ---------------------------------------------------------------------------
# vendor_class_description
# ---------------------------------------------------------------------------

class TestVendorClassDescription:
    def test_known_class_returns_non_empty(self):
        for cls in ["analytics", "advertising", "tag_manager", "form_platform",
                    "crm_or_lead_capture", "payment", "cdn_or_static", "fonts",
                    "maps", "video_or_media", "social", "chat_widget",
                    "call_tracking", "consent_management", "unknown"]:
            desc = vendor_class_description(cls)
            assert desc, f"Expected non-empty description for '{cls}'"

    def test_unknown_class_fallback(self):
        desc = vendor_class_description("made_up_class")
        assert desc  # should return a generic fallback


# ---------------------------------------------------------------------------
# submit_analysis_service — _classify_action
# ---------------------------------------------------------------------------

class TestClassifyAction:
    def test_empty_action_is_unknown(self):
        _, t = _classify_action("", "https://example.com/signup")
        assert t == "unknown"

    def test_hash_only_is_unknown(self):
        _, t = _classify_action("#anchor", "https://example.com/page")
        assert t == "unknown"

    def test_relative_path_is_relative(self):
        _, t = _classify_action("/api/submit", "https://example.com/signup")
        assert t == "relative"

    def test_same_host_is_first_party(self):
        target, t = _classify_action(
            "https://example.com/api/contact",
            "https://example.com/contact",
        )
        assert t == "first_party"
        assert target == "https://example.com/api/contact"

    def test_www_stripped_same_host(self):
        _, t = _classify_action(
            "https://www.example.com/submit",
            "https://example.com/form",
        )
        assert t == "first_party"

    def test_different_host_is_third_party(self):
        target, t = _classify_action(
            "https://forms.hubspot.com/submit",
            "https://example.com/contact",
        )
        assert t == "third_party"
        assert target == "https://forms.hubspot.com/submit"

    def test_no_scheme_action_treated_as_relative(self):
        _, t = _classify_action("submit.php", "https://example.com/page")
        assert t == "relative"


# ---------------------------------------------------------------------------
# submit_analysis_service — _detect_platform_from_scripts
# ---------------------------------------------------------------------------

class TestDetectPlatformFromScripts:
    def test_hubspot_detected(self):
        fp, crm = _detect_platform_from_scripts(["https://js.hsforms.net/forms/v2.js"])
        assert fp == "HubSpot Forms"

    def test_typeform_detected(self):
        fp, crm = _detect_platform_from_scripts(["https://embed.typeform.com/next/embed.js"])
        assert fp == "Typeform"

    def test_crm_detected(self):
        fp, crm = _detect_platform_from_scripts(["https://amocrm.ru/js/form.js"])
        assert crm == "amoCRM"

    def test_no_match_returns_none(self):
        fp, crm = _detect_platform_from_scripts(["https://cdn.example.com/app.js"])
        assert fp is None
        assert crm is None

    def test_empty_list(self):
        fp, crm = _detect_platform_from_scripts([])
        assert fp is None
        assert crm is None


# ---------------------------------------------------------------------------
# submit_analysis_service — _detect_platform_from_hidden_inputs
# ---------------------------------------------------------------------------

class TestDetectPlatformFromHiddenInputs:
    def test_wordpress_cf7(self):
        fp, crm = _detect_platform_from_hidden_inputs(["_wpcf7", "_wpcf7_version"])
        assert fp == "Contact Form 7"

    def test_hubspot_hidden(self):
        fp, crm = _detect_platform_from_hidden_inputs(["hs_context", "portalId"])
        assert fp == "HubSpot"

    def test_salesforce_web_to_lead(self):
        fp, crm = _detect_platform_from_hidden_inputs(["oid", "retURL"])
        assert crm == "Salesforce Web-to-Lead"

    def test_tilda_form(self):
        fp, crm = _detect_platform_from_hidden_inputs(["tilda-page"])
        assert fp == "Tilda"

    def test_no_match(self):
        fp, crm = _detect_platform_from_hidden_inputs(["user_id", "form_id"])
        assert fp is None
        assert crm is None
