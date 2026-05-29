import json
import os
from pathlib import Path

PROFILE_FILE = Path(__file__).parent.parent / "data" / "profile.json"
VALID_PROFILES = {"good_compliance", "mixed_compliance", "bad_compliance"}

def get_profile() -> str:
    if PROFILE_FILE.exists():
        try:
            data = json.loads(PROFILE_FILE.read_text())
            p = data.get("profile", "mixed_compliance")
            return p if p in VALID_PROFILES else "mixed_compliance"
        except Exception:
            pass
    return "mixed_compliance"

def set_profile(profile: str) -> None:
    if profile not in VALID_PROFILES:
        raise ValueError(f"Unknown profile: {profile}")
    PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_FILE.write_text(json.dumps({"profile": profile}))
