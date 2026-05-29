import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.core.config import settings
from backend.app.core.logging import setup_logging
from backend.app.models.db import init_db
from backend.app.api.routes_scan import router as scan_router
from backend.app.api.routes_history import router as history_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()
    logger.info("Starting up %s", settings.app_name)
    await init_db(settings.db_path)
    yield
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)

app.include_router(scan_router, prefix="/api")
app.include_router(history_router, prefix="/api")

# Serve scanner output directories as static files so the frontend can
# proxy /screenshots/* and /exports/* through Vite to these mounts.
for _dir, _mount in [("screenshots", "/screenshots"), ("exports", "/exports")]:
    _path = Path(_dir)
    _path.mkdir(exist_ok=True)
    app.mount(_mount, StaticFiles(directory=str(_path)), name=_dir)
