import typer
import os
from typing import Optional
from pathlib import Path

from llmlib.parsers.chatgpt import ChatGPTParser
from llmlib.parsers.claude import ClaudeParser
from llmlib.storage.db import LibraryDB

app = typer.Typer(help="Personal LLM Knowledge Base CLI")


def _get_tagger():
    """Returns an initialized GeminiTagger instance using the GEMINI_API_KEY environment variable."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        typer.echo("Error: GEMINI_API_KEY is required for this command.", err=True)
        raise typer.Exit(code=1)
    try:
        from llmlib.llm.gemini import GeminiTagger
    except ImportError:
        typer.echo(
            "Error: Gemini SDK is not installed. Install the dependencies from pyproject.toml.",
            err=True,
        )
        raise typer.Exit(code=1)

    return GeminiTagger(api_key=api_key)


def _get_parser(platform: str):
    """Returns the appropriate parser instance for the given platform."""
    parser_map = {
        "chatgpt": ChatGPTParser(),
        "claude": ClaudeParser(),
    }
    parser = parser_map.get(platform.lower())
    if parser is None:
        typer.echo("Error: platform must be either 'chatgpt' or 'claude'.", err=True)
        raise typer.Exit(code=1)
    return parser


@app.command()
def ingest(
    platform: str = typer.Argument(..., help="Platform: 'chatgpt' or 'claude'"),
    file_path: Path = typer.Argument(..., help="Path to export file"),
):
    """
    Ingest LLM export files into the library.
    """
    if not file_path.exists() or not file_path.is_file():
        typer.echo(f"Error: file not found: {file_path}", err=True)
        raise typer.Exit(code=1)

    parser = _get_parser(platform)
    tagger = _get_tagger()
    db = LibraryDB()

    try:
        sessions = parser.parse(file_path)
        if not sessions:
            typer.echo("No sessions found in export file.")
            return

        ingested_count = 0
        for session in sessions:
            metadata = tagger.tag_session(session)
            session.topic = metadata.get("topic")
            raw_tags = metadata.get("tags", [])
            session.tags = [tag for tag in raw_tags if isinstance(tag, str)]
            question_type = metadata.get("question_type")
            session.question_type = question_type if isinstance(question_type, str) else None
            summary = metadata.get("summary")
            session.summary = summary if isinstance(summary, str) else None

            embedding = tagger.embed_session(session)
            db.upsert_session(session, embedding)
            ingested_count += 1

        typer.echo(f"Ingested {ingested_count} sessions from {platform}.")
    finally:
        db.close()

@app.command()
def ask(
    query: str = typer.Argument(..., help="Question to search in library"),
):
    """
    Search your library for an answer.
    """
    tagger = _get_tagger()
    db = LibraryDB()

    try:
        query_embedding = tagger.embed_query(query)
        results = db.search(query_embedding, top_k=5)

        if not results:
            typer.echo("No matching sessions found.")
            return

        typer.echo(f"Top {len(results)} results:")
        for index, session in enumerate(results, start=1):
            tags = ", ".join(session.tags) if session.tags else "-"
            summary = session.summary or "-"
            typer.echo(f"{index}. {session.title}")
            typer.echo(f"   summary: {summary}")
            typer.echo(f"   tags: {tags}")
    finally:
        db.close()

@app.command()
def list(
    tag: Optional[str] = typer.Option(None, help="Filter by tag"),
    platform: Optional[str] = typer.Option(None, help="Filter by platform"),
    type: Optional[str] = typer.Option(None, help="Filter by question type"),
):
    """
    List ingested sessions with optional filters.
    """
    db = LibraryDB()
    try:
        sessions = db.list_sessions(tag=tag, platform=platform, question_type=type)
        if not sessions:
            typer.echo("No sessions found.")
            return

        for session in sessions:
            tags = ", ".join(session.tags) if session.tags else "-"
            qtype = session.question_type or "-"
            typer.echo(
                f"{session.id} | {session.platform} | {qtype} | {session.title} | tags: {tags}"
            )
    finally:
        db.close()

@app.command()
def show(
    session_id: str = typer.Argument(..., help="ID of the session to display"),
):
    """
    Show details of a specific session.
    """
    db = LibraryDB()
    try:
        session = db.get_session(session_id)
        if session is None:
            typer.echo(f"Session not found: {session_id}", err=True)
            raise typer.Exit(code=1)

        typer.echo(f"id: {session.id}")
        typer.echo(f"source_id: {session.source_id}")
        typer.echo(f"platform: {session.platform}")
        typer.echo(f"title: {session.title}")
        typer.echo(f"created_at: {session.created_at.isoformat()}")
        typer.echo(f"updated_at: {session.updated_at.isoformat()}")
        typer.echo(f"topic: {session.topic or '-'}")
        typer.echo(f"question_type: {session.question_type or '-'}")
        typer.echo(f"summary: {session.summary or '-'}")
        typer.echo(f"tags: {', '.join(session.tags) if session.tags else '-'}")
        typer.echo("messages:")
        for idx, message in enumerate(session.messages, start=1):
            timestamp = message.timestamp.isoformat() if message.timestamp else "-"
            typer.echo(f"  {idx}. [{message.role}] ({timestamp})")
            typer.echo(f"     {message.content}")
    finally:
        db.close()

if __name__ == "__main__":
    app()
