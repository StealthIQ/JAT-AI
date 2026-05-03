from __future__ import annotations

import httpx

from core.plan_executor import create_jules_session, poll_session_status


async def merge_branches(owner: str, repo: str, branches: list[str], target_branch: str, token: str) -> dict:
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    results: dict[str, str] = {}

    async with httpx.AsyncClient(timeout=30.0) as client:
        for branch in branches:
            res = await client.post(
                f"https://api.github.com/repos/{owner}/{repo}/merges",
                json={"base": target_branch, "head": branch, "commit_message": f"jat: merge {branch} into {target_branch}"},
                headers=headers,
            )
            if res.status_code == 201:
                results[branch] = "merged"
            elif res.status_code == 204:
                results[branch] = "already_merged"
            elif res.status_code == 409:
                results[branch] = "conflict"
            else:
                results[branch] = f"error_{res.status_code}"

    return results


async def create_integration_branch(owner: str, repo: str, base_sha: str, branch_name: str, token: str) -> bool:
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.post(
            f"https://api.github.com/repos/{owner}/{repo}/git/refs",
            json={"ref": f"refs/heads/{branch_name}", "sha": base_sha},
            headers=headers,
        )
    return res.status_code == 201


async def run_review_session(
    owner: str, repo: str, integration_branch: str, jules_key: str,
    context_summary: str, timeout_minutes: int = 20
) -> dict:
    prompt = (
        "You are the final reviewer. All agent work has been merged into this branch.\n\n"
        f"Agent context:\n{context_summary}\n\n"
        "Tasks:\n"
        "1. Review all changes for integration issues\n"
        "2. Run tests if available\n"
        "3. Fix any conflicts or broken imports\n"
        "4. Verify exit criteria from each agent were met\n"
        "5. Create a REVIEW.md summarizing what was done and any issues found"
    )

    session_id = await create_jules_session(
        prompt=prompt, owner=owner, repo=repo,
        branch=integration_branch, jules_key=jules_key,
    )
    if not session_id:
        return {"status": "failed", "error": "Could not create review session"}

    result = await poll_session_status(session_id, jules_key, timeout_minutes)
    return {"status": result.get("state", "UNKNOWN"), "session_id": session_id, "data": result}


async def cleanup_branches(owner: str, repo: str, branches: list[str], token: str) -> dict[str, bool]:
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    results = {}
    async with httpx.AsyncClient(timeout=15.0) as client:
        for branch in branches:
            res = await client.delete(
                f"https://api.github.com/repos/{owner}/{repo}/git/refs/heads/{branch}",
                headers=headers,
            )
            results[branch] = res.status_code == 204
    return results


async def create_final_pr(owner: str, repo: str, integration_branch: str, base: str, title: str, token: str) -> str | None:
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.post(
            f"https://api.github.com/repos/{owner}/{repo}/pulls",
            json={"title": title, "head": integration_branch, "base": base, "body": "Automated PR from JAT-AI orchestrator."},
            headers=headers,
        )
    if res.status_code == 201:
        return res.json().get("html_url")
    return None
