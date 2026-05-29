from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from ..profile import get_profile
from .. import policy_generator as _pg

router = APIRouter()
BASE_DIR = Path(__file__).parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _policy_dir() -> Path:
    """Return POLICY_DIR from the policy_generator module (supports test patching)."""
    return _pg.POLICY_DIR


def ctx(request: Request, **kwargs) -> dict:
    profile = get_profile()
    return {"profile": profile, **kwargs}


@router.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html", ctx(request))

@router.get("/about")
async def about(request: Request):
    return templates.TemplateResponse(request, "about.html", ctx(request))

@router.get("/services")
async def services(request: Request):
    return templates.TemplateResponse(request, "services.html", ctx(request))

@router.get("/pricing")
async def pricing(request: Request):
    return templates.TemplateResponse(request, "pricing.html", ctx(request))

@router.get("/request-demo")
async def request_demo(request: Request):
    return templates.TemplateResponse(request, "request_demo.html", ctx(request))

@router.get("/contact")
async def contact(request: Request):
    return templates.TemplateResponse(request, "contact.html", ctx(request))

@router.get("/webinar")
async def webinar(request: Request):
    return templates.TemplateResponse(request, "webinar.html", ctx(request))

@router.get("/careers")
async def careers(request: Request):
    return templates.TemplateResponse(request, "careers.html", ctx(request))

@router.get("/privacy")
async def privacy(request: Request):
    return templates.TemplateResponse(request, "privacy.html", ctx(request))

@router.get("/terms")
async def terms(request: Request):
    return templates.TemplateResponse(request, "terms.html", ctx(request))

@router.get("/cookies")
async def cookies(request: Request):
    return templates.TemplateResponse(request, "cookies.html", ctx(request))

@router.get("/privacy.pdf")
async def privacy_pdf():
    pdf_path = _policy_dir() / "privacy_policy.pdf"
    return FileResponse(str(pdf_path), media_type="application/pdf", filename="privacy_policy.pdf")

@router.get("/privacy.docx")
async def privacy_docx():
    docx_path = _policy_dir() / "privacy_policy.docx"
    return FileResponse(
        str(docx_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="privacy_policy.docx"
    )
