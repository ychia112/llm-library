import json
import pytest
from pathlib import Path
from llmlib.parsers.claude import ClaudeParser

def test_flat_list_parse(tmp_path):
    conv = {
        "uuid": "claude-1",
        "name": "Claude Test",
        "created_at": "2024-01-01T12:00:00Z",
        "updated_at": "2024-01-01T12:05:00Z",
        "chat_messages": [
            {"sender": "human", "text": "Hello Claude"},
            {"sender": "assistant", "text": "Hello! How can I help?"}
        ]
    }
    file_path = tmp_path / "claude.json"
    file_path.write_text(json.dumps([conv]))
    
    parser = ClaudeParser()
    sessions = parser.parse(file_path)
    
    assert len(sessions) == 1
    assert sessions[0].source_id == "claude-1"
    assert len(sessions[0].messages) == 2
    assert sessions[0].messages[0].role == "human"
    assert sessions[0].messages[0].content == "Hello Claude"

def test_missing_fields(tmp_path):
    # Minimal fields
    conv = {
        "uuid": "claude-2",
        "chat_messages": [{"sender": "human", "text": "Minimal"}]
    }
    file_path = tmp_path / "claude_min.json"
    file_path.write_text(json.dumps([conv]))
    
    parser = ClaudeParser()
    sessions = parser.parse(file_path)
    
    assert len(sessions) == 1
    assert sessions[0].title == "Untitled"
    assert sessions[0].created_at is not None

def test_claude_malformed(tmp_path):
    file_path = tmp_path / "malformed.json"
    file_path.write_text("[{\"uuid\": \"1\", \"chat_messages\": [{\"sender\": \"human\"}]}]") # missing text
    
    parser = ClaudeParser()
    sessions = parser.parse(file_path)
    assert len(sessions[0].messages) == 0 # Should skip invalid messages
