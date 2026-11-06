from fastmcp import FastMCP

from core.hello import sayHello

# create a mcp instance
mcp = FastMCP("HelloService")


@mcp.tool()
def hello(name: str):
    """say hello from app to a given name"""
    return sayHello(name)


# Allows running directly via stdio: python -m app.mcp.hello
if __name__ == "__main__":
    mcp.run(transport="stdio")
