import asyncio
from apple_container_mcp.tools import mcp

async def main():
    print("Listing tools...")
    tools = await mcp.list_tools()
    for tool in tools:
        print(f" - {tool.name}: {tool.description}")

    print("\nCalling check_apiserver_status...")
    try:
        # Call the underlying function directly to bypass MCP JSON-RPC routing for a quick sanity check
        from apple_container_mcp.tools import check_apiserver_status
        result = check_apiserver_status()
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
