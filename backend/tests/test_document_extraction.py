"""
Policy Document Parsing tests.

Covers:
  A. document_extraction_service: detect_document_type, extract_pdf_text,
     extract_docx_text, download_document
  B. policy_parser_service: routing (PDF/DOCX/HTML/legacy-doc), _analyse_text
     keyword coverage, parse-status propagation
  C. PolicyAnalysis schema: new fields present and serialise correctly
  D. Integration: PDF/DOCX policy → richer FZ152Assessment, potential_gaps
     decrease when sections are actually present in document text
"""
from __future__ import annotations

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.models.schemas import PolicyAnalysis
from backend.app.services.document_extraction_service import (
    detect_document_type,
    extract_docx_text,
    extract_pdf_text,
)
from backend.app.services.policy_parser_service import _analyse_text
from backend.app.services.fz152_assessment_service import build_fz152_assessment


# ---------------------------------------------------------------------------
# Helpers — generate in-memory fixture bytes
# ---------------------------------------------------------------------------

def _make_pdf_bytes(text: str) -> bytes:
    """
    Create a minimal text-based PDF using PyMuPDF.
    Uses insert_htmlbox for full Unicode/Cyrillic support (pymupdf >= 1.21).
    """
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_htmlbox(page.rect, text)
    buf = doc.tobytes()
    doc.close()
    return buf


def _make_docx_bytes(text: str) -> bytes:
    """Create a minimal DOCX in memory using python-docx."""
    from docx import Document as DocxDocument
    doc = DocxDocument()
    for line in text.splitlines():
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _make_empty_pdf_bytes() -> bytes:
    """PDF that opens but contains no text (simulates image-only)."""
    import fitz
    doc = fitz.open()
    doc.new_page()   # blank page — no text inserted
    buf = doc.tobytes()
    doc.close()
    return buf


# Full 152-FZ compliant policy text used in integration tests
FULL_POLICY_TEXT = """
Политика конфиденциальности и обработки персональных данных
ООО «Тест Компани»

1. Цели обработки персональных данных
Настоящая политика описывает цели обработки персональных данных пользователей.

2. Категории персональных данных
Состав персональных данных: имя, email, телефон.

3. Правовое основание обработки
Основание обработки — согласие субъекта персональных данных.

4. Третьи лица и контрагенты
Передача персональных данных третьим лицам осуществляется только на основании договора.

5. Трансграничная передача
Трансграничная передача данных не осуществляется.

6. Права субъектов персональных данных
Права субъекта: право на доступ, право на исправление, право отозвать согласие.

7. Сроки хранения персональных данных
Сроки хранения персональных данных определяются целями обработки.

8. Локализация данных
Персональные данные хранятся на территории Российской Федерации в соответствии с 152-ФЗ.

Контакты: privacy@test-company.ru, +7 (495) 123-45-67
""".strip()


# ---------------------------------------------------------------------------
# Part A — detect_document_type
# ---------------------------------------------------------------------------

class TestDetectDocumentType:
    def test_pdf_from_url_extension(self):
        assert detect_document_type("https://example.com/privacy.pdf") == "pdf"

    def test_docx_from_url_extension(self):
        assert detect_document_type("https://example.com/policy.docx") == "docx"

    def test_doc_from_url_extension(self):
        assert detect_document_type("https://example.com/policy.doc") == "doc"

    def test_defaults_to_html_for_unknown(self):
        assert detect_document_type("https://example.com/privacy") == "html"

    def test_defaults_to_html_for_html_page(self):
        assert detect_document_type("https://example.com/privacy.html") == "html"

    def test_pdf_from_content_type(self):
        assert detect_document_type(
            "https://example.com/policy",
            content_type="application/pdf",
        ) == "pdf"

    def test_docx_from_content_type(self):
        assert detect_document_type(
            "https://example.com/policy",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ) == "docx"

    def test_doc_from_content_type(self):
        assert detect_document_type(
            "https://example.com/policy",
            content_type="application/msword",
        ) == "doc"

    def test_url_extension_takes_precedence_over_content_type(self):
        # URL says .pdf — trust the extension
        assert detect_document_type(
            "https://example.com/policy.pdf",
            content_type="text/html",
        ) == "pdf"

    def test_query_string_not_confused_with_extension(self):
        # Query string after ? should not affect detection
        result = detect_document_type("https://example.com/download?file=policy.pdf")
        assert result == "html"   # path itself has no extension


# ---------------------------------------------------------------------------
# Part A — extract_pdf_text
# ---------------------------------------------------------------------------

class TestExtractPdfText:
    def test_extracts_text_from_simple_pdf(self):
        content = _make_pdf_bytes("Hello privacy policy world")
        text, status = extract_pdf_text(content)
        assert status == "parsed"
        assert "Hello" in text
        assert "privacy" in text

    def test_extracts_cyrillic_text_from_pdf(self):
        content = _make_pdf_bytes("Политика конфиденциальности ООО Тест")
        text, status = extract_pdf_text(content)
        assert status == "parsed"
        assert "конфиденциальности" in text

    def test_empty_page_pdf_returns_unreadable(self):
        content = _make_empty_pdf_bytes()
        text, status = extract_pdf_text(content)
        assert status == "unreadable"
        assert text == ""

    def test_corrupt_bytes_return_failed(self):
        text, status = extract_pdf_text(b"this is not a pdf at all %%EOF")
        assert status == "failed"
        assert text == ""

    def test_full_policy_text_round_trip(self):
        content = _make_pdf_bytes(FULL_POLICY_TEXT)
        text, status = extract_pdf_text(content)
        assert status == "parsed"
        # Key phrases must survive round-trip
        assert "персональных данных" in text.lower()
        assert "152" in text


# ---------------------------------------------------------------------------
# Part A — extract_docx_text
# ---------------------------------------------------------------------------

class TestExtractDocxText:
    def test_extracts_text_from_simple_docx(self):
        content = _make_docx_bytes("Hello privacy policy world")
        text, status = extract_docx_text(content)
        assert status == "parsed"
        assert "Hello" in text
        assert "privacy" in text

    def test_extracts_cyrillic_text_from_docx(self):
        content = _make_docx_bytes("Политика конфиденциальности ООО Тест")
        text, status = extract_docx_text(content)
        assert status == "parsed"
        assert "конфиденциальности" in text

    def test_corrupt_bytes_return_failed(self):
        text, status = extract_docx_text(b"this is not a docx at all")
        assert status == "failed"
        assert text == ""

    def test_full_policy_text_round_trip(self):
        content = _make_docx_bytes(FULL_POLICY_TEXT)
        text, status = extract_docx_text(content)
        assert status == "parsed"
        assert "персональных данных" in text.lower()
        assert "152" in text


# ---------------------------------------------------------------------------
# Part B — _analyse_text keyword coverage
# ---------------------------------------------------------------------------

class TestAnalyseText:
    def test_detects_all_eight_sections_in_full_policy(self):
        pa = _analyse_text(FULL_POLICY_TEXT, url="https://example.com/policy.pdf", doc_type="pdf")
        assert pa.has_purpose_section
        assert pa.has_categories_section
        assert pa.has_legal_basis_section
        assert pa.has_processor_or_third_party_section
        assert pa.has_cross_border_section
        assert pa.has_subject_rights_section
        assert pa.has_retention_or_destruction_section
        assert pa.has_localization_statement

    def test_no_sections_detected_for_unrelated_text(self):
        pa = _analyse_text("Buy our product now! Great deals!", url="https://example.com/page")
        assert not pa.has_purpose_section
        assert not pa.has_legal_basis_section
        assert pa.policy_signals == []

    def test_extracts_operator_name_from_russian_org_pattern(self):
        pa = _analyse_text(
            "ООО «Тест Компани» настоящим уведомляет об обработке данных.",
            url="https://example.com/policy",
        )
        assert pa.operator_name is not None
        assert "ООО" in pa.operator_name

    def test_extracts_email_contact(self):
        pa = _analyse_text(
            "Свяжитесь с нами: privacy@example.com",
            url="https://example.com/policy",
        )
        assert "privacy@example.com" in pa.operator_contacts

    def test_extracts_russian_phone_contact(self):
        pa = _analyse_text(
            "Телефон: +7 (495) 123-45-67",
            url="https://example.com/policy",
        )
        assert len(pa.operator_contacts) >= 1
        assert any("495" in c for c in pa.operator_contacts)

    def test_pdf_doc_type_adds_extraction_signal(self):
        pa = _analyse_text("Some policy text", url="https://example.com/policy.pdf", doc_type="pdf")
        assert any("PDF" in s for s in pa.policy_signals)

    def test_docx_doc_type_adds_extraction_signal(self):
        pa = _analyse_text("Some policy text", url="https://example.com/policy.docx", doc_type="docx")
        assert any("DOCX" in s for s in pa.policy_signals)

    def test_html_doc_type_does_not_add_extraction_signal(self):
        pa = _analyse_text("Some policy text", url="https://example.com/policy", doc_type="html")
        assert not any("PDF" in s or "DOCX" in s for s in pa.policy_signals)

    def test_parse_status_is_parsed(self):
        pa = _analyse_text("Some text", url="https://example.com/policy")
        assert pa.policy_parse_status == "parsed"

    def test_policy_document_url_set(self):
        pa = _analyse_text("Some text", url="https://example.com/policy.pdf", doc_type="pdf")
        assert pa.policy_document_url == "https://example.com/policy.pdf"


# ---------------------------------------------------------------------------
# Part B — policy_parser_service routing (mocked download)
# ---------------------------------------------------------------------------

class TestPolicyParserRouting:
    @pytest.mark.asyncio
    async def test_pdf_url_triggers_document_path_and_returns_analysis(self):
        from backend.app.services.policy_parser_service import parse_policy_page
        pdf_bytes = _make_pdf_bytes(FULL_POLICY_TEXT)
        mock_ctx = MagicMock()

        with patch(
            "backend.app.services.policy_parser_service.download_document",
            new=AsyncMock(return_value=(pdf_bytes, "application/pdf", "ok")),
        ):
            result = await parse_policy_page(
                context=mock_ctx,
                candidate_urls=["https://example.com/privacy.pdf"],
                base_host="example.com",
            )

        assert result is not None
        assert result.policy_document_type == "pdf"
        assert result.policy_parse_status == "parsed"
        assert result.has_purpose_section
        assert result.has_localization_statement

    @pytest.mark.asyncio
    async def test_docx_url_triggers_document_path_and_returns_analysis(self):
        from backend.app.services.policy_parser_service import parse_policy_page
        docx_bytes = _make_docx_bytes(FULL_POLICY_TEXT)
        mock_ctx = MagicMock()

        with patch(
            "backend.app.services.policy_parser_service.download_document",
            new=AsyncMock(return_value=(docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "ok")),
        ):
            result = await parse_policy_page(
                context=mock_ctx,
                candidate_urls=["https://example.com/privacy.docx"],
                base_host="example.com",
            )

        assert result is not None
        assert result.policy_document_type == "docx"
        assert result.policy_parse_status == "parsed"
        assert result.has_purpose_section

    @pytest.mark.asyncio
    async def test_doc_url_returns_unsupported_without_download(self):
        from backend.app.services.policy_parser_service import parse_policy_page
        mock_ctx = MagicMock()

        with patch(
            "backend.app.services.policy_parser_service.download_document",
            new=AsyncMock(),  # should NOT be called
        ) as mock_dl:
            result = await parse_policy_page(
                context=mock_ctx,
                candidate_urls=["https://example.com/privacy.doc"],
                base_host="example.com",
            )
            mock_dl.assert_not_called()

        assert result is not None
        assert result.policy_document_type == "doc"
        assert result.policy_parse_status == "unsupported"

    @pytest.mark.asyncio
    async def test_failed_download_returns_failed_parse_status(self):
        from backend.app.services.policy_parser_service import parse_policy_page
        mock_ctx = MagicMock()

        with patch(
            "backend.app.services.policy_parser_service.download_document",
            new=AsyncMock(return_value=(None, None, "failed")),
        ):
            result = await parse_policy_page(
                context=mock_ctx,
                candidate_urls=["https://example.com/privacy.pdf"],
                base_host="example.com",
            )

        assert result is not None
        assert result.policy_parse_status == "failed"

    @pytest.mark.asyncio
    async def test_unreadable_pdf_returns_unreadable_parse_status(self):
        from backend.app.services.policy_parser_service import parse_policy_page
        empty_pdf = _make_empty_pdf_bytes()
        mock_ctx = MagicMock()

        with patch(
            "backend.app.services.policy_parser_service.download_document",
            new=AsyncMock(return_value=(empty_pdf, "application/pdf", "ok")),
        ):
            result = await parse_policy_page(
                context=mock_ctx,
                candidate_urls=["https://example.com/privacy.pdf"],
                base_host="example.com",
            )

        assert result is not None
        assert result.policy_parse_status == "unreadable"
        assert any("image-only" in s.lower() or "manual" in s.lower() for s in result.policy_signals)

    @pytest.mark.asyncio
    async def test_cross_host_urls_are_skipped(self):
        from backend.app.services.policy_parser_service import parse_policy_page
        mock_ctx = MagicMock()

        with patch(
            "backend.app.services.policy_parser_service.download_document",
            new=AsyncMock(),
        ) as mock_dl:
            result = await parse_policy_page(
                context=mock_ctx,
                candidate_urls=["https://other-domain.com/privacy.pdf"],
                base_host="example.com",
            )
            mock_dl.assert_not_called()

        assert result is None

    @pytest.mark.asyncio
    async def test_first_successful_url_wins(self):
        from backend.app.services.policy_parser_service import parse_policy_page
        pdf_bytes = _make_pdf_bytes("Цели обработки персональных данных")
        mock_ctx = MagicMock()

        call_count = 0

        async def mock_download(url):
            nonlocal call_count
            call_count += 1
            return (pdf_bytes, "application/pdf", "ok")

        with patch(
            "backend.app.services.policy_parser_service.download_document",
            new=mock_download,
        ):
            result = await parse_policy_page(
                context=mock_ctx,
                candidate_urls=[
                    "https://example.com/privacy.pdf",
                    "https://example.com/terms.pdf",
                ],
                base_host="example.com",
            )

        assert result is not None
        assert call_count == 1  # stopped after first success


# ---------------------------------------------------------------------------
# Part C — PolicyAnalysis schema fields
# ---------------------------------------------------------------------------

class TestPolicyAnalysisSchema:
    def test_default_document_type_is_html(self):
        pa = PolicyAnalysis(url="https://example.com/policy")
        assert pa.policy_document_type == "html"

    def test_default_parse_status_is_parsed(self):
        pa = PolicyAnalysis(url="https://example.com/policy")
        assert pa.policy_parse_status == "parsed"

    def test_default_document_url_is_none(self):
        pa = PolicyAnalysis(url="https://example.com/policy")
        assert pa.policy_document_url is None

    def test_new_fields_serialise_to_dict(self):
        pa = PolicyAnalysis(
            url="https://example.com/policy.pdf",
            policy_document_type="pdf",
            policy_document_url="https://example.com/policy.pdf",
            policy_parse_status="parsed",
        )
        d = pa.model_dump()
        assert d["policy_document_type"] == "pdf"
        assert d["policy_document_url"] == "https://example.com/policy.pdf"
        assert d["policy_parse_status"] == "parsed"

    def test_unreadable_status_serialises(self):
        pa = PolicyAnalysis(
            url="https://example.com/policy.pdf",
            policy_document_type="pdf",
            policy_parse_status="unreadable",
        )
        d = pa.model_dump()
        assert d["policy_parse_status"] == "unreadable"


# ---------------------------------------------------------------------------
# Part D — Integration: FZ152Assessment enriched by document policy
# ---------------------------------------------------------------------------

class TestFZ152AssessmentWithDocumentPolicy:
    """
    Verify that a full-sections policy parsed from a PDF document propagates
    correctly into FZ152Assessment and reduces potential_gaps compared to a
    scan with no policy.
    """

    def _make_minimal_pages(self):
        """Minimal VisitedPageItem list with one form page."""
        from backend.app.models.schemas import (
            VisitedPageItem, DataCategoryItem, SiteSummary,
        )
        page = VisitedPageItem(
            url="https://example.com/register",
            forms_found=1,
            detected_categories=[
                DataCategoryItem(
                    category="name",
                    confidence=0.9,
                    matched_signals=["name field"],
                    explanation="name field detected",
                )
            ],
            has_privacy_link=True,
            has_consent_checkbox=True,
            registration_relevance="high",
        )
        return [page]

    def _make_site_summary(self):
        from backend.app.models.schemas import SiteSummary
        return SiteSummary(
            pages_scanned=1,
            pages_with_forms=1,
            total_forms_found=1,
            unique_categories_found=["name"],
            top_third_party_hosts=[],
            pages_with_privacy_link=1,
            pages_with_consent_checkbox=1,
            pages_with_marketing_consent=0,
        )

    def test_no_policy_generates_more_gaps_than_full_pdf_policy(self):
        pages = self._make_minimal_pages()
        summary = self._make_site_summary()

        # Assessment with NO policy
        assess_no_policy = build_fz152_assessment(
            visited_pages=pages,
            policy=None,
            site_summary=summary,
            vendor_summary=[],
            processor_map=[],
            operator_evidence=None,
            operator_metadata=None,
        )

        # Assessment WITH full PDF policy
        pdf_policy = _analyse_text(
            FULL_POLICY_TEXT,
            url="https://example.com/privacy.pdf",
            doc_type="pdf",
        )
        assess_with_policy = build_fz152_assessment(
            visited_pages=pages,
            policy=pdf_policy,
            site_summary=summary,
            vendor_summary=[],
            processor_map=[],
            operator_evidence=None,
            operator_metadata=None,
        )

        # Full policy should result in fewer manual validation targets or lower risk.
        # The fz152 assessment uses manual_validation_targets (not potential_gaps) for
        # missing-section signals when a privacy link is already present.
        assert (
            len(assess_with_policy.manual_validation_targets)
            < len(assess_no_policy.manual_validation_targets)
        ), "Full PDF policy should reduce manual_validation_targets vs no policy"

    def test_full_pdf_policy_sets_all_section_flags_true(self):
        pages = self._make_minimal_pages()
        pdf_policy = _analyse_text(
            FULL_POLICY_TEXT,
            url="https://example.com/privacy.pdf",
            doc_type="pdf",
        )
        assess = build_fz152_assessment(
            visited_pages=pages,
            policy=pdf_policy,
            site_summary=self._make_site_summary(),
            vendor_summary=[],
            processor_map=[],
            operator_evidence=None,
            operator_metadata=None,
        )
        assert assess.policy_has_purpose_section
        assert assess.policy_has_categories_section
        assert assess.policy_has_legal_basis_section
        assert assess.policy_has_processor_or_third_party_section
        assert assess.policy_has_cross_border_section
        assert assess.policy_has_subject_rights_section
        assert assess.policy_has_retention_or_destruction_section
        assert assess.policy_has_localization_statement

    def test_pdf_policy_publicly_available_set_true(self):
        pages = self._make_minimal_pages()
        pdf_policy = _analyse_text(
            FULL_POLICY_TEXT,
            url="https://example.com/privacy.pdf",
            doc_type="pdf",
        )
        assess = build_fz152_assessment(
            visited_pages=pages,
            policy=pdf_policy,
            site_summary=self._make_site_summary(),
            vendor_summary=[],
            processor_map=[],
            operator_evidence=None,
            operator_metadata=None,
        )
        assert assess.policy_publicly_available is True

    def test_full_policy_lowers_risk_compared_to_no_policy(self):
        pages = self._make_minimal_pages()
        summary = self._make_site_summary()

        assess_no_policy = build_fz152_assessment(
            visited_pages=pages,
            policy=None,
            site_summary=summary,
            vendor_summary=[],
            processor_map=[],
            operator_evidence=None,
            operator_metadata=None,
        )

        pdf_policy = _analyse_text(
            FULL_POLICY_TEXT,
            url="https://example.com/privacy.pdf",
            doc_type="pdf",
        )
        assess_with_policy = build_fz152_assessment(
            visited_pages=pages,
            policy=pdf_policy,
            site_summary=summary,
            vendor_summary=[],
            processor_map=[],
            operator_evidence=None,
            operator_metadata=None,
        )

        risk_order = {"low": 0, "medium": 1, "high": 2}
        no_policy_risk = risk_order.get(assess_no_policy.overall_public_risk_level, 1)
        with_policy_risk = risk_order.get(assess_with_policy.overall_public_risk_level, 1)
        assert with_policy_risk <= no_policy_risk, (
            "Full policy should not increase risk level"
        )

    def test_docx_policy_also_propagates_to_assessment(self):
        """DOCX-extracted text follows the same pathway as PDF."""
        pages = self._make_minimal_pages()
        docx_policy = _analyse_text(
            FULL_POLICY_TEXT,
            url="https://example.com/privacy.docx",
            doc_type="docx",
        )
        assess = build_fz152_assessment(
            visited_pages=pages,
            policy=docx_policy,
            site_summary=self._make_site_summary(),
            vendor_summary=[],
            processor_map=[],
            operator_evidence=None,
            operator_metadata=None,
        )
        assert assess.policy_has_localization_statement
        assert assess.policy_publicly_available
