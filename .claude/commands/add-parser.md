Add a new parser for $ARGUMENTS exports.

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
