from __future__ import annotations

import asyncio
from pathlib import Path

REPOS_DIR = Path("data/repos")
REPOMIX_DIR = Path("data/repomix")


async def clone_or_pull(owner: str, repo: str, token: str) -> Path:
    repo_path = REPOS_DIR / owner / repo
    repo_path.parent.mkdir(parents=True, exist_ok=True)

    if (repo_path / ".git").exists():
        proc = await asyncio.create_subprocess_exec(
            "git", "pull", "--ff-only",
            cwd=str(repo_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.wait()
    else:
        url = f"https://{token}@github.com/{owner}/{repo}.git"
        proc = await asyncio.create_subprocess_exec(
            "git", "clone", "--depth", "1", url, str(repo_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.wait()
        if proc.returncode != 0:
            stderr = await proc.stderr.read() if proc.stderr else b""
            raise RuntimeError(f"git clone failed: {stderr.decode()[:200]}")

    return repo_path


async def run_repomix(repo_path: Path, owner: str, repo: str) -> str:
    REPOMIX_DIR.mkdir(parents=True, exist_ok=True)
    output_path = REPOMIX_DIR / f"{owner}__{repo}.xml"

    proc = await asyncio.create_subprocess_exec(
        "npx", "repomix", "--output", str(output_path),
        cwd=str(repo_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await proc.wait()

    if proc.returncode != 0:
        stderr = await proc.stderr.read() if proc.stderr else b""
        raise RuntimeError(f"repomix failed: {stderr.decode()[:300]}")

    return output_path.read_text(encoding="utf-8", errors="replace")


async def analyze_repo(owner: str, repo: str, token: str) -> str:
    repo_path = await clone_or_pull(owner, repo, token)
    xml = await run_repomix(repo_path, owner, repo)
    return xml


def get_cached_xml(owner: str, repo: str) -> str | None:
    output_path = REPOMIX_DIR / f"{owner}__{repo}.xml"
    if output_path.exists():
        return output_path.read_text(encoding="utf-8", errors="replace")
    return None


def get_repo_last_commit(owner: str, repo: str) -> str | None:
    repo_path = REPOS_DIR / owner / repo
    head_file = repo_path / ".git" / "refs" / "heads" / "master"
    if not head_file.exists():
        head_file = repo_path / ".git" / "refs" / "heads" / "main"
    if head_file.exists():
        return head_file.read_text().strip()[:8]
    return None
