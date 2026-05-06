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
from rich.panel import Panel
from rich.text import Text

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
        model = model_override or os.getenv("LLMLIB_OLLAMA_MODEL", "llama3.2:3b-instruct-q4_K_M")
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
    provider: str = typer.Option("ollama", "--provider", help="AI provider: gemini | ollama"),
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
                    delay = float(os.getenv("LLMLIB_GEMINI_DELAY", "0"))
                    if delay > 0:
                        time.sleep(delay)

    console.print(
        f"[bold green][llmlib][/bold green] Done. "
        f"success=[green]{ingested_count}[/green], "
        f"failed=[red]{failed_count}[/red], "
        f"total={total_sessions}"
    )


@app.command()
def ask(
    query: str = typer.Argument(..., help="Your question"),
    provider: str = typer.Option("ollama", "--provider", help="Provider: gemini | ollama"),
    model: Optional[str] = typer.Option(None, "--model", help="Override embedding model"),
    chat_model: Optional[str] = typer.Option(None, "--chat-model", help="Override chat model for LLM fallback"),
    threshold_hit: float = typer.Option(0.85, "--threshold-hit", help="Cosine similarity threshold for direct hit"),
    threshold_partial: float = typer.Option(0.60, "--threshold-partial", help="Cosine similarity threshold for partial hit"),
    top_k: int = typer.Option(5, "--top-k", help="Number of sessions to retrieve"),
):
    """Search your library for an answer. History-First approach."""
    tagger = _get_tagger(provider, model)
    
    with LibraryDB() as db:
        query_embedding = tagger.embed_query(query)
        results = db.search_with_scores(query_embedding, top_k=top_k)
        
        best_score = results[0][1] if results else 0.0
        
        if best_score >= threshold_hit:
            # HIT
            session, score = results[0]
            console.print(f"[bold green]✓ HIT ({score:.2f})[/bold green] - Found in library")
            console.print(Panel(f"[bold]{session.title}[/bold]\n\n{session.summary or 'No summary available.'}", title="Summary"))
            
            console.print("\n[bold]Relevant Messages:[/bold]")
            for msg in session.messages[:5]: # Show first 5 messages
                role_color = "cyan" if msg.role in ["user", "human"] else "green"
                console.print(Text.assemble((f"[{msg.role}] ", role_color), msg.content))
            
            console.print(f"\n[bold green]tokens used: 0[/bold green]")
            
        elif best_score >= threshold_partial:
            # PARTIAL
            console.print(f"[bold yellow]⚡ PARTIAL ({best_score:.2f})[/bold yellow] - context injected")
            
            # Compose context from top-3 summaries
            context_parts = []
            for s, _ in results[:3]:
                context_parts.append(f"Title: {s.title}\nSummary: {s.summary}")
            context_text = "\n\n".join(context_parts)
            
            system_prompt = f"You are a helpful assistant. Use the following context from the user's past conversations to answer the question:\n\n{context_text}"
            
            if provider.lower() == "ollama":
                from llmlib.llm.ollama import OllamaTagger
                if isinstance(tagger, OllamaTagger):
                    answer = tagger.chat(system_prompt, query, model=chat_model)
                    console.print(Panel(answer, title="Assistant (Gemma)"))
                else:
                    console.print("[red]Error: Partial hit requires Ollama for chat fallback currently.[/red]")
            else:
                 console.print("[red]Error: Partial hit requires Ollama for chat fallback currently.[/red]")
                 
        else:
            # MISS
            console.print(f"[bold red]✗ MISS ({best_score:.2f})[/bold red] - LLM was queried")
            
            if provider.lower() == "ollama":
                from llmlib.llm.ollama import OllamaTagger
                if isinstance(tagger, OllamaTagger):
                    answer = tagger.chat("You are a helpful assistant.", query, model=chat_model)
                    console.print(Panel(answer, title="Assistant (Gemma)"))
                else:
                    console.print("[red]Error: Miss requires Ollama for chat fallback currently.[/red]")
            else:
                console.print("[red]Error: Miss requires Ollama for chat fallback currently.[/red]")


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


@app.command()
def serve(
    port: int = typer.Option(8765, "--port", help="Port to run the API server"),
    host: str = typer.Option("0.0.0.0", "--host", help="Host to bind"),
):
    """Start the REST API server for Mac App integration."""
    try:
        import uvicorn
        from llmlib.api.server import app as api_app
    except ImportError:
        typer.echo("Error: API dependencies not installed. Run: pip install 'llmlib[api]'", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"[llmlib] API server running at http://{host}:{port}")
    typer.echo("[llmlib] Press Ctrl+C to stop")
    uvicorn.run(api_app, host=host, port=port, log_level="error")


if __name__ == "__main__":
    app()
