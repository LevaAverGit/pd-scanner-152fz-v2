"""
Report export service for the PD Scanner.
Produces JSON and Markdown reports for completed scan results.
"""

import json
import logging
from pathlib import Path

from backend.app.models.schemas import ScanResult
from backend.app.services.vendor_classification_service import vendor_class_description
from backend.app.utils.pd_dictionary import PD_CATEGORIES
from backend.app.utils.patterns import HIGH_RISK_CATEGORIES

logger = logging.getLogger(__name__)

EXPORT_DIR = Path("exports")


def _ensure_export_dir() -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def export_json(result: ScanResult) -> str:
    """
    Write the scan result as formatted JSON to exports/{scan_id}.json.
    Returns the relative file path string.
    """
    _ensure_export_dir()
    file_path = EXPORT_DIR / f"{result.scan_id}.json"
    payload = result.model_dump()
    file_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    logger.info("report_service: JSON export written to %s", file_path)
    return str(file_path)


def export_markdown(result: ScanResult) -> str:
    """
    Write a human-readable Markdown report to exports/{scan_id}.md.
    Returns the relative file path string.
    """
    _ensure_export_dir()
    file_path = EXPORT_DIR / f"{result.scan_id}.md"

    lines: list[str] = []

    lines.append("# PD Scanner Report")
    lines.append("")
    lines.append(f"**Scan ID:** {result.scan_id}")
    lines.append(f"**URL:** {result.url}")
    lines.append(f"**Scan date:** {result.completed_at or result.created_at}")
    lines.append(f"**Status:** {result.status.value}")
    relevance = result.registration_relevance or "unknown"
    lines.append(f"**Seed page type:** {relevance}")
    lines.append("")

    # ---------------------------------------------------------------------------
    # Data categories table
    # ---------------------------------------------------------------------------
    lines.append("## Personal Data Categories Detected")
    lines.append("")
    if result.data_categories:
        lines.append("| Category | Confidence | GDPR Article | Risk | Explanation |")
        lines.append("|----------|------------|--------------|------|-------------|")
        for item in result.data_categories:
            cat_meta = PD_CATEGORIES.get(item.category, {})
            gdpr = cat_meta.get("gdpr_article", "—")
            risk = "HIGH" if item.category in HIGH_RISK_CATEGORIES else "standard"
            conf_pct = f"{int(item.confidence * 100)}%"
            explanation = item.explanation.replace("|", "\\|")
            lines.append(
                f"| {item.category} | {conf_pct} | {gdpr} | {risk} | {explanation} |"
            )
    else:
        lines.append("_No personal data categories detected._")
    lines.append("")

    # ---------------------------------------------------------------------------
    # Summary counts
    # ---------------------------------------------------------------------------
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Data categories found:** {len(result.data_categories)}")
    lines.append(
        "- **High-risk categories:** "
        + str(sum(1 for c in result.data_categories if c.category in HIGH_RISK_CATEGORIES))
    )
    net_obs = result.network_observations or []
    lines.append(f"- **Network requests observed:** {len(net_obs)}")
    third_party = [o for o in net_obs if o.is_third_party]
    lines.append(f"- **Third-party hosts:** {len({o.host for o in third_party})}")
    lines.append("")

    if third_party:
        lines.append("### Third-Party Hosts")
        lines.append("")
        for host in sorted({o.host for o in third_party}):
            lines.append(f"- `{host}`")
        lines.append("")

    if result.screenshot_path:
        lines.append("## Screenshot")
        lines.append("")
        lines.append(f"Saved at: `{result.screenshot_path}`")
        lines.append("")

    # ---------------------------------------------------------------------------
    # Site crawl summary
    # ---------------------------------------------------------------------------
    if result.site_summary:
        s = result.site_summary
        lines.append("## Site Crawl Summary")
        lines.append("")
        lines.append(f"- **Pages scanned:** {s.pages_scanned}")
        lines.append(f"- **Pages with forms:** {s.pages_with_forms}")
        lines.append(f"- **Total forms found:** {s.total_forms_found}")
        lines.append(
            "- **Unique data categories across site:** "
            + (", ".join(s.unique_categories_found) if s.unique_categories_found else "none")
        )
        if s.top_third_party_hosts:
            lines.append(
                "- **Top third-party hosts:** "
                + ", ".join(f"`{h}`" for h in s.top_third_party_hosts)
            )
        # Consent signal counts
        lines.append(f"- **Pages with privacy/policy link:** {s.pages_with_privacy_link}")
        lines.append(f"- **Pages with consent checkbox:** {s.pages_with_consent_checkbox}")
        lines.append(f"- **Pages with marketing consent checkbox:** {s.pages_with_marketing_consent}")
        lines.append("")
        lines.append(
            "> _Consent/privacy signals are heuristic indicators only "
            "and do not constitute a legal compliance assessment._"
        )
        lines.append("")

    # ---------------------------------------------------------------------------
    # Per-page breakdown
    # ---------------------------------------------------------------------------
    if result.visited_pages:
        lines.append("## Pages Visited")
        lines.append("")
        lines.append("| # | URL | Page Type | Forms | Categories | Privacy | Terms | Consent |")
        lines.append("|---|-----|-----------|-------|------------|---------|-------|---------|")
        for i, p in enumerate(result.visited_pages, 1):
            rel = p.registration_relevance or "—"
            cats = (
                ", ".join(c.category for c in p.detected_categories)
                if p.detected_categories
                else "—"
            )
            url_display = p.url.replace("|", "\\|")
            privacy = "yes" if p.has_privacy_link else "—"
            terms = "yes" if p.has_terms_link else "—"
            consent = "yes" if p.has_consent_checkbox else "—"
            lines.append(
                f"| {i} | {url_display} | {rel} | {p.forms_found} "
                f"| {cats} | {privacy} | {terms} | {consent} |"
            )
        lines.append("")

        # Per-page consent signal details (only for pages that have any)
        consent_pages = [p for p in result.visited_pages if p.consent_signals]
        if consent_pages:
            lines.append("### Consent Signal Details")
            lines.append("")
            lines.append(
                "> _Heuristic evidence only. Signals are extracted from visible page "
                "text — no form interaction or page navigation was performed._"
            )
            lines.append("")
            for p in consent_pages:
                lines.append(f"**{p.url}**")
                for sig in p.consent_signals:
                    lines.append(f"- {sig}")
                lines.append("")

        # Interactive Discovery Findings
        interactive_pages = [
            p for p in result.visited_pages
            if p.interactions_performed or p.hidden_forms_revealed > 0
        ]
        if interactive_pages:
            lines.append("### Interactive Discovery Findings")
            lines.append("")
            lines.append(
                "> _CTA-like buttons were clicked to reveal hidden/modal forms. "
                "No forms were submitted and no personal data was entered._"
            )
            lines.append("")
            total_interactions = sum(len(p.interactions_performed) for p in interactive_pages)
            total_hidden = sum(p.hidden_forms_revealed for p in interactive_pages)
            total_modal = sum(p.modal_forms_found for p in interactive_pages)
            lines.append(f"- Pages with interactions performed: {len(interactive_pages)}")
            lines.append(f"- Total interactions: {total_interactions}")
            lines.append(f"- Hidden/dynamic forms revealed: {total_hidden}")
            lines.append(f"- Modal forms found: {total_modal}")
            lines.append("")
            lines.append("| Page | Interactions | Hidden Forms | Modal Forms |")
            lines.append("|------|-------------|--------------|-------------|")
            for p in interactive_pages:
                url_disp = p.url.replace("|", "\\|")
                lines.append(
                    f"| {url_disp} | {len(p.interactions_performed)} "
                    f"| {p.hidden_forms_revealed} | {p.modal_forms_found} |"
                )
            lines.append("")
            # Per-page interaction details
            for p in interactive_pages:
                if p.interactions_performed:
                    lines.append(f"**{p.url}** — interactions:")
                    for act in p.interactions_performed[:5]:
                        lines.append(f"- {act}")
                    if p.dynamic_consent_signals:
                        lines.append("  Dynamic consent signals found after reveal:")
                        for sig in p.dynamic_consent_signals[:3]:
                            lines.append(f"  - {sig}")
                    lines.append("")

        # Bundled consent text summary
        bundled_pages = [p for p in result.visited_pages if p.has_bundled_consent_text]
        if bundled_pages:
            lines.append("### Bundled / Implied Consent Text")
            lines.append("")
            lines.append(
                "> _Pages where consent appears to be implied by form submission rather than "
                "collected via an explicit checkbox:_"
            )
            lines.append("")
            for p in bundled_pages:
                lines.append(f"- {p.url}")
            lines.append("")

        # Per-page submit-target analysis
        submit_pages = [
            p for p in result.visited_pages
            if p.forms_found > 0 and p.submission_evidence
        ]
        if submit_pages:
            lines.append("### Form Submission Analysis")
            lines.append("")
            lines.append(
                "> _Passive DOM inspection only. No forms were submitted._"
            )
            lines.append("")
            for p in submit_pages:
                lines.append(f"**{p.url}**")
                if p.probable_form_platform:
                    lines.append(f"- Form platform: **{p.probable_form_platform}**")
                if p.probable_crm_or_capture_tool:
                    lines.append(f"- CRM / lead capture: **{p.probable_crm_or_capture_tool}**")
                if p.probable_submission_target:
                    lines.append(
                        f"- Probable submit target: `{p.probable_submission_target}` "
                        f"({p.submission_target_type}, {p.submission_method or 'unknown method'})"
                    )
                for ev in p.submission_evidence:
                    lines.append(f"  - {ev}")
                lines.append("")

    # ---------------------------------------------------------------------------
    # Vendor / third-party ecosystem
    # ---------------------------------------------------------------------------
    if result.vendor_summary:
        lines.append("## Vendor / Third-Party Ecosystem")
        lines.append("")
        lines.append(
            "> _Classification is based on hostname pattern matching. "
            "Review each vendor's privacy policy to confirm data handling practices._"
        )
        lines.append("")
        lines.append("| Vendor | Class | Description | First Seen On | Notes |")
        lines.append("|--------|-------|-------------|---------------|-------|")
        for v in result.vendor_summary:
            vendor_name = v.vendor_name or v.host
            desc = vendor_class_description(v.vendor_class)
            first_seen = v.first_seen_on or "—"
            notes_str = "; ".join(v.notes) if v.notes else "—"
            lines.append(
                f"| {vendor_name} (`{v.host}`) | {v.vendor_class} "
                f"| {desc} | {first_seen} | {notes_str} |"
            )
        lines.append("")

        # Highlight high-interest vendors
        _HIGH_INTEREST = {"form_platform", "crm_or_lead_capture", "call_tracking",
                          "advertising", "tag_manager"}
        attention_vendors = [v for v in result.vendor_summary if v.vendor_class in _HIGH_INTEREST]
        if attention_vendors:
            lines.append("### Vendors Requiring Data Flow Review")
            lines.append("")
            lines.append(
                "_These vendor classes are associated with personal data collection "
                "or lead routing and warrant manual verification:_"
            )
            lines.append("")
            for v in attention_vendors:
                label = v.vendor_name or v.host
                lines.append(
                    f"- **{label}** (`{v.host}`) — {vendor_class_description(v.vendor_class)}"
                )
                for n in v.notes:
                    lines.append(f"  - {n}")
            lines.append("")

    # ---------------------------------------------------------------------------
    # Policy / Privacy Page Analysis
    # ---------------------------------------------------------------------------
    if result.policy_analysis:
        pa = result.policy_analysis
        lines.append("## Policy / Privacy Page Analysis")
        lines.append("")
        lines.append(
            "> _Findings are heuristic only. Text analysis does not constitute "
            "a legal compliance assessment._"
        )
        lines.append("")
        lines.append(f"**URL:** {pa.url}")
        # Document type and parse status
        _DOC_TYPE_LABELS = {"html": "HTML page", "pdf": "PDF document", "docx": "DOCX document",
                            "doc": "DOC document (legacy)", "unknown": "Unknown"}
        _PARSE_STATUS_LABELS = {"parsed": "parsed ✓", "unreadable": "unreadable (image-only or protected)",
                                "unsupported": "unsupported format", "failed": "download/parse failed"}
        doc_type_label = _DOC_TYPE_LABELS.get(pa.policy_document_type, pa.policy_document_type)
        parse_status_label = _PARSE_STATUS_LABELS.get(pa.policy_parse_status, pa.policy_parse_status)
        lines.append(f"**Document type:** {doc_type_label}")
        lines.append(f"**Parse status:** {parse_status_label}")
        if pa.operator_name:
            lines.append(f"**Operator (inferred):** {pa.operator_name}")
        if pa.operator_contacts:
            lines.append(f"**Contacts found:** {', '.join(pa.operator_contacts)}")
        lines.append("")
        lines.append("| Section | Present |")
        lines.append("|---------|---------|")
        lines.append(f"| Purpose / goals | {'yes' if pa.has_purpose_section else '—'} |")
        lines.append(f"| Personal data categories | {'yes' if pa.has_categories_section else '—'} |")
        lines.append(f"| Legal basis | {'yes' if pa.has_legal_basis_section else '—'} |")
        lines.append(f"| Third-party processors | {'yes' if pa.has_processor_or_third_party_section else '—'} |")
        lines.append(f"| Cross-border transfers | {'yes' if pa.has_cross_border_section else '—'} |")
        lines.append(f"| Data subject rights | {'yes' if pa.has_subject_rights_section else '—'} |")
        lines.append(f"| Retention / destruction | {'yes' if pa.has_retention_or_destruction_section else '—'} |")
        lines.append(f"| Localization (152-FZ) | {'yes' if pa.has_localization_statement else '—'} |")
        lines.append("")
        if pa.policy_signals:
            lines.append("**Signals:**")
            for sig in pa.policy_signals:
                lines.append(f"- {sig}")
            lines.append("")

    # ---------------------------------------------------------------------------
    # Recommended Manual Follow-up
    # ---------------------------------------------------------------------------
    lines.append("## Recommended Manual Follow-up")
    lines.append("")
    lines.append(
        "> _These findings are based on automated public-site observation. "
        "Manual review is recommended for:_"
    )
    lines.append("")
    lines.append("- Pages with third-party form submission targets")
    lines.append("- Forms where consent relies on bundled / implied text rather than explicit checkboxes")
    lines.append("- Any hidden or modal forms revealed during interactive discovery")
    lines.append("- Policy pages missing key sections (legal basis, retention, subject rights)")
    lines.append("- Cross-border data transfer claims (verify adequate safeguards)")
    lines.append("- High-risk data categories (national ID, financial, health)")
    lines.append("")

    # ---------------------------------------------------------------------------
    # Synthetic Submission Findings
    # ---------------------------------------------------------------------------
    if result.synthetic_submission_enabled:
        lines.append("### Synthetic Submission Findings")
        lines.append("")
        lines.append("> **Warning:** Submissions used clearly synthetic placeholder values only. No real personal data was submitted.")
        lines.append("> Inferred downstream routing still requires manual validation.")
        lines.append("")
        if result.synthetic_submission_summary:
            s = result.synthetic_submission_summary
            lines.append(f"- Pages attempted: {s.pages_attempted}")
            lines.append(f"- Successful submissions: {s.successful_submissions}")
            lines.append(f"- First-party submissions: {s.first_party_submissions}")
            lines.append(f"- Third-party submissions: {s.third_party_submissions}")
            lines.append(f"- Blocked / validation failed: {s.blocked_or_failed}")
            lines.append("")

        submitted = [
            p for p in result.visited_pages
            if p.synthetic_submission_attempted and p.synthetic_submission_status != "not_attempted"
        ]
        if submitted:
            lines.append("#### Observed Submit Endpoints")
            lines.append("")
            lines.append("| Page | Status | Method | URL | Target |")
            lines.append("|------|--------|--------|-----|--------|")
            for p in submitted:
                url_cell = p.observed_submit_url or "—"
                if len(url_cell) > 60:
                    url_cell = url_cell[:57] + "..."
                lines.append(
                    f"| {p.url[:50]} | {p.synthetic_submission_status} "
                    f"| {p.observed_submit_method or '—'} | {url_cell} | {p.observed_submit_target_type} |"
                )
            lines.append("")

        with_followon = [p for p in result.visited_pages if p.observed_follow_on_hosts]
        if with_followon:
            lines.append("#### Follow-on Routing Observations")
            lines.append("")
            for p in with_followon:
                lines.append(f"- {p.url}: follow-on hosts → {', '.join(p.observed_follow_on_hosts)}")
            lines.append("")

        lines.append("#### Recommended Manual Validation")
        lines.append("")
        lines.append("- Verify actual downstream data routing for any third-party submit endpoints")
        lines.append("- Confirm consent / data processing agreements with observed third-party capture tools")
        lines.append("- Review follow-on redirect chains for unexpected data routing")
        lines.append("")
    else:
        lines.append("### Synthetic Submission Findings")
        lines.append("")
        lines.append("> Synthetic submission mode was not enabled for this scan.")
        lines.append("")

    # ---- Downstream Processor Mapping ----
    lines.append("## Downstream Processor Mapping")
    lines.append("")
    lines.append("> _Processor mapping combines observed submit evidence, passive DOM inference, and vendor network signals._")
    lines.append("> **Source key:** `observed_submit` = confirmed by actual network request (synthetic mode); `inferred_public_signal` = heuristic from DOM/scripts/network; `operator_supplied` = operator-provided (not independently verified).")
    lines.append("")

    if result.processor_map:
        lines.append("| Processor | Type | Source | Confidence | Related Hosts |")
        lines.append("|-----------|------|--------|------------|---------------|")
        for pm in result.processor_map:
            name = pm.processor_name or "—"
            hosts = ", ".join(pm.related_hosts[:2]) or "—"
            if len(hosts) > 50:
                hosts = hosts[:47] + "..."
            lines.append(f"| {name} | {pm.processor_type} | {pm.source} | {pm.confidence} | {hosts} |")
        lines.append("")

        # Observed vs Inferred detail
        pages_with_routing = [p for p in result.visited_pages if p.downstream_routing_signals]
        if pages_with_routing:
            lines.append("### Observed vs Inferred Routing")
            lines.append("")
            lines.append("| Page | Observed Submit | Inferred Processor | Confidence |")
            lines.append("|------|-----------------|--------------------|------------|")
            for p in pages_with_routing:
                obs = p.observed_submit_url[:40] + "..." if p.observed_submit_url and len(p.observed_submit_url) > 40 else (p.observed_submit_url or "—")
                inf = p.downstream_processor_name or p.downstream_processor_type or "—"
                page_cell = p.url[:50] + "..." if len(p.url) > 50 else p.url
                lines.append(f"| {page_cell} | {obs} | {inf} | {p.downstream_routing_confidence} |")
            lines.append("")
    else:
        lines.append("_No processor signals detected._")
        lines.append("")

    # Operator-supplied evidence (clearly separate section)
    if result.operator_integration_evidence:
        oe = result.operator_integration_evidence
        lines.append("### Operator-Supplied Integration Evidence")
        lines.append("")
        lines.append("> **Warning:** The following was provided by the operator and has NOT been independently verified by the scanner.")
        lines.append("")
        if oe.source:
            lines.append(f"- Source: {oe.source}")
        if oe.form_platform:
            lines.append(f"- Form platform: {oe.form_platform}")
        if oe.crm_destination:
            lines.append(f"- CRM destination: {oe.crm_destination}")
        if oe.webhook_urls:
            for wh in oe.webhook_urls[:3]:
                try:
                    from urllib.parse import urlparse as _up
                    host = _up(wh).netloc or wh[:40]
                except Exception:
                    host = wh[:40]
                lines.append(f"- Webhook destination host: {host}")
        if oe.notification_targets:
            for nt in oe.notification_targets[:3]:
                lines.append(f"- Notification target: {nt[:60]}")
        if oe.notes:
            for note in oe.notes[:3]:
                lines.append(f"- Note: {note[:120]}")
        lines.append("")

    # Recommended manual validation targets (medium/low confidence)
    uncertain = [pm for pm in result.processor_map if pm.confidence in ("low", "medium") and pm.source != "operator_supplied"]
    if uncertain:
        lines.append("### Recommended Manual Validation Targets")
        lines.append("")
        lines.append("The following downstream processors were inferred but not directly observed and should be manually verified:")
        lines.append("")
        for pm in uncertain[:5]:
            name = pm.processor_name or pm.processor_type
            lines.append(f"- {name} (confidence: {pm.confidence}) — {pm.evidence[0][:100] if pm.evidence else 'no evidence'}")
        lines.append("")

    # ---- 152-FZ Evidence Summary ----
    fz = result.fz152_assessment
    if fz:
        lines.append("## 152-FZ Public Evidence Summary")
        lines.append("")
        lines.append(
            "> **Disclaimer:** This summary is based solely on publicly observable site behavior "
            "and heuristic analysis. It does **not** constitute legal advice or a definitive "
            "compliance determination under 152-FZ. All findings require manual validation."
        )
        lines.append("")

        # Risk level
        risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(fz.overall_public_risk_level, "⚪")
        lines.append(f"**Overall public-signal risk level:** {risk_emoji} {fz.overall_public_risk_level.upper()}")
        lines.append("")

        # Operator / policy presence
        lines.append("### Operator & Policy Public Presence")
        lines.append("")
        if fz.operator_name:
            lines.append(f"- **Operator (inferred):** {fz.operator_name}")
        if fz.operator_contacts:
            lines.append(f"- **Contacts found:** {', '.join(fz.operator_contacts[:3])}")
        lines.append(f"- **Policy publicly available:** {'Yes' if fz.policy_publicly_available else 'Not detected'}")
        lines.append(f"- **Privacy links found:** {fz.privacy_links_found}")
        lines.append("")

        # Data collection scope
        lines.append("### Data Collection Scope")
        lines.append("")
        lines.append(f"- Forms collecting personal data: {fz.forms_collecting_pd}")
        if fz.detected_pd_categories:
            lines.append(f"- Detected PD categories: {', '.join(fz.detected_pd_categories)}")
        lines.append(f"- Consent mechanism type: **{fz.consent_mechanism_type}**")
        lines.append("")

        # Policy coverage table
        lines.append("### Policy Section Coverage")
        lines.append("")
        lines.append("| Section | Publicly Evidenced |")
        lines.append("|---------|-------------------|")
        sections = [
            ("Purpose / processing goals", fz.policy_has_purpose_section),
            ("Personal data categories", fz.policy_has_categories_section),
            ("Legal basis", fz.policy_has_legal_basis_section),
            ("Third-party / processor disclosure", fz.policy_has_processor_or_third_party_section),
            ("Cross-border transfers", fz.policy_has_cross_border_section),
            ("Data subject rights", fz.policy_has_subject_rights_section),
            ("Retention / destruction", fz.policy_has_retention_or_destruction_section),
            ("Localization (Art. 18.1)", fz.policy_has_localization_statement),
        ]
        for label, val in sections:
            lines.append(f"| {label} | {'✓' if val else '—'} |")
        lines.append("")

        # Processing / routing scope
        lines.append("### Processing & Routing Scope")
        lines.append("")
        lines.append(f"- Third-party routing signals present: {'Yes' if fz.third_party_routing_present else 'Not detected'}")
        lines.append(f"- Observed form submission (synthetic mode): {'Yes' if fz.observed_submit_present else 'No / not enabled'}")
        lines.append(f"- Processor map entries present: {'Yes' if fz.processor_map_present else 'No'}")
        lines.append(f"- Metrics/tracking signals: {'Yes' if fz.metrics_or_tracking_present else 'Not detected'}")
        lines.append(f"- Operator-supplied evidence: {'Yes' if fz.operator_supplied_evidence_present else 'None'}")
        lines.append("")

        # Potential gaps
        if fz.potential_gaps:
            lines.append("### Potential Public-Signal Gaps")
            lines.append("")
            lines.append(
                "> _These are potential gaps identified from public signals only. "
                "They do not constitute confirmed violations._"
            )
            lines.append("")
            for gap in fz.potential_gaps:
                lines.append(f"- {gap}")
            lines.append("")

        # Manual validation checklist
        if fz.manual_validation_targets:
            lines.append("### Manual Validation Checklist")
            lines.append("")
            for target in fz.manual_validation_targets:
                lines.append(f"- [ ] {target}")
            lines.append("")

    # Operator metadata (if present)
    if result.operator_metadata:
        om = result.operator_metadata
        lines.append("### Operator-Supplied Metadata")
        lines.append("")
        lines.append(
            "> **Note:** The following was supplied by the operator and has NOT been verified by the scanner."
        )
        lines.append("")
        if om.legal_name:
            lines.append(f"- Legal name: {om.legal_name}")
        if om.inn:
            lines.append(f"- INN: {om.inn}")
        if om.ogrn:
            lines.append(f"- OGRN: {om.ogrn}")
        for note in om.notes[:3]:
            lines.append(f"- Note: {note[:120]}")
        lines.append("")

    if result.error:
        lines.append("## Error")
        lines.append("")
        lines.append(f"```\n{result.error}\n```")
        lines.append("")

    content = "\n".join(lines)
    file_path.write_text(content, encoding="utf-8")
    logger.info("report_service: Markdown export written to %s", file_path)
    return str(file_path)
