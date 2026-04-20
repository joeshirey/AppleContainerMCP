import logging
import sys

from apple_container_mcp.tools import mcp


def main() -> None:
    """Main entry point for running the Apple Container MCP Server."""
    # Route server logs to stderr so they don't interfere with the MCP stdio transport.
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    # FastMCP run() automatically starts stdio mode if no args are matched
    mcp.run()


if __name__ == "__main__":
    main()
