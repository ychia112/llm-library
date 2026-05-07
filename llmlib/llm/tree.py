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


def assign_knowledge_tree(session: Session, tagger, db: "LibraryDB") -> tuple[str, str]:
    """
    Ask the LLM to assign a topic and sub_topic to a session.
    Returns (topic, sub_topic). Falls back to (session.topic or "General", "General") on any error.
    Uses only db.get_knowledge_tree() — never reads raw session bodies.
    """
    try:
        tree = db.get_knowledge_tree()
        tree_text = _format_tree_for_prompt(tree)

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
        data = json.loads(cleaned.strip())
        topic = str(data.get("topic", "General")).strip() or "General"
        sub_topic = str(data.get("sub_topic", "General")).strip() or "General"
        return topic, sub_topic
    except Exception:
        return session.topic or "General", "General"
