from openai import OpenAI, APIConnectionError
from typing import List, Optional, Dict, Any
import json
import os
from llmlib.models import Session

class OllamaTagger:
    """Handles session metadata generation and embedding using Ollama's OpenAI-compatible API."""
    
    def __init__(self, model="gemma4:26b", embed_model="nomic-embed-text",
                 base_url="http://localhost:11434/v1"):
        """Initializes the Ollama client using OpenAI SDK."""
        self.client = OpenAI(base_url=base_url, api_key="ollama", timeout=60.0)
        self.model = model
        self.embed_model = embed_model

    def _build_context(self, session: Session) -> str:
        """
        Builds a richer context for tagging.
        - Takes up to 20 messages (instead of 10)
        - User messages: up to 600 chars
        - Assistant messages: up to 800 chars (preserves technical detail, code, results)
        """
        lines = []
        for msg in session.messages[:20]:
            prefix = "U" if msg.role in ["user", "human"] else "A"
            if prefix == "U":
                content = msg.content[:600].replace("\n", " ").strip()
            else:
                # Preserve more content and structure for assistant messages
                content = msg.content[:800].strip()
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
Analyze the following LLM chat session and extract detailed metadata for a searchable knowledge library.
Output strict JSON only, no markdown fence.

Title: {session.title}
Context:
{context}

Expected JSON schema:
{{
    "topic": "Single noun or short phrase describing the main subject (e.g. Recommendation System, BPR Loss, FastAPI)",
    "tags": [
        "Extract 15-25 keywords covering ALL of the following categories:",
        "1. Technical terms: algorithm, model, or architecture names (e.g. collaborative filtering, Alpha Gating, HybridRecommender)",
        "2. Function / class / file names: every function, class, or filename mentioned (e.g. recommend.py, embed_session, _build_context)",
        "3. Library / framework names: every library or framework mentioned (e.g. TensorFlow, BeautifulSoup4, pandas)",
        "4. Metrics and numeric results: all metric names AND their values (e.g. NDCG@10, HR@10, AUC, 0.1456, 0.2341)",
        "5. Dataset / data file names: any data files referenced (e.g. userrealinteraction.csv, searchresultwithclicks.json)",
        "6. Core concept keywords: the key terms from the user's actual questions (e.g. embedding, triplet loss, geo-aware ranking)",
        "7. Language / tooling: programming language or CLI tools used (e.g. Python, bash, curl)"
    ],
    "question_type": "One of: debug | design | research | howto",
    "summary": "3-5 sentences covering: (1) what was asked, (2) what was solved, (3) key techniques or methods used, (4) any specific numeric results if present",
    "key_entities": ["List every concrete name that appears in the session: function names, class names, file names, dataset names, model names — one entry per item"]
}}

Important rules:
- tags must be a flat array of plain strings — no nested descriptions, only real keywords
- Aim for 15-25 tags; more is better as long as every tag genuinely appears in the session
- summary must be written entirely in English
- question_type MUST be exactly one of [debug, design, research, howto]
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
                "key_entities": [e for e in data.get("key_entities", []) if isinstance(e, str)],
            }
        except APIConnectionError:
            raise ConnectionError("Failed to connect to Ollama. Please ensure 'ollama serve' is running.")
        except (json.JSONDecodeError, Exception):
            return {
                "topic": "Unknown",
                "tags": [],
                "question_type": "research",
                "summary": "Failed to parse metadata",
                "key_entities": [],
            }

    def chat(self, system_prompt: str, user_message: str, model: Optional[str] = None) -> str:
        """用 chat model 回答問題，回傳純文字。"""
        chat_model = model or os.getenv("LLMLIB_OLLAMA_CHAT_MODEL", "gemma4:26b")
        try:
            response = self.client.chat.completions.create(
                model=chat_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content
        except APIConnectionError:
            return "Error: 無法連線到 Ollama。請確認 Ollama 正在執行：ollama serve"
        except Exception as e:
            return f"Error: {str(e)}"

    def embed_session(self, session: Session) -> List[float]:
        """Generates an embedding for a session using title, topic, tags, entities, and summary."""
        tags_str = ", ".join(session.tags) if session.tags else ""
        entities_str = ", ".join(session.key_entities) if session.key_entities else ""

        text_to_embed = f"""Title: {session.title}
Topic: {session.topic or ''}
Tags: {tags_str}
Key Entities: {entities_str}
Summary: {session.summary or ''}"""
        return self._get_embedding(text_to_embed)

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
