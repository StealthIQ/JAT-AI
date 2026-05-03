from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from config import load_settings

router = APIRouter()
settings = load_settings()


@router.get("/api/settings")
async def get_settings():
    config_path = Path("config.json")
    db_mode = "local"
    if config_path.exists():
        try:
            raw = json.loads(config_path.read_text())
            db_mode = raw.get("database", {}).get("mode", "local")
        except Exception:
            pass
    return {
        "github_token": settings.github_token[:4] + "..." if settings.github_token else "",
        "github_fg_token": settings.github_fg_token[:12] + "..." if hasattr(settings, "github_fg_token") and settings.github_fg_token else "",
        "supabase_url": settings.supabase_url,
        "supabase_key": settings.supabase_key[:8] + "..." if settings.supabase_key else "",
        "encryption_key_status": "configured" if settings.encryption_key else "",
        "database_mode": db_mode,
    }


class SettingsUpdate(BaseModel):
    github_token: str = ""
    github_fg_token: str = ""
    supabase_url: str = ""
    supabase_key: str = ""
    database_mode: str = "local"


@router.put("/api/settings")
async def put_settings(body: SettingsUpdate):
    config_path = Path("config.json")
    config = {}
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text())
        except Exception:
            pass

    config["database"] = {"mode": body.database_mode, "local_path": "./data/jat.db", "sync_interval": 30}

    env_path = Path(".env")
    lines = env_path.read_text().splitlines() if env_path.exists() else []
    env_map = {}
    for line in lines:
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env_map[k.strip()] = v.strip()

    # Only overwrite keys when the user provides a real value (not masked)
    if body.github_token and not body.github_token.endswith("..."):
        env_map["GITHUB_TOKEN"] = body.github_token
    if body.github_fg_token and not body.github_fg_token.endswith("..."):
        env_map["GITHUB_FG_TOKEN"] = body.github_fg_token
    if body.supabase_url:
        env_map["SUPABASE_URL"] = body.supabase_url
    if body.supabase_key and not body.supabase_key.endswith("..."):
        env_map["SUPABASE_KEY"] = body.supabase_key

    # Auto-generate encryption key on first save if not present
    if "ENCRYPTION_KEY" not in env_map or not env_map["ENCRYPTION_KEY"]:
        from cryptography.fernet import Fernet
        env_map["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

    env_path.write_text("\n".join(f"{k}={v}" for k, v in env_map.items()) + "\n")
    config_path.write_text(json.dumps(config, indent=2))

    return {"ok": True}


@router.post("/api/settings/regenerate-key")
async def regenerate_encryption_key():
    from cryptography.fernet import Fernet

    new_key = Fernet.generate_key().decode()

    env_path = Path(".env")
    lines = env_path.read_text().splitlines() if env_path.exists() else []
    env_map = {}
    for line in lines:
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env_map[k.strip()] = v.strip()

    env_map["ENCRYPTION_KEY"] = new_key
    env_path.write_text("\n".join(f"{k}={v}" for k, v in env_map.items()) + "\n")

    return {"ok": True}


async def _check_github_token(token: str) -> dict:
    import httpx
    if not token:
        return {"status": "not_configured"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get("https://api.github.com/user", headers={"Authorization": f"token {token}"})
        if res.status_code == 200:
            return {"status": "active", "user": res.json().get("login", "")}
        return {"status": "error", "error": f"HTTP {res.status_code}: {res.json().get('message', res.text[:100])}"}
    except Exception as e:
        return {"status": "error", "error": str(e)[:200]}


@router.get("/api/settings/status")
async def get_settings_status():
    import httpx

    results = {
        "github_token": await _check_github_token(settings.github_token),
        "github_fg_token": await _check_github_token(getattr(settings, "github_fg_token", "")),
    }

    if settings.supabase_url and settings.supabase_key:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(
                    f"{settings.supabase_url}/rest/v1/",
                    headers={"apikey": settings.supabase_key, "Authorization": f"Bearer {settings.supabase_key}"},
                )
            if res.status_code == 200:
                results["supabase"] = {"status": "active"}
            else:
                results["supabase"] = {"status": "error", "error": f"HTTP {res.status_code}: {res.text[:100]}"}
        except Exception as e:
            results["supabase"] = {"status": "error", "error": str(e)[:200]}
    else:
        results["supabase"] = {"status": "not_configured"}

    return results
