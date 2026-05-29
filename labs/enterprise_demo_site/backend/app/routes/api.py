from fastapi import APIRouter
from fastapi.responses import JSONResponse
from ..profile import get_profile, set_profile

router = APIRouter()


@router.get("/profile")
async def get_profile_endpoint():
    return JSONResponse({"profile": get_profile()})


@router.post("/profile/{profile_name}")
async def set_profile_endpoint(profile_name: str):
    try:
        set_profile(profile_name)
        return JSONResponse({"profile": profile_name, "status": "ok"})
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.get("/status")
async def status():
    return JSONResponse({"status": "ok", "lab": "enterprise_demo_site", "profile": get_profile()})
