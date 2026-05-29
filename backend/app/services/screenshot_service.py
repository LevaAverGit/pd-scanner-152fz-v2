"""
Screenshot capture service for the PD Scanner.
Saves full-page PNG screenshots to the screenshots/ directory.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

SCREENSHOT_DIR = Path("screenshots")


async def capture_screenshot(page, scan_id: str) -> str:
    """
    Save a full-page PNG screenshot to screenshots/{scan_id}.png.
    Creates the screenshots/ directory if it does not exist.

    Returns the relative file path as a string on success.
    On any failure, logs a warning and returns an empty string.
    """
    try:
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        file_path = SCREENSHOT_DIR / f"{scan_id}.png"
        await page.screenshot(path=str(file_path), full_page=True)
        logger.info("screenshot_service: saved %s", file_path)
        return str(file_path)
    except Exception as exc:
        logger.warning("screenshot_service: failed to capture screenshot: %s", exc)
        return ""
