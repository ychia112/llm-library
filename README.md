# llm-library

Personal LLM Knowledge Base CLI for turning ChatGPT/Claude exports into a local, searchable knowledge library.

## What this project does today

- Ingests chat exports from:
  - ChatGPT (`mapping` tree traversal, first-child path)
  - Claude (`chat_messages` / `messages` flat parsing)
- Generates metadata with Gemini:
  - `topic`, `tags`, `question_type`, `summary`
- Generates embeddings with Gemini and stores everything locally in SQLite + `sqlite-vec`
- Supports CLI workflows:
  - `ingest` (parse -> tag -> embed -> store)
  - `ask` (embed query -> vector search top-5)
  - `list` (filter by tag/platform/type)
  - `show` (full session + message transcript)

## Architecture (current)

| Layer | File(s) | Responsibility |
| --- | --- | --- |
| CLI | `llmlib/cli.py` | User-facing commands and flow orchestration |
| Parsers | `llmlib/parsers/*.py` | Normalize platform exports into `Session` |
| Models | `llmlib/models.py` | Pydantic models for `Session` and `Message` |
| LLM | `llmlib/llm/gemini.py` | Tagging and embedding via Gemini API |
| Storage | `llmlib/storage/db.py` | Local DB schema, upsert/search/list/get/delete |
| Tests | `tests/*.py` | Parser, storage, and Gemini-tagger behavior |

## Quick start

### 1. Prerequisites

- Python 3.10+
- A Gemini API key

### 2. Install

```bash
pip install -e .
pip install pytest
```

### 3. Configure environment

```bash
export GEMINI_API_KEY="your_key_here"
```

`ingest` and `ask` require this variable.

### 4. Run CLI

```bash
llmlib ingest chatgpt /path/to/conversations.json
llmlib ingest claude /path/to/conversations.json
llmlib ask "fastapi middleware auth"
llmlib list
llmlib list --platform chatgpt --tag python --type howto
llmlib show <session-id>
```

## Local data and privacy

- Main DB path: `~/.llmlib/library.db`
- Data is stored locally in:
  - `sessions` (metadata + messages)
  - `session_vectors` (embeddings via `sqlite-vec`)
- The only external call is Gemini API usage for tag/embedding operations.

## Open-source hygiene policy

To keep this public repository clean and contributor-friendly:

1. **No secrets or private exports in git**
   - Never commit API keys, tokens, or real chat export files.
   - Keep real data local only.
2. **Tests are public-safe**
   - Use synthetic fixtures/mocks in `tests/`.
   - Do not include personal/company conversation content.
3. **Reproducible setup**
   - Setup and command examples are documented in this README.
4. **Quality gate before merge**
   - Run:
     ```bash
     python -m pytest -q
     ```
   - PRs should only merge when tests pass.
5. **Contributor clarity**
   - Keep command behavior, required env vars, and data expectations explicit in docs.
6. **Versioning and change visibility**
   - Use tagged releases and maintain a changelog as the project evolves.
7. **Docs-first for public APIs**
   - Any CLI behavior changes should update README examples and command docs.

## Testing

```bash
python -m pytest -q
```

Current tests cover:
- ChatGPT parser traversal + role filtering
- Claude parser normalization
- LibraryDB upsert/search/list/delete
- Gemini tagger JSON parsing + embedding calls (mocked)

## Known limitations (current implementation)

- `ask` currently prints top-5 matches but does not yet implement a similarity-threshold decision layer (for direct cache-hit behavior).
- Local embedding fallback providers are not wired yet; current embedding/tagging flow is Gemini-based.
