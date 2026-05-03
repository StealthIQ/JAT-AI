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
    return res.status_code == 201


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
    body = {
        "title": f"JAT-AI: {branch}",
        "repositoryOwner": owner,
        "repositoryName": repo,
        "repositoryBranch": branch,
        "prompt": prompt,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.post(url, json=body, headers=headers)
    if res.status_code == 200:
        return res.json().get("name", "").split("/")[-1]
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


async def _answer_jules_question(session_data: dict, task_context: str, ai_key: str, ai_provider: str, ai_model: str) -> str:
    from api.chat import _call_provider
    question = session_data.get("lastMessage", {}).get("content", "Unknown question")
    prompt = f"Jules is asking: {question}\n\nContext from planning phase:\n{task_context}\n\nAnswer concisely."
    try:
        return await _call_provider(ai_key, ai_provider, ai_model, [{"role": "user", "content": prompt}], "")
    except Exception:
        return "Please proceed with your best judgment based on the task description."


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
            answer = await _answer_jules_question(data, task_context, ai_key, ai_provider, ai_model)
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
    return best.get("api_key", "")
