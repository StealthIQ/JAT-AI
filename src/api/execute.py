from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import load_settings
from core.plan_executor import (
    parse_plan,
    create_branch_from_ref,
    get_default_branch_sha,
    create_jules_session,
    poll_session_status,
    get_jules_key,
    ExecutionPlan,
    AgentTask,
)

router = APIRouter()
settings = load_settings()


class ExecuteRequest(BaseModel):
    plan_json: str
    repo_owner: str
    repo_name: str


class TaskResult(BaseModel):
    task_id: str
    status: str
    session_id: str | None = None
    pr_url: str | None = None
    error: str | None = None


class ExecuteResponse(BaseModel):
    status: str
    results: list[TaskResult]


async def _run_task(task: AgentTask, plan: ExecutionPlan, base_sha: str, jules_key: str, token: str) -> TaskResult:
    branch_created = await create_branch_from_ref(
        plan.repo_owner, plan.repo_name, task.branch_name, base_sha, token
    )
    if not branch_created:
        return TaskResult(task_id=task.id, status="failed", error="Branch creation failed")

    prompt = task.description
    if task.exit_criteria:
        prompt += f"\n\nExit criteria: {task.exit_criteria}"

    session_id = await create_jules_session(
        prompt=prompt,
        owner=plan.repo_owner,
        repo=plan.repo_name,
        branch=task.branch_name,
        jules_key=jules_key,
    )
    if not session_id:
        return TaskResult(task_id=task.id, status="failed", error="Session creation failed")

    result = await poll_session_status(session_id, jules_key, plan.timeout_minutes)
    state = result.get("state", "UNKNOWN")

    pr_url = None
    outputs = result.get("outputs", [])
    for out in outputs:
        if "pull_request" in out:
            pr_url = out["pull_request"].get("url", "")
            break

    return TaskResult(
        task_id=task.id,
        status="completed" if state == "COMPLETED" else "failed",
        session_id=session_id,
        pr_url=pr_url,
        error=None if state == "COMPLETED" else f"Session ended with state: {state}",
    )


async def _execute_sequential(plan: ExecutionPlan, jules_key: str, token: str) -> list[TaskResult]:
    base_sha = await get_default_branch_sha(plan.repo_owner, plan.repo_name, token)
    if not base_sha:
        return [TaskResult(task_id=t.id, status="failed", error="Could not get base SHA") for t in plan.tasks]

    results = []
    for task in plan.tasks:
        result = await _run_task(task, plan, base_sha, jules_key, token)
        results.append(result)
        if result.status == "failed":
            break
    return results


async def _execute_parallel(plan: ExecutionPlan, jules_key: str, token: str) -> list[TaskResult]:
    base_sha = await get_default_branch_sha(plan.repo_owner, plan.repo_name, token)
    if not base_sha:
        return [TaskResult(task_id=t.id, status="failed", error="Could not get base SHA") for t in plan.tasks]

    coros = [_run_task(task, plan, base_sha, jules_key, token) for task in plan.tasks]
    return await asyncio.gather(*coros)


async def _execute_hybrid(plan: ExecutionPlan, jules_key: str, token: str) -> list[TaskResult]:
    base_sha = await get_default_branch_sha(plan.repo_owner, plan.repo_name, token)
    if not base_sha:
        return [TaskResult(task_id=t.id, status="failed", error="Could not get base SHA") for t in plan.tasks]

    completed: dict[str, TaskResult] = {}
    pending = list(plan.tasks)
    results = []

    while pending:
        ready = [t for t in pending if all(d in completed for d in t.dependencies)]
        if not ready:
            break

        coros = [_run_task(t, plan, base_sha, jules_key, token) for t in ready]
        batch_results = await asyncio.gather(*coros)

        for task, result in zip(ready, batch_results):
            completed[task.id] = result
            results.append(result)
            pending.remove(task)

    for t in pending:
        results.append(TaskResult(task_id=t.id, status="blocked", error="Dependencies not met"))

    return results


@router.post("/api/execute")
async def execute_plan(request: ExecuteRequest):
    jules_key = await get_jules_key()
    if not jules_key:
        raise HTTPException(400, "No Jules API key configured")

    token = settings.github_token
    if not token:
        raise HTTPException(400, "No GitHub token configured")

    try:
        plan = parse_plan(request.plan_json, request.repo_owner, request.repo_name)
    except Exception as e:
        raise HTTPException(400, f"Invalid plan: {e}")

    if plan.execution_mode == "parallel":
        results = await _execute_parallel(plan, jules_key, token)
    elif plan.execution_mode == "hybrid":
        results = await _execute_hybrid(plan, jules_key, token)
    else:
        results = await _execute_sequential(plan, jules_key, token)

    all_done = all(r.status == "completed" for r in results)
    return ExecuteResponse(
        status="completed" if all_done else "partial",
        results=results,
    )
