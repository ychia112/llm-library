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
                # Preserve more content and structure for assistant messages
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
        """Generates an embedding for a session using its title and summary."""
        tags_str = ", ".join(session.tags) if session.tags else ""
        entities_str = ", ".join(session.key_entities) if session.key_entities else ""

        text_to_embed = f"""Title: {session.title}
Topic: {session.topic or ''}
Tags: {tags_str}
Key Entities: {entities_str}
Summary: {session.summary or ''}"""
        
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
