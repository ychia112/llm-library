import pytest
from pathlib import Path
from datetime import datetime, timezone
from llmlib.models import Session, Message
from llmlib.storage.db import LibraryDB

@pytest.fixture
def db(tmp_path):
    db_file = tmp_path / "test.db"
    return LibraryDB(db_file)

def test_upsert_and_get(db):
    session = Session(
        source_id="src-1",
        platform="chatgpt",
        title="Test Title",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        messages=[Message(role="user", content="hello")]
    )
    embedding = [0.1] * 1536
    
    db.upsert_session(session, embedding)
    
    retrieved = db.get_session(session.id)
    assert retrieved is not None
    assert retrieved.title == "Test Title"
    assert len(retrieved.messages) == 1

def test_search(db):
    s1 = Session(
        source_id="s1", platform="p", title="T1", 
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
        messages=[Message(role="u", content="c1")]
    )
    s2 = Session(
        source_id="s2", platform="p", title="T2", 
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
        messages=[Message(role="u", content="c2")]
    )
    
    db.upsert_session(s1, [0.1] * 1536)
    db.upsert_session(s2, [0.5] * 1536)
    
    # Search for something close to s1
    results = db.search([0.1] * 1536, top_k=1)
    assert len(results) == 1
    assert results[0].id == s1.id

def test_list_and_delete(db):
    s1 = Session(
        source_id="s1", platform="chatgpt", title="T1", 
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
        messages=[], tags=["tag1"]
    )
    db.upsert_session(s1, [0.1] * 1536)
    
    # List by tag
    sessions = db.list_sessions(tag="tag1")
    assert len(sessions) == 1
    
    # Delete
    db.delete_session(s1.id)
    assert db.get_session(s1.id) is None
    assert len(db.list_sessions()) == 0
