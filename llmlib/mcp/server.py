import json
import os
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from llmlib.models import Message, Session
from llmlib.storage.db import LibraryDB

mcp = FastMCP("llmlib")


def _get_tagger():
    provider = os.getenv("LLMLIB_PROVIDER", "ollama").lower()
    if provider == "gemini":
        from llmlib.llm.gemini import GeminiTagger
        api_key = os.environ["GEMINI_API_KEY"]
        model = os.getenv("LLMLIB_GEMINI_MODEL", "gemini-2.0-flash-lite")
        return GeminiTagger(api_key=api_key, model=model)
    from llmlib.llm.ollama import OllamaTagger
    model = os.getenv("LLMLIB_OLLAMA_MODEL", "llama3.2:3b-instruct-q4_K_M")
    return OllamaTagger(model=model)


def _format_tree_for_prompt(tree: dict) -> str:
    if not tree:
        return "(empty — this will be the first session)"
    lines = []
    for topic, subtopics in sorted(tree.items()):
        lines.append(f"- {topic}")
        for sub, count in sorted(subtopics.items(), key=lambda x: -x[1]):
            lines.append(f"    • {sub} ({count} sessions)")
    return "\n".join(lines)


def _assign_knowledge_tree(session: Session, tagger, db: LibraryDB) -> tuple[str, str]:
    """Ask the LLM to place the session into the 2-level knowledge tree."""
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

    try:
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


@mcp.tool()
def search_library(query: str, top_k: int = 5) -> str:
    """Search the local knowledge library using semantic similarity. Returns ranked sessions with scores, titles, topics, summaries, and tags."""
    tagger = _get_tagger()
    with LibraryDB() as db:
        embedding = tagger.embed_query(query)
        results = db.search_with_scores(embedding, top_k=top_k)

    if not results:
        return "No matching sessions found in library."

    parts = []
    for session, score in results:
        sub = session.sub_topic or "—"
        parts.append(
            f"[{score:.2f}] {session.title}\n"
            f"  id: {session.id}\n"
            f"  topic: {session.topic or '—'} / {sub}\n"
            f"  summary: {session.summary or '(none)'}\n"
            f"  tags: {', '.join(session.tags) if session.tags else '—'}"
        )
    return "\n\n".join(parts)


@mcp.tool()
def get_session(session_id: str) -> str:
    """Retrieve a full session by ID, including all messages, metadata, and knowledge tree placement."""
    with LibraryDB() as db:
        session = db.get_session(session_id)

    if session is None:
        return f"Session not found: {session_id}"

    lines = [
        f"id: {session.id}",
        f"title: {session.title}",
        f"platform: {session.platform}",
        f"topic: {session.topic or '—'} / {session.sub_topic or '—'}",
        f"question_type: {session.question_type or '—'}",
        f"summary: {session.summary or '—'}",
        f"tags: {', '.join(session.tags) if session.tags else '—'}",
        f"key_entities: {', '.join(session.key_entities) if session.key_entities else '—'}",
        f"created_at: {session.created_at.isoformat()}",
        "",
        "--- Messages ---",
    ]
    for msg in session.messages:
        ts = f" ({msg.timestamp.isoformat()})" if msg.timestamp else ""
        lines.append(f"[{msg.role}]{ts}: {msg.content}")

    return "\n".join(lines)


@mcp.tool()
def get_knowledge_tree() -> str:
    """Return the 2-level knowledge tree (topic → sub_topic → session count) for the local library."""
    with LibraryDB() as db:
        tree = db.get_knowledge_tree()

    if not tree:
        return "Library is empty — no knowledge tree yet."

    total_sessions = sum(sum(subs.values()) for subs in tree.values())
    lines = [f"Knowledge Tree — {total_sessions} sessions across {len(tree)} topics\n"]
    for topic in sorted(tree):
        subtopics = tree[topic]
        topic_count = sum(subtopics.values())
        lines.append(f"{topic} ({topic_count})")
        for sub, count in sorted(subtopics.items(), key=lambda x: -x[1]):
            lines.append(f"  • {sub} ({count})")

    return "\n".join(lines)


@mcp.tool()
def ingest_session(
    title: str,
    messages: list[dict],
    platform: str = "claude_code",
) -> str:
    """Ingest a new session into the knowledge library. Automatically tags, embeds, and places it in the 2-level knowledge tree. messages should be a list of {role, content, timestamp?} dicts."""
    tagger = _get_tagger()

    parsed_messages = []
    for m in messages:
        ts = None
        if m.get("timestamp"):
            try:
                ts = datetime.fromisoformat(m["timestamp"])
            except ValueError:
                pass
        parsed_messages.append(Message(
            role=m.get("role", "user"),
            content=m.get("content", ""),
            timestamp=ts,
        ))

    now = datetime.now(timezone.utc)
    session = Session(
        source_id=f"mcp-{int(now.timestamp())}",
        platform=platform,
        title=title,
        created_at=now,
        updated_at=now,
        messages=parsed_messages,
    )

    with LibraryDB() as db:
        metadata = tagger.tag_session(session)
        session.topic = metadata.get("topic")
        raw_tags = metadata.get("tags", [])
        session.tags = [t for t in raw_tags if isinstance(t, str)]
        qtype = metadata.get("question_type")
        session.question_type = qtype if qtype in {"debug", "design", "research", "howto"} else "research"
        session.summary = metadata.get("summary")
        session.key_entities = [e for e in metadata.get("key_entities", []) if isinstance(e, str)]

        topic, sub_topic = _assign_knowledge_tree(session, tagger, db)
        session.topic = topic
        session.sub_topic = sub_topic

        embedding = tagger.embed_session(session)
        db.upsert_session(session, embedding)

    return (
        f"Ingested: {session.id}\n"
        f"title: {session.title}\n"
        f"topic: {session.topic} / {session.sub_topic}\n"
        f"question_type: {session.question_type}\n"
        f"tags: {', '.join(session.tags) if session.tags else '—'}"
    )


def main():
    mcp.run()


if __name__ == "__main__":
    main()
