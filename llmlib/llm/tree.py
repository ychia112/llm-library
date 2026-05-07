import json
from typing import TYPE_CHECKING

from llmlib.models import Session

if TYPE_CHECKING:
    from llmlib.storage.db import LibraryDB


def _format_tree_for_prompt(tree: dict) -> str:
    if not tree:
        return "(empty — this will be the first session)"
    lines = []
    for topic, subtopics in sorted(tree.items()):
        lines.append(f"- {topic}")
        for sub, count in sorted(subtopics.items(), key=lambda x: -x[1]):
            lines.append(f"    • {sub} ({count} sessions)")
    return "\n".join(lines)


def _parse_batch_response(response: str, batch: list[Session]) -> list[tuple[str, str]] | None:
    """Parse a JSON array response. Returns None if parsing fails or length mismatches."""
    cleaned = response.strip()
    if cleaned.startswith("```"):
        parts = cleaned.split("```")
        cleaned = parts[1] if len(parts) > 1 else parts[0]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    try:
        data = json.loads(cleaned.strip())
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, list) or len(data) != len(batch):
        return None
    results = []
    for item in data:
        topic = str(item.get("topic", "General")).strip() or "General"
        sub_topic = str(item.get("sub_topic", "General")).strip() or "General"
        results.append((topic, sub_topic))
    return results


def _fallback_single(session: Session, tagger, tree_text: str) -> tuple[str, str]:
    """Classify one session individually; returns ("General", "General") on any error."""
    try:
        system_prompt = (
            "You assign sessions to a 2-level knowledge tree. "
            "Prefer reusing existing topics/sub-topics when a reasonable match exists. "
            "Return ONLY a JSON object with keys 'topic' and 'sub_topic', no extra text."
        )
        user_msg = (
            f"Existing tree:\n{tree_text}\n\n"
            f"Session title: {session.title}\n"
            f"Summary: {session.summary or '(none)'}\n"
            f"Tags: {', '.join(session.tags) if session.tags else '(none)'}\n\n"
            'Assign topic and sub_topic (2–5 words each). '
            'Reply with JSON only: {"topic": "...", "sub_topic": "..."}'
        )
        chat_model = getattr(tagger, "model", None)
        response = tagger.chat(system_prompt, user_msg, model=chat_model)
        cleaned = response.strip()
        if cleaned.startswith("```"):
            parts = cleaned.split("```")
            cleaned = parts[1] if len(parts) > 1 else parts[0]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        item = json.loads(cleaned.strip())
        topic = str(item.get("topic", "General")).strip() or "General"
        sub_topic = str(item.get("sub_topic", "General")).strip() or "General"
        return topic, sub_topic
    except Exception:
        return session.topic or "General", "General"


def assign_knowledge_tree_batch(
    sessions: list[Session],
    tagger,
    db: "LibraryDB",
    batch_size: int = 10,
) -> list[tuple[str, str]]:
    """
    Classify a list of sessions into the knowledge tree in batches.
    Returns a list of (topic, sub_topic) tuples, same order as input.
    Falls back to ("General", "General") for any session that fails.
    """
    if not sessions:
        return []

    tree = db.get_knowledge_tree()
    tree_text = _format_tree_for_prompt(tree)
    chat_model = getattr(tagger, "model", None)
    results: list[tuple[str, str]] = []

    for batch_start in range(0, len(sessions), batch_size):
        batch = sessions[batch_start : batch_start + batch_size]

        session_lines = []
        for i, s in enumerate(batch):
            session_lines.append(
                f"[{i}] Title: {s.title}\n"
                f"    Summary: {s.summary or '(none)'}\n"
                f"    Tags: {', '.join(s.tags) if s.tags else '(none)'}"
            )

        system_prompt = (
            "You assign sessions to a 2-level knowledge tree. "
            "Prefer reusing existing topics/sub-topics when a reasonable match exists. "
            "Return ONLY a JSON array, one object per session, in the same order as input."
        )
        user_msg = (
            f"Existing tree:\n{tree_text}\n\n"
            f"Classify these {len(batch)} sessions:\n"
            + "\n\n".join(session_lines)
            + "\n\nReply with a JSON array only:\n"
            + '[{"topic": "...", "sub_topic": "..."}, ...]'
        )

        try:
            response = tagger.chat(system_prompt, user_msg, model=chat_model)
            batch_results = _parse_batch_response(response, batch)
        except Exception:
            batch_results = None

        if batch_results is not None:
            results.extend(batch_results)
        else:
            # Fall back to individual calls for each session in this batch
            for s in batch:
                results.append(_fallback_single(s, tagger, tree_text))

    return results


def assign_knowledge_tree(session: Session, tagger, db: "LibraryDB") -> tuple[str, str]:
    """
    Ask the LLM to assign a topic and sub_topic to a session.
    Returns (topic, sub_topic). Falls back to (session.topic or "General", "General") on any error.
    Uses only db.get_knowledge_tree() — never reads raw session bodies.
    """
    results = assign_knowledge_tree_batch([session], tagger, db, batch_size=1)
    return results[0]
