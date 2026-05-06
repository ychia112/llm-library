from fastapi import FastAPI, HTTPException, Query, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime
import os
import time

from llmlib.storage.db import LibraryDB
from llmlib.models import Session, Message, QuestionType
from llmlib.parsers.chatgpt import ChatGPTParser
from llmlib.parsers.claude import ClaudeParser

app = FastAPI(title="llmlib Knowledge API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Models ---

class SessionSummary(BaseModel):
    id: str
    platform: str
    title: str
    topic: Optional[str]
    tags: List[str]
    key_entities: List[str] = []
    question_type: Optional[str]
    summary: Optional[str]
    created_at: datetime
    updated_at: datetime

class PaginatedSessions(BaseModel):
    sessions: List[SessionSummary]
    total: int

class TopicStats(BaseModel):
    topic: str
    count: int
    top_tags: List[str]

class QuestionTypeStats(BaseModel):
    question_type: str
    count: int

class PlatformStats(BaseModel):
    platform: str
    count: int

class TagStats(BaseModel):
    tag: str
    count: int

class LibraryOverview(BaseModel):
    total_sessions: int
    by_topic: List[TopicStats]
    by_question_type: List[QuestionTypeStats]
    by_platform: List[PlatformStats]
    top_tags: List[TagStats]
    recent_sessions: List[SessionSummary]

class IngestRequest(BaseModel):
    file_path: str
    platform: str # "chatgpt" | "claude"
    provider: str = "ollama"

class AskRequest(BaseModel):
    query: str
    platform: Optional[str] = None
    provider: str = "ollama"
    chat_model: Optional[str] = None

class AskResponse(BaseModel):
    answer: str
    hit_type: str # "hit" | "partial" | "miss"
    referenced_sessions: List[SessionSummary] = []
    tokens_used: int = 0

# --- DB Dependency ---
def get_db():
    with LibraryDB() as db:
        yield db

# --- Ingest Logic (Background) ---
def run_ingest(file_path: str, platform: str, provider: str):
    parser = ChatGPTParser() if platform.lower() == "chatgpt" else ClaudeParser()
    
    if provider.lower() == "ollama":
        from llmlib.llm.ollama import OllamaTagger
        tagger = OllamaTagger()
    else:
        from llmlib.llm.gemini import GeminiTagger
        tagger = GeminiTagger(api_key=os.getenv("GEMINI_API_KEY", ""))

    try:
        sessions = parser.parse(os.path.expanduser(file_path))
        with LibraryDB() as db:
            for session in sessions:
                metadata = tagger.tag_session(session)
                session.topic = metadata.get("topic")
                session.tags = metadata.get("tags", [])
                session.question_type = metadata.get("question_type")
                session.summary = metadata.get("summary")
                session.key_entities = metadata.get("key_entities", [])
                
                embedding = tagger.embed_session(session)
                db.upsert_session(session, embedding)
                
                if provider.lower() == "gemini":
                    time.sleep(float(os.getenv("LLMLIB_GEMINI_DELAY", "0")))
    except Exception as e:
        print(f"Ingest failed: {e}")

# --- Endpoints ---

@app.post("/ingest")
async def ingest_file(request: IngestRequest, background_tasks: BackgroundTasks):
    if not os.path.exists(os.path.expanduser(request.file_path)):
        raise HTTPException(status_code=400, detail="File not found")
    background_tasks.add_task(run_ingest, request.file_path, request.platform, request.provider)
    return {"message": "Ingest started in background"}

@app.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest, db: LibraryDB = Depends(get_db)):
    if request.provider.lower() == "ollama":
        from llmlib.llm.ollama import OllamaTagger
        tagger = OllamaTagger()
    else:
        from llmlib.llm.gemini import GeminiTagger
        tagger = GeminiTagger(api_key=os.getenv("GEMINI_API_KEY", ""))

    query_embedding = tagger.embed_query(request.query)
    results_with_scores = db.search_with_scores(query_embedding, top_k=20)
    
    if request.platform and request.platform.lower() != "all":
        results_with_scores = [r for r in results_with_scores if r[0].platform.lower() == request.platform.lower()]
    
    results = results_with_scores[:5]
    best_score = results[0][1] if results else 0.0
    
    if best_score >= 0.85:
        session, _ = results[0]
        return {
            "answer": f"Found a highly relevant conversation: {session.title}\n\nSummary: {session.summary}",
            "hit_type": "hit",
            "referenced_sessions": [SessionSummary(**session.model_dump())],
            "tokens_used": 0
        }
    
    context_text = ""
    hit_type = "miss"
    ref_sessions = []
    
    if best_score >= 0.60:
        hit_type = "partial"
        context_parts = []
        for s, _ in results[:3]:
            context_parts.append(f"Related Session: {s.title}\nSummary: {s.summary}")
            ref_sessions.append(SessionSummary(**s.model_dump()))
        context_text = "Use this context from previous chats:\n" + "\n\n".join(context_parts)
    
    if request.provider.lower() == "ollama":
        from llmlib.llm.ollama import OllamaTagger
        tagger_ollama = tagger
        system_prompt = f"You are a helpful knowledge base assistant. {context_text}"
        answer = tagger_ollama.chat(system_prompt, request.query, model=request.chat_model)
    else:
        answer = "Gemini chat fallback not yet implemented in API"

    return {
        "answer": answer,
        "hit_type": hit_type,
        "referenced_sessions": ref_sessions,
        "tokens_used": -1
    }

@app.get("/sessions", response_model=PaginatedSessions)
def list_sessions(
    tag: Optional[str] = None,
    platform: Optional[str] = None,
    question_type: Optional[str] = None,
    topic: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: LibraryDB = Depends(get_db)
):
    sessions, total = db.list_sessions(
        tag=tag,
        platform=platform,
        question_type=question_type,
        topic=topic,
        limit=limit,
        offset=offset,
        return_total=True,
    )
    return {
        "sessions": [SessionSummary(**s.model_dump()) for s in sessions],
        "total": total
    }

@app.get("/sessions/{id}", response_model=Session)
def get_session(id: str, db: LibraryDB = Depends(get_db)):
    session = db.get_session(id)
    if not session: raise HTTPException(status_code=404, detail="Session not found")
    return session

@app.get("/library/overview", response_model=LibraryOverview)
def get_overview(db: LibraryDB = Depends(get_db)):
    stats = db.get_library_overview()
    stats["recent_sessions"] = [SessionSummary(**s.model_dump()) for s in stats["recent_sessions"]]
    return stats

@app.get("/library/topics", response_model=List[TopicStats])
def get_topics(db: LibraryDB = Depends(get_db)):
    return db.get_topics()

@app.get("/library/tags", response_model=List[TagStats])
def get_tags(topic: Optional[str] = None, db: LibraryDB = Depends(get_db)):
    return db.get_tags(topic=topic)
