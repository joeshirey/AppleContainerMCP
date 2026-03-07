import sys
from pathlib import Path

# Add src to the path so fastmcp can resolve and import the module locally
sys.path.insert(0, str(Path(__file__).parent.parent))

from apple_container_mcp.tools import mcp

def main():
    """Main entry point for running the Apple Container MCP Server."""
    # FastMCP run() automatically starts stdio mode if no args are matched
    mcp.run()

if __name__ == "__main__":
    main()
