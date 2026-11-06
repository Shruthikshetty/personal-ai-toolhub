"""
CLI entry point for ToolHub (Personal AI Toolkit).
"""

import typer

from core.hello import sayHello

app = typer.Typer(
    name="toolhub",
    help="ToolHub — Personal AI Toolkit CLI",
    no_args_is_help=True,
    add_completion=False,
)


@app.command()
def hello(name: str = typer.Argument("world", help="Name of the person to greet")):
    """Say hello using the core greeting logic."""
    typer.echo(sayHello(name))


@app.command()
def version():
    """Print the ToolHub version."""
    typer.echo("ToolHub v0.1.0")


if __name__ == "__main__":
    app()
