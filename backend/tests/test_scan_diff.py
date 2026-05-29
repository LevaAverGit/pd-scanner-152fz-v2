"""Tests for Scan Diff / Compare Mode."""
import pytest
import pytest_asyncio
from unittest.mock import patch
from httpx import ASGITransport, AsyncClient

from backend.app.main import app
from backend.app.models.db import init_db
from backend.app.models.schemas import (
    DataCategoryItem,
    FZ152Assessment,
    PolicyAnalysis,
    ProcessorMapItem,
    ScanDiffRequest,
    ScanDiffResult,
    ScanResult,
    ScanStatus,
    SiteSummary,
    VendorSummaryItem,
)
from backend.app.services.scan_diff_service import compute_scan_diff


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_category(category: str, confidence: float = 1.0) -> DataCategoryItem:
    return DataCategoryItem(
        category=category,
        confidence=confidence,
        matched_signals=[category],
        explanation=f"{category} field detected",
    )


def _make_vendor(host: str, vendor_class: str = "analytics") -> VendorSummaryItem:
    return VendorSummaryItem(host=host, vendor_class=vendor_class, vendor_name=host)


def _make_processor(name: str) -> ProcessorMapItem:
    return ProcessorMapItem(processor_name=name, processor_type="analytics")


def _make_fz152(**kwargs) -> FZ152Assessment:
    defaults = dict(
        overall_public_risk_level="medium",
        consent_mechanism_type="explicit_checkbox",
        policy_has_purpose_section=True,
        policy_has_categories_section=True,
        policy_has_legal_basis_section=False,
        policy_has_processor_or_third_party_section=False,
        policy_has_cross_border_section=False,
        policy_has_subject_rights_section=False,
        policy_has_retention_or_destruction_section=False,
        policy_has_localization_statement=False,
        potential_gaps=[],
        manual_validation_targets=[],
    )
    defaults.update(kwargs)
    return FZ152Assessment(**defaults)


def _make_scan(
    scan_id: str = "scan-a",
    url: str = "https://example.com",
    status: ScanStatus = ScanStatus.complete,
    categories: list[DataCategoryItem] | None = None,
    vendors: list[VendorSummaryItem] | None = None,
    processors: list[ProcessorMapItem] | None = None,
    fz152: FZ152Assessment | None = None,
    site_summary: SiteSummary | None = None,
    registration_relevance: str | None = None,
    completed_at: str | None = "2026-04-01T10:00:00Z",
) -> ScanResult:
    return ScanResult(
        scan_id=scan_id,
        url=url,
        status=status,
        data_categories=categories or [],
        created_at="2026-04-01T09:00:00Z",
        completed_at=completed_at,
        vendor_summary=vendors or [],
        processor_map=processors or [],
        fz152_assessment=fz152,
        site_summary=site_summary,
        registration_relevance=registration_relevance,
    )


# ---------------------------------------------------------------------------
# TestComputeScanDiff — unit tests for the diff service
# ---------------------------------------------------------------------------

class TestComputeScanDiff:
    def test_identical_scans_produce_no_diff(self):
        fz = _make_fz152()
        scan = _make_scan(
            categories=[_make_category("email")],
            vendors=[_make_vendor("mc.yandex.ru")],
            processors=[_make_processor("Yandex Metrica")],
            fz152=fz,
        )
        result = compute_scan_diff(scan, scan)
        assert result.added_categories == []
        assert result.removed_categories == []
        assert result.added_vendors == []
        assert result.removed_vendors == []
        assert result.changed_items == []
        assert len(result.summary_lines) == 1
        assert "No significant differences" in result.summary_lines[0]

    def test_added_category_detected(self):
        base = _make_scan(categories=[_make_category("email")])
        compare = _make_scan(
            scan_id="scan-b",
            categories=[_make_category("email"), _make_category("phone")],
        )
        result = compute_scan_diff(base, compare)
        assert "phone" in result.added_categories
        assert result.removed_categories == []

    def test_removed_category_detected(self):
        base = _make_scan(categories=[_make_category("email"), _make_category("phone")])
        compare = _make_scan(scan_id="scan-b", categories=[_make_category("email")])
        result = compute_scan_diff(base, compare)
        assert "phone" in result.removed_categories
        assert result.added_categories == []

    def test_added_and_removed_categories(self):
        base = _make_scan(categories=[_make_category("email"), _make_category("phone")])
        compare = _make_scan(
            scan_id="scan-b",
            categories=[_make_category("email"), _make_category("address")],
        )
        result = compute_scan_diff(base, compare)
        assert "address" in result.added_categories
        assert "phone" in result.removed_categories

    def test_added_vendor_detected(self):
        base = _make_scan(vendors=[_make_vendor("mc.yandex.ru")])
        compare = _make_scan(
            scan_id="scan-b",
            vendors=[_make_vendor("mc.yandex.ru"), _make_vendor("connect.facebook.net")],
        )
        result = compute_scan_diff(base, compare)
        assert "connect.facebook.net" in result.added_vendors

    def test_removed_vendor_detected(self):
        base = _make_scan(vendors=[_make_vendor("mc.yandex.ru"), _make_vendor("connect.facebook.net")])
        compare = _make_scan(scan_id="scan-b", vendors=[_make_vendor("mc.yandex.ru")])
        result = compute_scan_diff(base, compare)
        assert "connect.facebook.net" in result.removed_vendors

    def test_added_processor_detected(self):
        base = _make_scan(processors=[])
        compare = _make_scan(
            scan_id="scan-b",
            processors=[_make_processor("Amplitude")],
        )
        result = compute_scan_diff(base, compare)
        assert "Amplitude" in result.added_processors

    def test_removed_processor_detected(self):
        base = _make_scan(processors=[_make_processor("Amplitude")])
        compare = _make_scan(scan_id="scan-b", processors=[])
        result = compute_scan_diff(base, compare)
        assert "Amplitude" in result.removed_processors

    def test_risk_level_change_detected(self):
        base = _make_scan(fz152=_make_fz152(overall_public_risk_level="low"))
        compare = _make_scan(scan_id="scan-b", fz152=_make_fz152(overall_public_risk_level="high"))
        result = compute_scan_diff(base, compare)
        risk_changes = [c for c in result.changed_items if c.dimension == "risk_level"]
        assert len(risk_changes) == 1
        assert risk_changes[0].base_value == "low"
        assert risk_changes[0].compare_value == "high"

    def test_consent_mechanism_change_detected(self):
        base = _make_scan(fz152=_make_fz152(consent_mechanism_type="explicit_checkbox"))
        compare = _make_scan(
            scan_id="scan-b",
            fz152=_make_fz152(consent_mechanism_type="bundled_text"),
        )
        result = compute_scan_diff(base, compare)
        consent_changes = [c for c in result.changed_items if c.dimension == "consent_mechanism"]
        assert len(consent_changes) == 1
        assert consent_changes[0].compare_value == "bundled_text"

    def test_policy_section_boolean_change_detected(self):
        base = _make_scan(fz152=_make_fz152(policy_has_cross_border_section=False))
        compare = _make_scan(
            scan_id="scan-b",
            fz152=_make_fz152(policy_has_cross_border_section=True),
        )
        result = compute_scan_diff(base, compare)
        section_changes = [
            c for c in result.changed_items if c.dimension == "policy_section.cross_border"
        ]
        assert len(section_changes) == 1
        assert section_changes[0].base_value == "no"
        assert section_changes[0].compare_value == "yes"

    def test_added_gaps_detected(self):
        base = _make_scan(fz152=_make_fz152(potential_gaps=[]))
        compare = _make_scan(
            scan_id="scan-b",
            fz152=_make_fz152(potential_gaps=["Cross-border section missing."]),
        )
        result = compute_scan_diff(base, compare)
        assert result.added_gaps == ["Cross-border section missing."]
        assert result.removed_gaps == []

    def test_removed_gaps_detected(self):
        base = _make_scan(fz152=_make_fz152(potential_gaps=["Cross-border section missing."]))
        compare = _make_scan(scan_id="scan-b", fz152=_make_fz152(potential_gaps=[]))
        result = compute_scan_diff(base, compare)
        assert result.removed_gaps == ["Cross-border section missing."]
        assert result.added_gaps == []

    def test_site_summary_pages_scanned_change(self):
        base_ss = SiteSummary(pages_scanned=3, pages_with_forms=1, total_forms_found=1,
                              unique_categories_found=[], top_third_party_hosts=[])
        cmp_ss = SiteSummary(pages_scanned=8, pages_with_forms=3, total_forms_found=3,
                             unique_categories_found=[], top_third_party_hosts=[])
        base = _make_scan(site_summary=base_ss)
        compare = _make_scan(scan_id="scan-b", site_summary=cmp_ss)
        result = compute_scan_diff(base, compare)
        pages_changes = [c for c in result.changed_items if c.dimension == "pages_scanned"]
        assert len(pages_changes) == 1
        assert pages_changes[0].base_value == "3"
        assert pages_changes[0].compare_value == "8"

    def test_summary_lines_mention_added_category(self):
        base = _make_scan(categories=[_make_category("email")])
        compare = _make_scan(
            scan_id="scan-b",
            categories=[_make_category("email"), _make_category("phone")],
        )
        result = compute_scan_diff(base, compare)
        assert any("phone" in line for line in result.summary_lines)

    def test_no_fz152_in_base_produces_added_change(self):
        base = _make_scan(fz152=None)
        compare = _make_scan(scan_id="scan-b", fz152=_make_fz152())
        result = compute_scan_diff(base, compare)
        fz_changes = [c for c in result.changed_items if c.dimension == "fz152_assessment"]
        assert len(fz_changes) == 1
        assert fz_changes[0].change_type == "added"

    def test_result_model_fields_populated(self):
        base = _make_scan()
        compare = _make_scan(scan_id="scan-b", url="https://other.com")
        result = compute_scan_diff(base, compare)
        assert result.base_scan_id == "scan-a"
        assert result.compare_scan_id == "scan-b"
        assert result.base_url == "https://example.com"
        assert result.compare_url == "https://other.com"
        assert result.base_scanned_at == "2026-04-01T10:00:00Z"


# ---------------------------------------------------------------------------
# TestScanDiffSchema — Pydantic model serialisation
# ---------------------------------------------------------------------------

class TestScanDiffSchema:
    def test_scan_diff_request_valid(self):
        req = ScanDiffRequest(base_scan_id="aaa", compare_scan_id="bbb")
        assert req.base_scan_id == "aaa"

    def test_scan_diff_result_default_lists(self):
        result = ScanDiffResult(
            base_scan_id="a", compare_scan_id="b",
            base_url="https://a.com", compare_url="https://b.com",
        )
        assert result.added_categories == []
        assert result.changed_items == []
        assert result.summary_lines == []

    def test_scan_diff_result_serialises_to_dict(self):
        base = _make_scan()
        compare = _make_scan(scan_id="scan-b")
        result = compute_scan_diff(base, compare)
        d = result.model_dump()
        assert "base_scan_id" in d
        assert "summary_lines" in d


# ---------------------------------------------------------------------------
# TestDiffAPIRoute — integration tests via ASGITransport
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestDiffAPIRoute:
    @pytest_asyncio.fixture(autouse=True)
    async def _init_db(self, tmp_path):
        path = str(tmp_path / "test.db")
        await init_db(path)
        with patch("backend.app.core.config.settings.db_path", path):
            yield

    async def test_diff_returns_404_for_missing_base(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/scan/diff",
                json={"base_scan_id": "nonexistent-base", "compare_scan_id": "nonexistent-cmp"},
            )
        assert resp.status_code == 404
        assert "nonexistent-base" in resp.json()["detail"]

    async def test_diff_endpoint_validates_body(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/scan/diff", json={})
        # Missing required fields → 422
        assert resp.status_code == 422
