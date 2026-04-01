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
3. **Apple Container CLI**: Provided by Apple's virtualization framework. Tested with **v0.11.0**. Install via Homebrew, then start the system service:
   ```bash
   brew install container
   container system start
   ```

---

## 📥 Installation & Setup

You have two options for installing and running the Apple Container MCP server: using `uvx` to run it directly from GitHub (recommended), or cloning the repository to run it locally.

Both methods require adding the server to your preferred MCP Client's configuration file.

### Option A: Direct Execution via `uvx` (Recommended)
This approach does not require cloning the repository. `uvx` will automatically fetch, sandbox, and run the latest version of the server. Ensure you have `uv` installed (`brew install uv`).

### Option B: Clone & Local Environment
Use this approach if you want to inspect or modify the code locally. 
```bash
git clone https://github.com/joeshirey/AppleContainerMCP.git
cd AppleContainerMCP
```
*Note: For Option B, you must replace `/path/to/uv` with your actual `uv` path (e.g. `/opt/homebrew/bin/uv`) and `/absolute/path/to/AppleContainerMCP` with the directory you cloned into.*

---

### Configuration by Tool

Below are the specific instructions for adding the MCP server to major LLM tools. Use either the **Option A** or **Option B** snippet.

#### 1. Antigravity (Google)
*(For full details, see the [AntiGravity MCP install and configuration docs](https://goto.google.com/antigravity-mcp) or internal Google documentation).*

Open your global MCP settings file (typically `~/.gemini/settings.json`) and add:

**Option A (`uvx`):**
```json
{
  "mcpServers": {
    "apple-container-mcp": {
      "command": "/usr/bin/env",
      "args": [
        "FASTMCP_SHOW_SERVER_BANNER=false",
        "uvx",
        "--from",
        "git+https://github.com/joeshirey/AppleContainerMCP.git",
        "apple-container-mcp"
      ]
    }
  }
}
```

**Option B (Clone):**
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

#### 2. Cursor
*(See the [Cursor MCP Documentation](https://docs.cursor.com/advanced/models-context-protocol) for more info).*
1. Open Cursor Settings -> Features -> MCP
2. Click **+ Add New MCP Server**
3. Choose **command** type.
4. **Name**: `apple-container`
5. **Command**:
   - **Option A (`uvx`)**: `/usr/bin/env FASTMCP_SHOW_SERVER_BANNER=false uvx --from git+https://github.com/joeshirey/AppleContainerMCP.git apple-container-mcp`
   - **Option B (Clone)**: `/usr/bin/env FASTMCP_SHOW_SERVER_BANNER=false /path/to/uv run --directory /absolute/path/to/AppleContainerMCP --quiet apple-container-mcp`

#### 3. Claude Desktop
*(See the [Official MCP Quickstart](https://modelcontextprotocol.io/quickstart/user) for full setup instructions).*

Open the Claude Desktop configuration file (`~/Library/Application Support/Claude/claude_desktop_config.json`) and add:

**Option A (`uvx`):**
```json
{
  "mcpServers": {
    "apple-container-mcp": {
      "command": "/usr/bin/env",
      "args": [
        "FASTMCP_SHOW_SERVER_BANNER=false",
        "uvx",
        "--from",
        "git+https://github.com/joeshirey/AppleContainerMCP.git",
        "apple-container-mcp"
      ]
    }
  }
}
```

**Option B (Clone):**
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
*(Restart Claude Desktop after updating).*

#### 4. VSCode (via Cline / RooCode)
*(See the [Cline MCP Documentation](https://github.com/cline/cline) for more details).*

Open the extension MCP settings file (e.g., `~/.vscode/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`) and add:

**Option A (`uvx`):**
```json
{
  "mcpServers": {
    "apple-container": {
      "command": "/usr/bin/env",
      "args": [
        "FASTMCP_SHOW_SERVER_BANNER=false",
        "uvx",
        "--from",
        "git+https://github.com/joeshirey/AppleContainerMCP.git",
        "apple-container-mcp"
      ]
    }
  }
}
```

**Option B (Clone):**
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

#### 5. Gemini CLI
*(See the [Gemini CLI Documentation](https://github.com/google/gemini-cli) for setup details).*

Open your Gemini CLI settings file (typically `~/.gemini/settings.json`) and add:

**Option A (`uvx`):**
```json
{
  "mcpServers": {
    "apple-container-mcp": {
      "command": "/usr/bin/env",
      "args": [
        "FASTMCP_SHOW_SERVER_BANNER=false",
        "uvx",
        "--from",
        "git+https://github.com/joeshirey/AppleContainerMCP.git",
        "apple-container-mcp"
      ]
    }
  }
}
```

**Option B (Clone):**
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

## 🛠 Active Capabilities

### Tools Exposed

- **System**: `check_apiserver_status`, `start_system`, `stop_system`, `system_status`
- **Containers**: `run_container` (supports `--init-image`), `list_containers`, `start_container`, `stop_container`, `remove_container`, `export_container`, `inspect_container`, `get_logs`, `prune_containers`
- **Images**: `list_images`, `pull_image`, `build_image`, `check_build_status`, `remove_image`, `prune_images`
- **Networks**: `create_network`, `remove_network`, `list_networks`, `inspect_network`, `prune_networks`
- **Volumes**: `create_volume`, `remove_volume`, `list_volumes`, `inspect_volume`, `prune_volumes`

### Resources Exposed

- **System Status**: `apple-container://system/status`