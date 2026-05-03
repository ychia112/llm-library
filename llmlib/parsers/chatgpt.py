from pathlib import Path
from typing import Any, List, Optional
import json
from datetime import datetime, timezone
from llmlib.models import Session, Message
from llmlib.parsers.base import BaseParser


class ChatGPTParser(BaseParser):
    def parse(self, file_path: Path) -> List[Session]:
        """Parse ChatGPT conversations.json."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        conversations = data if isinstance(data, list) else [data]
        sessions: List[Session] = []

        for conversation in conversations:
            if not isinstance(conversation, dict):
                continue

            mapping = conversation.get("mapping")
            if not isinstance(mapping, dict):
                continue

            messages = self._traverse_tree(mapping)
            created_at = self._parse_timestamp(conversation.get("create_time"))
            updated_at = self._parse_timestamp(conversation.get("update_time"))

            if created_at is None and updated_at is None:
                created_at = updated_at = datetime.now(timezone.utc)
            elif created_at is None:
                created_at = updated_at
            elif updated_at is None:
                updated_at = created_at

            sessions.append(
                Session(
                    source_id=str(conversation.get("id", "")),
                    platform="chatgpt",
                    title=conversation.get("title") or "Untitled",
                    created_at=created_at,
                    updated_at=updated_at,
                    messages=messages,
                )
            )

        return sessions

    def _traverse_tree(self, mapping: dict[str, Any]) -> List[Message]:
        """Traverse mapping from root through first-child path."""
        if not mapping:
            return []

        children_to_parent: dict[str, str] = {}
        for node_id, node in mapping.items():
            if not isinstance(node, dict):
                continue
            children = node.get("children")
            if not isinstance(children, list):
                continue
            for child_id in children:
                if isinstance(child_id, str):
                    children_to_parent[child_id] = str(node_id)

        root_id = next(
            (
                str(node_id)
                for node_id, node in mapping.items()
                if isinstance(node, dict) and node.get("parent") is None
            ),
            None,
        )
        if root_id is None:
            root_id = next(
                (str(node_id) for node_id in mapping.keys() if str(node_id) not in children_to_parent),
                None,
            )
        if root_id is None:
            return []

        messages: List[Message] = []
        visited: set[str] = set()
        current_id: Optional[str] = root_id

        while current_id and current_id in mapping and current_id not in visited:
            visited.add(current_id)
            node = mapping.get(current_id)
            if not isinstance(node, dict):
                break

            message = self._message_from_node(node.get("message"))
            if message is not None:
                messages.append(message)

            children = node.get("children")
            if not isinstance(children, list) or not children:
                break

            first_child = children[0]
            current_id = first_child if isinstance(first_child, str) else None

        return messages

    def _message_from_node(self, message_data: Any) -> Optional[Message]:
        if not isinstance(message_data, dict):
            return None

        author = message_data.get("author")
        role = author.get("role") if isinstance(author, dict) else None
        if not isinstance(role, str) or role in {"system", "tool"}:
            return None

        content = message_data.get("content")
        parts = content.get("parts") if isinstance(content, dict) else None
        if not isinstance(parts, list):
            return None

        text_parts = [part for part in parts if isinstance(part, str) and part]
        if not text_parts:
            return None

        return Message(
            role=role,
            content="\n".join(text_parts),
            timestamp=self._parse_timestamp(message_data.get("create_time")),
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
