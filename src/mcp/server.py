from __future__ import annotations

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("JAT MCP Server")


@mcp.tool()
def jat_list_sessions(page_size: int = 30) -> str:
    return "Not yet implemented"


@mcp.tool()
def jat_create_workflow(name: str, description: str = "") -> str:
    return "Not yet implemented"


@mcp.tool()
def jat_get_workflow_status(workflow_id: str) -> str:
    return "Not yet implemented"


@mcp.tool()
def jat_list_accounts() -> str:
    return "Not yet implemented"


if __name__ == "__main__":
    mcp.run()
