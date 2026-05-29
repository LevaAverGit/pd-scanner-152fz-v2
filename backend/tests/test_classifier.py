"""
Unit tests for classifier_service.py

Tests cover:
- Known PD category detection (email, full_name, phone, password, dob)
- False-positive guard: "language" must not match date_of_birth
- Multi-field deduplication via classify_fields
- No match on irrelevant fields
"""

import pytest

from backend.app.services.classifier_service import classify_field, classify_fields


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_field(
    name: str = "",
    label: str = "",
    placeholder: str = "",
    autocomplete: str = "",
    field_type: str = "text",
) -> dict:
    return {
        "tag": "input",
        "field_type": field_type,
        "name": name,
        "id": name,
        "label": label or None,
        "placeholder": placeholder or None,
        "autocomplete": autocomplete or None,
        "required": False,
        "selector": f"#{name}",
    }


# ---------------------------------------------------------------------------
# Single-field classification
# ---------------------------------------------------------------------------

class TestClassifyField:
    def test_email_by_name(self):
        result = classify_field(make_field(name="email"))
        assert result is not None
        assert result.category == "email"

    def test_email_by_label(self):
        result = classify_field(make_field(name="contact", label="Email Address"))
        assert result is not None
        assert result.category == "email"

    def test_field_type_is_not_a_classification_signal(self):
        # field_type is not used by extract_text_signals; only name/id/label/
        # placeholder/aria_label/autocomplete drive classification.
        # A field with name="xfield" and type="email" should not match email.
        result = classify_field(make_field(name="xfield", field_type="email"))
        assert result is None or result.category != "email"

    def test_email_by_autocomplete(self):
        result = classify_field(make_field(name="inp1", autocomplete="email"))
        assert result is not None
        assert result.category == "email"

    def test_full_name_by_name(self):
        result = classify_field(make_field(name="full_name"))
        assert result is not None
        assert result.category == "full_name"

    def test_full_name_by_label(self):
        result = classify_field(make_field(name="field1", label="First Name"))
        assert result is not None
        assert result.category == "full_name"

    def test_full_name_surname_label(self):
        result = classify_field(make_field(name="surname", label="Last name"))
        assert result is not None
        assert result.category == "full_name"

    def test_phone_by_name(self):
        result = classify_field(make_field(name="phone"))
        assert result is not None
        assert result.category == "phone"

    def test_phone_by_label(self):
        result = classify_field(make_field(name="contact_num", label="Mobile Number"))
        assert result is not None
        assert result.category == "phone"

    def test_password_by_type(self):
        result = classify_field(make_field(name="secret", field_type="password"))
        assert result is not None
        assert result.category == "password"

    def test_password_by_name(self):
        result = classify_field(make_field(name="password"))
        assert result is not None
        assert result.category == "password"

    def test_date_of_birth_by_name(self):
        result = classify_field(make_field(name="dob"))
        assert result is not None
        assert result.category == "date_of_birth"

    def test_date_of_birth_by_label(self):
        result = classify_field(make_field(name="field_x", label="Date of Birth"))
        assert result is not None
        assert result.category == "date_of_birth"

    def test_no_match_on_unrelated_field(self):
        result = classify_field(make_field(name="submit_btn", label="Submit"))
        assert result is None

    def test_no_match_on_empty_field(self):
        result = classify_field(
            {"tag": "input", "field_type": "text", "name": None, "id": None,
             "label": None, "placeholder": None, "autocomplete": None,
             "required": False, "selector": "input"}
        )
        assert result is None


# ---------------------------------------------------------------------------
# False-positive guard
# ---------------------------------------------------------------------------

class TestFalsePositives:
    def test_language_does_not_match_date_of_birth(self):
        """'age' inside 'language' must not trigger date_of_birth."""
        result = classify_field(make_field(name="language", label="Language"))
        assert result is None or result.category != "date_of_birth", (
            "FALSE POSITIVE: 'language' matched date_of_birth via substring 'age'"
        )

    def test_message_does_not_match_email(self):
        """'mail' inside 'mailing' should not produce a false positive via boundary check."""
        # 'mail' IS a keyword — 'mailing list' contains whole word 'mail'?
        # Actually \bmail\b matches in "mailing" only if it ends there — it doesn't.
        # This test guards that "email_newsletter" type labels with embedded words
        # don't over-fire if the actual intent is different.
        result = classify_field(make_field(name="comments", label="Leave a message"))
        assert result is None or result.category != "email"

    def test_stage_does_not_match_address(self):
        result = classify_field(make_field(name="stage", label="Stage"))
        # "stage" contains no address keywords as whole tokens
        if result is not None:
            assert result.category != "address"


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------

class TestConfidence:
    def test_single_signal_gives_0_7(self):
        result = classify_field(make_field(name="email"))
        assert result is not None
        assert result.confidence == pytest.approx(0.7)

    def test_multiple_signals_gives_1_0(self):
        # name="email" + label="Email" → 2 distinct signals both match
        result = classify_field(make_field(name="email", label="Email Address"))
        assert result is not None
        assert result.confidence == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Multi-field deduplication
# ---------------------------------------------------------------------------

class TestClassifyFields:
    def test_deduplication_keeps_highest_confidence(self):
        fields = [
            make_field(name="email"),                         # confidence 0.7
            make_field(name="email_addr", label="Email"),     # confidence 1.0
        ]
        results = classify_fields(fields)
        email_results = [r for r in results if r.category == "email"]
        assert len(email_results) == 1
        assert email_results[0].confidence == pytest.approx(1.0)

    def test_multiple_categories_detected(self):
        fields = [
            make_field(name="email", label="Email"),
            make_field(name="full_name", label="Full Name"),
            make_field(name="phone", label="Phone Number"),
        ]
        results = classify_fields(fields)
        cats = {r.category for r in results}
        assert "email" in cats
        assert "full_name" in cats
        assert "phone" in cats

    def test_empty_fields_returns_empty(self):
        assert classify_fields([]) == []
