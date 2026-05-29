import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .database import init_db
from .policy_generator import generate_all
from .routes.public import router as public_router
from .routes.forms import router as forms_router
from .routes.admin import router as admin_router
from .routes.mock_services import router as mock_router
from .routes.api import router as api_router

BASE_DIR = Path(__file__).parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB and generate policy files on startup
    await init_db()
    generate_all()
    yield


app = FastAPI(title="Enterprise Demo Lab", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

app.include_router(public_router)
app.include_router(forms_router)
app.include_router(admin_router, prefix="/admin")
app.include_router(mock_router, prefix="/mock")
app.include_router(api_router, prefix="/api")
