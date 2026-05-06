from __future__ import annotations


def should_summarize(messages: list[dict]) -> bool:
    return len(messages) > 10


def extract_summary(messages: list[dict]) -> str:
    points = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if isinstance(content, list):
            content = " ".join(
                p.get("text", "") for p in content if isinstance(p, dict)
            )
        if not content:
            continue
        if role == "user":
            points.append(f"- User asked: {content[:120]}")
        elif role == "assistant":
            first_sentence = content.split(".")[0].strip()
            if first_sentence:
                points.append(f"- AI responded: {first_sentence[:120]}")
    return "\n".join(points) if points else "No significant exchanges."


def build_summarized_history(messages: list[dict], keep_recent: int = 4) -> list[dict]:
    if len(messages) <= keep_recent:
        return messages

    older = messages[:-keep_recent]
    recent = messages[-keep_recent:]
    summary = extract_summary(older)

    summary_msg = {
        "role": "system",
        "content": f"[Conversation summary]\n{summary}",
    }
    return [summary_msg] + recent
