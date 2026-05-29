import json
import uuid
from datetime import datetime, timezone

from backend.app.models.db import get_db
from backend.app.models.schemas import (
    DataCategoryItem,
    FZ152Assessment,
    HistoryItem,
    HistoryResponse,
    NetworkObservation,
    OperatorIntegrationEvidence,
    OperatorMetadata,
    PolicyAnalysis,
    ProcessorMapItem,
    ScanResult,
    ScanStatus,
    SiteSummary,
    SyntheticSubmissionSummary,
    VendorSummaryItem,
    VisitedPageItem,
)


def _safe_col(row, key):
    """Return row[key] falling back to None if the column doesn't exist."""
    try:
        return row[key]
    except (IndexError, KeyError):
        return None


def _row_to_scan_result(row) -> ScanResult:
    # Deserialize data_categories
    raw_cats = _safe_col(row, "data_categories")
    categories = [DataCategoryItem(**item) for item in json.loads(raw_cats)] if raw_cats else []

    # Deserialize network_observations
    raw_net = _safe_col(row, "network_observations")
    observations = [NetworkObservation(**item) for item in json.loads(raw_net)] if raw_net else []

    # Deserialize visited_pages
    raw_pages = _safe_col(row, "visited_pages")
    if raw_pages:
        visited_pages = [VisitedPageItem(**p) for p in json.loads(raw_pages)]
    else:
        visited_pages = []

    # Deserialize site_summary
    raw_summary = _safe_col(row, "site_summary")
    site_summary = SiteSummary(**json.loads(raw_summary)) if raw_summary else None

    # Deserialize vendor_summary
    raw_vendor = _safe_col(row, "vendor_summary")
    vendor_summary = [VendorSummaryItem(**item) for item in json.loads(raw_vendor)] if raw_vendor else []

    # Deserialize policy_analysis
    raw_policy = _safe_col(row, "policy_analysis")
    policy_analysis = PolicyAnalysis(**json.loads(raw_policy)) if raw_policy else None

    # Deserialize synthetic submission fields
    raw_synth_enabled = _safe_col(row, "synthetic_submission_enabled")
    synthetic_submission_enabled = bool(raw_synth_enabled) if raw_synth_enabled is not None else False
    raw_synth_summary = _safe_col(row, "synthetic_submission_summary")
    synthetic_submission_summary = (
        SyntheticSubmissionSummary(**json.loads(raw_synth_summary)) if raw_synth_summary else None
    )

    # Deserialize downstream routing fields
    raw_op_evidence = _safe_col(row, "operator_integration_evidence")
    operator_integration_evidence = (
        OperatorIntegrationEvidence(**json.loads(raw_op_evidence)) if raw_op_evidence else None
    )
    raw_proc_map = _safe_col(row, "processor_map")
    processor_map = (
        [ProcessorMapItem(**item) for item in json.loads(raw_proc_map)] if raw_proc_map else []
    )

    # Deserialize 152-FZ assessment fields
    raw_fz = _safe_col(row, "fz152_assessment")
    fz152_assessment = FZ152Assessment(**json.loads(raw_fz)) if raw_fz else None

    raw_om = _safe_col(row, "operator_metadata")
    operator_metadata = OperatorMetadata(**json.loads(raw_om)) if raw_om else None

    return ScanResult(
        scan_id=row["scan_id"],
        url=row["url"],
        status=ScanStatus(row["status"]),
        data_categories=categories,
        created_at=row["created_at"],
        completed_at=row["completed_at"],
        error=row["error"],
        network_observations=observations,
        screenshot_path=_safe_col(row, "screenshot_path"),
        registration_relevance=_safe_col(row, "registration_relevance"),
        raw_json_export_path=_safe_col(row, "raw_json_export_path"),
        markdown_export_path=_safe_col(row, "markdown_export_path"),
        visited_pages=visited_pages,
        site_summary=site_summary,
        vendor_summary=vendor_summary,
        policy_analysis=policy_analysis,
        synthetic_submission_enabled=synthetic_submission_enabled,
        synthetic_submission_summary=synthetic_submission_summary,
        operator_integration_evidence=operator_integration_evidence,
        processor_map=processor_map,
        fz152_assessment=fz152_assessment,
        operator_metadata=operator_metadata,
    )


async def create_scan(
    db_path: str, scan_id: str, url: str, notes: str | None
) -> ScanResult:
    now = datetime.now(timezone.utc).isoformat()
    async with get_db(db_path) as db:
        await db.execute(
            """
            INSERT INTO scans (scan_id, url, status, notes, data_categories, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (scan_id, url, ScanStatus.pending.value, notes, json.dumps([]), now),
        )
        await db.commit()
        async with db.execute(
            "SELECT * FROM scans WHERE scan_id = ?", (scan_id,)
        ) as cursor:
            row = await cursor.fetchone()
    return _row_to_scan_result(row)


async def get_scan(db_path: str, scan_id: str) -> ScanResult | None:
    async with get_db(db_path) as db:
        async with db.execute(
            "SELECT * FROM scans WHERE scan_id = ?", (scan_id,)
        ) as cursor:
            row = await cursor.fetchone()
    if row is None:
        return None
    return _row_to_scan_result(row)


async def list_scans(
    db_path: str, limit: int = 50, offset: int = 0
) -> HistoryResponse:
    async with get_db(db_path) as db:
        async with db.execute("SELECT COUNT(*) FROM scans") as cursor:
            count_row = await cursor.fetchone()
        total = count_row[0]
        async with db.execute(
            "SELECT * FROM scans ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ) as cursor:
            rows = await cursor.fetchall()
    items = [
        HistoryItem(
            scan_id=row["scan_id"],
            url=row["url"],
            status=ScanStatus(row["status"]),
            created_at=row["created_at"],
        )
        for row in rows
    ]
    return HistoryResponse(items=items, total=total)


async def delete_scan(db_path: str, scan_id: str) -> bool:
    async with get_db(db_path) as db:
        cursor = await db.execute(
            "DELETE FROM scans WHERE scan_id = ?", (scan_id,)
        )
        await db.commit()
        return cursor.rowcount > 0


async def update_scan_result(
    db_path: str,
    scan_id: str,
    status: ScanStatus,
    data_categories: list[DataCategoryItem] | None = None,
    network_observations: list[NetworkObservation] | None = None,
    screenshot_path: str | None = None,
    registration_relevance: str | None = None,
    completed_at: str | None = None,
    error: str | None = None,
    raw_json_export_path: str | None = None,
    markdown_export_path: str | None = None,
    visited_pages: list[VisitedPageItem] | None = None,
    site_summary: SiteSummary | None = None,
    vendor_summary: list[VendorSummaryItem] | None = None,
    policy_analysis: PolicyAnalysis | None = None,
    synthetic_submission_enabled: bool | None = None,
    synthetic_submission_summary: SyntheticSubmissionSummary | None = None,
    operator_integration_evidence: OperatorIntegrationEvidence | None = None,
    processor_map: list[ProcessorMapItem] | None = None,
    fz152_assessment: FZ152Assessment | None = None,
    operator_metadata: OperatorMetadata | None = None,
) -> None:
    """Update a scan row with the provided non-None fields (JSON-serialised blobs)."""
    col_updates: list[str] = ["status = ?"]
    params: list = [status.value]

    if data_categories is not None:
        col_updates.append("data_categories = ?")
        params.append(json.dumps([item.model_dump() for item in data_categories]))

    if network_observations is not None:
        col_updates.append("network_observations = ?")
        params.append(json.dumps([obs.model_dump() for obs in network_observations]))

    if screenshot_path is not None:
        col_updates.append("screenshot_path = ?")
        params.append(screenshot_path)

    if registration_relevance is not None:
        col_updates.append("registration_relevance = ?")
        params.append(registration_relevance)

    if completed_at is not None:
        col_updates.append("completed_at = ?")
        params.append(completed_at)

    if error is not None:
        col_updates.append("error = ?")
        params.append(error)

    if raw_json_export_path is not None:
        col_updates.append("raw_json_export_path = ?")
        params.append(raw_json_export_path)

    if markdown_export_path is not None:
        col_updates.append("markdown_export_path = ?")
        params.append(markdown_export_path)

    if visited_pages is not None:
        col_updates.append("visited_pages = ?")
        params.append(json.dumps([p.model_dump() for p in visited_pages]))

    if site_summary is not None:
        col_updates.append("site_summary = ?")
        params.append(json.dumps(site_summary.model_dump()))

    if vendor_summary is not None:
        col_updates.append("vendor_summary = ?")
        params.append(json.dumps([v.model_dump() for v in vendor_summary]))

    if policy_analysis is not None:
        col_updates.append("policy_analysis = ?")
        params.append(json.dumps(policy_analysis.model_dump()))

    if synthetic_submission_enabled is not None:
        col_updates.append("synthetic_submission_enabled = ?")
        params.append(1 if synthetic_submission_enabled else 0)

    if synthetic_submission_summary is not None:
        col_updates.append("synthetic_submission_summary = ?")
        params.append(json.dumps(synthetic_submission_summary.model_dump()))

    if operator_integration_evidence is not None:
        col_updates.append("operator_integration_evidence = ?")
        params.append(json.dumps(operator_integration_evidence.model_dump()))

    if processor_map is not None:
        col_updates.append("processor_map = ?")
        params.append(json.dumps([item.model_dump() for item in processor_map]))

    if fz152_assessment is not None:
        col_updates.append("fz152_assessment = ?")
        params.append(json.dumps(fz152_assessment.model_dump()))

    if operator_metadata is not None:
        col_updates.append("operator_metadata = ?")
        params.append(json.dumps(operator_metadata.model_dump()))

    params.append(scan_id)
    sql = f"UPDATE scans SET {', '.join(col_updates)} WHERE scan_id = ?"

    async with get_db(db_path) as db:
        await db.execute(sql, params)
        await db.commit()
