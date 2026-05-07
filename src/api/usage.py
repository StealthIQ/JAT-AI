from __future__ import annotations

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter

from db import db

router = APIRouter()


def _aggregate_by_field(rows: list[dict], field: str) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for r in rows:
        key = r.get(field, "unknown")
        if key not in result:
            result[key] = {"input_tokens": 0, "output_tokens": 0, "requests": 0}
        result[key]["input_tokens"] += r.get("input_tokens", 0)
        result[key]["output_tokens"] += r.get("output_tokens", 0)
        result[key]["requests"] += 1
    return result


def _daily_breakdown(rows: list[dict], now: datetime) -> list[dict]:
    daily: list[dict] = []
    for i in range(7):
        day_str = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        day_rows = [r for r in rows if r.get("created_at", "").startswith(day_str)]
        daily.append({
            "date": day_str,
            "input_tokens": sum(r.get("input_tokens", 0) for r in day_rows),
            "output_tokens": sum(r.get("output_tokens", 0) for r in day_rows),
            "requests": len(day_rows),
        })
    return list(reversed(daily))


@router.get("/api/usage/stats")
async def get_usage_stats():
    try:
        rows = await db.select("token_usage", order_by="created_at DESC")
    except Exception:
        rows = []

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

    today_rows = [r for r in rows if r.get("created_at", "") >= today_start]

    return {
        "total": {"input_tokens": sum(r.get("input_tokens", 0) for r in rows), "output_tokens": sum(r.get("output_tokens", 0) for r in rows), "requests": len(rows)},
        "today": {"input_tokens": sum(r.get("input_tokens", 0) for r in today_rows), "output_tokens": sum(r.get("output_tokens", 0) for r in today_rows), "requests": len(today_rows)},
        "by_provider": _aggregate_by_field(rows, "provider_type"),
        "by_model": _aggregate_by_field(rows, "model"),
        "daily": _daily_breakdown(rows, now),
        "recent": [{"provider": r.get("provider_type"), "model": r.get("model"), "input": r.get("input_tokens"), "output": r.get("output_tokens"), "at": r.get("created_at")} for r in rows[:20]],
    }


@router.post("/api/usage/track")
async def track_usage(body: dict):
    try:
        await db.insert("token_usage", {
            "provider_type": body.get("provider_type", ""),
            "model": body.get("model", ""),
            "input_tokens": body.get("input_tokens", 0),
            "output_tokens": body.get("output_tokens", 0),
            "conversation_id": body.get("conversation_id", ""),
        })
    except Exception:
        pass
    return {"ok": True}
