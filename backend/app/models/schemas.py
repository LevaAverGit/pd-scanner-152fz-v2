from enum import Enum

from pydantic import BaseModel, HttpUrl


class ScanStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    complete = "complete"
    failed = "failed"


class ScanRequest(BaseModel):
    url: HttpUrl
    notes: str | None = None
    enable_synthetic_submission: bool = False
    integration_evidence: dict | None = None
    operator_metadata: dict | None = None


class DataCategoryItem(BaseModel):
    category: str
    confidence: float
    matched_signals: list[str]
    explanation: str


class NetworkObservation(BaseModel):
    host: str
    resource_type: str
    is_third_party: bool
    method: str


# ---------------------------------------------------------------------------
# Multi-page crawl models
# ---------------------------------------------------------------------------

class VisitedPageItem(BaseModel):
    """Summary of a single page visited during a bounded same-site crawl."""
    url: str
    page_title: str | None = None
    registration_relevance: str | None = None
    detected_categories: list[DataCategoryItem] = []
    fields_count: int = 0
    forms_found: int = 0
    notes: list[str] = []
    # Consent / privacy signal detection
    has_privacy_link: bool = False
    has_terms_link: bool = False
    has_consent_checkbox: bool = False
    has_marketing_consent: bool = False
    consent_signals: list[str] = []
    # Submit-target analysis
    has_first_party_submission_hint: bool = False
    has_third_party_submission_hint: bool = False
    probable_form_platform: str | None = None
    probable_crm_or_capture_tool: str | None = None
    probable_submission_target: str | None = None
    submission_method: str | None = None
    submission_target_type: str = "unknown"
    submission_evidence: list[str] = []
    # Interactive discovery
    hidden_forms_revealed: int = 0
    interactions_performed: list[str] = []
    dynamic_consent_signals: list[str] = []
    modal_forms_found: int = 0
    # Deep consent
    has_bundled_consent_text: bool = False
    # Synthetic submission
    synthetic_submission_attempted: bool = False
    synthetic_submission_status: str = "not_attempted"  # not_attempted|submitted|blocked|validation_failed|indeterminate
    observed_submit_url: str | None = None
    observed_submit_method: str | None = None
    observed_submit_target_type: str = "unknown"  # first_party|third_party|relative|unknown
    observed_follow_on_hosts: list[str] = []
    observed_submission_evidence: list[str] = []
    observed_capture_tool: str | None = None
    observed_webhook_or_api_hint: str | None = None
    # Downstream routing inference
    downstream_processor_type: str | None = None
    downstream_processor_name: str | None = None
    downstream_routing_confidence: str = "low"
    downstream_routing_signals: list[str] = []


class SyntheticSubmissionSummary(BaseModel):
    pages_attempted: int = 0
    successful_submissions: int = 0
    third_party_submissions: int = 0
    first_party_submissions: int = 0
    blocked_or_failed: int = 0


class SiteSummary(BaseModel):
    """Aggregate statistics across all pages visited in a crawl."""
    pages_scanned: int
    pages_with_forms: int
    total_forms_found: int
    unique_categories_found: list[str]
    top_third_party_hosts: list[str]
    # Site-wide consent/privacy signal counts
    pages_with_privacy_link: int = 0
    pages_with_consent_checkbox: int = 0
    pages_with_marketing_consent: int = 0


# ---------------------------------------------------------------------------
# Vendor / third-party ecosystem model
# ---------------------------------------------------------------------------

class VendorSummaryItem(BaseModel):
    """A single classified third-party vendor observed during the scan."""
    host: str
    vendor_class: str
    vendor_name: str | None = None
    first_seen_on: str | None = None
    notes: list[str] = []


# ---------------------------------------------------------------------------
# Policy / privacy page analysis model
# ---------------------------------------------------------------------------

class PolicyAnalysis(BaseModel):
    """Heuristic analysis of a linked privacy/policy page."""
    url: str
    operator_name: str | None = None
    operator_contacts: list[str] = []
    has_purpose_section: bool = False
    has_categories_section: bool = False
    has_legal_basis_section: bool = False
    has_processor_or_third_party_section: bool = False
    has_cross_border_section: bool = False
    has_subject_rights_section: bool = False
    has_retention_or_destruction_section: bool = False
    has_localization_statement: bool = False
    policy_signals: list[str] = []
    # Document type detection and parse status
    policy_document_type: str = "html"   # html | pdf | docx | doc | unknown
    policy_document_url: str | None = None
    policy_parse_status: str = "parsed"  # parsed | unsupported | unreadable | failed


# ---------------------------------------------------------------------------
# Integration audit models
# ---------------------------------------------------------------------------

class OperatorIntegrationEvidence(BaseModel):
    """Operator-supplied integration evidence. Not scanner-observed — must be clearly labelled."""
    source: str | None = None
    form_platform: str | None = None
    crm_destination: str | None = None
    webhook_urls: list[str] = []
    notification_targets: list[str] = []
    notes: list[str] = []


class ProcessorMapItem(BaseModel):
    """One entry in the site-level downstream processor map."""
    processor_name: str | None = None
    processor_type: str = "unknown"
    # observed_submit | inferred_public_signal | operator_supplied
    source: str = "inferred_public_signal"
    related_hosts: list[str] = []
    related_pages: list[str] = []
    confidence: str = "low"  # low | medium | high
    evidence: list[str] = []


# ---------------------------------------------------------------------------
# 152-FZ Evidence Layer models
# ---------------------------------------------------------------------------

class OperatorMetadata(BaseModel):
    """
    Optional operator-supplied legal/corporate metadata.
    Explicitly NOT scanner-observed — must be clearly labelled in all outputs.
    """
    legal_name: str | None = None
    inn: str | None = None
    ogrn: str | None = None
    notes: list[str] = []


class FZ152Assessment(BaseModel):
    """
    Structured 152-FZ evidence summary derived from public scanner findings.

    IMPORTANT DISCLAIMER:
    This is a heuristic, evidence-based summary derived from publicly observable
    site behavior. It does NOT constitute legal advice or a definitive compliance
    determination. All findings require manual validation by a qualified specialist.
    """
    # Operator / policy public presence
    operator_name: str | None = None
    operator_contacts: list[str] = []
    policy_publicly_available: bool = False
    privacy_links_found: int = 0
    # Data collection scope
    forms_collecting_pd: int = 0
    detected_pd_categories: list[str] = []
    # Consent mechanism
    consent_mechanism_type: str = "unknown"  # explicit_checkbox|bundled_text|weak_or_absent|mixed|unknown
    # Policy section coverage
    policy_has_purpose_section: bool = False
    policy_has_categories_section: bool = False
    policy_has_legal_basis_section: bool = False
    policy_has_processor_or_third_party_section: bool = False
    policy_has_cross_border_section: bool = False
    policy_has_subject_rights_section: bool = False
    policy_has_retention_or_destruction_section: bool = False
    policy_has_localization_statement: bool = False
    # Processing / routing scope
    processor_map_present: bool = False
    third_party_routing_present: bool = False
    observed_submit_present: bool = False
    operator_supplied_evidence_present: bool = False
    metrics_or_tracking_present: bool = False
    # Findings
    potential_gaps: list[str] = []
    manual_validation_targets: list[str] = []
    overall_public_risk_level: str = "medium"  # low|medium|high
    disclaimer: str = (
        "This assessment is based solely on publicly observable site behavior and "
        "heuristic analysis. It does not constitute legal advice or a definitive "
        "compliance determination under 152-FZ. All findings require manual "
        "validation by a qualified specialist."
    )


# ---------------------------------------------------------------------------
# Core result model
# ---------------------------------------------------------------------------

class ScanResult(BaseModel):
    scan_id: str
    url: str
    status: ScanStatus
    data_categories: list[DataCategoryItem]
    created_at: str
    completed_at: str | None = None
    error: str | None = None
    network_observations: list[NetworkObservation] = []
    screenshot_path: str | None = None
    registration_relevance: str | None = None
    raw_json_export_path: str | None = None
    markdown_export_path: str | None = None
    # Default to empty/None so existing records still deserialize
    visited_pages: list[VisitedPageItem] = []
    site_summary: SiteSummary | None = None
    # Vendor/third-party ecosystem summary
    vendor_summary: list[VendorSummaryItem] = []
    # Policy/privacy page analysis
    policy_analysis: PolicyAnalysis | None = None
    # Synthetic submission
    synthetic_submission_enabled: bool = False
    synthetic_submission_summary: SyntheticSubmissionSummary | None = None
    # Integration audit
    operator_integration_evidence: OperatorIntegrationEvidence | None = None
    processor_map: list[ProcessorMapItem] = []
    # 152-FZ evidence layer
    fz152_assessment: FZ152Assessment | None = None
    operator_metadata: OperatorMetadata | None = None


class HistoryItem(BaseModel):
    scan_id: str
    url: str
    status: ScanStatus
    created_at: str


class HistoryResponse(BaseModel):
    items: list[HistoryItem]
    total: int


# ---------------------------------------------------------------------------
# Scan diff / compare models
# ---------------------------------------------------------------------------

class ScanDiffRequest(BaseModel):
    base_scan_id: str
    compare_scan_id: str


class ChangedItem(BaseModel):
    """Represents a single changed dimension between two scans."""
    dimension: str       # e.g. "risk_level", "consent_mechanism", "policy_section.purpose"
    label: str           # human-readable label
    base_value: str | None = None
    compare_value: str | None = None
    change_type: str = "changed"  # added | removed | changed | unchanged


class ScanDiffResult(BaseModel):
    """
    Result of comparing two completed scans.
    Computed on-demand from stored ScanResult objects — no new DB schema.
    """
    base_scan_id: str
    compare_scan_id: str
    base_url: str
    compare_url: str
    base_scanned_at: str | None = None
    compare_scanned_at: str | None = None
    # Set-level differences
    added_categories: list[str] = []
    removed_categories: list[str] = []
    added_vendors: list[str] = []
    removed_vendors: list[str] = []
    added_processors: list[str] = []
    removed_processors: list[str] = []
    added_gaps: list[str] = []
    removed_gaps: list[str] = []
    # Scalar / enum changes
    changed_items: list[ChangedItem] = []
    # Human-readable summary lines
    summary_lines: list[str] = []
