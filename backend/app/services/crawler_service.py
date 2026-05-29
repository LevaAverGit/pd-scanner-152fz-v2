"""
Bounded same-site crawler for the PD Scanner.

Performs a breadth-first crawl starting from a seed URL, staying within the
same scheme + host, respecting hard limits on pages and depth.

For each visited page the crawler:
- Navigates headlessly (no form interaction, no button clicks)
- Extracts form fields using the existing dom_parser
- Classifies personal data categories using the existing classifier
- Classifies page/form type using the page_classifier_service
- Detects consent/privacy signals using consent_detection_service
- Infers form submission targets passively via submit_analysis_service
- Collects network request metadata
- Returns a structured per-page summary

Safety constraints (same as single-page scanner):
- No form submission
- No credential entry
- No CAPTCHA bypass
- No external domain navigation
- No stealth automation
- Bounded timeouts throughout
"""

import asyncio
import logging
from collections import deque
from urllib.parse import urlparse

from playwright.async_api import BrowserContext, Page, TimeoutError as PlaywrightTimeout

from backend.app.models.schemas import DataCategoryItem, NetworkObservation, VisitedPageItem
from backend.app.services.classifier_service import classify_fields
from backend.app.services.consent_detection_service import detect_consent_signals
from backend.app.services.dom_parser import extract_fields
from backend.app.services.interactive_discovery_service import run_interactive_discovery
from backend.app.services.link_discovery_service import discover_links
from backend.app.services.network_capture import setup_capture, get_observations
from backend.app.services.page_classifier_service import classify_page
from backend.app.services.submit_analysis_service import analyse_submit_targets
from backend.app.utils.patterns import CONSENT_PRIVACY_KEYWORDS

logger = logging.getLogger(__name__)

# Hard limits — not configurable by the user to prevent abuse
MAX_PAGES: int = 20
MAX_DEPTH: int = 2

# Per-page navigation timeout (ms)
PAGE_TIMEOUT_MS: int = 20_000
# Per-page stabilisation wait (ms)
STABILISE_TIMEOUT_MS: int = 8_000


async def _visit_page(
    context: BrowserContext,
    url: str,
    all_observations: list[NetworkObservation],
    base_url: str,
    discovered_policy_urls: list[str] | None = None,
    enable_synthetic_submission: bool = False,
    submissions_counter: list[int] | None = None,
) -> VisitedPageItem:
    """
    Open a new browser page, navigate to url, extract fields + metadata,
    return a VisitedPageItem. Always closes the page on completion.
    """
    notes: list[str] = []
    page: Page | None = None

    try:
        page = await context.new_page()
        collector = setup_capture(page, base_url)

        try:
            await page.goto(url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
        except PlaywrightTimeout:
            notes.append("Navigation timed out; partial content analysed.")
            logger.debug("crawler: timeout navigating to %s", url)

        # Wait for stabilisation
        try:
            await page.wait_for_load_state("networkidle", timeout=STABILISE_TIMEOUT_MS)
        except PlaywrightTimeout:
            pass

        # Page title
        try:
            title = (await page.title()) or ""
        except Exception:
            title = ""

        # Form count
        try:
            forms_found: int = await page.locator("form").count()
        except Exception:
            forms_found = 0

        # Headings and form context text for classification
        try:
            headings = await page.locator("h1, h2").all_text_contents()
        except Exception:
            headings = []
        try:
            form_texts = await page.locator(
                "form label, form button, form legend"
            ).all_text_contents()
        except Exception:
            form_texts = []

        # Field extraction + classification
        fields = await extract_fields(page)
        categories = classify_fields(fields)

        # Field presence signals for page classification
        has_password = any(f.get("field_type") == "password" for f in fields)
        has_email = any(
            f.get("field_type") == "email"
            or "email" in (f.get("name") or "").lower()
            or "email" in (f.get("label") or "").lower()
            for f in fields
        )

        # Page/form type classification
        relevance = classify_page(
            url=url,
            title=title,
            headings=headings,
            form_texts=form_texts,
            has_password_field=has_password,
            has_email_field=has_email,
        )

        # Consent / privacy signal detection
        consent = await detect_consent_signals(page)

        # Collect policy/privacy page URL if found
        if consent["has_privacy_link"] and discovered_policy_urls is not None:
            try:
                base_host = urlparse(base_url).netloc.lower()
                policy_url = await page.evaluate(
                    """
                    (function(privacyKws) {
                        for (const a of document.querySelectorAll('a')) {
                            const t = (a.innerText || a.textContent || '').toLowerCase()
                                      + ' ' + (a.href || '').toLowerCase();
                            if (privacyKws.some(k => t.includes(k))) {
                                return a.href || null;
                            }
                        }
                        return null;
                    })
                    """,
                    list(CONSENT_PRIVACY_KEYWORDS),
                )
                if policy_url and urlparse(policy_url).netloc.lower() == base_host:
                    if policy_url not in discovered_policy_urls:
                        discovered_policy_urls.append(policy_url)
            except Exception:
                pass

        # Interactive discovery — bounded CTA reveal
        discovery: dict = {}
        try:
            discovery = await run_interactive_discovery(page, url)
        except Exception:
            pass

        # Submit-target analysis — passive DOM inspection only
        submit: dict = {}
        if forms_found > 0:
            submit = await analyse_submit_targets(page, url)

        # Accumulate network observations (shared list, capped globally by caller)
        page_obs = get_observations(collector, max_observations=50)
        all_observations.extend(page_obs)

        # Synthetic submission (only if enabled and form exists)
        synth: dict = {}
        if enable_synthetic_submission and forms_found > 0 and submissions_counter is not None:
            from backend.app.services.synthetic_submission_service import run_synthetic_submission
            try:
                synth = await run_synthetic_submission(page, url, base_url, submissions_counter[0])
                if synth.get("synthetic_submission_attempted"):
                    submissions_counter[0] += 1
            except Exception as exc:
                logger.warning("crawler: synthetic submission error on %s: %s", url, exc)

        page_item = VisitedPageItem(
            url=url,
            page_title=title or None,
            registration_relevance=relevance,
            detected_categories=categories,
            fields_count=len(fields),
            forms_found=forms_found,
            notes=notes,
            has_privacy_link=consent["has_privacy_link"],
            has_terms_link=consent["has_terms_link"],
            has_consent_checkbox=consent["has_consent_checkbox"],
            has_marketing_consent=consent["has_marketing_consent"],
            consent_signals=consent["consent_signals"],
            has_bundled_consent_text=consent.get("has_bundled_consent_text", False),
            hidden_forms_revealed=discovery.get("hidden_forms_revealed", 0),
            interactions_performed=discovery.get("interactions_performed", []),
            dynamic_consent_signals=discovery.get("dynamic_consent_signals", []),
            modal_forms_found=discovery.get("modal_forms_found", 0),
            has_first_party_submission_hint=submit.get("has_first_party_submission_hint", False),
            has_third_party_submission_hint=submit.get("has_third_party_submission_hint", False),
            probable_form_platform=submit.get("probable_form_platform"),
            probable_crm_or_capture_tool=submit.get("probable_crm_or_capture_tool"),
            probable_submission_target=submit.get("probable_submission_target"),
            submission_method=submit.get("submission_method"),
            submission_target_type=submit.get("submission_target_type", "unknown"),
            submission_evidence=submit.get("submission_evidence", []),
            synthetic_submission_attempted=synth.get("synthetic_submission_attempted", False),
            synthetic_submission_status=synth.get("synthetic_submission_status", "not_attempted"),
            observed_submit_url=synth.get("observed_submit_url"),
            observed_submit_method=synth.get("observed_submit_method"),
            observed_submit_target_type=synth.get("observed_submit_target_type", "unknown"),
            observed_follow_on_hosts=synth.get("observed_follow_on_hosts", []),
            observed_submission_evidence=synth.get("observed_submission_evidence", []),
            observed_capture_tool=synth.get("observed_capture_tool"),
            observed_webhook_or_api_hint=synth.get("observed_webhook_or_api_hint"),
            # Populated below
            downstream_processor_type=None,
            downstream_processor_name=None,
            downstream_routing_confidence="low",
            downstream_routing_signals=[],
        )
        # Infer downstream routing
        from backend.app.services.integration_audit_service import infer_downstream_routing
        downstream = infer_downstream_routing(page_item)
        return page_item.model_copy(update=downstream)

    except Exception as exc:
        logger.warning("crawler: failed to visit %s: %s", url, exc)
        return VisitedPageItem(
            url=url,
            page_title=None,
            registration_relevance=None,
            detected_categories=[],
            fields_count=0,
            forms_found=0,
            notes=[f"Page could not be loaded: {exc}"],
        )
    finally:
        if page is not None:
            try:
                await page.close()
            except Exception:
                pass


async def crawl(
    context: BrowserContext,
    seed_url: str,
    enable_synthetic_submission: bool = False,
) -> tuple[list[VisitedPageItem], list[NetworkObservation], dict[str, str], list[str]]:
    """
    Run a bounded BFS crawl starting from seed_url within the same host.

    Returns:
        (visited_pages, aggregated_network_observations, host_first_seen, discovered_policy_urls)

    host_first_seen maps third-party hostname → page URL where it was first
    observed, used by vendor_classification_service to populate first_seen_on.

    Constraints:
    - max MAX_PAGES pages visited total
    - max MAX_DEPTH link hops from the seed
    - same scheme + host only (enforced by link_discovery_service)
    - no form interaction
    """
    base_host = urlparse(seed_url).netloc.lower()
    visited_urls: set[str] = set()
    visited_pages: list[VisitedPageItem] = []
    all_observations: list[NetworkObservation] = []
    discovered_policy_urls: list[str] = []
    submissions_counter: list[int] = [0]  # mutable counter shared across page visits
    # Maps third-party host → URL of the page where it was first seen
    host_first_seen: dict[str, str] = {}

    # BFS queue: (url, depth)
    queue: deque[tuple[str, int]] = deque()
    queue.append((seed_url, 0))
    # Track which page URL produced which observations batch
    page_url_for_obs: list[tuple[str, list[NetworkObservation]]] = []

    while queue and len(visited_pages) < MAX_PAGES:
        url, depth = queue.popleft()

        # Normalise before dedup check
        if url in visited_urls:
            continue
        visited_urls.add(url)

        logger.info("crawler: visiting [depth=%d] %s", depth, url)
        obs_before = len(all_observations)
        page_item = await _visit_page(
            context, url, all_observations, seed_url, discovered_policy_urls,
            enable_synthetic_submission, submissions_counter,
        )
        visited_pages.append(page_item)

        # Record first-seen page for any new third-party hosts introduced by this page
        new_obs = all_observations[obs_before:]
        for obs in new_obs:
            if obs.is_third_party and obs.host not in host_first_seen:
                host_first_seen[obs.host] = url

        # Only discover further links if within depth limit
        if depth < MAX_DEPTH and len(visited_pages) < MAX_PAGES:
            try:
                # Re-open page briefly for link extraction
                link_page = await context.new_page()
                try:
                    await link_page.goto(
                        url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded"
                    )
                    new_links = await discover_links(link_page, url)
                except Exception as exc:
                    logger.debug("crawler: link extraction failed for %s: %s", url, exc)
                    new_links = []
                finally:
                    await link_page.close()

                for link in new_links:
                    if link not in visited_urls:
                        # Verify host hasn't drifted (redundant but defensive)
                        if urlparse(link).netloc.lower() == base_host:
                            queue.append((link, depth + 1))
            except Exception as exc:
                logger.debug("crawler: link discovery error at %s: %s", url, exc)

    # Cap total network observations to avoid unbounded accumulation
    seen_obs: set[tuple] = set()
    deduped: list[NetworkObservation] = []
    for obs in all_observations:
        key = (obs.host, obs.resource_type, obs.method)
        if key not in seen_obs and len(deduped) < 100:
            seen_obs.add(key)
            deduped.append(obs)

    logger.info(
        "crawler: crawl complete — %d pages visited, %d network observations",
        len(visited_pages), len(deduped),
    )
    return visited_pages, deduped, host_first_seen, discovered_policy_urls
