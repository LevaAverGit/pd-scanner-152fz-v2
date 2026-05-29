import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException

from backend.app.core.config import settings
from backend.app.models.schemas import ScanDiffRequest, ScanDiffResult, ScanRequest, ScanResult, ScanStatus
from backend.app.services.scan_diff_service import compute_scan_diff
from backend.app.services.scanner_service import run_scan
from backend.app.services.storage_service import (
    create_scan as storage_create_scan,
    get_scan as storage_get_scan,
)
from backend.app.services.url_validation import URLValidationError, validate_url

router = APIRouter(tags=["scan"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.post("/scan", response_model=ScanResult)
async def create_scan(body: ScanRequest, background_tasks: BackgroundTasks) -> ScanResult:
    url_str = str(body.url)

    # Validate URL safety before creating the DB record
    try:
        validate_url(url_str, allow_local=settings.allow_local_test_targets)
    except URLValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    scan_id = str(uuid.uuid4())
    result = await storage_create_scan(
        db_path=settings.db_path,
        scan_id=scan_id,
        url=url_str,
        notes=body.notes,
    )

    # Enqueue scan pipeline as a background task
    background_tasks.add_task(
        run_scan, scan_id, url_str, settings.db_path,
        body.enable_synthetic_submission, body.integration_evidence,
        body.operator_metadata
    )

    return result


@router.get("/scan/{scan_id}", response_model=ScanResult)
async def get_scan(scan_id: str) -> ScanResult:
    result = await storage_get_scan(db_path=settings.db_path, scan_id=scan_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Scan '{scan_id}' not found.")
    return result


@router.post("/scan/diff", response_model=ScanDiffResult)
async def diff_scans(body: ScanDiffRequest) -> ScanDiffResult:
    """Compare two completed scans and return a structured diff."""
    base = await storage_get_scan(db_path=settings.db_path, scan_id=body.base_scan_id)
    if base is None:
        raise HTTPException(status_code=404, detail=f"Base scan '{body.base_scan_id}' not found.")
    compare = await storage_get_scan(db_path=settings.db_path, scan_id=body.compare_scan_id)
    if compare is None:
        raise HTTPException(status_code=404, detail=f"Compare scan '{body.compare_scan_id}' not found.")
    if base.status != ScanStatus.complete:
        raise HTTPException(status_code=422, detail=f"Base scan '{body.base_scan_id}' is not complete.")
    if compare.status != ScanStatus.complete:
        raise HTTPException(status_code=422, detail=f"Compare scan '{body.compare_scan_id}' is not complete.")
    return compute_scan_diff(base, compare)
