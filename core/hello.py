"""
Core logic for taking in a name and replying hello.
Reference implementation on how to structure core logic and wire it up
with CLI, REST, MCP (stdio/SSE), and Agent Skills.
"""


def say_hello(name: str) -> str:
    """Return a personalized greeting message."""
    return f"Hello {name or 'Guest'} from Personal Ai ToolKit"
