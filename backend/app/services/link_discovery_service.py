"""
Link discovery service for the PD Scanner same-site crawler.

Extracts and filters outgoing links from a Playwright page.
Only returns same-scheme + same-host URLs that are safe to follow.
Never returns links to external domains, dangerous paths, or binary files.
"""

import logging
import re
from urllib.parse import urljoin, urlparse, urlunparse

from backend.app.utils.patterns import (
    CRAWL_LOW_VALUE_PATTERNS,
    CRAWL_PRIORITY_KEYWORDS,
    CRAWL_SKIP_EXTENSIONS,
    CRAWL_SKIP_PATTERNS,
)

# Matches pagination segments: /page/2, /p/3, /page-2, /pg/4
_PAGINATION_RE: re.Pattern = re.compile(r"/p(?:age|g)?[/-]\d+")

logger = logging.getLogger(__name__)


def _normalize_url(url: str) -> str:
    """
    Normalize a URL for deduplication:
    - Lowercase scheme and host
    - Remove fragment (#...)
    - Preserve path, query
    - Remove trailing slash from path only if path != '/'
    """
    try:
        p = urlparse(url)
        path = p.path
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        normalized = urlunparse((
            p.scheme.lower(),
            p.netloc.lower(),
            path,
            p.params,
            p.query,
            "",          # strip fragment
        ))
        return normalized
    except Exception:
        return url


def _is_safe_to_follow(href: str, base_scheme: str, base_host: str) -> bool:
    """
    Return True only if the resolved URL should be enqueued:
    - Scheme is http or https and matches base scheme family
    - Host matches base host exactly
    - Path does not match any CRAWL_SKIP_PATTERNS
    - File extension is not in CRAWL_SKIP_EXTENSIONS
    """
    try:
        p = urlparse(href)
    except Exception:
        return False

    if p.scheme not in ("http", "https"):
        return False

    if p.netloc.lower() != base_host.lower():
        return False

    path_lower = p.path.lower()

    # Skip dangerous path patterns
    for skip in CRAWL_SKIP_PATTERNS:
        if skip in path_lower:
            return False

    # Skip binary / document extensions
    for ext in CRAWL_SKIP_EXTENSIONS:
        if path_lower.endswith(ext):
            return False

    return True


def _priority_score(url: str) -> int:
    """
    Return a priority score for a URL (higher = scan sooner).

    Scoring:
    +1 per CRAWL_PRIORITY_KEYWORD match in path  (form-bearing page signals)
    -5 for any CRAWL_LOW_VALUE_PATTERN match      (taxonomy/archive pages)
    -3 for pagination patterns like /page/2       (paginated content)

    Negative-score links sort to the end of the discovered-links list
    and are only visited when higher-value pages have been exhausted.
    """
    path_lower = urlparse(url).path.lower()
    score = sum(1 for kw in CRAWL_PRIORITY_KEYWORDS if kw in path_lower)
    # Penalise low-value content pages
    for pat in CRAWL_LOW_VALUE_PATTERNS:
        if pat in path_lower:
            score -= 5
            break
    # Penalise pagination
    if _PAGINATION_RE.search(path_lower):
        score -= 3
    return score


async def discover_links(page, page_url: str) -> list[str]:
    """
    Extract all outgoing links from a Playwright page, resolve them against
    page_url, filter to same-host safe links, deduplicate, and return sorted
    by priority score descending.

    Returns a list of normalized absolute URL strings.
    """
    base_host = urlparse(page_url).netloc.lower()
    base_scheme = urlparse(page_url).scheme.lower()

    # Extract raw href values from all <a> tags
    try:
        raw_hrefs: list[str] = await page.evaluate("""
            () => {
                const links = document.querySelectorAll('a[href]');
                return Array.from(links)
                    .map(a => a.getAttribute('href') || '')
                    .filter(h => h.length > 0 && !h.startsWith('#'));
            }
        """)
    except Exception as exc:
        logger.debug("link_discovery: could not extract hrefs: %s", exc)
        return []

    seen: set[str] = set()
    candidates: list[tuple[int, str]] = []

    for href in raw_hrefs:
        href = href.strip()
        if not href:
            continue
        # Skip non-navigable schemes early
        if href.lower().startswith(("mailto:", "tel:", "javascript:", "file:", "data:")):
            continue
        try:
            resolved = urljoin(page_url, href)
            normalized = _normalize_url(resolved)
        except Exception:
            continue

        if normalized in seen:
            continue

        if not _is_safe_to_follow(normalized, base_scheme, base_host):
            continue

        seen.add(normalized)
        candidates.append((_priority_score(normalized), normalized))

    # Sort: higher priority first, then alphabetically for stability
    candidates.sort(key=lambda t: (-t[0], t[1]))
    result = [url for _, url in candidates]
    logger.debug("link_discovery: found %d same-host links on %s", len(result), page_url)
    return result
