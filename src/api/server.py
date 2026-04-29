from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api.providers import router as providers_router
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
app.include_router(providers_router)


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


# --- Agent tasks (terminals on the canvas) ---

@app.get("/api/terminals")
async def list_terminals():
    rows = await db.select("agent_tasks")
    return [{
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


@app.get("/api/conversations")
async def list_conversations():
    rows = await db.select("conversations")
    return {"sessions": [{
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
    } for r in rows]}


@app.get("/api/claude/usage")
async def get_usage():
    accounts = await db.select("accounts")
    total_daily = sum(a.get("max_daily_tasks", 0) for a in accounts)
    active_count = len([a for a in accounts if a.get("enabled")])
    return {
        "status": "ok",
        "fetchedAt": "connected" if settings.supabase_url else "disconnected",
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


# --- Static endpoints and UI write catch-alls ---
# Octogent UI expects these but we don't persist them yet

@app.get("/api/ui-state")
async def get_ui_state():
    return {
        "activePrimaryNav": 1,
        "sidebarWidth": 260,
        "isAgentsSidebarVisible": True,
        "isRuntimeStatusStripVisible": True,
        "isBottomTelemetryVisible": False,
        "isMonitorVisible": True,
        "minimizedTerminalIds": [],
        "isActiveAgentsSectionExpanded": True,
        "isClaudeUsageSectionExpanded": True,
        "isCodexUsageSectionExpanded": False,
        "terminalCompletionSound": "none",
        "canvasOpenTerminalIds": [],
        "canvasOpenTentacleIds": [],
        "canvasTerminalsPanelWidth": None,
    }


@app.put("/api/ui-state")
async def put_ui_state():
    return {"ok": True}


@app.patch("/api/ui-state")
async def patch_ui_state():
    return {"ok": True}


@app.get("/api/setup")
async def get_setup():
    return {"shouldShowSetupCard": False, "steps": []}


@app.get("/api/codex/usage")
async def get_codex_usage():
    return {"status": "unavailable", "source": "none"}


@app.get("/api/github/summary")
async def get_github_summary():
    return {"status": "ok", "repo": "", "stargazerCount": 0, "openIssueCount": 0, "openPullRequestCount": 0, "commitsPerDay": [], "recentCommits": []}


@app.get("/api/analytics/usage-heatmap")
async def get_usage_heatmap():
    return {"days": [], "projects": [], "models": []}


@app.get("/api/monitor/feed")
async def get_monitor_feed():
    return {"providerId": "x", "queryTerms": [], "posts": [], "isStale": False, "lastError": None}


@app.get("/api/monitor/config")
async def get_monitor_config():
    return {"providerId": "x", "queryTerms": [], "refreshPolicy": {"maxCacheAgeMs": 3600000, "maxPosts": 30, "searchWindowDays": 7}, "providers": {}}


@app.get("/api/code-intel/events")
async def get_code_intel():
    return {"events": []}


@app.get("/api/deck/skills")
async def get_deck_skills():
    return []


@app.post("/api/terminals")
async def post_terminals():
    return {"ok": True}


@app.put("/api/deck/tentacles/{tentacle_id}")
async def put_tentacle(tentacle_id: str):
    return {"ok": True}


@app.post("/api/deck/tentacles")
async def post_tentacle():
    return {"ok": True}
