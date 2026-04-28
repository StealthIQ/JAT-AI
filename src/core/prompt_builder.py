from __future__ import annotations

from pathlib import Path

import structlog

log = structlog.get_logger()

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


def build_session_prompt(
    task: str,
    dependency_context: list[dict] | None = None,
    plan_tier: str = "Ultra",
    daily_used: int = 0,
    daily_limit: int = 300,
    concurrent_used: int = 0,
    concurrent_limit: int = 60,
    account_name: str = "default",
) -> str:
    rules = _load_template("rules.md")
    gates = _load_template("gates.md")
    anti_patterns = _load_template("anti_patterns.md")
    environment = _load_template("environment.md")

    environment = environment.replace("{plan_tier}", plan_tier)
    environment = environment.replace("{daily_used}", str(daily_used))
    environment = environment.replace("{daily_limit}", str(daily_limit))
    environment = environment.replace("{concurrent_used}", str(concurrent_used))
    environment = environment.replace("{concurrent_limit}", str(concurrent_limit))
    environment = environment.replace("{account_name}", account_name)

    sections = [rules, gates, anti_patterns, environment]

    if dependency_context:
        context_template = _load_template("context.md")
        context_body = _format_dependency_context(dependency_context)
        sections.append(context_template.replace("{dependency_context}", context_body))

    sections.append(f"---\n\nTASK:\n{task}")

    return "\n\n".join(sections)


def _load_template(filename: str) -> str:
    path = PROMPTS_DIR / filename
    if not path.exists():
        log.warning("template_missing", file=filename)
        return ""
    return path.read_text(encoding="utf-8").strip()


def _format_dependency_context(contexts: list[dict]) -> str:
    lines = []
    for ctx in contexts:
        prompt = ctx.get("prompt", "unknown task")[:100]
        status = ctx.get("status", "unknown")
        pr_url = ctx.get("pr_url", "")
        entry = f"- [{status}] {prompt}"
        if pr_url:
            entry += f" | PR: {pr_url}"
        lines.append(entry)
    return "\n".join(lines) if lines else "No prior context available."
