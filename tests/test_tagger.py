import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from llmlib.models import Session, Message
from llmlib.llm.gemini import GeminiTagger

@pytest.fixture
def tagger():
    return GeminiTagger(api_key="fake-key")

def test_tag_session_format(tagger):
    session = Session(
        source_id="s1", platform="p", title="T1",
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
        messages=[Message(role="user", content="hello")]
    )
    
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "topic": "Testing",
        "tags": ["pytest", "mock"],
        "question_type": "howto",
        "summary": "This is a test summary."
    })
    
    with patch.object(tagger.client.models, 'generate_content', return_value=mock_response):
        metadata = tagger.tag_session(session)
        
    assert metadata["topic"] == "Testing"
    assert "pytest" in metadata["tags"]
    assert metadata["question_type"] in ["debug", "design", "research", "howto"]
    assert isinstance(metadata["summary"], str)

def test_tag_session_fallback(tagger):
    session = Session(
        source_id="s1", platform="p", title="T1",
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
        messages=[]
    )
    
    mock_response = MagicMock()
    mock_response.text = "invalid json"
    
    with patch.object(tagger.client.models, 'generate_content', return_value=mock_response):
        metadata = tagger.tag_session(session)
        
    assert metadata["topic"] == "Unknown"
    assert metadata["question_type"] == "research"

def test_embed_session(tagger):
    session = Session(
        source_id="s1", platform="p", title="T1",
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
        messages=[], summary="Summary"
    )
    
    mock_embedding = MagicMock()
    mock_embedding.values = [0.1, 0.2, 0.3]
    mock_response = MagicMock()
    mock_response.embeddings = [mock_embedding]
    
    with patch.object(tagger.client.models, 'embed_content', return_value=mock_response):
        embedding = tagger.embed_session(session)
        
    assert len(embedding) == 3
    assert embedding[0] == 0.1
