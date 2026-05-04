from openai import OpenAI, APIConnectionError
from typing import List, Optional, Dict, Any
import json
from llmlib.models import Session

class OllamaTagger:
    """Handles session metadata generation and embedding using Ollama's OpenAI-compatible API."""
    
    def __init__(self, model="gemma4:26b", embed_model="nomic-embed-text",
                 base_url="http://localhost:11434/v1"):
        """Initializes the Ollama client using OpenAI SDK."""
        self.client = OpenAI(base_url=base_url, api_key="ollama")
        self.model = model
        self.embed_model = embed_model

    def _build_context(self, session: Session) -> str:
        """Constructs a condensed context from session messages."""
        lines = []
        for msg in session.messages[:10]:
            prefix = "U" if msg.role in ["user", "human"] else "A"
            limit = 300 if prefix == "U" else 220
            content = msg.content[:limit].replace("\n", " ").strip()
            if content:
                lines.append(f"{prefix}: {content}")
        return "\n".join(lines)

    def tag_session(self, session: Session) -> Dict[str, Any]:
        """
        Generates metadata using Ollama.
        Output: strict JSON (topic, tags, question_type, summary).
        """
        context = self._build_context(session)
        prompt = f"""
Analyze the following LLM chat session and provide metadata in strict JSON format.
Output strict JSON only, no markdown fence.

Title: {session.title}
Context:
{context}

Expected JSON schema:
{{
    "topic": "主要主題（單一名詞，例如 FastAPI、Machine Learning）",
    "tags": ["列出 6-10 個關鍵字，需覆蓋 session 內所有出現的主題，不只主題"],
    "question_type": "debug | design | research | howto 擇一",
    "summary": "一句話總結，說明這個 session 解決了什麼問題"
}}

Constraint: question_type MUST be exactly one of [debug, design, research, howto].
"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0
            )
            data = json.loads(response.choices[0].message.content)
            
            valid_types = {"debug", "design", "research", "howto"}
            qtype = data.get("question_type", "research")
            if qtype not in valid_types:
                qtype = "research"
            
            return {
                "topic": data.get("topic") or "Unknown",
                "tags": [t for t in data.get("tags", []) if isinstance(t, str)],
                "question_type": qtype,
                "summary": data.get("summary") or "No summary",
            }
        except APIConnectionError:
            raise ConnectionError("Failed to connect to Ollama. Please ensure 'ollama serve' is running.")
        except (json.JSONDecodeError, Exception):
            return {
                "topic": "Unknown",
                "tags": [],
                "question_type": "research",
                "summary": "Failed to parse metadata"
            }

    def embed_session(self, session: Session) -> List[float]:
        """Generates an embedding using nomic-embed-text via Ollama."""
        text = f"Title: {session.title}\nSummary: {session.summary or ''}"
        return self._get_embedding(text)

    def embed_query(self, query: str) -> List[float]:
        """Generates an embedding for a query string."""
        return self._get_embedding(query)

    def _get_embedding(self, text: str) -> List[float]:
        try:
            response = self.client.embeddings.create(
                model=self.embed_model,
                input=text
            )
            return response.data[0].embedding
        except APIConnectionError:
            raise ConnectionError("Failed to connect to Ollama. Please ensure 'ollama serve' is running.")
