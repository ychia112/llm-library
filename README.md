# llm-library

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org)
[![SQLite](https://img.shields.io/badge/storage-sqlite--vec-green)](https://github.com/asg017/sqlite-vec)

> Turn your scattered ChatGPT and Claude chat history into a local, searchable, auto-tagged knowledge library.

**CLI-first · Local-first · Privacy-first** — zero cloud dependency, one `.db` file.

---

## Problem

Every LLM session you've ever had is siloed. You've solved the same bug twice, asked for the same explanation three times, and can't find that FastAPI middleware solution from last month. **llmlib fixes this.**

## How it works

```
Export → Parse → Tag → Embed → Query
```

1. Export your chat history from ChatGPT or Claude
2. Run `llmlib ingest` — sessions are parsed, auto-tagged, and embedded locally
3. Run `llmlib ask "your question"` — vector search finds relevant past sessions instantly

---

## Features

- **Multi-platform parsing** — ChatGPT (tree traversal) and Claude (flat list)
- **Auto-tagging** — Gemini 2.0 Flash generates `topic`, `tags`, `question_type`, and `summary` per session
- **Vector search** — embeddings stored in `sqlite-vec`, cosine similarity search with `llmlib ask`
- **Fully local storage** — single `~/.llmlib/library.db` file, no server needed
- **Flexible filtering** — `llmlib list` by tag, platform, or question type

---

## Architecture

| Layer | File | Responsibility |
|-------|------|----------------|
| CLI | `llmlib/cli.py` | User-facing commands and flow orchestration |
| Parsers | `llmlib/parsers/` | Normalize platform exports into `Session` objects |
| Models | `llmlib/models.py` | Pydantic models: `Session`, `Message` |
| LLM | `llmlib/llm/gemini.py` | Tagging and embedding via Gemini API |
| Storage | `llmlib/storage/db.py` | SQLite + sqlite-vec: upsert, search, list, get, delete |
| Tests | `tests/` | Parser, storage, and tagger unit tests |

---

## Quick Start

### Prerequisites

- Python 3.10+
- A [Gemini API key](https://aistudio.google.com) (free tier: 1,000 req/day)

### Install

```bash
git clone https://github.com/ychia112/llm-library.git
cd llm-library
pip install -e .
```

### Configure

```bash
export GEMINI_API_KEY="your_key_here"
```

Add to `~/.zshrc` or `~/.bash_profile` to persist across sessions.

### Usage

```bash
# Ingest a ChatGPT export
llmlib ingest chatgpt ~/Downloads/conversations.json

# Ingest a Claude export
llmlib ingest claude ~/Downloads/conversations.json

# Search your library
llmlib ask "fastapi middleware authentication"

# List all sessions
llmlib list

# Filter by platform, tag, and type
llmlib list --platform chatgpt --tag python --type debug

# Show full session with messages
llmlib show <session-id>
```

---

## Data & Privacy

- All data is stored locally at `~/.llmlib/library.db`
- The **only** external API call is to Gemini (for tagging and embedding during `ingest` and `ask`)
- Never commit your `.db` file or export files to version control (see `.gitignore`)

---

## Development

```bash
# Install with dev dependencies
pip install -e .
pip install pytest

# Run tests
python -m pytest -q
```

Tests cover:
- ChatGPT parser tree traversal and role filtering
- Claude parser flat-list normalization
- `LibraryDB` upsert / search / list / delete
- Gemini tagger JSON output and embedding calls (mocked)

---

## Roadmap

- [x] ChatGPT parser (multi-file format, tree traversal)
- [x] Claude parser
- [x] Auto-tagger via Gemini API
- [x] sqlite-vec storage + cosine search
- [x] CLI: `ingest` / `ask` / `list` / `show`
- [ ] Similarity threshold for cache-hit behavior in `ask`
- [ ] Gemini / Perplexity export support
- [ ] Chrome extension for auto-sync
- [ ] MCP server interface (query your library from Gemini CLI / Copilot)
- [ ] VS Code extension sidebar

---

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you'd like to change.

Please make sure tests pass before submitting a PR:

```bash
python -m pytest -q
```

---

## License

[MIT](LICENSE)
