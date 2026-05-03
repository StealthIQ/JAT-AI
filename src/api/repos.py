from __future__ import annotations

from fastapi import APIRouter, HTTPException

from config import load_settings
from core.repomix import analyze_repo, get_cached_xml

router = APIRouter()
settings = load_settings()


@router.post("/api/repos/{owner}/{repo}/analyze")
async def analyze(owner: str, repo: str, force: bool = False):
    token = settings.github_token
    if not token:
        raise HTTPException(400, "No GitHub token configured")

    if not force:
        cached = get_cached_xml(owner, repo)
        if cached:
            return {"xml": cached, "cached": True, "chars": len(cached)}

    try:
        xml = await analyze_repo(owner, repo, token)
    except RuntimeError as e:
        raise HTTPException(500, str(e))

    return {"xml": xml, "cached": False, "chars": len(xml)}


@router.get("/api/repos/{owner}/{repo}/context")
async def get_context(owner: str, repo: str):
    cached = get_cached_xml(owner, repo)
    if not cached:
        raise HTTPException(404, "No cached analysis. Run analyze first.")
    return {"xml": cached, "chars": len(cached)}


@router.post("/api/repos/{owner}/{repo}/init-jdocs")
async def init_jdocs_endpoint(owner: str, repo: str, branch: str = "main"):
    token = settings.github_token
    if not token:
        raise HTTPException(400, "No GitHub token configured")

    from core.jdocs import init_jdocs
    results = await init_jdocs(owner, repo, branch, token)
    return {"results": results}
