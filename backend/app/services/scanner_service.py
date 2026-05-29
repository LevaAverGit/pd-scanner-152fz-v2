"""
Main scanner orchestrator for the PD Scanner.
Runs the full scan pipeline as a background task.

Pipeline:
  1. Validate URL
  2. Mark scan as "processing"
  3. Launch headless Chromium via Playwright
  4. Run bounded same-site BFS crawl
  5. Take screenshot of seed URL
  6. Aggregate data categories and network observations across all pages
  7. Build SiteSummary
  8. Classify vendors
  9. Persist results to DB
 10. Export JSON + Markdown reports
 11. On exception: mark scan as failed
"""

import asyncio
import logging
from collections import Counter
from datetime import datetime, timezone
from urllib.parse import urlparse

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

from backend.app.core.config import settings
from backend.app.models.schemas import DataCategoryItem, FZ152Assessment, OperatorIntegrationEvidence, OperatorMetadata, ScanStatus, SiteSummary, SyntheticSubmissionSummary
from backend.app.services.crawler_service import crawl
from backend.app.services.fz152_assessment_service import build_fz152_assessment
from backend.app.services.integration_audit_service import build_processor_map
from backend.app.services.policy_parser_service import parse_policy_page
from backend.app.services.report_service import export_json, export_markdown
from backend.app.services.screenshot_service import capture_screenshot
from backend.app.services.storage_service import update_scan_result, get_scan
from backend.app.services.url_validation import validate_url, URLValidationError
from backend.app.services.vendor_classification_service import classify_vendors

logger = logging.getLogger(__name__)


def _aggregate_categories(
    per_page_categories: list[list[DataCategoryItem]],
) -> list[DataCategoryItem]:
    """
    Merge DataCategoryItem lists from multiple pages.
    Keeps one entry per category (highest confidence wins).
    Merges matched_signals across pages for the winning entry.
    """
    best: dict[str, DataCategoryItem] = {}
    all_signals: dict[str, set[str]] = {}

    for page_cats in per_page_categories:
        for item in page_cats:
            cat = item.category
            existing = best.get(cat)
            if existing is None or item.confidence > existing.confidence:
                best[cat] = item
            if cat not in all_signals:
                all_signals[cat] = set()
            all_signals[cat].update(item.matched_signals)

    result: list[DataCategoryItem] = []
    for cat, item in best.items():
        merged_signals = sorted(all_signals.get(cat, set(item.matched_signals)))
        result.append(
            DataCategoryItem(
                category=item.category,
                confidence=item.confidence,
                matched_signals=merged_signals,
                explanation=item.explanation,
            )
        )
    return sorted(result, key=lambda x: -x.confidence)


def _build_site_summary(visited_pages, observations) -> SiteSummary:
    pages_with_forms = sum(1 for p in visited_pages if p.forms_found > 0)
    total_forms = sum(p.forms_found for p in visited_pages)

    unique_cats: list[str] = sorted(
        {cat.category for p in visited_pages for cat in p.detected_categories}
    )

    third_party_counts: Counter = Counter(
        obs.host for obs in observations if obs.is_third_party
    )
    top_third_party = [host for host, _ in third_party_counts.most_common(5)]

    # Site-wide consent/privacy signal counts
    pages_with_privacy_link = sum(1 for p in visited_pages if p.has_privacy_link)
    pages_with_consent_checkbox = sum(1 for p in visited_pages if p.has_consent_checkbox)
    pages_with_marketing_consent = sum(1 for p in visited_pages if p.has_marketing_consent)

    return SiteSummary(
        pages_scanned=len(visited_pages),
        pages_with_forms=pages_with_forms,
        total_forms_found=total_forms,
        unique_categories_found=unique_cats,
        top_third_party_hosts=top_third_party,
        pages_with_privacy_link=pages_with_privacy_link,
        pages_with_consent_checkbox=pages_with_consent_checkbox,
        pages_with_marketing_consent=pages_with_marketing_consent,
    )


async def run_scan(scan_id: str, url: str, db_path: str, enable_synthetic_submission: bool = False, integration_evidence: dict | None = None, operator_metadata: dict | None = None) -> None:
    """
    Full scan pipeline. Called as a FastAPI background task.
    Synthetic submission only runs when explicitly enabled.
    """
    logger.info("scanner_service: starting scan %s for %s", scan_id, url)

    # Parse operator integration evidence early
    operator_evidence: OperatorIntegrationEvidence | None = None
    if integration_evidence:
        try:
            operator_evidence = OperatorIntegrationEvidence(**integration_evidence)
        except Exception as exc:
            logger.warning("scanner: invalid integration_evidence ignored: %s", exc)

    op_metadata: OperatorMetadata | None = None
    if operator_metadata:
        try:
            op_metadata = OperatorMetadata(**operator_metadata)
        except Exception as exc:
            logger.warning("scanner: invalid operator_metadata ignored: %s", exc)

    # Step 1: Validate URL
    try:
        validate_url(url, allow_local=settings.allow_local_test_targets)
    except URLValidationError as exc:
        logger.warning("scanner_service: URL validation failed for %s: %s", url, exc)
        await update_scan_result(
            db_path=db_path,
            scan_id=scan_id,
            status=ScanStatus.failed,
            error=str(exc),
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        return

    # Step 2: Mark as processing
    await update_scan_result(
        db_path=db_path,
        scan_id=scan_id,
        status=ScanStatus.processing,
    )

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )

            # Step 4: Bounded same-site BFS crawl
            visited_pages, observations, host_first_seen, policy_candidate_urls = await crawl(
                context, url, enable_synthetic_submission=enable_synthetic_submission
            )
            logger.info(
                "scanner_service: crawl returned %d pages, %d observations",
                len(visited_pages), len(observations),
            )

            # Step 4b: Parse policy page if a candidate was discovered
            policy_analysis = None
            if policy_candidate_urls:
                base_host = urlparse(url).netloc.lower()
                try:
                    policy_analysis = await parse_policy_page(context, policy_candidate_urls, base_host)
                    if policy_analysis:
                        logger.info(
                            "scanner_service: policy analysis complete for %s",
                            policy_analysis.url,
                        )
                except Exception as policy_exc:
                    logger.warning("scanner_service: policy analysis failed: %s", policy_exc)

            # Step 5: Screenshot of seed URL
            screenshot_path: str | None = None
            try:
                screenshot_page = await context.new_page()
                try:
                    await screenshot_page.goto(url, timeout=20000, wait_until="domcontentloaded")
                    try:
                        await screenshot_page.wait_for_load_state("networkidle", timeout=8000)
                    except PlaywrightTimeoutError:
                        pass
                    screenshot_path = await capture_screenshot(screenshot_page, scan_id)
                finally:
                    await screenshot_page.close()
            except Exception as ss_exc:
                logger.warning("scanner_service: screenshot failed: %s", ss_exc)

            await context.close()
            await browser.close()

        # Step 6: Aggregate data categories across all pages
        data_categories = _aggregate_categories(
            [p.detected_categories for p in visited_pages]
        )
        logger.info("scanner_service: %d aggregate categories", len(data_categories))

        # Seed URL relevance = first visited page's relevance
        registration_relevance = (
            visited_pages[0].registration_relevance if visited_pages else "ambiguous"
        )

        # Step 7: Build SiteSummary
        site_summary = _build_site_summary(visited_pages, observations)

        # Step 8: Classify vendors
        vendor_summary = classify_vendors(observations, host_first_seen)
        logger.info("scanner_service: %d vendor entries classified", len(vendor_summary))

        # Step 8c: Build processor map
        processor_map = build_processor_map(visited_pages, vendor_summary, operator_evidence)
        logger.info("scanner_service: %d processor map entries built", len(processor_map))

        # Step 8d: Build 152-FZ assessment
        fz152_assessment = build_fz152_assessment(
            visited_pages=visited_pages,
            policy=policy_analysis,
            site_summary=site_summary,
            vendor_summary=vendor_summary,
            processor_map=processor_map,
            operator_evidence=operator_evidence,
            operator_metadata=op_metadata,
        )
        logger.info("scanner_service: 152-FZ assessment built — risk=%s", fz152_assessment.overall_public_risk_level)

        # Step 8b: Build SyntheticSubmissionSummary
        synth_summary: SyntheticSubmissionSummary | None = None
        if enable_synthetic_submission:
            attempted = [
                p for p in visited_pages
                if p.synthetic_submission_attempted and p.synthetic_submission_status != "not_attempted"
            ]
            synth_summary = SyntheticSubmissionSummary(
                pages_attempted=len(attempted),
                successful_submissions=sum(1 for p in attempted if p.synthetic_submission_status == "submitted"),
                third_party_submissions=sum(1 for p in attempted if p.observed_submit_target_type == "third_party"),
                first_party_submissions=sum(1 for p in attempted if p.observed_submit_target_type == "first_party"),
                blocked_or_failed=sum(
                    1 for p in attempted
                    if p.synthetic_submission_status in ("blocked", "validation_failed")
                ),
            )

        # Step 9: Persist results
        completed_at = datetime.now(timezone.utc).isoformat()
        await update_scan_result(
            db_path=db_path,
            scan_id=scan_id,
            status=ScanStatus.complete,
            data_categories=data_categories,
            network_observations=observations,
            screenshot_path=screenshot_path,
            registration_relevance=registration_relevance,
            completed_at=completed_at,
            visited_pages=visited_pages,
            site_summary=site_summary,
            vendor_summary=vendor_summary,
            policy_analysis=policy_analysis,
            synthetic_submission_enabled=enable_synthetic_submission,
            synthetic_submission_summary=synth_summary,
            operator_integration_evidence=operator_evidence,
            processor_map=processor_map,
            fz152_assessment=fz152_assessment,
            operator_metadata=op_metadata,
        )

        # Step 10: Export reports
        try:
            scan_result = await get_scan(db_path=db_path, scan_id=scan_id)
            if scan_result:
                raw_json_export_path = export_json(scan_result)
                markdown_export_path = export_markdown(scan_result)
                await update_scan_result(
                    db_path=db_path,
                    scan_id=scan_id,
                    status=ScanStatus.complete,
                    raw_json_export_path=raw_json_export_path,
                    markdown_export_path=markdown_export_path,
                )
        except Exception as report_exc:
            logger.warning("scanner_service: report export failed: %s", report_exc)

        logger.info("scanner_service: scan %s completed successfully", scan_id)

    except Exception as exc:
        # Step 10: Mark as failed
        logger.error("scanner_service: scan %s failed: %s", scan_id, exc)
        await update_scan_result(
            db_path=db_path,
            scan_id=scan_id,
            status=ScanStatus.failed,
            error=str(exc),
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
