# SKILLS.md — Claude Code Slash Commands

This file documents the available slash commands for Claude Code.
Each command is a reusable prompt template to guide development tasks consistently.

---

## `/add-parser`

**Purpose**: Add support for a new LLM export platform (e.g. Gemini, Perplexity).

```
Add a new parser for <PLATFORM> exports.

Steps:
1. Read `llmlib/parsers/base.py` to understand the BaseParser interface.
2. Read `llmlib/models.py` for the Session and Message schema.
3. Examine `llmlib/parsers/chatgpt.py` or `llmlib/parsers/claude.py` as reference.
4. Create `llmlib/parsers/<platform>.py`:
   - Inherit from BaseParser
   - Implement `parse(file_path: Path) -> list[Session]`
   - Map all fields to the Session model — never use raw dicts
   - Handle malformed / missing fields gracefully with defaults
5. Register the new parser in `_get_parser()` in `llmlib/cli.py`
6. Add at least one test in `tests/test_parsers.py` with a minimal fixture JSON
7. Update CLAUDE.md parser table if it lists supported platforms

Constraints:
- Return type must be `list[Session]` using the Pydantic model from `models.py`
- Do not add new dependencies unless absolutely necessary
- Keep platform name lowercase in file name and in `_get_parser()` mapping
```

---

## `/add-provider`

**Purpose**: Add a new LLM provider for tagging and embedding (e.g. OpenAI, Anthropic).

```
Add a new LLM provider called <PROVIDER>.

Steps:
1. Read `llmlib/llm/gemini.py` and `llmlib/llm/ollama.py` as reference implementations.
2. Create `llmlib/llm/<provider>.py` with a class named `<Provider>Tagger`.
3. Implement all three required methods:
   - `tag_session(session: Session) -> dict`
     Returns: {"topic": str, "tags": list[str], "key_entities": list[str],
               "question_type": "debug"|"design"|"research"|"howto", "summary": str}
   - `embed_session(session: Session) -> list[float]`
   - `embed_query(query: str) -> list[float]`
4. Register in `_get_tagger()` in `llmlib/cli.py`
5. Add the provider as an option in `llmlib/api/server.py` `run_ingest()` and `/ask`
6. Document required env vars (API keys) in README.md

Constraints:
- question_type must be validated against {"debug", "design", "research", "howto"}
- Default provider must remain `ollama` — never change the CLI default
- If the provider requires an API key, read it from env var, never hardcode
- Embedding dimension must be consistent with existing DB or trigger a reindex warning
```

---

## `/enhance-topic-view`

**Purpose**: Build the full Topic Detail knowledge exploration view.

```
Implement the Library → TopicDetailView feature for knowledge exploration.

Goal: When a user taps a topic card, they should enter a rich "knowledge space"
for that topic — not just see a filtered list.

Target layout of TopicDetailView (top to bottom):
1. Hero section: large topic name, session count badge, platform breakdown chips
2. Question type distribution: horizontal segmented bar
   - debug = blue / research = green / howto = orange / design = purple
3. Key entities chip cloud: aggregated top_entities from all sessions in topic
4. Tag filter pills: tappable, filters the session list below
5. Session cards list: title + one-line summary + question_type badge + tag chips

Steps (in order — do not skip):
1. **Python: `llmlib/storage/db.py`**
   - Extend `get_library_overview()` topic aggregation to include:
     - `by_question_type`: count per question_type for this topic
     - `top_entities`: top 8 key_entities by frequency across sessions in topic
   - Extend `get_topics()` to return the same enriched data

2. **Python: `llmlib/api/server.py`**
   - Add fields to `TopicStats`:
     ```python
     by_question_type: List[QuestionTypeStats]
     top_entities: List[str]
     ```
   - Verify `/library/overview` and `/library/topics` both return these fields

3. **Swift: `macapp/Models/LibraryOverview.swift`**
   - Sync `TopicSummary` with new fields:
     ```swift
     let byQuestionType: [QuestionTypeStats]
     let topEntities: [String]
     ```
   - Add CodingKeys: `by_question_type`, `top_entities`

4. **Swift: `macapp/ViewModels/TopicDetailViewModel.swift`** (new file)
   - `@Observable @MainActor class TopicDetailViewModel`
   - Properties: `sessions`, `selectedTags`, `isLoading`
   - `func load(topic: String) async` — calls `GET /sessions?topic=<topic>`
   - `func toggleTag(_ tag: String)` — filters sessions by tag client-side

5. **Swift: `macapp/Views/Library/TopicDetailView.swift`** (new file)
   - Accepts `topic: TopicSummary` as init parameter
   - `.navigationTitle(topic.topic)`
   - Implement all 5 sections described in the goal above
   - Reuse `FlowLayout` from LibraryView.swift for chip clouds

6. **Swift: `macapp/Views/Library/TopicCardView.swift`**
   - Add mini question-type distribution bar at the bottom of each card
   - Use coloured `RoundedRectangle` segments proportional to `byQuestionType` counts

7. **Swift: `macapp/Views/Library/LibraryView.swift`**
   - Replace `onTapGesture { viewModel.selectedTopic = topic.topic }` with:
     `navigationDestination(for: TopicSummary.self) { topic in TopicDetailView(topic: topic) }`
   - Change TopicCardView tap to use `NavigationLink(value: topic)`

8. **Swift: `macapp/ViewModels/LibraryViewModel.swift`**
   - Remove `selectedTopic: String?` property (navigation is now stack-based)
   - Remove `selectedTopic`-triggered `loadSessions()` observer

Constraints:
- Always update Python and Swift models in the same task (Model Sync Rule)
- Do not use `selectedTopic` string state for navigation — use NavigationStack value-based routing
- FlowLayout is already defined in LibraryView.swift — do not duplicate it
- Question type colour mapping must be consistent across TopicDetailView and TopicCardView
```

---

## `/add-api-endpoint`

**Purpose**: Add a new FastAPI endpoint and its corresponding Swift APIClient method.

```
Add a new API endpoint: <METHOD> <PATH>

Steps:
1. Read `llmlib/api/server.py` to understand existing endpoint patterns.
2. Define a Pydantic response model in `server.py` if the response shape is new.
3. Implement the endpoint using `db: LibraryDB = Depends(get_db)`.
4. Read `macapp/Services/APIClient.swift` to understand the existing fetch pattern.
5. Add a corresponding `func fetch<Name>(...) async throws -> <ResponseType>` in APIClient.
6. Add a matching Swift model in `macapp/Models/` if the response type is new.
7. Ensure CodingKeys in Swift match the snake_case JSON from Python.

Constraints:
- Never break existing endpoint signatures
- New endpoints must use the existing `get_db` dependency
- Swift model fields must exactly mirror the Pydantic response model
- Use `async throws` pattern in APIClient, consistent with existing methods
```

---

## `/sync-models`

**Purpose**: Verify and fix Python ↔ Swift model consistency.

```
Audit and sync the Python and Swift data models.

Check the following pairs for field consistency:

1. `llmlib/models.py :: Session`
   ↔ `macapp/Models/Session.swift :: Session`
   Fields to check: id, source_id, platform, title, created_at, updated_at,
                    messages, topic, tags, key_entities, question_type, summary

2. `llmlib/api/server.py :: TopicStats`
   ↔ `macapp/Models/LibraryOverview.swift :: TopicSummary`
   Fields to check: topic, count, top_tags (+ any new fields)

3. `llmlib/api/server.py :: LibraryOverview`
   ↔ `macapp/Models/LibraryOverview.swift :: LibraryOverview`

4. `llmlib/api/server.py :: SessionSummary`
   ↔ `macapp/Models/Session.swift` (summary variant if any)

For each mismatch found:
- Report the field name, Python type, and Swift type
- Apply the fix to both files in the same edit
- Ensure CodingKeys in Swift use the snake_case equivalent of the Python field name

Constraints:
- Never remove fields that exist on both sides without confirming the feature is gone
- Optional fields in Python (`Optional[str]`) → optional in Swift (`String?`)
- List fields in Python (`List[str]`) → array in Swift (`[String]`)
- datetime in Python → String in Swift (ISO8601, decoded via `iso8601DateDecodingStrategy`)
```

---

## `/run-tests`

**Purpose**: Run the full test suite and summarise failures.

```
Run the test suite for the Python backend.

Steps:
1. Run: `pytest tests/ -v --tb=short`
2. Report: number passed, failed, errors
3. For each failure: show the test name, the assertion that failed, and the likely cause
4. If all pass: confirm and suggest any missing test coverage for recently changed files

Do not fix failures automatically — report them first and wait for confirmation.
```
