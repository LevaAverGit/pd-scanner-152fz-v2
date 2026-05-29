from fastapi import APIRouter, HTTPException

from backend.app.core.config import settings
from backend.app.models.schemas import HistoryResponse
from backend.app.services.storage_service import (
    delete_scan as storage_delete_scan,
    list_scans as storage_list_scans,
)

router = APIRouter(tags=["history"])


@router.get("/history", response_model=HistoryResponse)
async def get_history(limit: int = 50, offset: int = 0) -> HistoryResponse:
    return await storage_list_scans(
        db_path=settings.db_path, limit=limit, offset=offset
    )


@router.delete("/history/{scan_id}")
async def delete_history_item(scan_id: str) -> dict:
    deleted = await storage_delete_scan(db_path=settings.db_path, scan_id=scan_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Scan '{scan_id}' not found.")
    return {"deleted": scan_id}
