import os
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import aiosqlite
from ..database import DB_PATH

router = APIRouter()
BASE_DIR = Path(__file__).parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

ADMIN_PASSWORD = os.environ.get("LAB_ADMIN_PASSWORD", "demo-lab-only")
SESSION_COOKIE = "lab_admin_session"
SESSION_VALUE = "authenticated"


def is_authenticated(request: Request) -> bool:
    return request.cookies.get(SESSION_COOKIE) == SESSION_VALUE


@router.get("/login")
async def admin_login_get(request: Request):
    return templates.TemplateResponse(request, "admin/login.html", {"error": None})


@router.post("/login")
async def admin_login_post(request: Request, password: str = Form("")):
    if password == ADMIN_PASSWORD:
        response = RedirectResponse(url="/admin/submissions", status_code=302)
        response.set_cookie(SESSION_COOKIE, SESSION_VALUE, httponly=True, samesite="lax")
        return response
    return templates.TemplateResponse(request, "admin/login.html", {"error": "Invalid password"})


@router.get("/logout")
async def admin_logout():
    response = RedirectResponse(url="/admin/login", status_code=302)
    response.delete_cookie(SESSION_COOKIE)
    return response


@router.get("/submissions")
async def admin_submissions(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login")
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM submissions ORDER BY created_at DESC LIMIT 100")
        rows = [dict(r) for r in await cursor.fetchall()]
    return templates.TemplateResponse(request, "admin/submissions.html", {"rows": rows})


@router.get("/routing-log")
async def admin_routing_log(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login")
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM routing_events ORDER BY created_at DESC LIMIT 100")
        rows = [dict(r) for r in await cursor.fetchall()]
    return templates.TemplateResponse(request, "admin/routing_log.html", {"rows": rows})


@router.get("/consent-log")
async def admin_consent_log(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login")
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM consent_events ORDER BY created_at DESC LIMIT 100")
        rows = [dict(r) for r in await cursor.fetchall()]
    return templates.TemplateResponse(request, "admin/consent_log.html", {"rows": rows})


@router.get("/processors")
async def admin_processors(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login")
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM processor_events ORDER BY created_at DESC LIMIT 100")
        rows = [dict(r) for r in await cursor.fetchall()]
    return templates.TemplateResponse(request, "admin/processors.html", {"rows": rows})
