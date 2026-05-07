from openai import OpenAI, APIConnectionError
from typing import List, Optional, Dict, Any
import json
import os
from llmlib.models import Session

class OllamaTagger:
    """Handles session metadata generation and embedding using Ollama's OpenAI-compatible API."""
    
    def __init__(self, model="llama3.2:3b-instruct-q4_K_M", embed_model="nomic-embed-text",
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
        # Change 1: instructions moved OUT of JSON schema into plain-text section
        prompt = f"""Analyze this LLM chat session and extract structured metadata for a searchable knowledge library.
Output STRICT JSON only — no markdown fences, no explanation.

Title: {session.title}
Context:
{context}

Tag extraction rules (apply before writing JSON):
Extract 15–25 keywords covering ALL of the following categories:
1. Technical terms: algorithm, model, or architecture names
2. Function / class / file names actually mentioned in the session
3. Library / framework names
4. Metrics and numeric results (include both name and value, e.g. "NDCG@10", "0.1456")
5. Dataset / data file names
6. Core concept keywords from the user's questions
7. Programming language or CLI tools used

Rules:
- tags must be a flat array of plain strings only — no nested descriptions, no instruction text
- Aim for 15–25 tags; include only terms that genuinely appear in the session
- summary must be written entirely in English, 3–5 sentences
- question_type MUST be exactly one of: debug | design | research | howto

Output this JSON shape:
{{
    "topic": "<single noun or short phrase, e.g. FastAPI, Recommendation System>",
    "tags": ["<keyword1>", "<keyword2>", "..."],
    "question_type": "<debug|design|research|howto>",
    "summary": "<3–5 sentence English summary covering: what was asked, what was solved, key techniques, any numeric results>",
    "key_entities": ["<function name>", "<class name>", "<file name>", "<dataset name>", "..."]
}}"""

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
        """Generates an embedding for a session using title, summary, tags, entities, and user questions."""
        # Change 2: include raw user questions for better semantic match at query time
        tags_str = ", ".join(session.tags[:15]) if session.tags else ""
        entities_str = ", ".join(session.key_entities[:10]) if session.key_entities else ""

        user_questions = []
        for msg in session.messages[:10]:
            if msg.role in ["user", "human"]:
                user_questions.append(msg.content[:300].replace("\n", " ").strip())
            if len(user_questions) >= 3:
                break
        questions_str = " | ".join(user_questions)

        text_to_embed = f"""Title: {session.title}
Summary: {session.summary or ''}
Tags: {tags_str}
Key Entities: {entities_str}
User questions: {questions_str}"""

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
