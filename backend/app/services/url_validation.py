"""
URL validation for the PD Scanner.
Blocks localhost, loopback (full /8), RFC1918 private ranges, and link-local.
"""

from urllib.parse import urlparse

# Maximum URL length accepted (characters)
MAX_URL_LENGTH = 2048

BLOCKED_HOSTS: set[str] = {
    "localhost",
    "0.0.0.0",
    "::1",
}

BLOCKED_PREFIXES: tuple[str, ...] = (
    # Loopback — full 127.0.0.0/8 range
    "127.",
    # Link-local — includes cloud metadata endpoints (169.254.169.254, etc.)
    "169.254.",
    # RFC1918 private ranges
    "10.",
    "172.16.",
    "172.17.",
    "172.18.",
    "172.19.",
    "172.20.",
    "172.21.",
    "172.22.",
    "172.23.",
    "172.24.",
    "172.25.",
    "172.26.",
    "172.27.",
    "172.28.",
    "172.29.",
    "172.30.",
    "172.31.",
    "192.168.",
)

ALLOWED_SCHEMES: set[str] = {"http", "https"}


class URLValidationError(ValueError):
    pass


def validate_url(url: str, *, allow_local: bool = False) -> str:
    """
    Validate that a URL is safe to scan:
    - Must not exceed MAX_URL_LENGTH characters.
    - Scheme must be http or https.
    - Host must not be localhost, loopback (127.0.0.0/8), link-local (169.254.0.0/16),
      or an RFC1918 private range.

    allow_local: when True, localhost and 127.x addresses are permitted.
      ONLY set this from PD_ALLOW_LOCAL_TEST_TARGETS=true for controlled local
      fixture testing. NEVER enable in production.
      All other checks (scheme, length, link-local 169.254.x, RFC1918) remain
      active regardless of this flag.

    Raises URLValidationError with a descriptive message on failure.
    Returns the url string unchanged if valid.
    """
    if len(url) > MAX_URL_LENGTH:
        raise URLValidationError(
            f"URL exceeds maximum allowed length of {MAX_URL_LENGTH} characters."
        )

    try:
        parsed = urlparse(url)
    except Exception as exc:
        raise URLValidationError(f"Could not parse URL: {exc}") from exc

    scheme = parsed.scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        raise URLValidationError(
            f"URL scheme '{scheme}' is not allowed. Only http and https are accepted."
        )

    host = parsed.hostname or ""
    if not host:
        raise URLValidationError("URL has no host component.")

    host_lower = host.lower()

    if allow_local and (host_lower in {"localhost", "127.0.0.1", "::1"}
                        or host_lower.startswith("127.")):
        # Localhost / loopback exempted for local fixture testing only.
        # Link-local and RFC1918 ranges remain blocked even with allow_local.
        if host_lower.startswith("169.254.") or any(
            host_lower.startswith(p) for p in BLOCKED_PREFIXES
            if not p.startswith("127.")
        ):
            raise URLValidationError(
                f"Scanning '{host}' is not allowed (private/internal IP range)."
            )
        return url

    if host_lower in BLOCKED_HOSTS:
        raise URLValidationError(
            f"Scanning '{host}' is not allowed (localhost/loopback address)."
        )

    if host_lower.startswith(BLOCKED_PREFIXES):
        raise URLValidationError(
            f"Scanning '{host}' is not allowed (private/internal IP range)."
        )

    return url
