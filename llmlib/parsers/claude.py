from pathlib import Path
from typing import Any, List, Optional
import json
from datetime import datetime, timezone
from llmlib.models import Session, Message
from llmlib.parsers.base import BaseParser


class ClaudeParser(BaseParser):
    """Parser for Claude conversations export files."""
    def parse(self, file_path: Path) -> List[Session]:
        """Parses Claude conversations.json."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        conversations = data if isinstance(data, list) else [data]
        sessions: List[Session] = []

        for conversation in conversations:
            if not isinstance(conversation, dict):
                continue

            raw_messages = conversation.get("chat_messages")
            if not isinstance(raw_messages, list):
                raw_messages = conversation.get("messages")
            if not isinstance(raw_messages, list):
                raw_messages = []

            messages: List[Message] = []
            for raw in raw_messages:
                parsed = self._message_from_raw(raw)
                if parsed is not None:
                    messages.append(parsed)

            created_at = self._parse_timestamp(
                conversation.get("created_at") or conversation.get("create_time")
            )
            updated_at = self._parse_timestamp(
                conversation.get("updated_at") or conversation.get("update_time")
            )

            if created_at is None and updated_at is None:
                created_at = updated_at = datetime.now(timezone.utc)
            elif created_at is None:
                created_at = updated_at
            elif updated_at is None:
                updated_at = created_at

            sessions.append(
                Session(
                    source_id=str(
                        conversation.get("uuid")
                        or conversation.get("id")
                        or conversation.get("conversation_id")
                        or ""
                    ),
                    platform="claude",
                    title=conversation.get("name")
                    or conversation.get("title")
                    or "Untitled",
                    created_at=created_at,
                    updated_at=updated_at,
                    messages=messages,
                )
            )

        return sessions

    def _message_from_raw(self, raw: Any) -> Optional[Message]:
        if not isinstance(raw, dict):
            return None

        role = raw.get("sender") or raw.get("role")
        if not role and isinstance(raw.get("author"), dict):
            role = raw["author"].get("role")
        if not isinstance(role, str):
            return None

        content: Optional[str] = None
        if isinstance(raw.get("text"), str):
            content = raw.get("text")
        elif isinstance(raw.get("content"), str):
            content = raw.get("content")
        elif isinstance(raw.get("content"), dict):
            parts = raw["content"].get("parts")
            if isinstance(parts, list):
                text_parts = [part for part in parts if isinstance(part, str) and part]
                content = "\n".join(text_parts) if text_parts else None

        if not isinstance(content, str) or not content:
            return None

        return Message(
            role=role,
            content=content,
            timestamp=self._parse_timestamp(raw.get("created_at") or raw.get("create_time")),
        )

    def _parse_timestamp(self, value: Any) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        if isinstance(value, str):
            try:
                return datetime.fromtimestamp(float(value), tz=timezone.utc)
            except ValueError:
                pass
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None
