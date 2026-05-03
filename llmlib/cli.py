import typer
from typing import Optional
from pathlib import Path

app = typer.Typer(help="Personal LLM Knowledge Base CLI")

@app.command()
def ingest(
    platform: str = typer.Argument(..., help="Platform: 'chatgpt' or 'claude'"),
    file_path: Path = typer.Argument(..., help="Path to export file"),
):
    """
    Ingest LLM export files into the library.
    """
    typer.echo(f"Ingesting {platform} data from {file_path}...")
    # Implementation will go here

@app.command()
def ask(
    query: str = typer.Argument(..., help="Question to search in library"),
):
    """
    Search your library for an answer.
    """
    typer.echo(f"Searching for: {query}")
    # Implementation will go here

@app.command()
def list(
    tag: Optional[str] = typer.Option(None, help="Filter by tag"),
    type: Optional[str] = typer.Option(None, help="Filter by question type"),
):
    """
    List ingested sessions with optional filters.
    """
    typer.echo(f"Listing sessions (tag={tag}, type={type})...")
    # Implementation will go here

@app.command()
def show(
    session_id: str = typer.Argument(..., help="ID of the session to display"),
):
    """
    Show details of a specific session.
    """
    typer.echo(f"Showing session: {session_id}")
    # Implementation will go here

if __name__ == "__main__":
    app()
