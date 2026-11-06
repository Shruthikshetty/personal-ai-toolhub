from fastmcp import FastMCP

from core.hello import say_hello

# create a mcp instance
mcp = FastMCP("HelloService")


@mcp.tool()
def hello(name: str):
    """say hello from app to a given name"""
    return say_hello(name)


# Allows running directly via stdio: python -m app.mcp.hello
if __name__ == "__main__":
    mcp.run(transport="stdio")
