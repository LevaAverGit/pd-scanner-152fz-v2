"""
policy_parser_service.py — heuristic analysis of linked privacy/policy pages.

Fetches the first candidate privacy/policy page (same-host only) and analyses
its text content for common policy section indicators.  Results are heuristic
signals, not legal compliance determinations.

Routes PDF and DOCX policy URLs to document extraction
instead of Playwright.  HTML pages use the existing Playwright path unchanged.
Image-only / unextractable documents are recorded with policy_parse_status
"unreadable".
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

from playwright.async_api import BrowserContext, TimeoutError as PlaywrightTimeout

from backend.app.models.schemas import PolicyAnalysis
from backend.app.services.document_extraction_service import (
    detect_document_type,
    download_document,
    extract_docx_text,
    extract_pdf_text,
)
from backend.app.utils.patterns import (
    POLICY_CATEGORIES_KEYWORDS,
    POLICY_CROSS_BORDER_KEYWORDS,
    POLICY_LEGAL_BASIS_KEYWORDS,
    POLICY_LOCALIZATION_KEYWORDS,
    POLICY_PROCESSOR_KEYWORDS,
    POLICY_PURPOSE_KEYWORDS,
    POLICY_RETENTION_KEYWORDS,
    POLICY_SUBJECT_RIGHTS_KEYWORDS,
)

logger = logging.getLogger(__name__)

PAGE_TIMEOUT_MS: int = 20_000
STABILISE_TIMEOUT_MS: int = 6_000

# Regex patterns for contact extraction
_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_PHONE_RE = re.compile(
    r"(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}"
    r"|(?:\+\d{1,3}[\s\-]?\d{1,4}[\s\-]?\d{2,4}[\s\-]?\d{2,4}[\s\-]?\d{2,4})"
)

# Patterns to infer operator name from body text / h1 / title
_ORG_NAME_RE = re.compile(
    r"(?:ООО|ОАО|ЗАО|АО|ИП|ПАО|НКО|ФГУП|МУП|АНО)\s+[«\"]?[\wА-Яа-яЁё\s\-]+[»\"]?",
    re.UNICODE,
)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def parse_policy_page(
    context: BrowserContext,
    candidate_urls: list[str],
    base_host: str,
) -> PolicyAnalysis | None:
    """
    Try each URL in candidate_urls (same-host only).  Return a PolicyAnalysis
    for the first successfully loaded page, or None if none worked.

    Routing:
      .pdf  → document extraction via PyMuPDF
      .docx → document extraction via python-docx
      .doc  → unsupported (recorded with policy_parse_status "unsupported")
      other → Playwright HTML analysis (original behaviour)
    """
    for url in candidate_urls:
        # Enforce same-host
        try:
            if urlparse(url).netloc.lower() != base_host:
                continue
        except Exception:
            continue

        doc_type = detect_document_type(url)

        if doc_type in ("pdf", "docx"):
            result = await _analyse_document(url, doc_type)
        elif doc_type == "doc":
            result = PolicyAnalysis(
                url=url,
                policy_document_type="doc",
                policy_document_url=url,
                policy_parse_status="unsupported",
                policy_signals=[
                    "Legacy .doc (binary Word) format is not supported for "
                    "automated text extraction. Manual review required."
                ],
            )
        else:
            result = await _analyse_one(context, url)

        if result is not None:
            return result

    return None


# ---------------------------------------------------------------------------
# Document path (PDF / DOCX)
# ---------------------------------------------------------------------------

async def _analyse_document(url: str, doc_type: str) -> PolicyAnalysis | None:
    """Download and extract text from a PDF or DOCX policy document."""
    content, _content_type, dl_status = await download_document(url)

    if dl_status != "ok" or content is None:
        logger.warning(
            "policy_parser: document download %s for %s", dl_status, url
        )
        return PolicyAnalysis(
            url=url,
            policy_document_type=doc_type,
            policy_document_url=url,
            policy_parse_status="failed",
            policy_signals=[
                f"Document download failed (status: {dl_status}). "
                "Manual review required."
            ],
        )

    if doc_type == "pdf":
        text, extract_status = extract_pdf_text(content)
    else:
        text, extract_status = extract_docx_text(content)

    if extract_status != "parsed":
        logger.info(
            "policy_parser: %s extraction status '%s' for %s",
            doc_type.upper(), extract_status, url,
        )
        return PolicyAnalysis(
            url=url,
            policy_document_type=doc_type,
            policy_document_url=url,
            policy_parse_status="unreadable",
            policy_signals=[
                f"{doc_type.upper()} document is present but yielded no extractable text "
                "(likely image-only or encrypted). Manual review required."
            ],
        )

    return _analyse_text(text=text, url=url, doc_type=doc_type)


# ---------------------------------------------------------------------------
# HTML path (Playwright)
# ---------------------------------------------------------------------------

async def _analyse_one(context: BrowserContext, url: str) -> PolicyAnalysis | None:
    page = None
    try:
        page = await context.new_page()
        try:
            await page.goto(url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
        except PlaywrightTimeout:
            logger.debug("policy_parser: timeout loading %s", url)
        try:
            await page.wait_for_load_state("networkidle", timeout=STABILISE_TIMEOUT_MS)
        except PlaywrightTimeout:
            pass

        # Extract full visible text and title/h1
        try:
            body_text: str = await page.evaluate("document.body.innerText || ''")
        except Exception:
            body_text = ""

        try:
            title: str = await page.title()
        except Exception:
            title = ""

        try:
            h1_texts: list[str] = await page.locator("h1").all_text_contents()
            h1 = " ".join(h1_texts)
        except Exception:
            h1 = ""

        if not body_text.strip():
            return None

        return _analyse_text(text=body_text, url=url, doc_type="html", title=title, h1=h1)

    except Exception as exc:
        logger.warning("policy_parser: failed to analyse %s: %s", url, exc)
        return None
    finally:
        if page is not None:
            try:
                await page.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Shared keyword analysis (used by both HTML and document paths)
# ---------------------------------------------------------------------------

def _analyse_text(
    text: str,
    url: str,
    doc_type: str = "html",
    title: str = "",
    h1: str = "",
) -> PolicyAnalysis:
    """
    Run keyword-based heuristic analysis on extracted plain text.
    Returns a PolicyAnalysis regardless of how many sections were found.
    This function is pure Python and works identically for HTML, PDF, and DOCX.
    """
    lower = text.lower()

    def _has(*kws: str) -> bool:
        return any(kw.lower() in lower for kw in kws)

    has_purpose = _has(*POLICY_PURPOSE_KEYWORDS)
    has_categories = _has(*POLICY_CATEGORIES_KEYWORDS)
    has_legal_basis = _has(*POLICY_LEGAL_BASIS_KEYWORDS)
    has_processor = _has(*POLICY_PROCESSOR_KEYWORDS)
    has_cross_border = _has(*POLICY_CROSS_BORDER_KEYWORDS)
    has_subject_rights = _has(*POLICY_SUBJECT_RIGHTS_KEYWORDS)
    has_retention = _has(*POLICY_RETENTION_KEYWORDS)
    has_localization = _has(*POLICY_LOCALIZATION_KEYWORDS)

    # Operator name — try org patterns in body, then h1, then title
    operator_name: str | None = None
    org_match = _ORG_NAME_RE.search(text)
    if org_match:
        operator_name = org_match.group(0).strip()[:120]
    elif h1.strip():
        operator_name = h1.strip()[:120]
    elif title.strip():
        operator_name = title.strip()[:120]

    # Contact extraction
    emails = list({m for m in _EMAIL_RE.findall(text)})[:5]
    phones = list({m for m in _PHONE_RE.findall(text)})[:5]
    contacts = emails + phones

    # Build policy signals
    signals: list[str] = []
    if has_purpose:
        signals.append("Purpose/goals section found")
    if has_categories:
        signals.append("Personal data categories section found")
    if has_legal_basis:
        signals.append("Legal basis section found")
    if has_processor:
        signals.append("Third-party processor/transfer section found")
    if has_cross_border:
        signals.append("Cross-border data transfer section found")
    if has_subject_rights:
        signals.append("Data subject rights section found")
    if has_retention:
        signals.append("Data retention/destruction section found")
    if has_localization:
        signals.append("Data localization statement found (possible 152-FZ reference)")
    if doc_type in ("pdf", "docx"):
        signals.append(f"Findings extracted from {doc_type.upper()} document text")

    return PolicyAnalysis(
        url=url,
        operator_name=operator_name,
        operator_contacts=contacts,
        has_purpose_section=has_purpose,
        has_categories_section=has_categories,
        has_legal_basis_section=has_legal_basis,
        has_processor_or_third_party_section=has_processor,
        has_cross_border_section=has_cross_border,
        has_subject_rights_section=has_subject_rights,
        has_retention_or_destruction_section=has_retention,
        has_localization_statement=has_localization,
        policy_signals=signals,
        policy_document_type=doc_type,
        policy_document_url=url,
        policy_parse_status="parsed",
    )
