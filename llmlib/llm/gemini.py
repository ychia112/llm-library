import google.generativeai as genai
from typing import List, Optional
from llmlib.models import Session

class GeminiClient:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def tag_session(self, session: Session) -> Session:
        """Use Gemini to generate topic, tags, and summary."""
        # Implementation logic
        return session

    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for a piece of text."""
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document"
        )
        return result['embedding']
