from google import genai
from google.genai import types
from typing import List, Optional, Dict, Any
import json
from llmlib.models import Session

class GeminiTagger:
    """Handles session metadata generation and embedding using Gemini API."""
    
    def __init__(self, api_key: str, model="gemini-2.0-flash-lite"):
        """Initializes the Gemini client with the provided API key."""
        self.client = genai.Client(api_key=api_key)
        self.tagger_model = model
        self.embedding_model = "text-embedding-004"

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
        Uses Gemini 2.0 Flash Lite to generate metadata.
        Output: Dictionary containing 'topic', 'tags', 'question_type', and 'summary'.
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
            response = self.client.models.generate_content(
                model=self.tagger_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0
                ),
            )
            data = json.loads(response.text)
            
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
        except (json.JSONDecodeError, Exception):
            return {
                "topic": "Unknown",
                "tags": [],
                "question_type": "research",
                "summary": "Failed to parse metadata"
            }

    def embed_session(self, session: Session) -> List[float]:
        """Generates an embedding for a session using its title and summary."""
        text_to_embed = f"Title: {session.title}\nSummary: {session.summary or ''}"
        
        response = self.client.models.embed_content(
            model=self.embedding_model,
            contents=text_to_embed,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
        )
        return response.embeddings[0].values

    def embed_query(self, query: str) -> List[float]:
        """Generates an embedding for a search query."""
        response = self.client.models.embed_content(
            model=self.embedding_model,
            contents=query,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
        )
        return response.embeddings[0].values
