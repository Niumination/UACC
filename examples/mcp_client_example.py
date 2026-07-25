"""
Example: Interacting with UACC MCP Server via MCP Client Session.

This example demonstrates how an MCP client connects to the UACC MCP server
over stdio or SSE transport and calls UACC tools.

Usage:
    python examples/mcp_client_example.py
"""

import asyncio
import sys
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def main():
    print("=" * 60)
    print("  UACC MCP Client Example")
    print("  Connecting to UACC MCP Server via stdio...")
    print("=" * 60)

    # Launch UACC MCP server process
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "uacc.mcp"],
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # Initialize connection
            await session.initialize()
            print("\n🔌 Connected to UACC MCP Server successfully!")

            # List available tools
            tools_result = await session.list_tools()
            print(f"\n🛠️  Available Tools ({len(tools_result.tools)}):")
            for tool in tools_result.tools:
                print(f"  - {tool.name}: {tool.description.split('.')[0]}")

            # Call uacc_planner tool
            print("\n⚡ Executing uacc_planner...")
            planner_res = await session.call_tool(
                "uacc_planner",
                arguments={
                    "task": "Find Notepad window and get screen info",
                    "mode": "UI Navigation",
                },
            )
            print("Planner Output:")
            for content in planner_res.content:
                print(content.text)


if __name__ == "__main__":
    asyncio.run(main())
