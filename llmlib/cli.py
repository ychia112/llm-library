import os
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from llmlib.parsers.chatgpt import ChatGPTParser
from llmlib.parsers.claude import ClaudeParser
from llmlib.storage.db import LibraryDB

app = typer.Typer(help="Personal LLM Knowledge Base CLI")
console = Console()


def _get_tagger(provider: str, model_override: Optional[str]):
    provider = provider.lower()
    if provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            typer.echo("Error: GEMINI_API_KEY is required for Gemini provider.", err=True)
            raise typer.Exit(code=1)
        from llmlib.llm.gemini import GeminiTagger
        model = model_override or "gemini-2.0-flash-lite"
        return GeminiTagger(api_key=api_key, model=model)
    if provider == "ollama":
        from llmlib.llm.ollama import OllamaTagger
        model = model_override or "gemma4:26b"
        return OllamaTagger(model=model)
    typer.echo(f"Error: Unknown provider '{provider}'.", err=True)
    raise typer.Exit(code=1)


def _get_parser(platform: str):
    parser_map = {"chatgpt": ChatGPTParser(), "claude": ClaudeParser()}
    parser = parser_map.get(platform.lower())
    if parser is None:
        typer.echo("Error: platform must be either 'chatgpt' or 'claude'.", err=True)
        raise typer.Exit(code=1)
    return parser


@app.command()
def ingest(
    platform: str = typer.Argument(..., help="Platform: 'chatgpt' or 'claude'"),
    file_path: Path = typer.Argument(..., help="Path to export file"),
    provider: str = typer.Option("gemini", "--provider", help="AI provider: gemini | ollama"),
    model: Optional[str] = typer.Option(None, "--model", help="Override default model"),
):
    """Ingest LLM export files into the library."""
    if not file_path.exists() or not file_path.is_file():
        typer.echo(f"Error: file not found: {file_path}", err=True)
        raise typer.Exit(code=1)

    parser = _get_parser(platform)
    tagger = _get_tagger(provider, model)
    current_model = getattr(tagger, "tagger_model", getattr(tagger, "model", "unknown"))
    console.print(f"[bold green][llmlib][/bold green] provider={provider.lower()} model={current_model}")

    sessions = parser.parse(file_path)
    if not sessions:
        console.print("No sessions found in export file.")
        return

    total_sessions = len(sessions)
    ingested_count = 0
    failed_count = 0

    with LibraryDB() as db:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Starting...", total=total_sessions)

            for session in sessions:
                short_title = (session.title or "Untitled")[:50]
                try:
                    progress.update(task, description=f"[cyan]Tagging:[/cyan]  {short_title}")
                    metadata = tagger.tag_session(session)
                    session.topic = metadata.get("topic")
                    session.tags = [t for t in metadata.get("tags", []) if isinstance(t, str)]
                    qtype = metadata.get("question_type")
                    session.question_type = qtype if qtype in {"debug", "design", "research", "howto"} else "research"
                    session.summary = metadata.get("summary")

                    progress.update(task, description=f"[yellow]Embedding:[/yellow] {short_title}")
                    embedding = tagger.embed_session(session)

                    progress.update(task, description=f"[green]Saving:[/green]    {short_title}")
                    db.upsert_session(session, embedding)

                    ingested_count += 1

                except Exception as e:
                    failed_count += 1
                    console.print(f"[red]  FAILED:[/red] {short_title} — {e}")

                finally:
                    progress.advance(task, 1)

                if provider.lower() == "gemini":
                    time.sleep(2)

    console.print(
        f"[bold green][llmlib][/bold green] Done. "
        f"success=[green]{ingested_count}[/green], "
        f"failed=[red]{failed_count}[/red], "
        f"total={total_sessions}"
    )


@app.command()
def ask(
    query: str = typer.Argument(..., help="Question to search in library"),
    provider: str = typer.Option("gemini", "--provider", help="Embedding provider: gemini | ollama"),
    model: Optional[str] = typer.Option(None, "--model", help="Override default model"),
):
    """Search your library for an answer."""
    tagger = _get_tagger(provider, model)
    with LibraryDB() as db:
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


@app.command()
def list(
    tag: Optional[str] = typer.Option(None, help="Filter by tag"),
    platform: Optional[str] = typer.Option(None, help="Filter by platform"),
    type: Optional[str] = typer.Option(None, help="Filter by question type"),
):
    """List ingested sessions with optional filters."""
    with LibraryDB() as db:
        sessions = db.list_sessions(tag=tag, platform=platform, question_type=type)
        if not sessions:
            typer.echo("No sessions found.")
            return
        for session in sessions:
            tags = ", ".join(session.tags) if session.tags else "-"
            qtype = session.question_type or "-"
            typer.echo(f"{session.id} | {session.platform} | {qtype} | {session.title} | tags: {tags}")


@app.command()
def show(
    session_id: str = typer.Argument(..., help="ID of the session to display"),
):
    """Show details of a specific session."""
    with LibraryDB() as db:
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


if __name__ == "__main__":
    app()
