from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from clients.supabase import SupabaseClient
from config import load_settings
from core.ai_interface import KeyVault

router = APIRouter()
settings = load_settings()
db = SupabaseClient(settings.supabase_url, settings.supabase_key)
vault = KeyVault(settings.encryption_key)

PLAN_LIMITS = {
    "free": {"daily": 15, "concurrent": 3},
    "pro": {"daily": 100, "concurrent": 15},
    "ultra": {"daily": 300, "concurrent": 60},
}


class AccountCreate(BaseModel):
    name: str
    api_key: str
    plan_tier: str = "free"


class AccountPatch(BaseModel):
    enabled: bool | None = None
    plan_tier: str | None = None


@router.get("/api/jules/accounts")
async def list_accounts():
    try:
        rows = await db.select("accounts")
    except Exception:
        rows = []
    accounts = []
    for r in rows:
        tier = r.get("plan_tier", "free")
        limits = PLAN_LIMITS.get(tier, PLAN_LIMITS["free"])
        key_raw = r.get("api_key", "")
        masked = f"{key_raw[:4]}...{key_raw[-4:]}" if len(key_raw) > 8 else "****"
        accounts.append({
            "id": r["id"],
            "name": r.get("name", ""),
            "api_key_masked": masked,
            "plan_tier": tier,
            "daily_limit": limits["daily"],
            "concurrent_limit": limits["concurrent"],
            "sessions_today": r.get("sessions_today", 0),
            "enabled": r.get("enabled", True),
        })
    return {"accounts": accounts}


@router.post("/api/jules/accounts")
async def create_account(body: AccountCreate):
    if body.plan_tier not in PLAN_LIMITS:
        raise HTTPException(400, f"Invalid plan tier: {body.plan_tier}")
    encrypted = vault.encrypt(body.api_key)
    row = {
        "name": body.name,
        "api_key": encrypted,
        "plan_tier": body.plan_tier,
        "enabled": True,
        "sessions_today": 0,
    }
    try:
        await db.insert("accounts", row)
    except Exception as e:
        raise HTTPException(500, str(e))
    return {"ok": True}


@router.patch("/api/jules/accounts/{account_id}")
async def patch_account(account_id: str, body: AccountPatch):
    updates = {}
    if body.enabled is not None:
        updates["enabled"] = body.enabled
    if body.plan_tier is not None:
        if body.plan_tier not in PLAN_LIMITS:
            raise HTTPException(400, f"Invalid plan tier: {body.plan_tier}")
        updates["plan_tier"] = body.plan_tier
    if not updates:
        return {"ok": True}
    try:
        await db.update("accounts", account_id, updates)
    except Exception as e:
        raise HTTPException(500, str(e))
    return {"ok": True}


@router.delete("/api/jules/accounts/{account_id}")
async def delete_account(account_id: str):
    try:
        await db.delete("accounts", account_id)
    except Exception as e:
        raise HTTPException(500, str(e))
    return {"ok": True}


@router.get("/api/jules/accounts/{account_id}/test")
async def test_account(account_id: str):
    try:
        rows = await db.select("accounts")
    except Exception:
        raise HTTPException(500, "DB unavailable")
    row = next((r for r in rows if str(r["id"]) == account_id), None)
    if not row:
        raise HTTPException(404, "Account not found")
    key_raw = row.get("api_key", "")
    try:
        key = vault.decrypt(key_raw)
    except Exception:
        key = key_raw
    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.get(
            "https://jules.googleapis.com/v1alpha/sources",
            headers={"X-Goog-Api-Key": key},
        )
    if res.status_code == 200:
        sources = res.json().get("sources", [])
        return {"ok": True, "sources_count": len(sources)}
    return {"ok": False, "error": f"HTTP {res.status_code}", "detail": res.text[:200]}
