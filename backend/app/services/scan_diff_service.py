"""
Scan diff / compare service.

Computes a structured diff between two completed ScanResult objects.
All computation is in-memory; no new DB schema is required.
"""

from backend.app.models.schemas import (
    ChangedItem,
    ScanDiffResult,
    ScanResult,
)


def _set_diff(
    base: list[str], compare: list[str]
) -> tuple[list[str], list[str]]:
    """Return (added, removed) comparing compare vs base."""
    base_set = set(base)
    cmp_set = set(compare)
    added = sorted(cmp_set - base_set)
    removed = sorted(base_set - cmp_set)
    return added, removed


def _scalar_change(
    dimension: str,
    label: str,
    base_val: str | None,
    cmp_val: str | None,
    changed: list[ChangedItem],
) -> None:
    if base_val != cmp_val:
        changed.append(
            ChangedItem(
                dimension=dimension,
                label=label,
                base_value=base_val,
                compare_value=cmp_val,
                change_type="changed",
            )
        )


def _bool_change(
    dimension: str,
    label: str,
    base_val: bool,
    cmp_val: bool,
    changed: list[ChangedItem],
) -> None:
    if base_val != cmp_val:
        changed.append(
            ChangedItem(
                dimension=dimension,
                label=label,
                base_value="yes" if base_val else "no",
                compare_value="yes" if cmp_val else "no",
                change_type="changed",
            )
        )


def compute_scan_diff(base: ScanResult, compare: ScanResult) -> ScanDiffResult:
    """
    Compare two completed scans and return a structured ScanDiffResult.
    """
    changed: list[ChangedItem] = []
    summary: list[str] = []

    # ------------------------------------------------------------------
    # 1. Data categories
    # ------------------------------------------------------------------
    base_cats = [c.category for c in base.data_categories]
    cmp_cats = [c.category for c in compare.data_categories]
    added_cats, removed_cats = _set_diff(base_cats, cmp_cats)

    # ------------------------------------------------------------------
    # 2. Vendor summary (by host)
    # ------------------------------------------------------------------
    base_vendors = [v.host for v in base.vendor_summary]
    cmp_vendors = [v.host for v in compare.vendor_summary]
    added_vendors, removed_vendors = _set_diff(base_vendors, cmp_vendors)

    # ------------------------------------------------------------------
    # 3. Processor map (by processor_name)
    # ------------------------------------------------------------------
    base_procs = [p.processor_name or "" for p in base.processor_map if p.processor_name]
    cmp_procs = [p.processor_name or "" for p in compare.processor_map if p.processor_name]
    added_procs, removed_procs = _set_diff(base_procs, cmp_procs)

    # ------------------------------------------------------------------
    # 4. FZ152 assessment scalars
    # ------------------------------------------------------------------
    base_fz = base.fz152_assessment
    cmp_fz = compare.fz152_assessment

    if base_fz is not None and cmp_fz is not None:
        _scalar_change(
            "risk_level", "Overall risk level",
            base_fz.overall_public_risk_level,
            cmp_fz.overall_public_risk_level,
            changed,
        )
        _scalar_change(
            "consent_mechanism", "Consent mechanism type",
            base_fz.consent_mechanism_type,
            cmp_fz.consent_mechanism_type,
            changed,
        )
        # Policy section booleans
        sections = [
            ("policy_section.purpose", "Policy: purpose section"),
            ("policy_section.categories", "Policy: categories section"),
            ("policy_section.legal_basis", "Policy: legal basis section"),
            ("policy_section.processors", "Policy: processor/third-party section"),
            ("policy_section.cross_border", "Policy: cross-border section"),
            ("policy_section.subject_rights", "Policy: subject rights section"),
            ("policy_section.retention", "Policy: retention/destruction section"),
            ("policy_section.localization", "Policy: localization (152-FZ) statement"),
        ]
        base_bools = [
            base_fz.policy_has_purpose_section,
            base_fz.policy_has_categories_section,
            base_fz.policy_has_legal_basis_section,
            base_fz.policy_has_processor_or_third_party_section,
            base_fz.policy_has_cross_border_section,
            base_fz.policy_has_subject_rights_section,
            base_fz.policy_has_retention_or_destruction_section,
            base_fz.policy_has_localization_statement,
        ]
        cmp_bools = [
            cmp_fz.policy_has_purpose_section,
            cmp_fz.policy_has_categories_section,
            cmp_fz.policy_has_legal_basis_section,
            cmp_fz.policy_has_processor_or_third_party_section,
            cmp_fz.policy_has_cross_border_section,
            cmp_fz.policy_has_subject_rights_section,
            cmp_fz.policy_has_retention_or_destruction_section,
            cmp_fz.policy_has_localization_statement,
        ]
        for (dim, lbl), bv, cv in zip(sections, base_bools, cmp_bools):
            _bool_change(dim, lbl, bv, cv, changed)

        # Gaps as sets
        added_gaps, removed_gaps = _set_diff(
            base_fz.potential_gaps, cmp_fz.potential_gaps
        )
    else:
        added_gaps, removed_gaps = [], []
        if base_fz is None and cmp_fz is not None:
            changed.append(ChangedItem(
                dimension="fz152_assessment",
                label="152-FZ assessment",
                base_value="absent",
                compare_value="present",
                change_type="added",
            ))
        elif base_fz is not None and cmp_fz is None:
            changed.append(ChangedItem(
                dimension="fz152_assessment",
                label="152-FZ assessment",
                base_value="present",
                compare_value="absent",
                change_type="removed",
            ))

    # ------------------------------------------------------------------
    # 5. Site summary scalars
    # ------------------------------------------------------------------
    base_ss = base.site_summary
    cmp_ss = compare.site_summary
    if base_ss is not None and cmp_ss is not None:
        if base_ss.pages_scanned != cmp_ss.pages_scanned:
            changed.append(ChangedItem(
                dimension="pages_scanned",
                label="Pages scanned",
                base_value=str(base_ss.pages_scanned),
                compare_value=str(cmp_ss.pages_scanned),
                change_type="changed",
            ))
        if base_ss.pages_with_forms != cmp_ss.pages_with_forms:
            changed.append(ChangedItem(
                dimension="pages_with_forms",
                label="Pages with forms",
                base_value=str(base_ss.pages_with_forms),
                compare_value=str(cmp_ss.pages_with_forms),
                change_type="changed",
            ))

    # ------------------------------------------------------------------
    # 6. Registration relevance
    # ------------------------------------------------------------------
    _scalar_change(
        "registration_relevance", "Registration relevance",
        base.registration_relevance,
        compare.registration_relevance,
        changed,
    )

    # ------------------------------------------------------------------
    # 7. Build human-readable summary lines
    # ------------------------------------------------------------------
    if not (added_cats or removed_cats or added_vendors or removed_vendors
            or added_procs or removed_procs or added_gaps or removed_gaps
            or changed):
        summary.append("No significant differences detected between the two scans.")
    else:
        if added_cats:
            summary.append(f"New personal data categories: {', '.join(added_cats)}.")
        if removed_cats:
            summary.append(f"Personal data categories no longer detected: {', '.join(removed_cats)}.")
        if added_vendors:
            summary.append(f"New third-party vendors: {', '.join(added_vendors)}.")
        if removed_vendors:
            summary.append(f"Vendors no longer observed: {', '.join(removed_vendors)}.")
        if added_procs:
            summary.append(f"New downstream processors identified: {', '.join(added_procs)}.")
        if removed_procs:
            summary.append(f"Processors no longer identified: {', '.join(removed_procs)}.")
        if added_gaps:
            summary.append(f"New potential compliance gaps: {len(added_gaps)} item(s) added.")
        if removed_gaps:
            summary.append(f"Potential compliance gaps resolved: {len(removed_gaps)} item(s) removed.")
        for item in changed:
            summary.append(
                f"{item.label}: {item.base_value!r} → {item.compare_value!r}."
            )

    return ScanDiffResult(
        base_scan_id=base.scan_id,
        compare_scan_id=compare.scan_id,
        base_url=base.url,
        compare_url=compare.url,
        base_scanned_at=base.completed_at,
        compare_scanned_at=compare.completed_at,
        added_categories=added_cats,
        removed_categories=removed_cats,
        added_vendors=added_vendors,
        removed_vendors=removed_vendors,
        added_processors=added_procs,
        removed_processors=removed_procs,
        added_gaps=added_gaps,
        removed_gaps=removed_gaps,
        changed_items=changed,
        summary_lines=summary,
    )
