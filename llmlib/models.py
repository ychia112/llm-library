from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator
import uuid

QuestionType = Literal["debug", "design", "research", "howto"]

class Message(BaseModel):
    """Represents a single message within an LLM session."""
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: Optional[datetime] = None

class Session(BaseModel):
    """Represents a complete LLM chat session with its metadata and messages."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str  # Original ID from platform
    platform: str  # "chatgpt" | "claude" | "gemini"
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[Message]
    
    # AI Generated Metadata
    topic: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    key_entities: List[str] = Field(default_factory=list)
    question_type: Optional[QuestionType] = None
    summary: Optional[str] = None
    embedding_id: Optional[int] = None # Reference to sqlite-vec row

    @field_validator("tags", "key_entities", mode="before")
    @classmethod
    def normalize_list(cls, value):
        if not value:
            return []
        return [str(v).strip() for v in value if str(v).strip()]
