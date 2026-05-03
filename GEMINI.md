# GEMINI.md - Project Structure & Context

## Project Overview
`llmlib` is a personal LLM knowledge base CLI. It ingests chat exports from platforms like ChatGPT and Claude, normalizes them, generates tags and embeddings, and stores them in a local `sqlite-vec` database for offline querying.

## Directory Structure
- `llmlib/`: Main package
  - `cli.py`: Entry point using `Typer`.
  - `models.py`: Pydantic models for `Session`, `Message`, and metadata.
  - `parsers/`: Logic for parsing different LLM export formats.
  - `storage/`: Database schema and `sqlite-vec` interactions.
  - `llm/`: Logic for tagging and embeddings (Gemini API / Local).
- `DESIGN.md`: Original design specification.
- `pyproject.toml`: Dependency management and CLI script registration.

## Engineering Conventions
- Use **Pydantic** for data validation and serialization.
- Follow **Typer** conventions for CLI commands.
- Database: Use `sqlite-vec` for vector search.
- Privacy: Ensure all data stays local unless explicitly sending to Gemini API for tagging/embedding.

## Key Files to Remember
- `llmlib/models.py`: Source of truth for data structures.
- `llmlib/parsers/base.py`: Abstract base class for all parsers.
- `llmlib/storage/db.py`: Database connection and query logic.
