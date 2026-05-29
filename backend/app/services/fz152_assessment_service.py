"""
152-FZ Evidence Layer Assessment Service.

Derives a structured FZ152Assessment from existing scanner findings.
All assessments are heuristic and evidence-based only.

IMPORTANT: This service does NOT produce legal conclusions.
All findings use careful wording:
- "signal detected" not "violation found"
- "potential gap" not "non-compliant"
- "manual validation required" not "illegal"
"""
from __future__ import annotations

import logging

from backend.app.models.schemas import (
    FZ152Assessment,
    OperatorIntegrationEvidence,
    OperatorMetadata,
    PolicyAnalysis,
    ProcessorMapItem,
    ScanResult,
    SiteSummary,
    VendorSummaryItem,
    VisitedPageItem,
)

logger = logging.getLogger(__name__)

# Vendor classes that indicate metrics/tracking presence
_TRACKING_VENDOR_CLASSES = {
    "analytics", "ad_tech", "tracking", "retargeting", "marketing_automation",
}

# Policy sections that should be present for a reasonably complete policy
_REQUIRED_POLICY_SECTIONS = [
    ("has_purpose_section", "purpose / processing goals"),
    ("has_categories_section", "personal data categories"),
    ("has_legal_basis_section", "legal basis"),
    ("has_subject_rights_section", "data subject rights"),
    ("has_retention_or_destruction_section", "retention / destruction"),
    ("has_localization_statement", "localization (152-FZ Art. 18.1)"),
]


def _derive_consent_mechanism_type(visited_pages: list[VisitedPageItem]) -> str:
    """
    Classify the dominant consent mechanism found across the site.
    Returns: explicit_checkbox | bundled_text | weak_or_absent | mixed | unknown
    """
    has_explicit = any(p.has_consent_checkbox or p.has_marketing_consent for p in visited_pages)
    has_bundled = any(p.has_bundled_consent_text for p in visited_pages)
    has_any_form = any(p.forms_found > 0 or p.fields_count > 0 for p in visited_pages)

    if not has_any_form:
        return "unknown"
    if has_explicit and has_bundled:
        return "mixed"
    if has_explicit and not has_bundled:
        return "explicit_checkbox"
    if has_bundled and not has_explicit:
        return "bundled_text"
    # Forms present but no consent mechanism detected
    return "weak_or_absent"


def _derive_potential_gaps(
    assessment: FZ152Assessment,
    policy: PolicyAnalysis | None,
    visited_pages: list[VisitedPageItem],
    processor_map: list[ProcessorMapItem],
) -> list[str]:
    gaps: list[str] = []

    if not assessment.policy_publicly_available:
        gaps.append(
            "No public privacy policy link detected — public availability required under 152-FZ Art. 18.1."
        )
    elif policy:
        # Check each required section
        for attr, label in _REQUIRED_POLICY_SECTIONS:
            if not getattr(assessment, f"policy_{attr}", False):
                gaps.append(
                    f"Policy section not publicly evidenced: {label} — manual review recommended."
                )

    if assessment.consent_mechanism_type in ("weak_or_absent",):
        gaps.append(
            "No explicit consent mechanism detected on data-collection forms — "
            "potential gap: 152-FZ requires documented consent for PD processing."
        )
    elif assessment.consent_mechanism_type == "bundled_text":
        gaps.append(
            "Bundled/implied consent text detected instead of explicit checkbox — "
            "adequacy of this mechanism requires manual legal review."
        )

    if assessment.third_party_routing_present:
        if not assessment.policy_has_processor_or_third_party_section:
            gaps.append(
                "Third-party routing signals present but policy does not publicly evidence "
                "processor/third-party disclosure — manual validation required."
            )

    if assessment.third_party_routing_present and not assessment.policy_has_cross_border_section:
        gaps.append(
            "Third-party routing present but no cross-border transfer statement publicly evidenced — "
            "verify if cross-border transfer applies and whether adequate safeguards are documented."
        )

    if assessment.metrics_or_tracking_present:
        gaps.append(
            "Metrics/tracking signals detected — cookie and analytics consent disclosure "
            "should be manually validated against public policy."
        )

    if assessment.processor_map_present:
        medium_low = [
            pm for pm in processor_map
            if pm.confidence in ("low", "medium") and pm.source != "operator_supplied"
        ]
        if medium_low:
            gaps.append(
                f"{len(medium_low)} inferred processor(s) with low/medium confidence — "
                "processor agreements and sub-processing disclosure require manual review."
            )

    if assessment.forms_collecting_pd == 0 and assessment.detected_pd_categories:
        gaps.append(
            "Personal data categories detected in scanner but no forms counted — "
            "data collection source requires manual investigation."
        )

    return gaps


def _derive_manual_validation_targets(assessment: FZ152Assessment) -> list[str]:
    targets: list[str] = []

    targets.append("Verify operator legal identity (INN/OGRN/full legal name) from public registry.")

    if assessment.policy_publicly_available:
        targets.append("Verify public policy is complete, current, and authored by a qualified specialist.")
    else:
        targets.append("Locate or establish a public privacy policy.")

    if assessment.consent_mechanism_type in ("bundled_text", "weak_or_absent", "mixed"):
        targets.append(
            "Review and validate the legal basis and consent mechanism for all data-collection forms."
        )

    if assessment.third_party_routing_present or assessment.processor_map_present:
        targets.append(
            "Review and confirm data processing agreements (DPA) with all observed/inferred processors."
        )

    if assessment.policy_has_cross_border_section is False and assessment.third_party_routing_present:
        targets.append(
            "Verify cross-border transfer handling and document applicable legal grounds."
        )

    if not assessment.policy_has_retention_or_destruction_section:
        targets.append(
            "Define and document personal data retention and destruction procedures."
        )

    if not assessment.policy_has_subject_rights_section:
        targets.append(
            "Document and publish data subject rights and the procedure for exercising them."
        )

    if assessment.metrics_or_tracking_present:
        targets.append(
            "Review cookie and analytics data collection — confirm appropriate notice and consent."
        )

    if assessment.operator_supplied_evidence_present:
        targets.append(
            "Cross-check operator-supplied integration evidence against actual system configuration."
        )

    return targets


def _derive_risk_level(assessment: FZ152Assessment) -> str:
    """
    Heuristic overall public risk level: low | medium | high.
    Based on number and severity of potential gaps.
    Does NOT constitute a legal risk assessment.
    """
    score = 0

    if not assessment.policy_publicly_available:
        score += 3
    if assessment.consent_mechanism_type in ("weak_or_absent",):
        score += 3
    elif assessment.consent_mechanism_type == "bundled_text":
        score += 2
    if assessment.third_party_routing_present and not assessment.policy_has_processor_or_third_party_section:
        score += 2
    if assessment.third_party_routing_present and not assessment.policy_has_cross_border_section:
        score += 1
    if not assessment.policy_has_legal_basis_section:
        score += 2
    if not assessment.policy_has_subject_rights_section:
        score += 1
    if not assessment.policy_has_retention_or_destruction_section:
        score += 1
    if assessment.metrics_or_tracking_present:
        score += 1
    if len(assessment.potential_gaps) > 5:
        score += 1

    if score >= 3:
        return "high"
    if score >= 1:
        return "medium"
    return "low"


def build_fz152_assessment(
    visited_pages: list[VisitedPageItem],
    policy: PolicyAnalysis | None,
    site_summary: SiteSummary | None,
    vendor_summary: list[VendorSummaryItem],
    processor_map: list[ProcessorMapItem],
    operator_evidence: OperatorIntegrationEvidence | None,
    operator_metadata: OperatorMetadata | None,
) -> FZ152Assessment:
    """
    Build a FZ152Assessment from all available scanner findings.
    All outputs are heuristic and evidence-based. No legal conclusions.
    """
    # Operator presence
    operator_name = None
    operator_contacts: list[str] = []
    if policy:
        operator_name = policy.operator_name
        operator_contacts = list(policy.operator_contacts)
    if operator_metadata and operator_metadata.legal_name and not operator_name:
        operator_name = operator_metadata.legal_name

    # Policy public availability
    privacy_links_found = sum(1 for p in visited_pages if p.has_privacy_link)
    policy_publicly_available = privacy_links_found > 0 or policy is not None

    # Data collection scope
    forms_collecting_pd = sum(1 for p in visited_pages if p.fields_count > 0 or p.forms_found > 0)
    all_cats: set[str] = set()
    for p in visited_pages:
        for cat in p.detected_categories:
            all_cats.add(cat.category)
    detected_pd_categories = sorted(all_cats)

    # Consent mechanism
    consent_mechanism_type = _derive_consent_mechanism_type(visited_pages)

    # Policy section coverage
    pa_fields = {
        "policy_has_purpose_section": False,
        "policy_has_categories_section": False,
        "policy_has_legal_basis_section": False,
        "policy_has_processor_or_third_party_section": False,
        "policy_has_cross_border_section": False,
        "policy_has_subject_rights_section": False,
        "policy_has_retention_or_destruction_section": False,
        "policy_has_localization_statement": False,
    }
    if policy:
        pa_fields = {
            "policy_has_purpose_section": policy.has_purpose_section,
            "policy_has_categories_section": policy.has_categories_section,
            "policy_has_legal_basis_section": policy.has_legal_basis_section,
            "policy_has_processor_or_third_party_section": policy.has_processor_or_third_party_section,
            "policy_has_cross_border_section": policy.has_cross_border_section,
            "policy_has_subject_rights_section": policy.has_subject_rights_section,
            "policy_has_retention_or_destruction_section": policy.has_retention_or_destruction_section,
            "policy_has_localization_statement": policy.has_localization_statement,
        }

    # Processing / routing scope
    processor_map_present = len(processor_map) > 0
    third_party_routing_present = any(
        pm.processor_type in ("crm_or_lead_capture", "form_platform", "webhook_or_api")
        and pm.source != "operator_supplied"
        for pm in processor_map
    ) or any(p.has_third_party_submission_hint or p.observed_submit_target_type == "third_party"
             for p in visited_pages)
    observed_submit_present = any(
        p.synthetic_submission_status == "submitted" for p in visited_pages
    )
    operator_supplied_evidence_present = (
        operator_evidence is not None or operator_metadata is not None
    )
    metrics_or_tracking_present = any(
        v.vendor_class in _TRACKING_VENDOR_CLASSES for v in vendor_summary
    )

    # Build partial assessment (without gaps/targets/risk yet)
    assessment = FZ152Assessment(
        operator_name=operator_name,
        operator_contacts=operator_contacts,
        policy_publicly_available=policy_publicly_available,
        privacy_links_found=privacy_links_found,
        forms_collecting_pd=forms_collecting_pd,
        detected_pd_categories=detected_pd_categories,
        consent_mechanism_type=consent_mechanism_type,
        processor_map_present=processor_map_present,
        third_party_routing_present=third_party_routing_present,
        observed_submit_present=observed_submit_present,
        operator_supplied_evidence_present=operator_supplied_evidence_present,
        metrics_or_tracking_present=metrics_or_tracking_present,
        **pa_fields,
    )

    # Derive gaps and targets using the partial assessment
    gaps = _derive_potential_gaps(assessment, policy, visited_pages, processor_map)
    targets = _derive_manual_validation_targets(assessment)
    assessment.potential_gaps = gaps
    assessment.manual_validation_targets = targets
    assessment.overall_public_risk_level = _derive_risk_level(assessment)

    logger.info(
        "fz152_assessment_service: assessment built — risk=%s gaps=%d targets=%d",
        assessment.overall_public_risk_level,
        len(gaps),
        len(targets),
    )
    return assessment
