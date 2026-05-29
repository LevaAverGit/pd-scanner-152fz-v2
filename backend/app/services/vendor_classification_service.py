"""
Vendor classification service for the PD Scanner.

Classifies observed third-party hosts into vendor categories based on
hostname pattern matching against a curated knowledge base.

All classification is heuristic — no external lookups, no DNS queries.
Results should be treated as informed estimates, not definitive facts.

Vendor classes:
  analytics           — web analytics, session tracking, heatmaps
  advertising         — ad networks, retargeting, bid management
  tag_manager         — tag management systems that may load further tracking
  chat_widget         — live chat and customer messaging tools
  call_tracking       — phone call tracking and analytics
  form_platform       — external form builders and submission endpoints
  crm_or_lead_capture — CRM integrations and lead routing tools
  consent_management  — cookie consent and preference management
  cdn_or_static       — content delivery networks and static hosting
  fonts               — web font services
  maps                — mapping and geolocation services
  video_or_media      — video hosting and media platforms
  payment             — payment processors
  social              — social media widgets and share buttons
  unknown             — unrecognised third-party host
"""

import logging
from backend.app.models.schemas import NetworkObservation, VendorSummaryItem

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Vendor rule table
# Each entry: (hostname_suffix_pattern, vendor_class, vendor_name, privacy_note)
# Matching: host == pattern OR host.endswith("." + pattern)
# Ordered longest-pattern-first within each class for specificity.
# ---------------------------------------------------------------------------

_VENDOR_RULES: list[tuple[str, str, str, str]] = [
    # ----- Analytics -------------------------------------------------------
    ("www.google-analytics.com",   "analytics",  "Google Analytics",        ""),
    ("google-analytics.com",       "analytics",  "Google Analytics",        ""),
    ("ssl.google-analytics.com",   "analytics",  "Google Analytics",        ""),
    ("mc.yandex.ru",               "analytics",  "Yandex Metrica",          ""),
    ("mc.yandex.com",              "analytics",  "Yandex Metrica",          ""),
    ("metrika.yandex.ru",          "analytics",  "Yandex Metrica",          ""),
    ("cdn.amplitude.com",          "analytics",  "Amplitude",               ""),
    ("amplitude.com",              "analytics",  "Amplitude",               ""),
    ("api.mixpanel.com",           "analytics",  "Mixpanel",                ""),
    ("mixpanel.com",               "analytics",  "Mixpanel",                ""),
    ("script.hotjar.com",          "analytics",  "Hotjar",                  "records mouse movements and clicks"),
    ("hotjar.com",                 "analytics",  "Hotjar",                  "records mouse movements and clicks"),
    ("clarity.ms",                 "analytics",  "Microsoft Clarity",       "session recording and heatmaps"),
    ("cdn.segment.com",            "analytics",  "Segment",                 "customer data platform"),
    ("api.segment.io",             "analytics",  "Segment",                 "customer data platform"),
    ("segment.io",                 "analytics",  "Segment",                 ""),
    ("fullstory.com",              "analytics",  "FullStory",               "session recording"),
    ("rs6.net",                    "analytics",  "Constant Contact",        ""),
    ("heap.io",                    "analytics",  "Heap Analytics",          ""),
    ("mouseflow.com",              "analytics",  "Mouseflow",               "session recording"),
    ("statcounter.com",            "analytics",  "StatCounter",             ""),
    ("roistat.com",                "analytics",  "Roistat",                 "marketing analytics with call tracking"),
    ("app.roistat.com",            "analytics",  "Roistat",                 ""),

    # ----- Tag manager -----------------------------------------------------
    ("googletagmanager.com",       "tag_manager", "Google Tag Manager",     "may load additional tracking"),
    ("tiqcdn.com",                 "tag_manager", "Tealium",                "may load additional tracking"),
    ("tags.tiqcdn.com",            "tag_manager", "Tealium",                ""),
    ("collect.igodigital.com",     "tag_manager", "Salesforce Tag",         ""),

    # ----- Advertising / retargeting ---------------------------------------
    ("googlesyndication.com",      "advertising", "Google Ads",             ""),
    ("doubleclick.net",            "advertising", "Google DoubleClick",     ""),
    ("adservice.google.com",       "advertising", "Google Ad Services",     ""),
    ("adservice.google.ru",        "advertising", "Google Ad Services",     ""),
    ("connect.facebook.net",       "advertising", "Facebook Pixel / SDK",   "tracks conversions and custom audiences"),
    ("facebook.net",               "advertising", "Facebook",               ""),
    ("ads.twitter.com",            "advertising", "Twitter Ads",            ""),
    ("analytics.twitter.com",      "advertising", "Twitter Analytics",      ""),
    ("snap.licdn.com",             "advertising", "LinkedIn Insight Tag",   ""),
    ("platform.linkedin.com",      "advertising", "LinkedIn",               ""),
    ("criteo.com",                 "advertising", "Criteo",                 "retargeting"),
    ("adnxs.com",                  "advertising", "AppNexus / Xandr",       ""),
    ("taboola.com",                "advertising", "Taboola",                "content recommendations"),
    ("outbrain.com",               "advertising", "Outbrain",               "content recommendations"),
    ("adroll.com",                 "advertising", "AdRoll",                 "retargeting"),
    ("adfox.ru",                   "advertising", "Adfox (Yandex)",         ""),
    ("vk.com",                     "advertising", "VKontakte",              "may be ads or social widget"),
    ("mindbox.ru",                 "advertising", "Mindbox",                "customer data and marketing automation"),
    ("rlcdn.com",                  "advertising", "LiveRamp",               "identity resolution"),
    ("rubiconproject.com",         "advertising", "Rubicon Project",        ""),

    # ----- Chat widget -----------------------------------------------------
    ("jivosite.com",               "chat_widget", "JivoChat",               "may capture visitor messages"),
    ("jivo.ru",                    "chat_widget", "JivoChat",               ""),
    ("jivochat.com",               "chat_widget", "JivoChat",               ""),
    ("tawk.to",                    "chat_widget", "Tawk.to",                ""),
    ("widget.intercom.io",         "chat_widget", "Intercom",               "may capture visitor data"),
    ("intercom.io",                "chat_widget", "Intercom",               ""),
    ("intercomcdn.com",            "chat_widget", "Intercom CDN",           ""),
    ("zopim.com",                  "chat_widget", "Zendesk Chat",           ""),
    ("zendesk.com",                "chat_widget", "Zendesk",                ""),
    ("crisp.chat",                 "chat_widget", "Crisp",                  ""),
    ("livechatinc.com",            "chat_widget", "LiveChat",               ""),
    ("tidio.com",                  "chat_widget", "Tidio",                  ""),
    ("freshchat.com",              "chat_widget", "Freshchat",              ""),
    ("carrotquest.io",             "chat_widget", "Carrot Quest",           ""),
    ("verbox.ru",                  "chat_widget", "Verbox",                 ""),
    ("helpcrunch.com",             "chat_widget", "HelpCrunch",             ""),
    ("supportize.me",              "chat_widget", "Supportize",             ""),
    ("usedesk.ru",                 "chat_widget", "Usedesk",                ""),

    # ----- Call tracking ---------------------------------------------------
    ("calltouch.ru",               "call_tracking", "Calltouch",            "tracks phone calls and ad attribution"),
    ("static.calltouch.ru",        "call_tracking", "Calltouch",            ""),
    ("widget.calltouch.ru",        "call_tracking", "Calltouch",            ""),
    ("comagic.ru",                 "call_tracking", "CoMagic",              "call analytics"),
    ("callibri.ru",                "call_tracking", "Callibri",             ""),
    ("mango-office.ru",            "call_tracking", "Mango Telecom",        ""),
    ("uiscom.ru",                  "call_tracking", "UIS",                  ""),
    ("calltracking.ru",            "call_tracking", "CallTracking.ru",      ""),

    # ----- Form platform ---------------------------------------------------
    ("js.hsforms.net",             "form_platform", "HubSpot Forms",        "form data routes to HubSpot"),
    ("forms.hsforms.com",          "form_platform", "HubSpot Forms",        ""),
    ("embed.typeform.com",         "form_platform", "Typeform",             "form data routes to Typeform"),
    ("form.typeform.com",          "form_platform", "Typeform",             ""),
    ("form.jotform.com",           "form_platform", "JotForm",              "form data routes to JotForm"),
    ("submit.jotform.com",         "form_platform", "JotForm",              ""),
    ("wufoo.com",                  "form_platform", "Wufoo",                ""),
    ("formstack.com",              "form_platform", "Formstack",            ""),
    ("getresponse.com",            "form_platform", "GetResponse",          ""),
    ("list-manage.com",            "form_platform", "Mailchimp",            "form data routes to Mailchimp"),
    ("chimpstatic.com",            "form_platform", "Mailchimp",            ""),
    ("klaviyo.com",                "form_platform", "Klaviyo",              ""),
    ("omnisend.com",               "form_platform", "Omnisend",             ""),
    ("activehosted.com",           "form_platform", "ActiveCampaign",       ""),
    ("activecampaign.com",         "form_platform", "ActiveCampaign",       ""),
    ("tildacdn.com",               "form_platform", "Tilda",                "Tilda website builder"),
    ("tilda.ws",                   "form_platform", "Tilda",                ""),
    ("forms.google.com",           "form_platform", "Google Forms",         ""),

    # ----- CRM / lead capture ----------------------------------------------
    ("amocrm.ru",                  "crm_or_lead_capture", "amoCRM",         "lead data may route here"),
    ("kommo.com",                  "crm_or_lead_capture", "Kommo (amoCRM)", ""),
    ("www.amocrm.ru",              "crm_or_lead_capture", "amoCRM",         ""),
    ("bitrix24.ru",                "crm_or_lead_capture", "Bitrix24",       "CRM and lead management"),
    ("bitrix24.com",               "crm_or_lead_capture", "Bitrix24",       ""),
    ("salesforce.com",             "crm_or_lead_capture", "Salesforce",     ""),
    ("pardot.com",                 "crm_or_lead_capture", "Salesforce Pardot", "marketing automation"),
    ("hs-scripts.com",             "crm_or_lead_capture", "HubSpot",        "HubSpot tracking"),
    ("hubspot.com",                "crm_or_lead_capture", "HubSpot",        ""),
    ("retailcrm.ru",               "crm_or_lead_capture", "RetailCRM",      ""),
    ("megaplan.ru",                "crm_or_lead_capture", "Megaplan",       ""),
    ("planfix.ru",                 "crm_or_lead_capture", "Planfix",        ""),
    ("zoho.com",                   "crm_or_lead_capture", "Zoho CRM",       ""),
    ("pipedrive.com",              "crm_or_lead_capture", "Pipedrive",      ""),
    ("freshsales.io",              "crm_or_lead_capture", "Freshsales",     ""),
    ("marketo.net",                "crm_or_lead_capture", "Marketo",        ""),
    ("eloqua.com",                 "crm_or_lead_capture", "Oracle Eloqua",  ""),

    # ----- Consent management platform ------------------------------------
    ("cookiebot.com",              "consent_management", "Cookiebot",       ""),
    ("cookielaw.org",              "consent_management", "OneTrust",        ""),
    ("onetrust.com",               "consent_management", "OneTrust",        ""),
    ("cookieinformation.com",      "consent_management", "Cookie Information", ""),
    ("iubenda.com",                "consent_management", "iubenda",         ""),
    ("usercentrics.eu",            "consent_management", "Usercentrics",    ""),
    ("didomi.io",                  "consent_management", "Didomi",          ""),
    ("termly.io",                  "consent_management", "Termly",          ""),

    # ----- CDN / static hosting -------------------------------------------
    ("cdn.jsdelivr.net",           "cdn_or_static", "jsDelivr CDN",         ""),
    ("cdnjs.cloudflare.com",       "cdn_or_static", "cdnjs (Cloudflare)",   ""),
    ("unpkg.com",                  "cdn_or_static", "unpkg",                ""),
    ("ajax.googleapis.com",        "cdn_or_static", "Google APIs CDN",      ""),
    ("stackpath.bootstrapcdn.com", "cdn_or_static", "BootstrapCDN",        ""),
    ("maxcdn.bootstrapcdn.com",    "cdn_or_static", "BootstrapCDN",        ""),
    ("cloudflare.com",             "cdn_or_static", "Cloudflare",           ""),
    ("fastly.net",                 "cdn_or_static", "Fastly CDN",           ""),
    ("akamaihd.net",               "cdn_or_static", "Akamai CDN",           ""),
    ("cloudfront.net",             "cdn_or_static", "AWS CloudFront",       ""),
    ("amazonaws.com",              "cdn_or_static", "Amazon AWS",           ""),
    ("yastatic.net",               "cdn_or_static", "Yandex Static CDN",    "may also carry Yandex tags"),

    # ----- Fonts -----------------------------------------------------------
    ("fonts.googleapis.com",       "fonts", "Google Fonts",                 ""),
    ("fonts.gstatic.com",          "fonts", "Google Fonts CDN",             ""),
    ("use.typekit.net",            "fonts", "Adobe Fonts (Typekit)",         ""),
    ("kit.fontawesome.com",        "fonts", "Font Awesome",                 ""),

    # ----- Maps ------------------------------------------------------------
    ("maps.googleapis.com",        "maps", "Google Maps",                   ""),
    ("maps.gstatic.com",           "maps", "Google Maps Static",            ""),
    ("api.mapbox.com",             "maps", "Mapbox",                        ""),
    ("tile.openstreetmap.org",     "maps", "OpenStreetMap",                 ""),
    ("api-maps.yandex.ru",         "maps", "Yandex Maps",                   ""),

    # ----- Video / media ---------------------------------------------------
    ("www.youtube.com",            "video_or_media", "YouTube",             ""),
    ("youtube.com",                "video_or_media", "YouTube",             ""),
    ("ytimg.com",                  "video_or_media", "YouTube",             ""),
    ("vimeo.com",                  "video_or_media", "Vimeo",               ""),
    ("player.vimeo.com",           "video_or_media", "Vimeo",               ""),
    ("wistia.com",                 "video_or_media", "Wistia",              ""),
    ("fast.wistia.com",            "video_or_media", "Wistia",              ""),
    ("brightcove.com",             "video_or_media", "Brightcove",          ""),
    ("jwplatform.com",             "video_or_media", "JW Player",           ""),
    ("rutube.ru",                  "video_or_media", "RuTube",              ""),

    # ----- Payment ---------------------------------------------------------
    ("js.stripe.com",              "payment", "Stripe",                     ""),
    ("stripe.com",                 "payment", "Stripe",                     ""),
    ("checkout.stripe.com",        "payment", "Stripe Checkout",            ""),
    ("paypal.com",                 "payment", "PayPal",                     ""),
    ("paypalobjects.com",          "payment", "PayPal",                     ""),
    ("robokassa.ru",               "payment", "Robokassa",                  ""),
    ("securepayments.sberbank.ru", "payment", "Sberbank",                   ""),
    ("yoomoney.ru",                "payment", "YooMoney",                   ""),
    ("cloudpayments.ru",           "payment", "CloudPayments",              ""),
    ("acquiring.tinkoff.ru",       "payment", "Tinkoff",                    ""),

    # ----- Social ----------------------------------------------------------
    ("platform.twitter.com",       "social", "Twitter/X Widget",            ""),
    ("s7.addthis.com",             "social", "AddThis",                     ""),
    ("sharethis.com",              "social", "ShareThis",                   ""),
    ("static.xx.fbcdn.net",        "social", "Facebook CDN",                ""),
]

# Build reverse-sorted lookup list (longer patterns first for specificity)
_SORTED_RULES = sorted(_VENDOR_RULES, key=lambda r: -len(r[0]))


def _match_host(host: str) -> tuple[str, str, str] | None:
    """
    Match a hostname against the vendor rule table.
    Returns (vendor_class, vendor_name, privacy_note) or None if no match.
    Matching is case-insensitive hostname-suffix comparison.
    """
    h = host.lower().strip()
    for pattern, vclass, vname, note in _SORTED_RULES:
        p = pattern.lower()
        if h == p or h.endswith("." + p):
            return vclass, vname, note
    return None


# Human-readable descriptions per vendor class for Markdown output
_CLASS_DESCRIPTIONS: dict[str, str] = {
    "analytics":          "Web analytics / session tracking",
    "advertising":        "Advertising network / retargeting",
    "tag_manager":        "Tag management system",
    "chat_widget":        "Live chat / customer messaging",
    "call_tracking":      "Phone call tracking / attribution",
    "form_platform":      "External form platform",
    "crm_or_lead_capture": "CRM / lead capture tool",
    "consent_management": "Cookie consent / preference platform",
    "cdn_or_static":      "Content delivery network",
    "fonts":              "Web font service",
    "maps":               "Mapping / geolocation service",
    "video_or_media":     "Video / media hosting",
    "payment":            "Payment processor",
    "social":             "Social media integration",
    "unknown":            "Unclassified third-party service",
}

# Vendor classes that warrant a privacy/compliance note
_HIGH_INTEREST_CLASSES: frozenset[str] = frozenset([
    "form_platform",
    "crm_or_lead_capture",
    "call_tracking",
    "advertising",
    "tag_manager",
])


def _build_notes(vendor_class: str, privacy_note: str) -> list[str]:
    notes: list[str] = []
    if privacy_note:
        notes.append(privacy_note)
    if vendor_class == "form_platform":
        notes.append("Form data may be routed to this third-party service.")
    elif vendor_class == "crm_or_lead_capture":
        notes.append("May receive lead/contact data from form submissions.")
    elif vendor_class == "call_tracking":
        notes.append("Replaces phone numbers dynamically to attribute calls.")
    elif vendor_class == "tag_manager":
        notes.append("Loads additional tags — check tag manager container for full inventory.")
    return notes


def classify_vendors(
    observations: list[NetworkObservation],
    host_first_seen: dict[str, str] | None = None,
) -> list[VendorSummaryItem]:
    """
    Classify a list of NetworkObservation entries into a VendorSummaryItem list.

    Only third-party observations are classified.
    Deduplicates by host — one VendorSummaryItem per unique third-party host.
    Results are sorted: high-interest classes first, then alphabetically by host.

    Parameters
    ----------
    observations : list[NetworkObservation]
        All deduplicated network observations from the crawl.
    host_first_seen : dict[str, str] | None
        Optional mapping of host → page URL where host was first observed.

    Returns
    -------
    list[VendorSummaryItem]
    """
    if host_first_seen is None:
        host_first_seen = {}

    seen_hosts: set[str] = set()
    items: list[VendorSummaryItem] = []

    for obs in observations:
        if not obs.is_third_party:
            continue
        host = obs.host.lower()
        if host in seen_hosts:
            continue
        seen_hosts.add(host)

        match = _match_host(host)
        if match:
            vendor_class, vendor_name, privacy_note = match
        else:
            vendor_class, vendor_name, privacy_note = "unknown", None, ""

        notes = _build_notes(vendor_class, privacy_note)
        first_seen = host_first_seen.get(host)

        items.append(
            VendorSummaryItem(
                host=obs.host,
                vendor_class=vendor_class,
                vendor_name=vendor_name,
                first_seen_on=first_seen,
                notes=notes,
            )
        )
        logger.debug(
            "vendor_classification: %s → %s (%s)", obs.host, vendor_class, vendor_name or "unknown"
        )

    # Sort: high-interest classes first, then alphabetically within class
    def _sort_key(item: VendorSummaryItem) -> tuple[int, str, str]:
        priority = 0 if item.vendor_class in _HIGH_INTEREST_CLASSES else 1
        return (priority, item.vendor_class, item.host)

    items.sort(key=_sort_key)
    logger.info("vendor_classification: classified %d third-party hosts", len(items))
    return items


def vendor_class_description(vendor_class: str) -> str:
    """Return a human-readable description for a vendor class."""
    return _CLASS_DESCRIPTIONS.get(vendor_class, "Third-party service")
