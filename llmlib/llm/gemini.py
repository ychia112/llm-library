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
        Uses Gemini 2.0 Flash Lite to generate metadata.
        Output: Dictionary containing 'topic', 'tags', 'question_type', and 'summary'.
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
                "key_entities": [e for e in data.get("key_entities", []) if isinstance(e, str)],
            }
        except (json.JSONDecodeError, Exception):
            return {
                "topic": "Unknown",
                "tags": [],
                "question_type": "research",
                "summary": "Failed to parse metadata",
                "key_entities": [],
            }

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
