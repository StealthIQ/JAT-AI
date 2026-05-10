from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field

import httpx

from config import load_settings
from db import db

settings = load_settings()


@dataclass
class AgentTask:
    id: str
    description: str
    prompt_id: str | None = None
    branch_name: str = ""
    dependencies: list[str] = field(default_factory=list)
    exit_criteria: str = ""
    status: str = "pending"
    session_id: str | None = None
    pr_url: str | None = None


@dataclass
class ExecutionPlan:
    repo_owner: str
    repo_name: str
    tasks: list[AgentTask]
    execution_mode: str = "sequential"
    max_sessions: int = 10
    max_retries: int = 2
    timeout_minutes: int = 20


def parse_plan(plan_json: str, repo_owner: str, repo_name: str) -> ExecutionPlan:
    data = json.loads(plan_json)
    tasks = []
    for i, t in enumerate(data.get("tasks", [])):
        tasks.append(AgentTask(
            id=t.get("id", f"agent-{i+1}"),
            description=t["description"],
            prompt_id=t.get("prompt_id"),
            branch_name=t.get("branch", f"jat/agent-{i+1}"),
            dependencies=t.get("dependencies", []),
            exit_criteria=t.get("exit_criteria", ""),
        ))
    return ExecutionPlan(
        repo_owner=repo_owner,
        repo_name=repo_name,
        tasks=tasks,
        execution_mode=data.get("execution_mode", "sequential"),
        max_sessions=data.get("max_sessions", 10),
    )


async def create_branch_from_ref(owner: str, repo: str, branch_name: str, sha: str, token: str) -> bool:
    url = f"https://api.github.com/repos/{owner}/{repo}/git/refs"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    body = {"ref": f"refs/heads/{branch_name}", "sha": sha}
    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.post(url, json=body, headers=headers)
    if res.status_code == 201:
        return True
    # Branch already exists — update it to the latest SHA
    if res.status_code == 422:
        update_url = f"https://api.github.com/repos/{owner}/{repo}/git/refs/heads/{branch_name}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            update_res = await client.patch(update_url, json={"sha": sha, "force": True}, headers=headers)
        return update_res.status_code == 200
    return False


async def get_default_branch_sha(owner: str, repo: str, token: str) -> str | None:
    url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.get(url, headers=headers)
    if res.status_code != 200:
        return None
    default_branch = res.json().get("default_branch", "main")
    ref_url = f"https://api.github.com/repos/{owner}/{repo}/git/ref/heads/{default_branch}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        ref_res = await client.get(ref_url, headers=headers)
    if ref_res.status_code != 200:
        return None
    return ref_res.json()["object"]["sha"]


async def create_jules_session(prompt: str, owner: str, repo: str, branch: str, jules_key: str) -> str | None:
    url = "https://jules.googleapis.com/v1alpha/sessions"
    headers = {"X-Goog-Api-Key": jules_key, "Content-Type": "application/json"}

    source_name = await _get_source_for_repo(owner, repo, jules_key)
    if not source_name:
        print(f"[JULES] No source found for {owner}/{repo}. Add it in Jules settings.")
        return None

    body = {
        "title": f"JAT-AI: {branch}",
        "prompt": prompt,
        "sourceContext": {
            "source": source_name,
            "githubRepoContext": {
                "startingBranch": branch,
            }
        }
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.post(url, json=body, headers=headers)
    if res.status_code == 200:
        return res.json().get("name", "").split("/")[-1]
    if res.status_code == 429:
        await asyncio.sleep(60)
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(url, json=body, headers=headers)
        if res.status_code == 200:
            return res.json().get("name", "").split("/")[-1]
    print(f"[JULES] Session creation failed ({res.status_code}): {res.text[:300]}")
    return None


async def _get_source_for_repo(owner: str, repo: str, jules_key: str) -> str | None:
    url = "https://jules.googleapis.com/v1alpha/sources"
    headers = {"X-Goog-Api-Key": jules_key}
    target = f"sources/github/{owner}/{repo}".lower()
    page_token = None

    while True:
        params = {}
        if page_token:
            params["pageToken"] = page_token
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.get(url, headers=headers, params=params)
        if res.status_code != 200:
            return None
        data = res.json()
        for s in data.get("sources", []):
            if s.get("name", "").lower() == target:
                return s.get("name", "")
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return None


async def send_message_to_session(session_id: str, message: str, jules_key: str) -> bool:
    url = f"https://jules.googleapis.com/v1alpha/sessions/{session_id}:sendMessage"
    headers = {"X-Goog-Api-Key": jules_key, "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.post(url, json={"message": message}, headers=headers)
    return res.status_code == 200


async def _approve_plan(session_id: str, jules_key: str) -> bool:
    url = f"https://jules.googleapis.com/v1alpha/sessions/{session_id}:approvePlan"
    headers = {"X-Goog-Api-Key": jules_key, "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.post(url, json={}, headers=headers)
    return res.status_code == 200


async def _fetch_recent_activities(session_id: str, jules_key: str, limit: int = 8) -> str:
    """Fetch the most recent Jules activities so the AI can ground its answer in what
    Jules has actually done so far, not just the latest question."""
    url = f"https://jules.googleapis.com/v1alpha/sessions/{session_id}/activities"
    headers = {"X-Goog-Api-Key": jules_key}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.get(url, headers=headers)
        if res.status_code != 200:
            return ""
        acts = res.json().get("activities", [])
    except Exception:
        return ""

    if not acts:
        return ""

    recent = acts[-limit:]
    lines = []
    for a in recent:
        atype = a.get("type", "unknown")
        state = a.get("state", "")
        summary = a.get("summary") or a.get("content") or ""
        if isinstance(summary, dict):
            summary = summary.get("text") or summary.get("message") or str(summary)
        summary = str(summary)[:200].replace("\n", " ").strip()
        entry = f"- [{atype}"
        if state:
            entry += f"/{state}"
        entry += "]"
        if summary:
            entry += f" {summary}"
        lines.append(entry)
    return "\n".join(lines)


async def _answer_jules_question(
    session_data: dict, task_context: str, ai_key: str, ai_provider: str, ai_model: str,
    session_id: str = "", jules_key: str = "",
) -> str:
    from api.chat import _call_provider
    question = session_data.get("lastMessage", {}).get("content", "Unknown question")

    activity_summary = ""
    if session_id and jules_key:
        activity_summary = await _fetch_recent_activities(session_id, jules_key)

    prompt_parts = [
        f"Jules is working on a task and asking: {question}",
        "",
        f"Context from planning phase:\n{task_context}",
    ]
    if activity_summary:
        prompt_parts.append("")
        prompt_parts.append(f"Recent Jules activity (most recent last):\n{activity_summary}")
    prompt_parts.extend([
        "",
        "Instructions:",
        "1. If the question indicates all work is complete and exit criteria are met, "
        "reply with exactly: [TASK_COMPLETE] All exit criteria satisfied.",
        "2. If the question indicates work is NOT complete, tell Jules what remains "
        "and instruct it to continue using its best judgment, searching the internet "
        "for documentation or examples if needed.",
        "3. If it's a clarification question, answer concisely based on the task "
        "context and recent activity, then tell Jules to proceed.",
        "Answer now:",
    ])
    prompt = "\n".join(prompt_parts)

    try:
        return await _call_provider(ai_key, ai_provider, ai_model, [{"role": "user", "content": prompt}], "")
    except Exception as e:
        if "429" in str(e) or "rate" in str(e).lower():
            await asyncio.sleep(60)
            try:
                return await _call_provider(ai_key, ai_provider, ai_model, [{"role": "user", "content": prompt}], "")
            except Exception:
                pass
        return "Check if all exit criteria are met. If yes, confirm completion. If not, continue working using your best judgment and search online for help if needed."


async def poll_session_status(
    session_id: str, jules_key: str, timeout_minutes: int = 20,
    task_context: str = "", ai_key: str = "", ai_provider: str = "", ai_model: str = ""
) -> dict:
    url = f"https://jules.googleapis.com/v1alpha/sessions/{session_id}"
    headers = {"X-Goog-Api-Key": jules_key}
    deadline = asyncio.get_event_loop().time() + (timeout_minutes * 60)

    while asyncio.get_event_loop().time() < deadline:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.get(url, headers=headers)
        if res.status_code != 200:
            await asyncio.sleep(15)
            continue
        data = res.json()
        state = data.get("state", "")
        if state in ("COMPLETED", "FAILED"):
            return data
        if state == "AWAITING_PLAN_APPROVAL":
            await _approve_plan(session_id, jules_key)
        elif state == "AWAITING_USER_INPUT" and ai_key:
            answer = await _answer_jules_question(
                data, task_context, ai_key, ai_provider, ai_model,
                session_id=session_id, jules_key=jules_key,
            )
            await send_message_to_session(session_id, answer, jules_key)
        await asyncio.sleep(15)

    return {"state": "TIMEOUT", "session_id": session_id}


async def get_jules_key() -> str | None:
    try:
        rows = await db.select("accounts")
    except Exception:
        return None
    enabled = [r for r in rows if r.get("enabled", True)]
    if not enabled:
        return None
    best = min(enabled, key=lambda r: r.get("sessions_today", 0))
    daily_limit = best.get("max_daily_tasks", 300)
    if best.get("sessions_today", 0) >= daily_limit:
        return None
    encrypted = best.get("api_key_encrypted", "")
    if not encrypted:
        return None
    from core.ai_interface import KeyVault
    from config import load_settings
    vault = KeyVault(load_settings().encryption_key)
    try:
        return vault.decrypt(encrypted)
    except Exception:
        return encrypted
