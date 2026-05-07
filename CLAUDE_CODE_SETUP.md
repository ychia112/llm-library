# llmlib MCP Server — Claude Code Setup

This guide connects your personal knowledge library to Claude Code so it can search your past conversations, retrieve sessions, and ingest new ones as MCP tools.

## Prerequisites

- llmlib installed with your library already populated (`llmlib ingest ...`)
- Ollama running locally with `llama3.2:3b-instruct-q4_K_M` (or set `LLMLIB_OLLAMA_MODEL`)
- Claude Code installed

## 1. Install MCP dependencies

```bash
pip install 'llmlib[mcp]'
```

## 2. Register the MCP server in Claude Code

Add to your Claude Code MCP config (`~/.claude/claude_code_config.json` or via `claude mcp add`):

```json
{
  "mcpServers": {
    "llmlib": {
      "command": "llmlib",
      "args": ["mcp"],
      "env": {
        "LLMLIB_PROVIDER": "ollama",
        "LLMLIB_OLLAMA_MODEL": "llama3.2:3b-instruct-q4_K_M"
      }
    }
  }
}
```

Or via CLI:

```bash
claude mcp add llmlib -- llmlib mcp
```

To use Gemini instead of Ollama:

```json
{
  "mcpServers": {
    "llmlib": {
      "command": "llmlib",
      "args": ["mcp"],
      "env": {
        "LLMLIB_PROVIDER": "gemini",
        "GEMINI_API_KEY": "your-key-here"
      }
    }
  }
}
```

## 3. Available Tools

| Tool | Description |
|---|---|
| `search_library(query, top_k=5)` | Semantic search across all ingested sessions |
| `get_session(session_id)` | Fetch full session with all messages |
| `get_knowledge_tree()` | Show the 2-level topic → sub_topic tree |
| `ingest_session(title, messages, platform)` | Save a new session into the library |

## 4. Usage Examples in Claude Code

```
# Search your library
search_library("how did I set up FastAPI authentication?")

# Browse the knowledge tree
get_knowledge_tree()

# Get a specific session
get_session("abc123-...")

# Save the current conversation
ingest_session(
  title="Debugging SQLite WAL mode with concurrent writes",
  messages=[
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  platform="claude_code"
)
```

## 5. Knowledge Tree

Sessions are organised into a 2-level hierarchy:

```
Python Backend (12)
  • FastAPI & APIs (5)
  • Database & ORM (4)
  • Testing (3)
Machine Learning (8)
  • Model Training (5)
  • Inference & Serving (3)
```

When you `ingest_session`, the LLM automatically places the session into the existing tree — reusing existing topics/sub-topics when a good match exists, or creating new ones.

## 6. Environment Variables

| Variable | Default | Description |
|---|---|---|
| `LLMLIB_PROVIDER` | `ollama` | `ollama` or `gemini` |
| `LLMLIB_OLLAMA_MODEL` | `llama3.2:3b-instruct-q4_K_M` | Ollama model for tagging + embedding |
| `LLMLIB_GEMINI_MODEL` | `gemini-2.0-flash-lite` | Gemini model (if using Gemini) |
| `GEMINI_API_KEY` | — | Required when `LLMLIB_PROVIDER=gemini` |
