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
        # Table may not exist yet — create it
        try:
            if hasattr(db, "_get_conn"):
                db._get_conn().execute("CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL DEFAULT '{}')")
                db._get_conn().commit()
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


@router.get("/api/settings/status")
async def get_settings_status():
    import os
    gh_token = os.getenv("GITHUB_TOKEN", "")
    gh_fg_token = os.getenv("GITHUB_FG_TOKEN", "")
    return {
        "github_token": {"status": "active" if gh_token else "missing"},
        "github_fg_token": {"status": "active" if gh_fg_token else "missing"},
    }
