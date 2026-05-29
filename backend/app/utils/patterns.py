"""
Compiled regex patterns and keyword lists used throughout the scanner pipeline.
"""

import re

# Strip non-alphanumeric characters (keep spaces) for field name normalization
FIELD_NAME_NORMALIZER_RE: re.Pattern = re.compile(r"[^a-z0-9\s]")

# Context detection keyword lists (all lowercase)
REGISTRATION_KEYWORDS: list[str] = [
    "register",
    "signup",
    "sign-up",
    "sign up",
    "create account",
    "join",
    "new account",
    "registration",
    "enroll",
    "subscribe",
    "create your account",
    "get started",
    "open account",
    "open an account",
]

LOGIN_KEYWORDS: list[str] = [
    "login",
    "log in",
    "signin",
    "sign in",
    "log into",
    "member login",
    "account login",
    "enter your password",
]

NEWSLETTER_KEYWORDS: list[str] = [
    "newsletter",
    "subscribe",
    "mailing list",
    "email list",
    "stay updated",
    "get updates",
    "email updates",
]

CONTACT_KEYWORDS: list[str] = [
    "contact",
    "message",
    "enquiry",
    "inquiry",
    "feedback",
    "get in touch",
    "send a message",
    "contact us",
    "reach us",
    "support",
]

# Additional page-type keyword lists
CHECKOUT_KEYWORDS: list[str] = [
    "checkout",
    "check out",
    "shopping cart",
    "order",
    "payment",
    "billing",
    "buy now",
    "purchase",
    "proceed to pay",
    "place order",
    "complete order",
]

CALLBACK_KEYWORDS: list[str] = [
    "request a call",
    "request callback",
    "schedule a call",
    "book a demo",
    "book a consultation",
    "schedule demo",
    "get a quote",
    "request demo",
    "free trial",
    "book a call",
    "talk to us",
    "speak to an expert",
]

# Categories that carry elevated privacy risk
HIGH_RISK_CATEGORIES: set[str] = {
    "national_id",
    "financial",
    "health",
    "date_of_birth",
    "password",
}

# URL path keywords that suggest a page likely contains a form of interest.
# Used to prioritise links in the bounded crawler queue.
CRAWL_PRIORITY_KEYWORDS: list[str] = [
    "register",
    "signup",
    "sign-up",
    "sign_up",
    "create-account",
    "create_account",
    "account",
    "login",
    "log-in",
    "contact",
    "form",
    "order",
    "checkout",
    "booking",
    "trial",
    "subscribe",
    "join",
    "enroll",
    "apply",
    "onboard",
    "get-started",
]

# URL path/query fragments that suggest the link should NOT be followed
# (account-danger, destructive, or logout-style actions).
CRAWL_SKIP_PATTERNS: list[str] = [
    "logout",
    "log-out",
    "log_out",
    "signout",
    "sign-out",
    "sign_out",
    "delete",
    "remove",
    "unsubscribe",
    "cancel",
    "deactivate",
    "admin",
]

# Path segments that indicate low-value content pages (taxonomy, archive, pagination).
# These are deprioritised (negative score) rather than skipped entirely,
# so they are still visited if nothing higher-value remains in the queue.
CRAWL_LOW_VALUE_PATTERNS: list[str] = [
    "/author/",
    "/tag/",
    "/tags/",
    "/category/",
    "/categories/",
    "/archive/",
    "/archives/",
    "/feed/",
    "/rss/",
    "/search/",
    "/wp-json/",
]

# File extensions that should never be crawled
CRAWL_SKIP_EXTENSIONS: set[str] = {
    ".pdf", ".zip", ".gz", ".tar",
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico",
    ".mp4", ".mp3", ".avi", ".mov",
    ".docx", ".xlsx", ".pptx", ".csv",
    ".exe", ".dmg", ".pkg",
    ".woff", ".woff2", ".ttf", ".eot",
}

# Consent / privacy signal detection keywords
# Used by consent_detection_service to identify privacy links, terms links,
# and consent / marketing checkboxes on pages.

CONSENT_PRIVACY_KEYWORDS: list[str] = [
    "privacy policy",
    "privacy notice",
    "data protection",
    "personal data",
    "privacy",
    "datenschutz",
    "конфиденциальность",
    "персональные данные",
    "политика конфиденциальности",
]

CONSENT_TERMS_KEYWORDS: list[str] = [
    "terms of service",
    "terms and conditions",
    "terms of use",
    "user agreement",
    "terms",
    "условия использования",
    "пользовательское соглашение",
    "eula",
]

CONSENT_MARKETING_KEYWORDS: list[str] = [
    "marketing",
    "promotional",
    "newsletter",
    "special offers",
    "news and offers",
    "commercial communications",
    "рассылка",
    "маркетинг",
]

# ---------------------------------------------------------------------------
# Interactive discovery: CTA button/link text patterns
# ---------------------------------------------------------------------------
INTERACTIVE_CTA_PATTERNS: list[str] = [
    # EN
    "leave request", "submit request", "get started", "sign up", "register",
    "book", "try free", "free trial", "contact us", "open form", "request demo",
    "request callback", "request a call", "callback", "consultation",
    "book a call", "schedule", "get quote", "get a quote", "apply",
    "subscribe", "join", "enroll", "get access", "start free",
    # RU
    "оставить заявку", "оставить заявление", "записаться", "записаться на",
    "зарегистрироваться", "зарегистрировать", "подать заявку",
    "бесплатная консультация", "консультация", "позвоните мне", "перезвоните",
    "обратный звонок", "заказать звонок", "заказать", "получить консультацию",
    "записаться на приём", "подписаться", "вступить", "попробовать бесплатно",
    "начать бесплатно", "получить доступ", "открыть форму",
]

# Interactive: expand/reveal patterns (accordion, tab, read-more)
INTERACTIVE_EXPAND_PATTERNS: list[str] = [
    "show more", "read more", "expand", "details", "learn more",
    "подробнее", "узнать больше", "показать", "раскрыть",
]

# ---------------------------------------------------------------------------
# Policy parser: section heading keywords (EN + RU)
# ---------------------------------------------------------------------------
POLICY_PURPOSE_KEYWORDS: list[str] = [
    "purpose", "purposes", "цели", "цель обработки", "основания обработки",
    "для каких целей", "предмет и цели",
]
POLICY_CATEGORIES_KEYWORDS: list[str] = [
    "categories of personal data", "categories of data", "what data",
    "данные которые", "состав персональных данных", "категории персональных данных",
    "перечень персональных данных", "виды персональных данных", "какие данные",
]
POLICY_LEGAL_BASIS_KEYWORDS: list[str] = [
    "legal basis", "lawful basis", "legitimate interest",
    "основание обработки", "правовое основание", "согласие субъекта",
    "законный интерес",
]
POLICY_PROCESSOR_KEYWORDS: list[str] = [
    "third party", "third-party", "processor", "sub-processor", "data processor",
    "service provider", "partner", "vendor",
    "третье лицо", "третьи лица", "оператор", "поручение оператора",
    "передача третьим", "передача персональных данных третьим",
    "контрагент",
]
POLICY_CROSS_BORDER_KEYWORDS: list[str] = [
    "cross-border", "international transfer", "transfer abroad", "transborder",
    "outside the", "трансграничная передача", "за рубеж", "иностранное",
    "передача за пределы", "в иностранное государство",
]
POLICY_SUBJECT_RIGHTS_KEYWORDS: list[str] = [
    "rights of data subjects", "your rights", "subject rights",
    "right to access", "right to erasure", "right to rectification",
    "права субъекта", "права субъектов", "право на доступ", "право на исправление",
    "право на удаление", "право отозвать согласие", "права пользователей",
]
POLICY_RETENTION_KEYWORDS: list[str] = [
    "retention", "retention period", "storage period", "deletion",
    "destroy", "destruction", "how long", "archive",
    "сроки хранения", "срок обработки", "уничтожение персональных данных",
    "период хранения", "как долго",
]
POLICY_LOCALIZATION_KEYWORDS: list[str] = [
    "localization", "stored in russia", "russian federation", "within russia",
    "on territory", "на территории", "локализация", "хранение на территории",
    "российская федерация", "серверы расположены", "фз-152", "федеральный закон",
    "152-фз",
]

# ---------------------------------------------------------------------------
# Deep consent: submit-adjacent / bundled consent text (EN + RU)
# ---------------------------------------------------------------------------
CONSENT_BUNDLED_KEYWORDS: list[str] = [
    # EN
    "by clicking", "by submitting", "by registering", "by signing up",
    "i agree", "i accept", "i consent", "you agree", "you accept",
    "agreeing to", "accept our", "accept the", "consent to",
    "terms and conditions", "privacy policy", "personal data",
    # RU
    "нажимая", "нажимая на кнопку", "нажимая кнопку",
    "отправляя форму", "регистрируясь", "подавая заявку",
    "я соглашаюсь", "соглашаюсь с", "согласен с", "согласна с",
    "даю согласие", "выражаю согласие", "принимаю условия",
    "политику обработки", "политика конфиденциальности",
    "обработку персональных данных", "персональные данные",
]
