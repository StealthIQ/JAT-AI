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


# --- Agent tasks (terminals on the canvas) ---

@app.get("/api/terminals")
async def list_terminals():
    rows = await db.select("agent_tasks")
    terminals = [{
        "terminalId": r["id"],
        "label": r.get("prompt", "")[:40],
        "state": "live" if r["status"] == "running" else ("queued" if r["status"] == "pending" else "idle"),
        "tentacleId": f"{r['repo_owner']}/{r['repo_name']}",
        "tentacleName": r.get("prompt", "")[:30],
        "workspaceMode": "shared",
        "createdAt": r["created_at"],
        "agentRuntimeState": "processing" if r["status"] == "running" else "idle",
        "lifecycleState": "running" if r["status"] == "running" else ("registered" if r["status"] == "pending" else "exited"),
        "hasUserPrompt": True,
        "sessionId": r.get("session_id", ""),
    } for r in rows]
    return terminals


@app.get("/api/terminal-snapshots")
async def list_terminal_snapshots():
    return await list_terminals()


# --- Repos (tentacles on the canvas) ---

@app.get("/api/deck/tentacles")
async def list_tentacles():
    rows = await db.select("agent_tasks")
    repos: dict[str, dict] = {}
    for r in rows:
        key = f"{r['repo_owner']}/{r['repo_name']}"
        if key not in repos:
            repos[key] = {
                "tentacleId": key,
                "displayName": key,
                "description": "",
                "status": "idle",
                "color": "#d6a21a",
                "octopus": {"animation": "idle", "expression": "normal", "accessory": "none", "hairColor": None},
                "scope": {"paths": [key], "tags": []},
                "vaultFiles": [],
                "todoTotal": 0,
                "todoDone": 0,
                "todoItems": [],
                "suggestedSkills": [],
            }
        repo = repos[key]
        repo["todoTotal"] += 1
        if r["status"] in ("completed", "failed"):
            repo["todoDone"] += 1
        if r["status"] == "running":
            repo["status"] = "active"
        repo["todoItems"].append({
            "text": r.get("prompt", "")[:60],
            "done": r["status"] in ("completed",),
        })
    return list(repos.values())


# --- Conversations ---

@app.get("/api/conversations")
async def list_conversations():
    rows = await db.select("conversations")
    sessions = [{
        "sessionId": r["id"],
        "tentacleId": f"{r['repo_owner']}/{r['repo_name']}" if r.get("repo_owner") else "",
        "startedAt": r["created_at"],
        "endedAt": r.get("updated_at"),
        "lastEventAt": r.get("updated_at"),
        "eventCount": 0,
        "turnCount": 0,
        "userTurnCount": 0,
        "assistantTurnCount": 0,
        "firstUserTurnPreview": r.get("title", ""),
        "lastUserTurnPreview": r.get("title", ""),
        "lastAssistantTurnPreview": "",
    } for r in rows]
    return {"sessions": sessions}


# --- Usage stats ---

@app.get("/api/claude/usage")
async def get_usage():
    accounts = await db.select("accounts")
    total_daily = sum(a.get("max_daily_tasks", 0) for a in accounts)
    active_count = len([a for a in accounts if a.get("enabled")])
    return {
        "status": "ok",
        "fetchedAt": settings.supabase_url and "connected" or "disconnected",
        "source": "cli-pty",
        "planType": "ultra",
        "primaryUsedPercent": 0,
        "primaryResetAt": None,
        "secondaryUsedPercent": 0,
        "secondaryResetAt": None,
        "extraUsageCostUsed": 0,
        "extraUsageCostLimit": total_daily or 300,
        "message": f"0/{total_daily or 300} daily sessions | {active_count} accounts",
    }
