from fastapi import FastAPI, HTTPException, Query, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import time

from llmlib.storage.db import LibraryDB
from llmlib.models import Session, Message, QuestionType
from llmlib.parsers.chatgpt import ChatGPTParser
from llmlib.parsers.claude import ClaudeParser
from llmlib.llm.tree import assign_knowledge_tree, assign_knowledge_tree_batch

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
    sub_topic: Optional[str] = None
    tags: List[str]
    key_entities: List[str] = []
    question_type: Optional[str]
    summary: Optional[str]
    created_at: datetime
    updated_at: datetime

class PaginatedSessions(BaseModel):
    sessions: List[SessionSummary]
    total: int

class QuestionTypeStats(BaseModel):
    question_type: str
    count: int

class TopicStats(BaseModel):
    topic: str
    count: int
    top_tags: List[str]
    by_question_type: List[QuestionTypeStats] = []
    top_entities: List[str] = []

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

class RetopicizeRequest(BaseModel):
    provider: str = "ollama"
    target_topics: int = 15
    dry_run: bool = False

# --- DB Dependency ---
def get_db():
    with LibraryDB() as db:
        yield db

# --- Ingest Status ---
_ingest_state: dict = {
    "running": False, "total": 0, "processed": 0, "current_title": "", "error": None
}

# --- Retopicize Status ---
_retopicize_state: dict = {
    "running": False, "done": False, "clusters_found": 0, "total": 0, "error": None
}

_INGEST_WORKERS = int(os.getenv("LLMLIB_INGEST_WORKERS", "4"))

def _tag_and_embed(session, tagger):
    """Tag and embed a single session. Runs in a worker thread."""
    metadata = tagger.tag_session(session)
    session.topic = metadata.get("topic")
    session.tags = metadata.get("tags", [])
    session.question_type = metadata.get("question_type")
    session.summary = metadata.get("summary")
    session.key_entities = metadata.get("key_entities", [])
    embedding = tagger.embed_session(session)
    return session, embedding

# --- Ingest Logic (Background) ---
def run_ingest(file_path: str, platform: str, provider: str):
    global _ingest_state
    _ingest_state = {"running": True, "total": 0, "processed": 0, "current_title": "", "error": None}

    parser = ChatGPTParser() if platform.lower() == "chatgpt" else ClaudeParser()

    if provider.lower() == "ollama":
        from llmlib.llm.ollama import OllamaTagger
        tagger = OllamaTagger()
    else:
        from llmlib.llm.gemini import GeminiTagger
        tagger = GeminiTagger(api_key=os.getenv("GEMINI_API_KEY", ""))

    try:
        sessions = parser.parse(os.path.expanduser(file_path))
        _ingest_state["total"] = len(sessions)

        workers = 1 if provider.lower() == "gemini" else _INGEST_WORKERS

        with LibraryDB() as db:
            # Phase 1: parallel tag + embed
            tagged_results: list[tuple] = []
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {pool.submit(_tag_and_embed, s, tagger): s for s in sessions}
                for future in as_completed(futures):
                    try:
                        session, embedding = future.result()
                        tagged_results.append((session, embedding))
                    except Exception as e:
                        print(f"Failed to tag session: {e}")
                    finally:
                        _ingest_state["processed"] += 1
                        _ingest_state["current_title"] = futures[future].title

                    if provider.lower() == "gemini":
                        time.sleep(float(os.getenv("LLMLIB_GEMINI_DELAY", "0")))

            # Phase 2: batch classify topics (one LLM call per 10 sessions)
            tagged_sessions = [s for s, _ in tagged_results]
            topic_assignments = assign_knowledge_tree_batch(tagged_sessions, tagger, db)

            # Phase 3: upsert all
            for (session, embedding), (topic, sub_topic) in zip(tagged_results, topic_assignments):
                session.topic = topic
                session.sub_topic = sub_topic
                db.upsert_session(session, embedding)
    except Exception as e:
        _ingest_state["error"] = str(e)
        print(f"Ingest failed: {e}")
    finally:
        _ingest_state["running"] = False

# --- Retopicize Logic (Background) ---
def _run_retopicize(provider: str, target_topics: int, dry_run: bool):
    global _retopicize_state
    _retopicize_state = {"running": True, "done": False, "clusters_found": 0, "total": 0, "error": None}

    if provider.lower() == "ollama":
        from llmlib.llm.ollama import OllamaTagger
        tagger = OllamaTagger()
    else:
        from llmlib.llm.gemini import GeminiTagger
        tagger = GeminiTagger(api_key=os.getenv("GEMINI_API_KEY", ""))

    try:
        from llmlib.cluster import retopicize
        with LibraryDB() as db:
            result = retopicize(db, tagger, target_topics=target_topics, dry_run=dry_run)
        _retopicize_state["clusters_found"] = result["clusters_found"]
        _retopicize_state["total"] = result["total"]
    except ImportError:
        _retopicize_state["error"] = "Cluster dependencies not installed. Run: pip install 'llmlib[cluster]'"
    except Exception as e:
        _retopicize_state["error"] = str(e)
        print(f"Retopicize failed: {e}")
    finally:
        _retopicize_state["running"] = False
        _retopicize_state["done"] = True

# --- Endpoints ---

@app.post("/ingest")
async def ingest_file(request: IngestRequest, background_tasks: BackgroundTasks):
    if not os.path.exists(os.path.expanduser(request.file_path)):
        raise HTTPException(status_code=400, detail="File not found")
    background_tasks.add_task(run_ingest, request.file_path, request.platform, request.provider)
    return {"message": "Ingest started in background"}

@app.get("/ingest/status")
def get_ingest_status():
    return _ingest_state

@app.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest, db: LibraryDB = Depends(get_db)):
    if request.provider.lower() == "ollama":
        from llmlib.llm.ollama import OllamaTagger
        tagger = OllamaTagger()
    else:
        from llmlib.llm.gemini import GeminiTagger
        tagger = GeminiTagger(api_key=os.getenv("GEMINI_API_KEY", ""))

    query_embedding = tagger.embed_query(request.query)

    # Change 4: pass keyword hint for hybrid pre-filtering
    query_words = request.query.strip().split()
    keyword_hint = query_words[0] if len(query_words) > 1 else None

    results_with_scores = db.search_with_scores(query_embedding, top_k=20, keyword=keyword_hint)
    
    if request.platform and request.platform.lower() != "all":
        results_with_scores = [r for r in results_with_scores if r[0].platform.lower() == request.platform.lower()]
    
    results = results_with_scores[:5]
    best_score = results[0][1] if results else 0.0
    
    if best_score >= 0.72:
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
    
    if best_score >= 0.50:
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
    return LibraryOverview(
        total_sessions=stats["total_sessions"],
        by_topic=[TopicStats(**t) for t in stats["by_topic"]],
        by_question_type=[QuestionTypeStats(**q) for q in stats["by_question_type"]],
        by_platform=[PlatformStats(**p) for p in stats["by_platform"]],
        top_tags=[TagStats(**t) for t in stats["top_tags"]],
        recent_sessions=[SessionSummary(**s.model_dump()) for s in stats["recent_sessions"]],
    )

@app.get("/library/topics", response_model=List[TopicStats])
def get_topics(db: LibraryDB = Depends(get_db)):
    return [TopicStats(**t) for t in db.get_topics()]

@app.get("/library/tags", response_model=List[TagStats])
def get_tags(topic: Optional[str] = None, db: LibraryDB = Depends(get_db)):
    return db.get_tags(topic=topic)

@app.post("/library/retopicize")
async def retopicize_library(request: RetopicizeRequest, background_tasks: BackgroundTasks):
    """Re-cluster all sessions using embeddings. Run after large imports."""
    background_tasks.add_task(_run_retopicize, request.provider, request.target_topics, request.dry_run)
    return {"message": "Retopicize started in background"}

@app.get("/library/retopicize/status")
def get_retopicize_status():
    return _retopicize_state
