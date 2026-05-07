from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from db import db

router = APIRouter()

_SETTINGS_KEY = "summarizer_config"


class SummarizerConfig(BaseModel):
    mode: str = "free"
    provider: str = ""
    model: str = ""
    limit: int = 10


@router.get("/api/settings/summarizer")
async def get_summarizer_settings():
    try:
        rows = await db.select("app_settings", filters={"key": _SETTINGS_KEY})
        if rows:
            import json
            return json.loads(rows[0].get("value", "{}"))
    except Exception:
        pass
    return {"mode": "free", "provider": "", "model": "", "limit": 10}


@router.post("/api/settings/summarizer")
async def save_summarizer_settings(body: SummarizerConfig):
    import json
    value = json.dumps(body.model_dump())
    try:
        existing = await db.select("app_settings", filters={"key": _SETTINGS_KEY})
        if existing:
            await db.update("app_settings", {"value": value}, {"key": _SETTINGS_KEY})
        else:
            await db.insert("app_settings", {"key": _SETTINGS_KEY, "value": value})
    except Exception:
        pass
    return {"ok": True}
