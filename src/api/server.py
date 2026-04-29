from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from clients.supabase import SupabaseClient
from config import load_settings


settings = load_settings()
db = SupabaseClient(settings.supabase_url, settings.supabase_key)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="JAT-AI API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class PromptCreate(BaseModel):
    name: str
    content: str = ""
    format: str = "xml"


class PromptUpdate(BaseModel):
    content: str


@app.get("/api/prompts")
async def list_prompts():
    rows = await db.select("prompts", columns="name, source, format")
    return {"prompts": rows}


@app.get("/api/prompts/{name}")
async def get_prompt(name: str):
    rows = await db.select("prompts", filters={"name": name})
    if not rows:
        raise HTTPException(404, f"Prompt '{name}' not found")
    return rows[0]


@app.post("/api/prompts", status_code=201)
async def create_prompt(body: PromptCreate):
    existing = await db.select("prompts", filters={"name": body.name})
    if existing:
        raise HTTPException(409, f"Prompt '{body.name}' already exists")
    row = await db.insert("prompts", {
        "name": body.name,
        "source": "user",
        "content": body.content,
        "format": body.format,
    })
    return row


@app.put("/api/prompts/{name}")
async def update_prompt(name: str, body: PromptUpdate):
    rows = await db.select("prompts", filters={"name": name})
    if not rows:
        raise HTTPException(404, f"Prompt '{name}' not found")
    if rows[0]["source"] == "builtin":
        raise HTTPException(403, "Cannot edit built-in prompts")
    updated = await db.update("prompts", {"content": body.content}, {"name": name})
    return updated[0] if updated else {"ok": True}


@app.delete("/api/prompts/{name}")
async def delete_prompt(name: str):
    rows = await db.select("prompts", filters={"name": name})
    if not rows:
        raise HTTPException(404, f"Prompt '{name}' not found")
    if rows[0]["source"] == "builtin":
        raise HTTPException(403, "Cannot delete built-in prompts")
    await db.delete("prompts", {"name": name})
    return {"ok": True}


# --- Provider management (encrypted keys) ---

class ProviderCreate(BaseModel):
    provider_type: str
    name: str
    api_key: str = ""
    model: str = ""
    base_url: str = ""
    daily_limit: int = 0


class ProviderToggle(BaseModel):
    enabled: bool


@app.get("/api/providers")
async def list_providers():
    rows = await db.select(
        "ai_providers",
        columns="id, provider_type, name, model, base_url, enabled, daily_limit, api_key_encrypted",
    )
    providers = [{
        "id": r["id"],
        "provider_type": r["provider_type"],
        "name": r["name"],
        "model": r["model"],
        "base_url": r["base_url"],
        "enabled": r["enabled"],
        "daily_limit": r["daily_limit"],
        "has_key": r["api_key_encrypted"] is not None,
    } for r in rows]
    return {"providers": providers}


@app.post("/api/providers", status_code=201)
async def create_provider(body: ProviderCreate):
    from core.ai_interface import KeyVault
    vault = KeyVault(settings.encryption_key)
    encrypted = vault.encrypt(body.api_key) if body.api_key else None
    row = await db.insert("ai_providers", {
        "provider_type": body.provider_type,
        "name": body.name,
        "api_key_encrypted": encrypted,
        "model": body.model,
        "base_url": body.base_url,
        "daily_limit": body.daily_limit,
        "enabled": True,
    })
    return row


@app.patch("/api/providers/{provider_id}")
async def toggle_provider(provider_id: str, body: ProviderToggle):
    updated = await db.update(
        "ai_providers", {"enabled": body.enabled}, {"id": provider_id}
    )
    return updated[0] if updated else {"ok": True}


@app.delete("/api/providers/{provider_id}")
async def delete_provider(provider_id: str):
    await db.delete("ai_providers", {"id": provider_id})
    return {"ok": True}
