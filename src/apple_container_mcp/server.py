import argparse
import logging
import sys

from apple_container_mcp.tools import mcp


def main() -> None:
    """Main entry point for running the Apple Container MCP Server."""
    parser = argparse.ArgumentParser(description="Apple Container MCP Server")
    parser.add_argument("--transport", choices=("stdio", "streamable-http"), default="stdio")
    parser.add_argument("--port", type=int, default=8000, help="Local HTTP port (default: 8000)")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    mcp.settings.host = "127.0.0.1"
    mcp.settings.port = args.port
    # Route server logs to stderr so they don't interfere with the MCP stdio transport.
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
