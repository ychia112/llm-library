import json
import pytest
from llmlib.parsers.chatgpt import ChatGPTParser

def test_traverse_tree(tmp_path):
    # Create a dummy chatgpt-like json with a simple message tree
    conv = {
        "id": "conv-1",
        "title": "Test Chat",
        "create_time": 1700000000.0,
        "update_time": 1700000001.0,
        "mapping": {
            "node-1": {
                "message": {
                    "author": {"role": "user"},
                    "content": {"parts": ["Hello"]},
                    "create_time": 1700000000.0
                },
                "parent": None,
                "children": ["node-2"],
            },
            "node-2": {
                "message": {
                    "author": {"role": "assistant"},
                    "content": {"parts": ["Hi there!"]},
                    "create_time": 1700000001.0
                },
                "parent": "node-1",
                "children": [],
            }
        }
    }
    file_path = tmp_path / "conversations.json"
    file_path.write_text(json.dumps([conv]))
    
    parser = ChatGPTParser()
    sessions = parser.parse(file_path)
    
    assert len(sessions) == 1
    assert sessions[0].source_id == "conv-1"
    assert len(sessions[0].messages) == 2
    assert sessions[0].messages[0].content == "Hello"
    assert sessions[0].messages[1].content == "Hi there!"

def test_skip_system_nodes(tmp_path):
    conv = {
        "id": "conv-2",
        "title": "System Test",
        "create_time": 1700000000.0,
        "update_time": 1700000000.0,
        "mapping": {
            "node-1": {
                "message": {
                    "author": {"role": "system"},
                    "content": {"parts": ["System prompt"]},
                    "create_time": 1700000000.0
                },
                "parent": None,
                "children": ["node-2"],
            },
            "node-2": {
                "message": {
                    "author": {"role": "user"},
                    "content": {"parts": ["User msg"]},
                    "create_time": 1700000001.0
                },
                "parent": "node-1",
                "children": [],
            }
        }
    }
    file_path = tmp_path / "conversations.json"
    file_path.write_text(json.dumps([conv]))
    
    parser = ChatGPTParser()
    sessions = parser.parse(file_path)
    
    assert len(sessions) == 1
    roles = [m.role for m in sessions[0].messages]
    assert "system" not in roles
    assert roles == ["user"]

def test_malformed_data(tmp_path):
    file_path = tmp_path / "bad.json"
    file_path.write_text("invalid json")
    
    parser = ChatGPTParser()
    with pytest.raises(json.JSONDecodeError):
        parser.parse(file_path)

    # Empty data
    file_path.write_text("[]")
    sessions = parser.parse(file_path)
    assert sessions == []
