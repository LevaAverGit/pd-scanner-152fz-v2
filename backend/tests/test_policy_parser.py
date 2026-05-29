"""
Unit tests — no Playwright, no network, no personal data.

Covers:
  - Pattern keyword lists (patterns.py)
  - Policy parser section detection logic (pure Python, no browser)
  - Interactive discovery helper functions
  - Deep consent keyword presence
"""

import pytest

# ---------------------------------------------------------------------------
# 1. Pattern keyword lists
# ---------------------------------------------------------------------------

class TestPatternKeywords:
    def test_interactive_cta_patterns_non_empty(self):
        from backend.app.utils.patterns import INTERACTIVE_CTA_PATTERNS
        assert len(INTERACTIVE_CTA_PATTERNS) > 0

    def test_interactive_cta_has_ru_and_en(self):
        from backend.app.utils.patterns import INTERACTIVE_CTA_PATTERNS
        joined = " ".join(INTERACTIVE_CTA_PATTERNS)
        assert "заявку" in joined  # RU
        assert "contact us" in joined  # EN

    def test_interactive_expand_patterns_non_empty(self):
        from backend.app.utils.patterns import INTERACTIVE_EXPAND_PATTERNS
        assert len(INTERACTIVE_EXPAND_PATTERNS) > 0
        assert "read more" in INTERACTIVE_EXPAND_PATTERNS

    def test_policy_purpose_keywords(self):
        from backend.app.utils.patterns import POLICY_PURPOSE_KEYWORDS
        assert "purpose" in POLICY_PURPOSE_KEYWORDS
        assert "цели" in POLICY_PURPOSE_KEYWORDS

    def test_policy_categories_keywords(self):
        from backend.app.utils.patterns import POLICY_CATEGORIES_KEYWORDS
        assert any("categor" in kw for kw in POLICY_CATEGORIES_KEYWORDS)
        assert any("персональных данных" in kw for kw in POLICY_CATEGORIES_KEYWORDS)

    def test_policy_legal_basis_keywords(self):
        from backend.app.utils.patterns import POLICY_LEGAL_BASIS_KEYWORDS
        assert "legal basis" in POLICY_LEGAL_BASIS_KEYWORDS

    def test_policy_processor_keywords(self):
        from backend.app.utils.patterns import POLICY_PROCESSOR_KEYWORDS
        assert "third party" in POLICY_PROCESSOR_KEYWORDS
        assert "третьи лица" in POLICY_PROCESSOR_KEYWORDS

    def test_policy_cross_border_keywords(self):
        from backend.app.utils.patterns import POLICY_CROSS_BORDER_KEYWORDS
        assert "трансграничная передача" in POLICY_CROSS_BORDER_KEYWORDS

    def test_policy_subject_rights_keywords(self):
        from backend.app.utils.patterns import POLICY_SUBJECT_RIGHTS_KEYWORDS
        assert "your rights" in POLICY_SUBJECT_RIGHTS_KEYWORDS
        assert "права субъекта" in POLICY_SUBJECT_RIGHTS_KEYWORDS

    def test_policy_retention_keywords(self):
        from backend.app.utils.patterns import POLICY_RETENTION_KEYWORDS
        assert "retention" in POLICY_RETENTION_KEYWORDS
        assert "сроки хранения" in POLICY_RETENTION_KEYWORDS

    def test_policy_localization_keywords(self):
        from backend.app.utils.patterns import POLICY_LOCALIZATION_KEYWORDS
        assert "152-фз" in POLICY_LOCALIZATION_KEYWORDS
        assert "локализация" in POLICY_LOCALIZATION_KEYWORDS

    def test_consent_bundled_keywords_has_ru_and_en(self):
        from backend.app.utils.patterns import CONSENT_BUNDLED_KEYWORDS
        joined = " ".join(CONSENT_BUNDLED_KEYWORDS)
        assert "by clicking" in joined
        assert "нажимая" in joined
        assert "i agree" in joined
        assert "я соглашаюсь" in joined

    def test_consent_bundled_keywords_non_empty(self):
        from backend.app.utils.patterns import CONSENT_BUNDLED_KEYWORDS
        assert len(CONSENT_BUNDLED_KEYWORDS) > 10


# ---------------------------------------------------------------------------
# 2. Policy parser — section detection (pure Python, no browser)
# ---------------------------------------------------------------------------

class TestPolicyParserLogic:
    """Tests for the _has() pattern matching logic used inside _analyse_one."""

    def _has(self, text: str, *keywords: str) -> bool:
        lower = text.lower()
        return any(kw.lower() in lower for kw in keywords)

    def test_detects_purpose_section_en(self):
        from backend.app.utils.patterns import POLICY_PURPOSE_KEYWORDS
        text = "This policy describes the purposes of personal data processing."
        assert self._has(text, *POLICY_PURPOSE_KEYWORDS)

    def test_detects_purpose_section_ru(self):
        from backend.app.utils.patterns import POLICY_PURPOSE_KEYWORDS
        text = "Цели обработки: улучшение сервиса, выполнение договора."
        assert self._has(text, *POLICY_PURPOSE_KEYWORDS)

    def test_detects_categories_section_ru(self):
        from backend.app.utils.patterns import POLICY_CATEGORIES_KEYWORDS
        text = "Состав персональных данных: ФИО, телефон, email."
        assert self._has(text, *POLICY_CATEGORIES_KEYWORDS)

    def test_detects_legal_basis(self):
        from backend.app.utils.patterns import POLICY_LEGAL_BASIS_KEYWORDS
        text = "The legal basis for processing is consent of the data subject."
        assert self._has(text, *POLICY_LEGAL_BASIS_KEYWORDS)

    def test_detects_cross_border(self):
        from backend.app.utils.patterns import POLICY_CROSS_BORDER_KEYWORDS
        text = "Трансграничная передача персональных данных не осуществляется."
        assert self._has(text, *POLICY_CROSS_BORDER_KEYWORDS)

    def test_detects_subject_rights(self):
        from backend.app.utils.patterns import POLICY_SUBJECT_RIGHTS_KEYWORDS
        text = "Your rights include the right to access, rectification and erasure."
        assert self._has(text, *POLICY_SUBJECT_RIGHTS_KEYWORDS)

    def test_detects_retention(self):
        from backend.app.utils.patterns import POLICY_RETENTION_KEYWORDS
        text = "Сроки хранения: данные хранятся 5 лет после закрытия договора."
        assert self._has(text, *POLICY_RETENTION_KEYWORDS)

    def test_detects_localization(self):
        from backend.app.utils.patterns import POLICY_LOCALIZATION_KEYWORDS
        text = "Данные хранятся на серверах, расположенных на территории РФ (152-ФЗ)."
        # pattern is "152-фз" (lowercased)
        assert self._has(text, *POLICY_LOCALIZATION_KEYWORDS)

    def test_no_false_positive_empty_text(self):
        from backend.app.utils.patterns import POLICY_PURPOSE_KEYWORDS
        assert not self._has("", *POLICY_PURPOSE_KEYWORDS)

    def test_email_regex_matches(self):
        import re
        _EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
        text = "Contact us at support@example.com or info@company.ru"
        matches = _EMAIL_RE.findall(text)
        assert "support@example.com" in matches
        assert "info@company.ru" in matches

    def test_phone_regex_matches_ru(self):
        import re
        _PHONE_RE = re.compile(
            r"(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}"
        )
        text = "Телефон: +7 (495) 123-45-67"
        assert _PHONE_RE.search(text) is not None

    def test_org_name_regex_matches(self):
        import re
        _ORG_NAME_RE = re.compile(
            r"(?:ООО|ОАО|ЗАО|АО|ИП|ПАО|НКО|ФГУП|МУП|АНО)\s+[«\"]?[\wА-Яа-яЁё\s\-]+[»\"]?",
            re.UNICODE,
        )
        text = 'Оператор: ООО «Ромашка» осуществляет обработку.'
        match = _ORG_NAME_RE.search(text)
        assert match is not None
        assert "ООО" in match.group(0)


# ---------------------------------------------------------------------------
# 3. Interactive discovery service — pure Python helpers
# ---------------------------------------------------------------------------

class TestInteractiveDiscoveryHelpers:
    def test_empty_result_structure(self):
        from backend.app.services.interactive_discovery_service import _empty_result
        r = _empty_result()
        assert r["hidden_forms_revealed"] == 0
        assert r["interactions_performed"] == []
        assert r["dynamic_consent_signals"] == []
        assert r["modal_forms_found"] == 0

    def test_build_selector_button(self):
        from backend.app.services.interactive_discovery_service import _build_selector
        sel = _build_selector("Get Started", "button")
        assert sel.startswith("button")
        assert "Get Started" in sel

    def test_build_selector_anchor(self):
        from backend.app.services.interactive_discovery_service import _build_selector
        sel = _build_selector("Contact Us", "a")
        assert sel.startswith("a:")

    def test_build_selector_generic(self):
        from backend.app.services.interactive_discovery_service import _build_selector
        sel = _build_selector("Subscribe", "div")
        assert ":has-text(" in sel

    def test_build_selector_strips_quotes(self):
        from backend.app.services.interactive_discovery_service import _build_selector
        # Should not raise; quotes are sanitised
        sel = _build_selector('Say "hello"', "button")
        assert '"hello"' not in sel or sel.count('"') == 2  # outer quotes only

    def test_skip_text_patterns_contains_submit(self):
        from backend.app.services.interactive_discovery_service import _SKIP_TEXT_PATTERNS
        assert "submit" in _SKIP_TEXT_PATTERNS
        assert "отправить" in _SKIP_TEXT_PATTERNS
        assert "login" in _SKIP_TEXT_PATTERNS

    def test_max_interactions_constant(self):
        from backend.app.services.interactive_discovery_service import MAX_INTERACTIONS_PER_PAGE
        assert 1 <= MAX_INTERACTIONS_PER_PAGE <= 20  # sanity bounds

    def test_click_timeout_reasonable(self):
        from backend.app.services.interactive_discovery_service import CLICK_TIMEOUT_MS
        assert 500 <= CLICK_TIMEOUT_MS <= 10_000


# ---------------------------------------------------------------------------
# 4. Deep consent — CONSENT_BUNDLED_KEYWORDS completeness
# ---------------------------------------------------------------------------

class TestConsentBundledKeywords:
    def test_has_english_click_phrase(self):
        from backend.app.utils.patterns import CONSENT_BUNDLED_KEYWORDS
        assert "by clicking" in CONSENT_BUNDLED_KEYWORDS

    def test_has_russian_click_phrase(self):
        from backend.app.utils.patterns import CONSENT_BUNDLED_KEYWORDS
        assert "нажимая" in CONSENT_BUNDLED_KEYWORDS

    def test_has_i_agree(self):
        from backend.app.utils.patterns import CONSENT_BUNDLED_KEYWORDS
        assert "i agree" in CONSENT_BUNDLED_KEYWORDS

    def test_has_personal_data_ru(self):
        from backend.app.utils.patterns import CONSENT_BUNDLED_KEYWORDS
        assert "персональные данные" in CONSENT_BUNDLED_KEYWORDS

    def test_has_privacy_policy_en(self):
        from backend.app.utils.patterns import CONSENT_BUNDLED_KEYWORDS
        assert "privacy policy" in CONSENT_BUNDLED_KEYWORDS


# ---------------------------------------------------------------------------
# 5. Schema — PolicyAnalysis model defaults
# ---------------------------------------------------------------------------

class TestPolicyAnalysisSchema:
    def test_default_fields(self):
        from backend.app.models.schemas import PolicyAnalysis
        pa = PolicyAnalysis(url="https://example.com/privacy")
        assert pa.operator_name is None
        assert pa.operator_contacts == []
        assert pa.has_purpose_section is False
        assert pa.has_localization_statement is False
        assert pa.policy_signals == []

    def test_full_construction(self):
        from backend.app.models.schemas import PolicyAnalysis
        pa = PolicyAnalysis(
            url="https://example.com/privacy",
            operator_name="ООО Ромашка",
            operator_contacts=["info@example.com"],
            has_purpose_section=True,
            has_localization_statement=True,
            policy_signals=["Purpose/goals section found"],
        )
        assert pa.has_purpose_section is True
        assert pa.has_localization_statement is True
        assert len(pa.policy_signals) == 1

    def test_scan_result_has_policy_analysis_field(self):
        from backend.app.models.schemas import ScanResult, ScanStatus
        result = ScanResult(
            scan_id="test",
            url="https://example.com",
            status=ScanStatus.pending,
            data_categories=[],
            created_at="2026-01-01T00:00:00Z",
        )
        assert result.policy_analysis is None

    def test_visited_page_item_has_interactive_discovery_fields(self):
        from backend.app.models.schemas import VisitedPageItem
        page = VisitedPageItem(url="https://example.com")
        assert page.hidden_forms_revealed == 0
        assert page.interactions_performed == []
        assert page.dynamic_consent_signals == []
        assert page.modal_forms_found == 0
        assert page.has_bundled_consent_text is False
