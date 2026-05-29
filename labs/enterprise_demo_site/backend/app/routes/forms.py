import json
from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import Optional
import aiosqlite
from ..database import DB_PATH
from ..profile import get_profile

router = APIRouter()
BASE_DIR = Path(__file__).parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


async def _store_submission(form_type: str, name: str, email: str, phone: str,
                             company: str, message: str, source_page: str,
                             consent_type: str, privacy_link_present: bool,
                             profile: str) -> int:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        cursor = await db.execute(
            """INSERT INTO submissions
               (form_type, name, email, phone, company, message, source_page,
                consent_type, privacy_link_present, profile_mode)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (form_type, name, email, phone, company, message, source_page,
             consent_type, 1 if privacy_link_present else 0, profile)
        )
        sub_id = cursor.lastrowid
        await db.commit()
    return sub_id


async def _route_submission(sub_id: int, profile: str):
    """Route submission based on profile mode and record events."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        # Always: first-party internal route
        await db.execute(
            "INSERT INTO routing_events (submission_id, route_type, destination, status) VALUES (?, ?, ?, ?)",
            (sub_id, "first_party", "internal_db", "stored")
        )
        await db.execute(
            "INSERT INTO processor_events (submission_id, processor_name, processor_type, evidence) VALUES (?, ?, ?, ?)",
            (sub_id, "InternalDB", "storage", "direct_db_write")
        )

        if profile == "mixed_compliance":
            # Also route to webhook mock
            await db.execute(
                "INSERT INTO routing_events (submission_id, route_type, destination, status) VALUES (?, ?, ?, ?)",
                (sub_id, "webhook", "http://localhost:8001/webhook/mock", "dispatched")
            )
            await db.execute(
                "INSERT INTO processor_events (submission_id, processor_name, processor_type, evidence) VALUES (?, ?, ?, ?)",
                (sub_id, "WebhookReceiver", "notification", "webhook_post_observed")
            )

        elif profile == "bad_compliance":
            # Route to CRM mock (third-party simulation)
            await db.execute(
                "INSERT INTO routing_events (submission_id, route_type, destination, status) VALUES (?, ?, ?, ?)",
                (sub_id, "third_party_crm", "http://localhost:8001/crm/mock", "dispatched")
            )
            await db.execute(
                "INSERT INTO processor_events (submission_id, processor_name, processor_type, evidence) VALUES (?, ?, ?, ?)",
                (sub_id, "MockCRM", "crm", "crm_api_post_observed")
            )

        await db.commit()


async def _record_consent(sub_id: int, consent_type: str, text_snapshot: str, checkbox_present: bool):
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            "INSERT INTO consent_events (submission_id, consent_type, text_snapshot, checkbox_present) VALUES (?, ?, ?, ?)",
            (sub_id, consent_type, text_snapshot, 1 if checkbox_present else 0)
        )
        await db.commit()


@router.post("/submit")
async def submit_form(
    request: Request,
    name: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    company: str = Form(""),
    message: str = Form(""),
    consent: Optional[str] = Form(None),
    form_type: str = Form("contact"),
    source_page: str = Form("/contact"),
):
    profile = get_profile()

    # Determine consent type based on profile
    if profile == "good_compliance":
        consent_type = "explicit_checkbox" if consent else "absent"
        checkbox_present = True
        text_snapshot = "Я согласен с обработкой персональных данных в соответствии с Политикой конфиденциальности."
    elif profile == "mixed_compliance":
        consent_type = "bundled_text"
        checkbox_present = False
        text_snapshot = "Отправляя форму, вы соглашаетесь с Политикой конфиденциальности."
    else:  # bad_compliance
        consent_type = "absent"
        checkbox_present = False
        text_snapshot = ""

    privacy_link = profile != "bad_compliance"

    sub_id = await _store_submission(
        form_type=form_type, name=name, email=email, phone=phone,
        company=company, message=message, source_page=source_page,
        consent_type=consent_type, privacy_link_present=privacy_link,
        profile=profile
    )
    await _route_submission(sub_id, profile)
    await _record_consent(sub_id, consent_type, text_snapshot, checkbox_present)

    return templates.TemplateResponse(request, "_thank_you.html", {"profile": profile})


@router.post("/api/lead")
async def api_lead(request: Request):
    """API-style lead capture endpoint (JSON)."""
    profile = get_profile()
    body = await request.json()

    sub_id = await _store_submission(
        form_type="api_lead",
        name=body.get("name", ""),
        email=body.get("email", ""),
        phone=body.get("phone", ""),
        company=body.get("company", ""),
        message=body.get("message", ""),
        source_page=body.get("source_page", "/api/lead"),
        consent_type="api_implicit",
        privacy_link_present=True,
        profile=profile
    )
    await _route_submission(sub_id, profile)
    return JSONResponse({"status": "ok", "submission_id": sub_id})


@router.post("/webhook/mock")
async def webhook_mock(request: Request):
    """Mock webhook receiver — simulates notification dispatch."""
    body = await request.body()
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            "INSERT INTO audit_events (event_type, page, details) VALUES (?, ?, ?)",
            ("webhook_received", "/webhook/mock", body.decode(errors="replace")[:500])
        )
        await db.commit()
    return JSONResponse({"status": "received"})


@router.post("/crm/mock")
async def crm_mock(request: Request):
    """Mock CRM endpoint — simulates third-party CRM lead ingestion."""
    body = await request.body()
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            "INSERT INTO audit_events (event_type, page, details) VALUES (?, ?, ?)",
            ("crm_ingestion", "/crm/mock", body.decode(errors="replace")[:500])
        )
        await db.commit()
    return JSONResponse({"status": "lead_created", "crm": "MockCRM"})
