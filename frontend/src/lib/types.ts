export type ScanStatus = 'pending' | 'processing' | 'complete' | 'failed'

export interface DataCategoryItem {
  category: string
  confidence: number
  matched_signals: string[]
  explanation: string
}

export interface NetworkObservation {
  host: string
  resource_type: string
  is_third_party: boolean
  method: string
}

export interface VisitedPageItem {
  url: string
  page_title: string | null
  registration_relevance: string | null
  detected_categories: DataCategoryItem[]
  fields_count: number
  forms_found: number
  notes: string[]
  // Consent/privacy signals
  has_privacy_link: boolean
  has_terms_link: boolean
  has_consent_checkbox: boolean
  has_marketing_consent: boolean
  consent_signals: string[]
  // Submit-target analysis
  has_first_party_submission_hint: boolean
  has_third_party_submission_hint: boolean
  probable_form_platform: string | null
  probable_crm_or_capture_tool: string | null
  probable_submission_target: string | null
  submission_method: string | null
  submission_target_type: string
  submission_evidence: string[]
  // Interactive discovery
  hidden_forms_revealed: number
  interactions_performed: string[]
  dynamic_consent_signals: string[]
  modal_forms_found: number
  // Deep consent
  has_bundled_consent_text: boolean
  // Synthetic submission
  synthetic_submission_attempted: boolean
  synthetic_submission_status: string  // not_attempted|submitted|blocked|validation_failed|indeterminate
  observed_submit_url: string | null
  observed_submit_method: string | null
  observed_submit_target_type: string  // first_party|third_party|relative|unknown
  observed_follow_on_hosts: string[]
  observed_submission_evidence: string[]
  observed_capture_tool: string | null
  observed_webhook_or_api_hint: string | null
}

export interface SiteSummary {
  pages_scanned: number
  pages_with_forms: number
  total_forms_found: number
  unique_categories_found: string[]
  top_third_party_hosts: string[]
  // Site-wide consent/privacy signal counts
  pages_with_privacy_link: number
  pages_with_consent_checkbox: number
  pages_with_marketing_consent: number
}

export interface PolicyAnalysis {
  url: string
  operator_name: string | null
  operator_contacts: string[]
  has_purpose_section: boolean
  has_categories_section: boolean
  has_legal_basis_section: boolean
  has_processor_or_third_party_section: boolean
  has_cross_border_section: boolean
  has_subject_rights_section: boolean
  has_retention_or_destruction_section: boolean
  has_localization_statement: boolean
  policy_signals: string[]
  // Document type and parse status
  policy_document_type: string   // html | pdf | docx | doc | unknown
  policy_document_url: string | null
  policy_parse_status: string    // parsed | unsupported | unreadable | failed
}

export interface VendorSummaryItem {
  host: string
  vendor_class: string
  vendor_name: string | null
  first_seen_on: string | null
  notes: string[]
}

export interface SyntheticSubmissionSummary {
  pages_attempted: number
  successful_submissions: number
  third_party_submissions: number
  first_party_submissions: number
  blocked_or_failed: number
}

export interface ScanResult {
  scan_id: string
  url: string
  status: ScanStatus
  data_categories: DataCategoryItem[]
  created_at: string
  completed_at: string | null
  error: string | null
  network_observations: NetworkObservation[]
  screenshot_path: string | null
  registration_relevance: string | null
  raw_json_export_path: string | null
  markdown_export_path: string | null
  visited_pages: VisitedPageItem[]
  site_summary: SiteSummary | null
  // Vendor/third-party ecosystem
  vendor_summary: VendorSummaryItem[]
  // Policy/privacy page analysis
  policy_analysis: PolicyAnalysis | null
  // Synthetic submission
  synthetic_submission_enabled: boolean
  synthetic_submission_summary: SyntheticSubmissionSummary | null
  // 152-FZ evidence layer
  fz152_assessment: FZ152Assessment | null
  operator_metadata: OperatorMetadata | null
}

// Integration audit models
export interface ProcessorMapItem {
  processor_name: string | null
  processor_type: string
  source: string
  related_hosts: string[]
  related_pages: string[]
  confidence: string
  evidence: string[]
}

// 152-FZ evidence layer
export interface OperatorMetadata {
  legal_name: string | null
  inn: string | null
  ogrn: string | null
  notes: string[]
}

export interface FZ152Assessment {
  operator_name: string | null
  operator_contacts: string[]
  policy_publicly_available: boolean
  privacy_links_found: number
  forms_collecting_pd: number
  detected_pd_categories: string[]
  consent_mechanism_type: string
  policy_has_purpose_section: boolean
  policy_has_categories_section: boolean
  policy_has_legal_basis_section: boolean
  policy_has_processor_or_third_party_section: boolean
  policy_has_cross_border_section: boolean
  policy_has_subject_rights_section: boolean
  policy_has_retention_or_destruction_section: boolean
  policy_has_localization_statement: boolean
  processor_map_present: boolean
  third_party_routing_present: boolean
  observed_submit_present: boolean
  operator_supplied_evidence_present: boolean
  metrics_or_tracking_present: boolean
  potential_gaps: string[]
  manual_validation_targets: string[]
  overall_public_risk_level: string
  disclaimer: string
}

export interface HistoryItem {
  scan_id: string
  url: string
  status: ScanStatus
  created_at: string
}

export interface HistoryResponse {
  items: HistoryItem[]
  total: number
}

export interface ScanRequest {
  url: string
  notes?: string
  enable_synthetic_submission?: boolean
  operator_metadata?: Record<string, unknown>
}

// Scan diff / compare models
export interface ScanDiffRequest {
  base_scan_id: string
  compare_scan_id: string
}

export interface ChangedItem {
  dimension: string
  label: string
  base_value: string | null
  compare_value: string | null
  change_type: string  // added | removed | changed | unchanged
}

export interface ScanDiffResult {
  base_scan_id: string
  compare_scan_id: string
  base_url: string
  compare_url: string
  base_scanned_at: string | null
  compare_scanned_at: string | null
  added_categories: string[]
  removed_categories: string[]
  added_vendors: string[]
  removed_vendors: string[]
  added_processors: string[]
  removed_processors: string[]
  added_gaps: string[]
  removed_gaps: string[]
  changed_items: ChangedItem[]
  summary_lines: string[]
}
