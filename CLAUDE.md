# CLAUDE.md — llmlib Development Guide

## Project Overview

`llmlib` is a **privacy-first, local-first CLI tool** that ingests LLM chat exports
(ChatGPT, Claude) into a local `sqlite-vec` database for semantic search and knowledge exploration.
A companion macOS SwiftUI app (`macapp/`) connects via a local FastAPI server (`llmlib serve` on port 8765).

```
Python backend:
  ingest:  JSON export → Parser → Session (Pydantic) → Tagger (LLM) → Embedder → LibraryDB
  query:   query string → Embedder → cosine search → HIT / PARTIAL / MISS logic
  serve:   FastAPI server on localhost:8765

Swift frontend (macapp/):
  APIClient.swift → FastAPI → LibraryDB
  MVVM: App/Content → AppViewModel → LibraryViewModel / SearchViewModel → Views
  Navigation: NavigationSplitView (3-column: sidebar | content | detail)
```

---

## Directory Structure

### Python backend (`llmlib/`)

| File / Dir | Role |
|---|---|
| `cli.py` | Typer CLI entry point — commands: `ingest`, `ask`, `list`, `show`, `reindex`, `serve` |
| `models.py` | **Source of truth** for `Session` and `Message` Pydantic models |
| `parsers/base.py` | Abstract `BaseParser` — all parsers must inherit this |
| `parsers/chatgpt.py` | ChatGPT multi-file export parser (branching tree traversal) |
| `parsers/claude.py` | Claude flat-list export parser |
| `llm/gemini.py` | Gemini API tagger + embedder (`gemini-embedding-001`) |
| `llm/ollama.py` | Local Ollama tagger + embedder (default: `llama3.2:3b-instruct-q4_K_M`) |
| `storage/db.py` | sqlite-vec schema, upsert, hybrid search, overview aggregation |
| `api/server.py` | FastAPI server — all endpoints consumed by macapp |

### Swift macOS app (`macapp/`)

| File / Dir | Role |
|---|---|
| `App/LLMLibraryApp.swift` | `@main` entry point |
| `Views/ContentView.swift` | Root `NavigationSplitView` (sidebar / content / detail) |
| `Views/Library/LibraryView.swift` | Library tab: topic cards grid + filter sidebar + session list |
| `Views/Library/TopicCardView.swift` | Individual topic card (topic name, count, top tags) |
| `Views/Search/ChatView.swift` | Chat-style search interface |
| `Views/Search/SearchView.swift` | Keyword/filter search view |
| `Views/Session/SessionDetailView.swift` | Right-column session detail (messages, tags, metadata) |
| `Views/Placeholders.swift` | Empty state placeholders |
| `Models/Session.swift` | Swift mirror of Python `Session` — **must stay in sync with `models.py`** |
| `Models/LibraryOverview.swift` | `LibraryOverview`, `TopicSummary`, `TagStats`, `QuestionTypeStats`, `PlatformStats` |
| `Models/SearchResult.swift` | Search result response model |
| `Services/APIClient.swift` | All HTTP calls to `llmlib serve` |
| `ViewModels/AppViewModel.swift` | Root navigation state + `NavigationItem` enum |
| `ViewModels/LibraryViewModel.swift` | Library filter state + data loading |
| `ViewModels/SearchViewModel.swift` | Search query state + results |

---

## Engineering Conventions

### Core Rules

- **Pydantic** for all Python data models — never use raw dicts for `Session` / `Message`
- **Typer** for CLI — every new command gets `@app.command()` with a docstring
- **sqlite-vec** for vector search — never replace with an external vector DB
- **Privacy first**: Default provider is always `--provider ollama`. Only call Gemini API when user explicitly passes `--provider gemini`
- **Single DB file**: Everything lives in `~/.llmlib/library.db`

### ⚠️ Model Sync Rule (Critical)

`macapp/Models/Session.swift` mirrors `llmlib/models.py::Session`.
`macapp/Models/LibraryOverview.swift` mirrors `api/server.py` response shapes.

When modifying **either side**, update both in the **same task**. Never leave them out of sync.

Fields that must match:
- `Session`: `id`, `source_id`, `platform`, `title`, `created_at`, `updated_at`, `messages`, `topic`, `tags`, `key_entities`, `question_type`, `summary`
- `TopicSummary`: `topic`, `count`, `top_tags` (+ any new fields added to `TopicStats` in server.py)

### Adding a New Platform Parser

1. Create `llmlib/parsers/<platform>.py`
2. Inherit from `BaseParser` (`parsers/base.py`)
3. Return `list[Session]` — always use the Pydantic `Session` from `models.py`
4. Register in `_get_parser()` in `cli.py`
5. Add tests in `tests/`

### Adding a New LLM Provider

1. Create `llmlib/llm/<provider>.py`
2. Must implement all three methods:
   - `tag_session(session: Session) -> dict`
   - `embed_session(session: Session) -> list[float]`
   - `embed_query(query: str) -> list[float]`
3. Register in `_get_tagger()` in `cli.py`

### SwiftUI Conventions

- Use `@Observable` + `@MainActor` for ViewModels (already established pattern)
- All API calls go through `APIClient.shared` — never call URLs directly from Views
- Navigation is `NavigationSplitView` with 3 columns (sidebar 150–200pt / content / detail)
- `FlowLayout` is defined in `LibraryView.swift` — reuse for tag chip clouds
- `@Binding var selectedSessionID: String?` passes selection from content → detail column

---

## API Contract (Python ↔ Swift)

`api/server.py` is the **contract layer** between Python and Swift.

| Endpoint | Method | Used by |
|---|---|---|
| `GET /library/overview` | → `LibraryOverview` | `LibraryViewModel.loadOverview()` |
| `GET /library/topics` | → `[TopicStats]` | `LibraryViewModel.loadOverview()` |
| `GET /library/tags` | → `[TagStats]` | tag filter sidebar |
| `GET /sessions` | → `PaginatedSessions` | `LibraryViewModel.loadSessions()` |
| `GET /sessions/{id}` | → `Session` | `SessionDetailView` |
| `POST /ingest` | → background task | `LibraryViewModel.importFile()` |
| `POST /ask` | → `AskResponse` | `SearchViewModel` |

**Rules:**
- Do not rename or remove existing endpoints without updating `APIClient.swift`
- Do not change response shapes without updating `macapp/Models/`
- `CodingKeys` in Swift must match the snake_case JSON keys from Python

---

## Ask Command — Threshold Logic

| Score | Result | Behaviour |
|---|---|---|
| `>= 0.72` | **HIT** | Return cached answer, 0 tokens used |
| `>= 0.50` | **PARTIAL** | Inject top-3 sessions as context, call LLM |
| `< 0.50` | **MISS** | Call LLM with no context |

Do not change these thresholds without running embedding recall tests.

## Question Types (enum — do not change values)

`"debug"` | `"design"` | `"research"` | `"howto"`

---

## Active Development Goal: Library Knowledge Exploration

**Objective**: Transform the Library tab from a filter-list into a knowledge exploration experience.
Users should feel they are entering a topic "knowledge space", not just viewing a filtered list.

### Target UX Flow

```
Library (topic cards grid)
  └─ Tap TopicCard
       └─ TopicDetailView (new NavigationStack push)
            ├─ Hero: topic name + session count + platform breakdown chips
            ├─ Question type distribution bar (debug=blue / research=green / howto=orange / design=purple)
            ├─ Key entities chip cloud (aggregated from session.key_entities)
            ├─ Tag filter pills (tap to filter sessions below)
            └─ Session cards (title + summary + question_type badge + tags)
```

### Backend Changes Required

**`storage/db.py` — extend `get_topics()` / `get_library_overview()`:**
- `TopicSummary` needs: `by_question_type: list[dict]` and `top_entities: list[str]`
- Aggregate `key_entities` across all sessions in the topic (top 8 by frequency)
- Aggregate `question_type` counts per topic

**`api/server.py` — extend `TopicStats`:**
```python
class TopicStats(BaseModel):
    topic: str
    count: int
    top_tags: List[str]
    by_question_type: List[QuestionTypeStats]  # ADD
    top_entities: List[str]                    # ADD
```

**`macapp/Models/LibraryOverview.swift` — sync `TopicSummary`:**
```swift
struct TopicSummary: Codable, Identifiable, Hashable {
    var id: String { topic }
    let topic: String
    let count: Int
    let topTags: [String]
    let byQuestionType: [QuestionTypeStats]  // ADD
    let topEntities: [String]               // ADD
    // CodingKeys: by_question_type, top_entities
}
```

### New Files to Create

| File | Purpose |
|---|---|
| `macapp/ViewModels/TopicDetailViewModel.swift` | Load sessions + tags for a specific topic |
| `macapp/Views/Library/TopicDetailView.swift` | Hero + entity cloud + tag filter + session cards |

### Files to Modify

| File | Change |
|---|---|
| `macapp/Views/Library/TopicCardView.swift` | Add mini question-type bar (colour-coded horizontal segments) |
| `macapp/Views/Library/LibraryView.swift` | Replace `onTapGesture → selectedTopic` with `navigationDestination(for: TopicSummary.self)` |
| `macapp/ViewModels/LibraryViewModel.swift` | Remove `selectedTopic` navigation state (now handled by NavigationStack) |
| `llmlib/storage/db.py` | Extend topic aggregation |
| `llmlib/api/server.py` | Extend `TopicStats` model |

---

## Dependencies

**Python** (`pyproject.toml`):
- Core: `typer`, `pydantic`, `sqlite-vec`, `rich`, `google-genai`, `openai`
- API extra: `pip install 'llmlib[api]'` → adds `fastapi`, `uvicorn`

**Swift**: SwiftUI only, no third-party packages.

## Running

```bash
# Python CLI
llmlib ingest chatgpt ./conversations.json --provider ollama
llmlib ask "fastapi auth middleware"
llmlib serve                    # start API for macapp (port 8765)

# Tests
pytest tests/ -v
```

---

## v2 Roadmap (out of current scope)

- [ ] Gemini / Perplexity export parser
- [ ] MCP server interface (for Claude Code / Gemini CLI to query library)
- [ ] Chrome extension auto-sync
- [ ] Duplicate session detection + merge
- [ ] VS Code extension sidebar
