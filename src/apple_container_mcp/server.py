from apple_container_mcp.tools import mcp


def main() -> None:
    """Main entry point for running the Apple Container MCP Server."""
    # FastMCP run() automatically starts stdio mode if no args are matched
    mcp.run()


if __name__ == "__main__":
    main()
