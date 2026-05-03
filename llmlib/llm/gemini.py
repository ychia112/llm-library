from google import genai
from google.genai import types
from typing import List, Dict, Any
import json
from llmlib.models import Session

class GeminiTagger:
    """Handles session metadata generation and embedding using Gemini API."""
    def __init__(self, api_key: str):
        """Initializes the Gemini client with the provided API key."""
        self.client = genai.Client(api_key=api_key)
        self.tagger_model = "gemini-2.0-flash"
        self.embedding_model = "text-embedding-004" # google-genai uses this name

    def tag_session(self, session: Session) -> Dict[str, Any]:
        """
        Uses Gemini 2.0 Flash to generate topic, tags, question_type, and summary.
        Input: session object.
        Output: Dictionary containing 'topic', 'tags', 'question_type', and 'summary'.
        """
        # Prepare context: Title + first 5 messages
        context_msgs = session.messages[:5]
        messages_text = "\n".join([f"{m.role}: {m.content}" for m in context_msgs])
        
        prompt = f"""
        Analyze the following LLM chat session and provide metadata in strict JSON format.
        
        Title: {session.title}
        Messages:
        {messages_text}
        
        Expected JSON schema:
        {{
            "topic": "Brief topic name (e.g. Python, Machine Learning)",
            "tags": ["list", "of", "relevant", "keywords"],
            "question_type": "one of: debug, design, research, howto",
            "summary": "One-sentence summary of the session"
        }}
        
        Constraint: question_type MUST be exactly one of [debug, design, research, howto].
        """

        response = self.client.models.generate_content(
            model=self.tagger_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        
        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            # Fallback or error handling if needed
            return {
                "topic": "Unknown",
                "tags": [],
                "question_type": "research",
                "summary": "Failed to parse metadata"
            }

    def embed_session(self, session: Session) -> List[float]:
        """
        Generates an embedding for a session using its title and summary.
        """
        text_to_embed = f"Title: {session.title}\nSummary: {session.summary or ''}"
        
        response = self.client.models.embed_content(
            model=self.embedding_model,
            contents=text_to_embed,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
        )
        
        return response.embeddings[0].values

    def embed_query(self, query: str) -> List[float]:
        """
        Generates an embedding for a search query.
        """
        response = self.client.models.embed_content(
            model=self.embedding_model,
            contents=query,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
        )
        return response.embeddings[0].values
