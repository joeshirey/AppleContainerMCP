# Apple Container MCP Server

The **Apple Container MCP Server** is a bridge between the Model Context Protocol (MCP) and Apple's open-source `container` CLI. It enables developers to manage lightweight macOS-native containers seamlessly using natural language via LLM interfaces (like Claude, Cursor, Antigravity, and VSCode). 

By acting as an MCP Server, this tool abstracts away the complexity of specific CLI flags, networking mounts, and system-level configurations, letting the LLM inspect, analyze, and automatically run macOS container workflows on your behalf.

---

## 🚀 Prerequisites

1. **Python 3.11+** installed on your machine.
2. **`uv` Package Manager**: Used for fast environment setup and execution.
   ```bash
   brew install uv
   ```
3. **Apple Container CLI**: Provided by Apple's virtualization framework. Ensure you have the background apiserver running before executing container workloads.
   ```bash
   # Assuming installation via typical Apple dev channels or homebrew if ported
   brew install apple-container
   container system start
   ```

---

## 📥 Installation & Setup

You can run this project directly via `uv`, which handles creating a virtual environment and installing the required dependencies (like `fastmcp`) on the fly. 

To use the server, add it to the configuration file of your preferred MCP Client.

### Antigravity (Google)
*(For full details, see the [AntiGravity MCP install and configuration docs](https://goto.google.com/antigravity-mcp) or internal Google documentation).*

1. Open your global MCP settings file (typically `~/.gemini/settings.json`).
2. Add the following entry replacing `/path/to/uv` with the path to your `uv` binary (e.g. `/opt/homebrew/bin/uv`) and `/absolute/path/to/AppleContainerMCP` with the root source folder of this repository:
```json
{
  "mcpServers": {
    "apple-container-mcp": {
      "command": "/usr/bin/env",
      "args": [
        "FASTMCP_SHOW_SERVER_BANNER=false",
        "/path/to/uv",
        "--directory",
        "/absolute/path/to/AppleContainerMCP",
        "run",
        "--quiet",
        "apple-container-mcp"
      ]
    }
  }
}
```

### Cursor
*(See the [Cursor MCP Documentation](https://docs.cursor.com/advanced/models-context-protocol) for more info).*
1. Open Cursor Settings -> Features -> MCP
2. Click **+ Add New MCP Server**
3. Choose **command** type.
4. **Name**: `apple-container`
5. **Command**: `/path/to/uv run --directory /absolute/path/to/AppleContainerMCP apple-container-mcp`

### Claude Desktop
*(See the [Official MCP Quickstart](https://modelcontextprotocol.io/quickstart/user) for full setup instructions).*
1. Open the Claude Desktop configuration file (`~/Library/Application Support/Claude/claude_desktop_config.json`).
2. Add the following entry:
```json
{
  "mcpServers": {
    "apple-container-mcp": {
      "command": "/usr/bin/env",
      "args": [
        "FASTMCP_SHOW_SERVER_BANNER=false",
        "/path/to/uv",
        "--directory",
        "/absolute/path/to/AppleContainerMCP",
        "run",
        "--quiet",
        "apple-container-mcp"
      ]
    }
  }
}
```
3. Restart Claude Desktop.

### VSCode (via Cline / RooCode)
*(See the [Cline MCP Documentation](https://github.com/cline/cline) for more details).*
If using an MCP extension like Cline in VSCode:
1. Open the extension MCP settings file (e.g. `~/.vscode/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`).
2. Add the server configuration:
```json
{
  "mcpServers": {
    "apple-container": {
      "command": "/usr/bin/env",
      "args": [
        "FASTMCP_SHOW_SERVER_BANNER=false",
        "/path/to/uv",
        "--directory",
        "/absolute/path/to/AppleContainerMCP",
        "run",
        "--quiet",
        "apple-container-mcp"
      ]
    }
  }
}
```

### Gemini CLI
*(See the [Gemini CLI Documentation](https://github.com/google/gemini-cli) for setup details).*
For CLI-based LLM tools that support MCP:
```json
{
  "mcpServers": {
    "apple-container-mcp": {
      "command": "/usr/bin/env",
      "args": [
        "FASTMCP_SHOW_SERVER_BANNER=false",
        "/path/to/uv",
        "--directory",
        "/absolute/path/to/AppleContainerMCP",
        "run",
        "--quiet",
        "apple-container-mcp"
      ]
    }
  }
}
```

*(Note: Make sure to replace `/path/to/AppleContainerMCP` with the actual absolute path to the repository on your machine).*

---

## 💬 10 Natural Language Prompt Examples

Once the MCP server is configured in your LLM client, you can use natural language to manage your Mac containers instead of typing commands manually. Try prompts like these:

1. **"Can you check if my Apple container system service is currently running?"**
2. **"List all of the images I currently have downloaded locally."**
3. **"Run a new detached Debian container with 2 CPUs and 4GB of memory."**
4. **"What containers are currently running on my machine?"**
5. **"Please pull the latest `nginx` image for me."**
6. **"Start an Ubuntu container named 'web-test', expose port 8080:80, and set the ENV variable FOO=bar."**
7. **"Stop the container with ID `abc12345` safely. If it hangs, force kill it."**
8. **"Can you fetch the last 50 lines of logs from my 'web-test' container?"**
9. **"I need to build an image from the Dockerfile in my current directory and tag it as 'my-app:v1'."**
10. **"Clean up my environment by removing all stopped containers."**

---

## 🛠 Active Capabilities (Tools Exposed)

- **System**: `check_apiserver_status`, `start_system`, `stop_system`, `system_status`
- **Containers**: `run_container`, `list_containers`, `stop_container`, `remove_container`, `inspect_container`, `get_logs`, `prune_containers`
- **Images**: `list_images`, `pull_image`, `build_image`, `check_build_status`, `remove_image`, `prune_images`
- **Networks**: `create_network`, `remove_network`, `list_networks`, `inspect_network`, `prune_networks`
- **Volumes**: `create_volume`, `remove_volume`, `list_volumes`, `inspect_volume`, `prune_volumes`