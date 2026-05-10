from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import load_settings
from db import db
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
from core.session_limiter import get_session_limiter

router = APIRouter()
settings = load_settings()


async def _track_task(task: AgentTask, plan: ExecutionPlan, status: str, session_id: str | None = None):
    try:
        await db.insert("agent_tasks", {
            "prompt": task.description[:500],
            "repo_owner": plan.repo_owner,
            "repo_name": plan.repo_name,
            "status": status,
            "session_id": session_id or "",
        })
    except Exception:
        pass


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


async def _update_jdocs(plan: ExecutionPlan, task: AgentTask, status: str, session_id: str, pr_url: str | None, token: str):
    from core.jdocs import update_context_after_agent, append_session_history
    # Write to agent's own branch
    await update_context_after_agent(
        plan.repo_owner, plan.repo_name, task.branch_name, token,
        agent_id=task.id, task_description=task.description,
        status=status, pr_url=pr_url, files_changed=None,
    )
    await append_session_history(
        plan.repo_owner, plan.repo_name, task.branch_name, token,
        agent_id=task.id, session_id=session_id or "",
        status=status, prompt_summary=task.description[:200],
    )
    # Also write to main so subsequent agents can read prior context
    try:
        await update_context_after_agent(
            plan.repo_owner, plan.repo_name, "main", token,
            agent_id=task.id, task_description=task.description,
            status=status, pr_url=pr_url, files_changed=None,
        )
        await append_session_history(
            plan.repo_owner, plan.repo_name, "main", token,
            agent_id=task.id, session_id=session_id or "",
            status=status, prompt_summary=task.description[:200],
        )
    except Exception:
        pass  # Non-critical — agent branch has the data regardless


def _extract_pr_url(outputs: list[dict]) -> str | None:
    for out in outputs:
        if "pull_request" in out:
            return out["pull_request"].get("url", "")
    return None


async def _run_task_once(task: AgentTask, plan: ExecutionPlan, base_sha: str, jules_key: str, token: str, task_index: int = 0) -> TaskResult:
    limiter = get_session_limiter()
    pipeline_id = f"{plan.repo_owner}/{plan.repo_name}"

    acquired = await limiter.acquire(pipeline_id, plan.repo_name, task.id)
    if not acquired:
        return TaskResult(task_id=task.id, status="failed", error="Could not acquire session slot (global limit reached)")

    try:
        await _track_task(task, plan, "running")
        branch_created = await create_branch_from_ref(
            plan.repo_owner, plan.repo_name, task.branch_name, base_sha, token
        )
        if not branch_created:
            return TaskResult(task_id=task.id, status="failed", error="Branch creation failed")

        prompt = await _resolve_prompt(task, plan, token, task_index)
        session_id = await create_jules_session(
            prompt=prompt, owner=plan.repo_owner, repo=plan.repo_name,
            branch=task.branch_name, jules_key=jules_key,
        )
        if not session_id:
            return TaskResult(task_id=task.id, status="failed", error="Session creation failed")

        result = await poll_session_status(session_id, jules_key, plan.timeout_minutes)
        state = result.get("state", "UNKNOWN")

        if state == "TIMEOUT":
            return TaskResult(task_id=task.id, status="failed", session_id=session_id, error=f"Session timed out after {plan.timeout_minutes}min (still running on Jules)")

        pr_url = _extract_pr_url(result.get("outputs", []))
        status = "completed" if state == "COMPLETED" else "failed"
        await _track_task(task, plan, status, session_id)
        await _update_jdocs(plan, task, status, session_id or "", pr_url, token)

        return TaskResult(
            task_id=task.id, status=status, session_id=session_id, pr_url=pr_url,
            error=None if state == "COMPLETED" else f"Session ended with state: {state}",
        )
    finally:
        await limiter.release(task.id)


async def _resolve_prompt(task: AgentTask, plan: ExecutionPlan, token: str, task_index: int = 0) -> str:
    from core.prompt_builder import build_agent_xml_prompt

    # Read prior agent context from jdocs on the default branch
    dependency_context = await _read_jdocs_context(plan.repo_owner, plan.repo_name, token)

    # If task has a prompt_id, load the skill content as extra steps
    steps = ""
    if task.prompt_id:
        try:
            rows = await db.select("prompts", filters={"name": task.prompt_id})
            if rows:
                steps = rows[0].get("content", "")
        except Exception:
            pass

    # Parse acceptance criteria from exit_criteria (split on newlines or semicolons)
    criteria = [c.strip() for c in task.exit_criteria.replace(";", "\n").split("\n") if c.strip()] if task.exit_criteria else ["Task completed as described"]

    return build_agent_xml_prompt(
        agent_index=task_index + 1,
        total_agents=len(plan.tasks),
        title=task.description[:80],
        description=task.description,
        branch_name=task.branch_name,
        files_scope=[],  # Jules discovers files from the repo
        acceptance_criteria=criteria,
        repo_owner=plan.repo_owner,
        repo_name=plan.repo_name,
        dependency_context=dependency_context,
        steps=steps,
    )


async def _read_jdocs_context(owner: str, repo: str, token: str, branch: str = "main") -> str:
    """Fetch .jules/jdocs/context.xml from the repo so the next agent knows what prior agents did."""
    import httpx
    import base64

    url = f"https://api.github.com/repos/{owner}/{repo}/contents/.jules/jdocs/context.xml?ref={branch}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(url, headers=headers)
        if res.status_code == 200:
            content = base64.b64decode(res.json()["content"]).decode()
            return content
    except Exception:
        pass
    return "No prior agent context available."


async def _run_task(task: AgentTask, plan: ExecutionPlan, base_sha: str, jules_key: str, token: str, task_index: int = 0) -> TaskResult:
    max_retries = plan.max_retries if hasattr(plan, "max_retries") else 2
    for attempt in range(max_retries + 1):
        result = await _run_task_once(task, plan, base_sha, jules_key, token, task_index)
        if result.status == "completed":
            return result
        if attempt < max_retries:
            task.branch_name = f"{task.branch_name}-retry{attempt + 1}"
    return result


async def _execute_sequential(plan: ExecutionPlan, jules_key: str, token: str) -> list[TaskResult]:
    base_sha = await get_default_branch_sha(plan.repo_owner, plan.repo_name, token)
    if not base_sha:
        return [TaskResult(task_id=t.id, status="failed", error="Could not get base SHA") for t in plan.tasks]

    results = []
    for i, task in enumerate(plan.tasks):
        result = await _run_task(task, plan, base_sha, jules_key, token, i)
        results.append(result)
        if result.status == "failed":
            break
    return results


async def _execute_parallel(plan: ExecutionPlan, jules_key: str, token: str) -> list[TaskResult]:
    base_sha = await get_default_branch_sha(plan.repo_owner, plan.repo_name, token)
    if not base_sha:
        return [TaskResult(task_id=t.id, status="failed", error="Could not get base SHA") for t in plan.tasks]

    coros = [_run_task(task, plan, base_sha, jules_key, token, i) for i, task in enumerate(plan.tasks)]
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

        coros = [_run_task(t, plan, base_sha, jules_key, token, plan.tasks.index(t)) for t in ready]
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

    merge_result = None
    if all_done:
        from core.merge_review import merge_branches, create_integration_branch, run_review_session, create_final_pr
        base_sha = await get_default_branch_sha(request.repo_owner, request.repo_name, token)
        if base_sha:
            branches = [t.branch_name for t in plan.tasks]
            integration = f"jat/integration-{request.repo_name}"
            await create_integration_branch(request.repo_owner, request.repo_name, base_sha, integration, token)
            merge_result = await merge_branches(request.repo_owner, request.repo_name, branches, integration, token)
            pr_url = await create_final_pr(request.repo_owner, request.repo_name, integration, "main", f"JAT-AI: {integration}", token)
            merge_result["pr_url"] = pr_url

    return ExecuteResponse(
        status="completed" if all_done else "partial",
        results=results,
    )


@router.get("/api/session-limiter/status")
async def limiter_status():
    limiter = get_session_limiter()
    return limiter.status()


class MergeReviewRequest(BaseModel):
    repo_owner: str
    repo_name: str
    branches: list[str]
    integration_branch: str = "jat/integration"
    run_review: bool = True
    cleanup: bool = True


@router.post("/api/execute/merge-review")
async def merge_and_review(request: MergeReviewRequest):
    from core.merge_review import (
        merge_branches, create_integration_branch,
        run_review_session, cleanup_branches, create_final_pr,
    )
    from core.plan_executor import get_default_branch_sha

    token = settings.github_token
    jules_key = await get_jules_key()
    if not token:
        raise HTTPException(400, "No GitHub token configured")

    base_sha = await get_default_branch_sha(request.repo_owner, request.repo_name, token)
    if not base_sha:
        raise HTTPException(500, "Could not get base SHA")

    await create_integration_branch(
        request.repo_owner, request.repo_name, base_sha, request.integration_branch, token
    )

    merge_results = await merge_branches(
        request.repo_owner, request.repo_name, request.branches, request.integration_branch, token
    )

    review_result = None
    if request.run_review and jules_key:
        context = "\n".join(f"- {b}: {s}" for b, s in merge_results.items())
        review_result = await run_review_session(
            request.repo_owner, request.repo_name, request.integration_branch,
            jules_key, context,
        )

    pr_url = await create_final_pr(
        request.repo_owner, request.repo_name, request.integration_branch,
        "main", f"JAT-AI: {request.integration_branch}", token,
    )

    cleanup_result = None
    if request.cleanup:
        cleanup_result = await cleanup_branches(
            request.repo_owner, request.repo_name, request.branches, token
        )

    return {
        "merge_results": merge_results,
        "review": review_result,
        "pr_url": pr_url,
        "cleanup": cleanup_result,
    }


class AutoModeRequest(BaseModel):
    repo_owner: str
    repo_name: str
    goal: str
    provider_type: str
    model: str
    max_sessions: int = 10
    execution_mode: str = "sequential"


@router.post("/api/execute/auto")
async def start_auto_mode(request: AutoModeRequest):
    from core.auto_mode import AutoModeConfig, AutoModeState, run_auto_mode

    config = AutoModeConfig(
        repo_owner=request.repo_owner,
        repo_name=request.repo_name,
        goal=request.goal,
        provider_type=request.provider_type,
        model=request.model,
        max_sessions=request.max_sessions,
        execution_mode=request.execution_mode,
    )
    state = AutoModeState()
    result = await run_auto_mode(config, state)

    return {
        "status": result.status,
        "sessions_used": result.sessions_used,
        "plan": result.plan_json,
        "errors": result.errors,
    }
