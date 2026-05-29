"""
Unit tests for the page_classifier_service.

Tests cover:
- URL path token detection (login, registration, checkout, callback)
- Text keyword scoring
- Field presence signals (password / email)
- Tie-breaking rules
- Pagination / low-value path scoring in link_discovery_service
"""

import pytest

from backend.app.services.page_classifier_service import classify_page
from backend.app.services.link_discovery_service import _priority_score


# ---------------------------------------------------------------------------
# URL path signal tests
# ---------------------------------------------------------------------------

class TestURLPathSignals:
    def test_login_url_returns_login(self):
        result = classify_page(
            url="https://example.com/login",
            title="", headings=[], form_texts=[],
        )
        assert result == "login"

    def test_signin_url_returns_login(self):
        result = classify_page(
            url="https://example.com/signin",
            title="", headings=[], form_texts=[],
        )
        assert result == "login"

    def test_register_url_returns_likely_registration(self):
        # URL alone (no text evidence) → likely_registration, not full registration
        result = classify_page(
            url="https://example.com/register",
            title="", headings=[], form_texts=[],
        )
        assert result == "likely_registration"

    def test_signup_url_with_text_returns_registration(self):
        result = classify_page(
            url="https://example.com/signup",
            title="Create Account",
            headings=["Sign up for free"],
            form_texts=["Register now"],
        )
        assert result == "registration"

    def test_checkout_url_returns_checkout(self):
        result = classify_page(
            url="https://shop.example.com/checkout",
            title="", headings=[], form_texts=[],
        )
        assert result == "checkout"

    def test_cart_url_returns_checkout(self):
        result = classify_page(
            url="https://shop.example.com/cart",
            title="", headings=[], form_texts=[],
        )
        assert result == "checkout"

    def test_contact_url_returns_contact(self):
        result = classify_page(
            url="https://example.com/contact",
            title="", headings=[], form_texts=[],
        )
        assert result == "contact"


# ---------------------------------------------------------------------------
# Field presence signal tests
# ---------------------------------------------------------------------------

class TestFieldPresenceSignals:
    def test_password_field_alone_returns_login(self):
        result = classify_page(
            url="https://example.com/",
            title="",
            headings=[],
            form_texts=[],
            has_password_field=True,
        )
        assert result == "login"

    def test_password_and_email_returns_login(self):
        result = classify_page(
            url="https://example.com/",
            title="",
            headings=[],
            form_texts=[],
            has_password_field=True,
            has_email_field=True,
        )
        assert result == "login"

    def test_login_url_plus_password_field_returns_login(self):
        result = classify_page(
            url="https://example.com/login",
            title="Sign in to your account",
            headings=["Log in"],
            form_texts=["Email", "Password"],
            has_password_field=True,
            has_email_field=True,
        )
        assert result == "login"

    def test_no_signals_returns_ambiguous(self):
        result = classify_page(
            url="https://example.com/about",
            title="About Us",
            headings=[],
            form_texts=[],
        )
        assert result == "ambiguous"


# ---------------------------------------------------------------------------
# Text scoring tests
# ---------------------------------------------------------------------------

class TestTextScoring:
    def test_strong_registration_text_returns_registration(self):
        result = classify_page(
            url="https://example.com/account",
            title="Create Account",
            headings=["Register for free", "Sign up today"],
            form_texts=["Create your account", "Join us"],
        )
        assert result == "registration"

    def test_login_text_returns_login(self):
        result = classify_page(
            url="https://example.com/",
            title="Member Login",
            headings=["Sign in"],
            form_texts=["Log in"],
        )
        assert result == "login"

    def test_newsletter_text_returns_newsletter(self):
        result = classify_page(
            url="https://example.com/updates",
            title="Subscribe to our newsletter",
            headings=["Mailing list"],
            form_texts=["Stay updated", "Email updates"],
        )
        assert result == "newsletter"

    def test_checkout_text_returns_checkout(self):
        result = classify_page(
            url="https://example.com/",
            title="Complete Your Order",
            headings=["Checkout"],
            form_texts=["Billing", "Payment", "Place order"],
        )
        assert result == "checkout"


# ---------------------------------------------------------------------------
# Tie-breaking tests
# ---------------------------------------------------------------------------

class TestTieBreaking:
    def test_checkout_beats_contact_on_tie(self):
        # checkout should win tie over contact
        result = classify_page(
            url="https://example.com/order-contact",
            title="",
            headings=[],
            form_texts=[],
        )
        # /order-contact path → checkout token "order" wins (score 3)
        # vs contact (score 2)
        assert result == "checkout"

    def test_login_beats_newsletter_on_tie(self):
        # If login and newsletter tie on text, login wins
        result = classify_page(
            url="https://example.com/",
            title="login newsletter",
            headings=[],
            form_texts=[],
        )
        assert result == "login"


# ---------------------------------------------------------------------------
# Link discovery priority scoring
# ---------------------------------------------------------------------------

class TestPriorityScoring:
    def test_login_path_gets_positive_score(self):
        score = _priority_score("https://example.com/login")
        assert score > 0

    def test_register_path_gets_positive_score(self):
        score = _priority_score("https://example.com/register")
        assert score > 0

    def test_author_path_gets_negative_score(self):
        score = _priority_score("https://example.com/author/john-smith")
        assert score < 0

    def test_tag_path_gets_negative_score(self):
        score = _priority_score("https://example.com/tag/python")
        assert score < 0

    def test_pagination_gets_negative_score(self):
        score = _priority_score("https://example.com/blog/page/2")
        assert score < 0

    def test_homepage_gets_zero_score(self):
        score = _priority_score("https://example.com/")
        assert score == 0

    def test_login_scores_higher_than_author(self):
        assert _priority_score("https://example.com/login") > \
               _priority_score("https://example.com/author/jane")
