"""
Page-type classifier for the PD Scanner.

Classifies a visited page's primary form purpose into one of:
    login, registration, likely_registration, newsletter,
    contact, checkout, callback, ambiguous

All classification is heuristic and rule-based — no AI is used.
Signals are additive: URL path tokens carry the highest weight,
detected field types (password/email) carry medium weight, and
keyword matches in title/headings/form text carry standard weight.
"""

import re
from urllib.parse import urlparse

from backend.app.utils.patterns import (
    CALLBACK_KEYWORDS,
    CHECKOUT_KEYWORDS,
    CONTACT_KEYWORDS,
    LOGIN_KEYWORDS,
    NEWSLETTER_KEYWORDS,
    REGISTRATION_KEYWORDS,
)

# ---------------------------------------------------------------------------
# URL path token sets — strong signal (weight 3)
# ---------------------------------------------------------------------------

_URL_LOGIN_TOKENS: frozenset[str] = frozenset([
    "login", "log-in", "log_in", "signin", "sign-in", "sign_in",
    "auth", "authenticate", "logon",
])

_URL_REGISTRATION_TOKENS: frozenset[str] = frozenset([
    "register", "registration", "signup", "sign-up", "sign_up",
    "create-account", "create_account", "join", "enroll", "onboard",
    "get-started", "new-user", "new_user",
])

_URL_CHECKOUT_TOKENS: frozenset[str] = frozenset([
    "checkout", "cart", "order", "payment", "billing", "buy", "purchase",
])

_URL_CALLBACK_TOKENS: frozenset[str] = frozenset([
    "callback", "schedule", "booking", "demo", "consultation",
    "request-call", "requestcall",
])

_URL_CONTACT_TOKENS: frozenset[str] = frozenset([
    "contact", "feedback", "support", "enquiry", "inquiry",
])

_URL_NEWSLETTER_TOKENS: frozenset[str] = frozenset([
    "subscribe", "newsletter", "mailing-list",
])

# Regex that matches pagination segments like /page/2, /p/3, /page-2
_PAGINATION_RE: re.Pattern = re.compile(r"/p(?:age)?[/-]\d+")


def _url_path_boosts(url: str) -> dict[str, int]:
    """
    Extract page-type boosts from URL path segments.
    Returns {page_type: score_boost}. A path match carries weight 3.
    """
    boosts: dict[str, int] = {}
    try:
        path = urlparse(url).path.lower()
        tokens = set(re.split(r"[/_\-.]", path))
        tokens.discard("")
    except Exception:
        return boosts

    if tokens & _URL_LOGIN_TOKENS:
        boosts["login"] = 3
    if tokens & _URL_REGISTRATION_TOKENS:
        boosts["registration"] = 3
    if tokens & _URL_CHECKOUT_TOKENS:
        boosts["checkout"] = 3
    if tokens & _URL_CALLBACK_TOKENS:
        boosts["callback"] = 3
    if tokens & _URL_CONTACT_TOKENS:
        boosts["contact"] = 2
    if tokens & _URL_NEWSLETTER_TOKENS:
        boosts["newsletter"] = 2
    return boosts


def classify_page(
    url: str,
    title: str,
    headings: list[str],
    form_texts: list[str],
    has_password_field: bool = False,
    has_email_field: bool = False,
) -> str:
    """
    Classify the purpose of a page's primary form.

    Parameters
    ----------
    url : str
        Full URL of the page (used for path-token analysis).
    title : str
        Browser page title.
    headings : list[str]
        Text content of h1/h2 elements.
    form_texts : list[str]
        Text content of form labels, buttons, and legends.
    has_password_field : bool
        True if the page contains a visible password input.
    has_email_field : bool
        True if the page contains a visible email input.

    Returns
    -------
    str
        One of: login, registration, likely_registration, newsletter,
        contact, checkout, callback, ambiguous.
    """
    combined = " ".join([title] + headings + form_texts).lower()

    # Text-based keyword scores (weight 1 per hit)
    scores: dict[str, int] = {
        "registration": sum(1 for kw in REGISTRATION_KEYWORDS if kw in combined),
        "login": sum(1 for kw in LOGIN_KEYWORDS if kw in combined),
        "newsletter": sum(1 for kw in NEWSLETTER_KEYWORDS if kw in combined),
        "contact": sum(1 for kw in CONTACT_KEYWORDS if kw in combined),
        "checkout": sum(1 for kw in CHECKOUT_KEYWORDS if kw in combined),
        "callback": sum(1 for kw in CALLBACK_KEYWORDS if kw in combined),
    }

    # URL path boosts (weight 3 — strongest signal)
    for page_type, boost in _url_path_boosts(url).items():
        scores[page_type] = scores.get(page_type, 0) + boost

    # Field presence boosts (weight 2)
    # password + email together → login
    # password alone → login (could be change-password, but most commonly login)
    if has_password_field:
        scores["login"] = scores.get("login", 0) + 2

    max_score = max(scores.values())
    if max_score == 0:
        return "ambiguous"

    top = [k for k, v in scores.items() if v == max_score]

    if len(top) == 1:
        winner = top[0]
        if winner == "registration":
            # Require meaningful text evidence for full "registration" label;
            # URL-only match gets the softer "likely_registration"
            text_hits = sum(1 for kw in REGISTRATION_KEYWORDS if kw in combined)
            return "registration" if text_hits >= 2 else "likely_registration"
        return winner

    # Tie-break: more specific / higher-value types win
    for preferred in ("checkout", "login", "registration", "callback", "newsletter", "contact"):
        if preferred in top:
            return preferred

    return "ambiguous"
