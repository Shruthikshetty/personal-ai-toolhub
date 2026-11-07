"""
CLI entry point for ToolHub (Personal AI Toolkit).
"""

import asyncio

import typer

from core.hello import say_hello
from core.search import search as core_search

app = typer.Typer(
    name="toolhub",
    help="ToolHub — Personal AI Toolkit CLI",
    no_args_is_help=True,
    add_completion=False,
)


@app.command()
def hello(name: str = typer.Argument("world", help="Name of the person to greet")):
    """Say hello using the core greeting logic."""
    typer.echo(say_hello(name))


@app.command(name="web_search")
@app.command(name="search")
def web_search(
    query: str = typer.Argument(..., help="Search keywords or question"),
    max_results: int = typer.Option(
        5, "--max-results", "-m", help="Max number of web search results"
    ),
    fetch_content: bool = typer.Option(
        False, "--content", "-c", help="Fetch readable page content"
    ),
):
    """Search the web using the core search logic."""
    typer.echo(f"🔍 Searching for: '{query}' (top {max_results} results)...\n")
    try:
        results = asyncio.run(
            core_search(
                query=query,
                max_results=max_results,
                fetch_content=fetch_content,
            )
        )
        if not results:
            typer.secho("No results found.", fg=typer.colors.YELLOW)
            return

        for i, r in enumerate(results, 1):
            typer.secho(f"{i}. {r.title}", fg=typer.colors.BRIGHT_CYAN, bold=True)
            typer.secho(f"   URL: {r.url}", fg=typer.colors.BLUE)
            typer.echo(f"   {r.snippet}\n")
            if r.content:
                typer.secho(f"   [Content]: {r.content[:300]}...\n", dim=True)
    except Exception as e:
        typer.secho(f"Error during search: {e}", fg=typer.colors.RED)


@app.command()
def version():
    """Print the ToolHub version."""
    typer.echo("ToolHub v0.1.0")


if __name__ == "__main__":
    app()
