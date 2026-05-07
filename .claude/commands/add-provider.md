Add a new LLM provider called $ARGUMENTS.

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
