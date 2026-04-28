# **Technical Design Document: Apple Container MCP Server**

## **1\. Architecture Overview**

The solution is built as a Python-based MCP server using the FastMCP framework. It communicates with the host macOS system via the container binary using the subprocess module.

### **Components**

1. **MCP Host (e.g., Claude Desktop):** The user interface.  
2. **MCP Server:** The Python process orchestrating tools and logic.  
3. **Apple Container CLI:** The container binary (installed via Apple’s open-source project).  
4. **XPC Interface:** The underlying communication channel between the CLI and the container-apiserver daemon.

## **2\. Technical Stack**

* **Language:** Python 3.11+  
* **Framework:** mcp (using FastMCP)  
* **Communication:** Standard I/O (stdio)  
* **Serialization:** JSON (native container output)

## **3\. Tool Implementation Details**

### **A. The Execution Wrapper**

To ensure consistency, all tools use a shared function `_run_container_cmd(args, timeout)` in `cli_wrapper.py`.

**Key behaviours:**

1. **JSON format allowlist:** A set of `(command, subcommand)` tuple prefixes (e.g. `("image", "ls")`, `("network", "ls")`) identifies commands that support `--format json`. The flag is appended automatically when the command matches and `--format` is not already present.

2. **Heuristic timeout selection:** Commands containing tokens in `LONG_RUNNING_COMMANDS = {"pull", "push", "start", "build"}` (checked across *all* args, not just `args[0]`) receive a 300-second timeout. All other commands default to 30 seconds. An explicit `timeout` parameter overrides both heuristics.

3. **Structured error normalisation:** `subprocess.CalledProcessError` is caught and re-raised as `ContainerCLIError(message, exit_code, stderr)`. Connection-refused errors are normalised into a well-known "daemon is not running" message. Timeouts produce `exit_code = -1`.

4. **Structured logging:** Every command execution is logged at `DEBUG` level, failures at `WARNING`, and timeouts at `ERROR` — all routed to `stderr` so they don't interfere with the MCP stdio transport.

```python
def _run_container_cmd(args: List[str], timeout: Optional[int] = None) -> Any:
    full_cmd = ["container"] + args

    FORMAT_JSON_COMMANDS = {
        ("ls",), ("image", "ls"), ("network", "ls"),
        ("volume", "ls"),
        # Added in Apple Container 0.12 support update:
        ("system", "version"), ("system", "status"),
        ("builder", "status"), ("stats",),
        # Note: ("builder", "ls") was removed — that subcommand
        # does not exist in 0.12 (audit-verified).
    }
    leading = tuple(args)
    matches_allowlist = any(leading[:len(prefix)] == prefix for prefix in FORMAT_JSON_COMMANDS)
    if "--format" not in full_cmd and matches_allowlist:
        full_cmd.extend(["--format", "json"])

    if timeout is None:
        timeout = (LONG_RUNNING_TIMEOUT_SECONDS
                   if any(a in LONG_RUNNING_COMMANDS for a in args)
                   else DEFAULT_TIMEOUT_SECONDS)

    logger.debug("Executing: %s (timeout=%ss)", " ".join(full_cmd), timeout)

    try:
        process = subprocess.run(full_cmd, capture_output=True, text=True, check=True, timeout=timeout)
        stdout = process.stdout.strip()
        if not stdout:
            return {}
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            if matches_allowlist or args[0] == "inspect":
                return {"raw_output": stdout, "error": "Failed to parse JSON output"}
            return {"raw_output": stdout}
    except subprocess.TimeoutExpired as e:
        logger.error("Command timed out after %ss: %s", timeout, " ".join(full_cmd))
        raise ContainerCLIError(f"Command timed out after {timeout}s: ...", -1, "...")
    except subprocess.CalledProcessError as e:
        logger.warning("Command failed (exit %d): %s", e.returncode, " ".join(full_cmd))
        stderr_msg = e.stderr.strip().lower()
        if "connection refused" in stderr_msg or "cannot connect" in stderr_msg:
            raise ContainerCLIError("The container-apiserver daemon is not running. ...", ...)
        raise ContainerCLIError(f"Command failed with exit code {e.returncode}", ...)
```

### **B. Tool Mapping Strategy**

| MCP Tool Name | CLI Command Equivalent | Logic Notes |
| :---- | :---- | :---- |
| list_containers | container ls -a | Parse JSON array, return count and names. |
| run_container | container run ... | Map memory, cpus, ports, env, volumes, and init_image arguments to flags. |
| exec_in_container | container exec ... | Run commands inside running containers. |
| export_container | container export -o [file] [id] | Export container filesystem as an OCI-layout tar archive. |
| build_image | container build ... | Build images asynchronously. Supports `--secret`. |
| check_build_status | N/A | Poll in-memory build status. |
| tag_image | container image tag | Tag local images. |
| push_image | container image push | Push images to registries. |
| registry_login | container registry login | Authenticates with a registry via stdin. |
| create_network | container network create | Supports `--subnet` and `--mtu`. |
| create_volume | container volume create | Supports `-s` (size). |
| get_logs | container logs -n [limit] [id] | Use native `-n` flag instead of `--tail`. |
| system_status | container system status | Check if daemon is active. |
| builder_status | container builder status | Check if image builder is active. |
| prune_* | container * prune | Clean up unused resources (containers, images, networks, volumes). |
| system_version | container system version | Returns CLI/apiserver versions as JSON. Works without the daemon. (Apple Container 0.12+) |
| stats_container | container stats --no-stream [containers...] | One-shot resource-usage snapshot. Always non-streaming. (Apple Container 0.12+) |

### **C. Prompts (Guided Workflows)**

The server implements several `mcp.prompt` handlers to guide users through complex tasks:
- `troubleshoot_container`: Steps to debug a failing container.
- `build_and_run_workflow`: Full lifecycle from local code to running container.
- `cleanup_environment`: Guided cleanup of unused resources.
- `setup_private_registry`: Authentication and image movement for private registries.

## **4\. Error Handling & Edge Cases**

1. **Daemon Not Running:** If a command fails with "connection refused" or "cannot connect," `_run_container_cmd` normalises the error into a well-known `ContainerCLIError` message. `check_apiserver_status` catches this directly and returns `{"status": "stopped"}`.  
2. **Long-Running Builds:** `container build` blocks the process.  
   * *Solution:* `build_image` launches `_run_build_thread` in a daemon thread. The tool returns a `build_id` immediately for polling via `check_build_status`.  
   * *State Management:* An in-memory `active_builds` dict guarded by `threading.Lock()` tracks progress. Completed/failed builds are evicted after `BUILD_TTL_SECONDS` (1 hour) to prevent memory leaks.  
   * *Timeout:* `"build"` is included in `LONG_RUNNING_COMMANDS` so it receives the 300-second extended timeout by default.  
3. **Timeouts:** `pull`, `push`, `start`, and `build` commands receive a 300-second timeout. All other commands default to 30 seconds. Timeouts raise `ContainerCLIError` with `exit_code = -1`.  
4. **Large Log Files:** Avoid sending MBs of text back to the LLM.  
   * *Solution:* `get_logs` uses a `limit` parameter (default 100 lines) passed to the CLI via `-n`.  
5. **Standardised Response Shape:** Every tool returns `{"status": "ok/error", ...}`. Exceptions are caught and returned as structured dicts rather than propagated to the MCP host.

## **5\. Security Model**

* **Local Execution:** The MCP server only accepts requests from the local MCP Host.  
* **Path Validation:** `build_image` validates that `context_path` is within the user's home directory using `os.path.realpath` with a trailing `os.sep` check to prevent prefix-match bypasses (e.g. `/Users/joe` vs `/Users/joey`). The same guard is applied to `env_file` in `run_container`.  
* **Argument Sanitization:** `subprocess.run` is called with a list of arguments (never `shell=True`) to prevent shell injection. `run_container`'s `args_override` parameter is validated against a blocklist of dangerous flags to prevent privilege escalation, capability grants, and credential exposure via LLM prompt injection. The current blocklist: `--privileged`, `--cap-add`, `--cap-drop`, `--security-opt`, `--device`, `--pid`, `--ipc`, `--userns`, `--cgroupns`, `--no-new-privileges`, `--kernel` / `-k`, `--ssh`.
* **Capabilities and 0.12 audit additions:** Apple Container 0.12 promoted `--cap-add` / `--cap-drop` to documented public flags. This MCP deliberately keeps them in the blocklist and does NOT expose them as tool parameters. The 0.12 CLI audit also surfaced `--kernel` / `-k` (arbitrary host kernel-image path injection) and `--ssh` (host SSH-agent socket forwarding); both have been added to the blocklist for the same reasons.  
* **Credential Handling:** `registry_login` passes the password via `stdin` to avoid exposing it in process arguments.

## **6\. Deployment Plan**

1. **Pre-requisites:** Python 3.11+, `uv` (`brew install uv`), and the Apple `container` CLI (`brew install container`).  
2. **Installation:** Run directly via `uvx` (no clone required) or install from a local clone using `uv sync --dev`.  
3. **Configuration:** Add the MCP server to your client's configuration. Example for Claude Desktop (`~/Library/Application Support/Claude/claude_desktop_config.json`):

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

See the README for configuration snippets for Cursor, Gemini CLI, VSCode/Cline, and Antigravity.

## **7\. Future Considerations**

* **Streamed Logs:** Support for MCP resources to provide real-time log updates.  
* **Virtualization Framework Integration:** Direct inspection of the Virtualization.framework state if the CLI is insufficient.
