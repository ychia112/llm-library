# llmlib

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org)
[![SQLite](https://img.shields.io/badge/storage-sqlite--vec-green)](https://github.com/asg017/sqlite-vec)

> Turn your scattered ChatGPT and Claude chat history into a local, searchable knowledge library — with semantic search, auto-tagging, and a 2-level topic tree.

**CLI-first · Local-first · Privacy-first** — all data lives in a single `~/.llmlib/library.db` file. No cloud required.

---

## Problem

Every LLM session you've ever had is siloed. You've solved the same bug twice, asked for the same explanation three times, and can't find that FastAPI middleware solution from last month. **llmlib fixes this.**

## How it works

```
Export → Parse → Tag → Embed → Query
```

1. Export your chat history from ChatGPT or Claude
2. Run `llmlib ingest` — sessions are parsed, auto-tagged, and embedded locally via Ollama
3. Run `llmlib ask "your question"` — semantic search surfaces relevant past sessions instantly

---

## Features

- **Multi-platform parsing** — ChatGPT (branching tree traversal) and Claude (flat list)
- **Auto-tagging** — LLM assigns `topic`, `tags`, `key_entities`, `question_type`, and `summary` per session
- **2-level knowledge tree** — sessions are placed into a `topic → sub_topic` hierarchy that grows with your library
- **Semantic search** — embeddings stored in `sqlite-vec`, cosine similarity with hit / partial / miss thresholds
- **Re-clustering** — `llmlib retopicize` reshapes your topic taxonomy using UMAP + HDBSCAN on the embedding space
- **REST API** — `llmlib serve` starts a local FastAPI server consumed by the macOS and web frontends
- **MCP server** — `llmlib mcp` exposes your library as tools for Claude Code and other MCP-compatible AI agents
- **Fully local by default** — Ollama runs everything on-device; no data leaves your machine

---

## Architecture

```
Python backend:
  ingest:  export file → Parser → Session → Tagger → Knowledge Tree → Embedder → LibraryDB
  ask:     query → Embedder → cosine search → HIT / PARTIAL / MISS logic
  serve:   FastAPI server on localhost:8765
  mcp:     MCP stdio server for AI agent integration

Frontends (both connect to llmlib serve):
  macapp/  SwiftUI macOS app
  webapp/  Next.js web app
```

| Layer | Path | Responsibility |
|-------|------|----------------|
| CLI | `llmlib/cli.py` | Commands and flow orchestration |
| Parsers | `llmlib/parsers/` | Normalize platform exports into `Session` objects |
| Models | `llmlib/models.py` | Pydantic models: `Session`, `Message` |
| LLM | `llmlib/llm/` | Tagging and embedding (Ollama / Gemini) |
| Knowledge tree | `llmlib/llm/tree.py` | 2-level topic placement via LLM |
| Clustering | `llmlib/cluster.py` | Re-clustering via UMAP + HDBSCAN |
| Storage | `llmlib/storage/db.py` | SQLite + sqlite-vec: upsert, search, list |
| API | `llmlib/api/server.py` | FastAPI server for macOS / web frontends |
| MCP | `llmlib/mcp/server.py` | MCP stdio server for AI agents |
| macOS app | `macapp/` | SwiftUI companion app |
| Web app | `webapp/` | Next.js companion app |

---

## Quick Start

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com) (default, fully local) **or** a [Gemini API key](https://aistudio.google.com) (free tier: 1,000 req/day)

### Install

```bash
git clone https://github.com/ychia112/llm-library.git
cd llm-library
pip install -e .
```

For the REST API (macOS / web frontend):

```bash
pip install -e '.[api]'
```

For the MCP server:

```bash
pip install -e '.[mcp]'
```

For topic re-clustering:

```bash
pip install -e '.[cluster]'
```

### Setup — Ollama (recommended, fully offline)

```bash
ollama pull llama3.2:3b-instruct-q4_K_M
```

### Setup — Gemini (alternative, cloud)

```bash
export GEMINI_API_KEY="your_key_here"
# Add to ~/.zshrc or ~/.bash_profile to persist
```

---

## CLI Reference

### `llmlib ingest`

Parse an export file, tag sessions with the LLM, embed them, and store in the library.

```bash
# ChatGPT export (conversations.json or conversations-000.json)
llmlib ingest chatgpt ~/Downloads/conversations.json

# Claude export
llmlib ingest claude ~/Downloads/conversations.json

# Use Gemini instead of Ollama
llmlib ingest chatgpt ~/Downloads/conversations.json --provider gemini
```

### `llmlib ask`

Semantic search with a history-first answer strategy.

```bash
llmlib ask "fastapi middleware authentication"
llmlib ask "how do I configure uvicorn with ssl" --top-k 10
```

| Score | Result | Behaviour |
|-------|--------|-----------|
| ≥ 0.72 | **HIT** | Returns cached session, 0 LLM tokens used |
| ≥ 0.50 | **PARTIAL** | Injects top-3 sessions as context, then calls LLM |
| < 0.50 | **MISS** | Calls LLM directly |

### `llmlib list`

Browse the library with optional filters.

```bash
llmlib list
llmlib list --platform chatgpt --tag python --type debug
```

Question types: `debug` / `design` / `research` / `howto`

### `llmlib show`

Print a full session including all messages.

```bash
llmlib show <session-id>
```

### `llmlib reindex`

Re-embed all sessions. Run this after switching providers or models.

```bash
llmlib reindex
llmlib reindex --provider gemini
```

### `llmlib retopicize`

Re-cluster all sessions using UMAP + HDBSCAN on their embeddings, then ask the LLM to name each cluster. Fixes fragmented topic taxonomies over time.

```bash
llmlib retopicize                      # apply to library
llmlib retopicize --dry-run            # preview without saving
llmlib retopicize --target-topics 20   # hint for desired cluster count
```

Requires `pip install -e '.[cluster]'`.

### `llmlib serve`

Start the local REST API server for the macOS and web frontends.

```bash
llmlib serve              # http://localhost:8765
llmlib serve --port 9000
```

Requires `pip install -e '.[api]'`.

### `llmlib mcp`

Start the MCP stdio server. Exposes `search_library`, `get_session`, `get_knowledge_tree`, and `ingest_session` as tools for Claude Code and other MCP-compatible AI agents.

```bash
llmlib mcp
```

See [MCP_SETUP.md](MCP_SETUP.md) for full setup and usage guide.

Requires `pip install -e '.[mcp]'`.

---

## Frontends

Both frontends connect to `llmlib serve` running on `localhost:8765`.

### macOS App (`macapp/`)

A native SwiftUI companion app with a 3-column NavigationSplitView.

Features: topic card grid, knowledge tree navigation, session detail, semantic search chat interface.

To run: open `LLMLibrary/LLMLibrary.xcodeproj` in Xcode and build to your Mac.

### Web App (`webapp/`)

A Next.js interface for browser-based access to your library.

```bash
cd webapp
npm install
npm run dev     # http://localhost:3000
```

---

## Data & Privacy

- All data is stored locally at `~/.llmlib/library.db`
- With **Ollama** (default): fully offline, zero external network calls
- With **Gemini**: tagging and embedding are sent to the Gemini API; conversation content is transmitted
- Never commit your `.db` file or raw export JSON — both are in `.gitignore`

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLMLIB_PROVIDER` | `ollama` | `ollama` or `gemini` (used by MCP server) |
| `LLMLIB_OLLAMA_MODEL` | `llama3.2:3b-instruct-q4_K_M` | Ollama model for tagging + embedding |
| `LLMLIB_GEMINI_MODEL` | `gemini-2.0-flash-lite` | Gemini model (when using Gemini provider) |
| `GEMINI_API_KEY` | — | Required when `--provider gemini` |
| `LLMLIB_GEMINI_DELAY` | `0` | Seconds to wait between Gemini API calls (rate limiting) |
| `LLMLIB_INGEST_WORKERS` | `1` | Parallel ingest workers for the `serve` endpoint |

---

## Development

```bash
pip install -e .
pip install pytest
python -m pytest tests/ -v
```

Tests cover: ChatGPT parser tree traversal, Claude parser, `LibraryDB` upsert / search / delete, Gemini tagger (mocked).

---

## Roadmap

- [x] ChatGPT parser (multi-file, branching tree traversal)
- [x] Claude parser
- [x] Auto-tagging + 2-level knowledge tree placement
- [x] sqlite-vec storage + cosine search
- [x] CLI: `ingest` / `ask` / `list` / `show` / `reindex` / `retopicize`
- [x] REST API + macOS SwiftUI app + Next.js web app
- [x] MCP server for AI agent integration
- [ ] Gemini / Perplexity export parser
- [ ] Chrome extension for auto-sync
- [ ] Duplicate session detection + merge
- [ ] VS Code extension sidebar

---

## Contributing

Pull requests are welcome. For major changes, open an issue first to discuss what you'd like to change.

Ensure tests pass before submitting:

```bash
python -m pytest tests/ -v
```

---

## License

[MIT](LICENSE)
