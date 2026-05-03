from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
import uuid

class Message(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: Optional[datetime] = None

class Session(BaseModel):
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
    question_type: Optional[str] = None # "debug" | "design" | "research" | "howto"
    summary: Optional[str] = None
    embedding_id: Optional[int] = None # Reference to sqlite-vec row
