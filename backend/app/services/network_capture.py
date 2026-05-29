"""
Network request capture service for the PD Scanner.
Attaches a request listener to a Playwright page BEFORE navigation.
Collects host, resource type, third-party flag, and HTTP method.
Never stores response bodies or query parameters.
"""

import logging
from urllib.parse import urlparse

from backend.app.models.schemas import NetworkObservation

logger = logging.getLogger(__name__)


def _extract_host(url: str) -> str:
    """Return hostname from a URL string, or the raw URL on parse failure."""
    try:
        return urlparse(url).hostname or url
    except Exception:
        return url


def _is_third_party(request_host: str, base_host: str) -> bool:
    """
    Return True if request_host is considered third-party relative to base_host.
    Compares the registered domain (last two labels) to handle subdomains gracefully.
    """
    def _registered_domain(host: str) -> str:
        parts = host.lower().split(".")
        return ".".join(parts[-2:]) if len(parts) >= 2 else host.lower()

    return _registered_domain(request_host) != _registered_domain(base_host)


def setup_capture(page, base_url: str) -> list:
    """
    Register a request listener on *page* and return the collector list.
    Must be called BEFORE page.goto().

    The collector is a plain list; each element is a raw observation dict.
    Pass it to get_observations() after navigation completes.
    """
    collector: list[dict] = []
    base_host = _extract_host(base_url)

    def _on_request(request) -> None:
        try:
            req_url = request.url
            # Strip query string / fragment — never store them
            parsed = urlparse(req_url)
            host = parsed.hostname or req_url
            resource_type = request.resource_type or "other"
            method = request.method or "GET"
            third_party = _is_third_party(host, base_host)

            collector.append(
                {
                    "host": host,
                    "resource_type": resource_type,
                    "is_third_party": third_party,
                    "method": method,
                }
            )
        except Exception as exc:
            logger.debug("network_capture: error processing request: %s", exc)

    page.on("request", _on_request)
    logger.debug("network_capture: listener attached for base_url=%s", base_url)
    return collector


def get_observations(
    collector: list[dict], max_observations: int = 50
) -> list[NetworkObservation]:
    """
    Convert the raw collector list into a capped list of NetworkObservation objects.
    Deduplicates by (host, resource_type, method) to reduce noise, then caps.
    """
    seen: set[tuple] = set()
    observations: list[NetworkObservation] = []

    for entry in collector:
        key = (entry["host"], entry["resource_type"], entry["method"])
        if key in seen:
            continue
        seen.add(key)
        observations.append(NetworkObservation(**entry))
        if len(observations) >= max_observations:
            break

    logger.info("network_capture: %d unique observations collected", len(observations))
    return observations
