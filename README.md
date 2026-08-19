# Apple Container MCP Server

The **Apple Container MCP Server** is a bridge between the Model Context Protocol (MCP) and Apple's open-source `container` CLI. It enables developers to manage lightweight macOS-native containers seamlessly using natural language via LLM interfaces (like Claude, Cursor, Antigravity, and VSCode).

By acting as an MCP Server, this tool abstracts away the complexity of specific CLI flags, networking mounts, and system-level configurations, letting the LLM inspect, analyze, and automatically run macOS container workflows on your behalf.

The package installs two commands. `apple-container-mcp` is the MCP server described above. `d2c` is a standalone Docker-to-Apple-Container command translator for the terminal, with no LLM involved. See [`d2c` — Docker Command Translator](#-d2c--docker-command-translator) below.

---

## 🚀 Prerequisites

1. **Python 3.11+** installed on your machine.
2. **`uv` Package Manager**: Used for fast environment setup and execution.

   ```bash
   brew install uv
   ```

3. **Apple Container CLI**: Provided by Apple's virtualization framework. **Requires container CLI 1.0+; validated against 1.2.2, which is the recommended version** (Apple Silicon and macOS 26 recommended). 1.2.0 ships upstream security fixes — XPC request validation, kernel archive integrity checks, and no symlink following when copying user configuration — so `check_environment` will suggest upgrading if you are on an older 1.x. 1.2.1 added `run_container`'s `read_only_paths`/`masked_paths` and `build_image`'s `ssh` parameter (see [Security Model](#-security-model)); a local Kubernetes plugin (`container k8s`) also shipped in 1.2.1 but isn't wrapped by this server yet. Install via Homebrew, then start the system service:

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

- **System**: `check_apiserver_status`, `start_system`, `stop_system`, `system_status`, `system_version`, `system_property_list`, `system_df`, `system_logs`, `check_environment`
- **Containers**: `run_container` (supports `--init-image`, rosetta, platform, labels, `shm_size`, and more), `list_containers`, `start_container`, `stop_container`, `remove_container`, `export_container`, `inspect_container`, `exec_in_container`, `get_logs`, `prune_containers`, `stats_container`
- **Files**: `copy_to_container`, `copy_from_container`
- **Machines**: `create_machine` (supports nested virtualization on container 1.1+), `run_machine`, `list_machines`, `inspect_machine`, `set_machine`, `set_default_machine`, `machine_logs`, `stop_machine`, `delete_machine`
- **Images**: `list_images`, `pull_image`, `build_image`, `check_build_status`, `list_builds`, `tag_image`, `push_image`, `inspect_image`, `remove_image`, `prune_images`
- **Networks**: `create_network`, `remove_network`, `list_networks`, `inspect_network`, `prune_networks`
- **Volumes**: `create_volume`, `remove_volume`, `list_volumes`, `inspect_volume`, `prune_volumes`
- **Registry**: `registry_login`, `registry_logout`
- **Builder**: `builder_start`, `builder_stop`, `builder_status`

### Prompts Exposed

- **`troubleshoot_container`**: Guided workflow to inspect and debug a failing container.
- **`build_and_run_workflow`**: Step-by-step guide to build an image from a local project and run it.
- **`cleanup_environment`**: Safely review and prune stopped containers, unused images, volumes, and networks.
- **`setup_private_registry`**: Walk through authenticating with a private container registry.

### Resources Exposed

- **System Status**: `apple-container://system/status`

---

## 🔁 `d2c` — Docker Command Translator

This package also installs a second, standalone command: `d2c`. It takes a Docker CLI invocation and runs the Apple Container equivalent, so muscle memory and existing shell scripts keep working without a rewrite. It has nothing to do with MCP and needs no LLM client — it is a plain terminal tool.

### Usage

```bash
d2c [--dry-run] <docker-command> [args...]
```

If you installed via `uvx`, run it the same way you run the server:

```bash
uvx --from git+https://github.com/joeshirey/AppleContainerMCP.git d2c ps -a
```

From a local clone, `uv sync` puts `d2c` on your path inside the virtualenv. Many people alias it (`alias docker=d2c`) once they trust the translations.

### See the translation before running it

`--dry-run` prints what would run and exits without touching your system. Use it when you are unsure how a command maps:

```console
$ d2c --dry-run ps -a
[d2c dry-run] docker ps -a
           → container list -a

$ d2c --dry-run rmi nginx
[d2c dry-run] docker rmi nginx
           → container image delete nginx
           ℹ  'rmi' maps to Apple Container's 'image delete' subcommand
```

Without `--dry-run`, `d2c` executes the translated command and exits with that command's exit code, so it drops into scripts and CI cleanly.

### What it translates

Thirty Docker commands map onto Apple Container equivalents, covering container lifecycle (`ps`, `run`, `exec`, `stop`, `start`, `kill`, `rm`, `logs`, `inspect`, `cp`, `create`, `export`, `stats`), images (`images`, `pull`, `push`, `rmi`, `tag`, `build`, `load`, `save`), registry auth (`login`, `logout`), and the `network` / `volume` / `system` / `image` / `builder` management groups. Where a name differs enough to be surprising, the translation carries a note explaining the mapping.

The Docker management namespace is stripped automatically, so `docker container run ubuntu` and `docker run ubuntu` both resolve to `container run ubuntu`.

Flags after the command are passed through unchanged. `d2c` renames commands, not flags — a Docker flag with no Apple Container counterpart will be rejected by the `container` CLI rather than caught by `d2c`.

### Commands with no equivalent

Twenty-four Docker commands have no Apple Container counterpart. Rather than failing with a confusing CLI error, `d2c` refuses them up front and suggests what to do instead:

```console
$ d2c compose up
✗  'docker compose' is not supported by Apple Container.
   Hint: No equivalent — Apple Container has no orchestration layer. Run containers individually with 'container run'.
```

This covers the Swarm family (`service`, `stack`, `swarm`, `node`, `secret`, `config`), image operations Apple Container does not implement (`commit`, `import`, `history`, `manifest`, `search`), lifecycle gaps (`pause`, `unpause`, `restart`, `rename`, `attach`, `wait`, `port`, `diff`, `events`, `checkpoint`), plus `compose`, `context`, and `plugin`.

### Docker global flags

Global flags that come before the subcommand are handled separately. `--debug` / `-D` translates to `container --debug`. Flags that describe a world Apple Container does not have — remote daemons (`--host` / `-H`), context switching (`--context` / `-c`), TLS options, `--config`, `--log-level` / `-l` — trigger a warning and a confirmation prompt:

```console
$ d2c --host tcp://remote:2376 ps
⚠  '--host' is not supported by Apple Container.
   Apple Container connects to the local system service only — no remote daemon.
   Continue anyway? [y/N]
```

Answering anything but `y` aborts. The prompt defaults to no and treats a closed stdin as no, so a script that inherits a stale `DOCKER_HOST`-style flag stops instead of silently running against the wrong target.

Only flags appearing before the first positional argument are treated as global. `d2c exec mycontainer bash -c "echo hi"` keeps its `-c` where it belongs.

---

## 🔒 Security Model

This server applies several deliberate restrictions to keep LLM-driven container operations safe:

- **Path validation:** `build_image`'s `context_path` and `run_container`'s `env_file` are restricted to paths inside your home directory. The check uses `os.path.realpath` and a trailing-separator suffix test to prevent prefix-match bypasses (e.g. `/Users/joe` vs `/Users/joey`). `copy_to_container` and `copy_from_container` apply the same policy: the HOST path is restricted to your home directory in both directions (`copy_to_container`'s `source` and `copy_from_container`'s `dest`).
- **Argument blocklist:** `run_container`'s `args_override` parameter rejects flags that escalate privilege, weaken isolation, or expose host credentials: `--privileged`, `--cap-add`, `--cap-drop`, `--security-opt`, `--device`, `--pid`, `--ipc`, `--userns`, `--cgroupns`, `--no-new-privileges`, `--kernel` / `-k`, `--kernel-arg`, `--ssh`. This is defense in depth rather than the only barrier: `args_override` is appended *after* the image name, and the CLI treats everything after the image as arguments to the container's init process, not as `run` options. A blocked flag that slipped through would reach the guest as a command argument, not as a privilege grant. The blocklist stays because that positional guarantee is a CLI implementation detail, not a documented contract.
- **Linux capabilities (Apple Container 0.12+):** Container 0.12 promoted `--cap-add` / `--cap-drop` to documented public flags. **This MCP deliberately does NOT expose them as tool parameters.** Capability selection meaningfully weakens process isolation; if you need it, invoke `container run` directly. We may revisit this in a future release with an allowlist mechanism.
- **`--kernel`, `--kernel-arg`, and `run`'s `--ssh` blocked:** `--kernel` loads an arbitrary host filesystem path as a guest kernel. `--kernel-arg` (added in Apple Container 1.2) appends raw arguments to the guest kernel command line, so a value like `init=/bin/sh` subverts the VM before any container process starts. `run`'s `--ssh` forwards the host SSH agent socket into the *running* container, letting anything inside use your credentials silently for the container's whole lifetime. All three are blocked from `args_override` and none is exposed as a tool parameter.
- **`read_only_paths` / `masked_paths` are additive-only (Apple Container 1.2.1+, EXPERIMENTAL upstream):** `run_container` exposes these to *add* paths to the runtime's default read-only/masked lists, which only tightens isolation. The upstream CLI also accepts a `NONE` sentinel there that clears the defaults instead, widening the container's attack surface — this tool rejects that value.
- **`build_image`'s `--ssh` is a different, narrower flag:** it forwards the host's SSH agent to the *build* process only (Apple Container 1.2.1+), reachable solely during an explicit `RUN --mount=type=ssh` step in the Dockerfile — the same class of deliberate, scoped credential exposure as the existing `secrets` parameter. This is unrelated to `run`'s `--ssh` above, which stays blocked.
- **No shell injection:** `subprocess.run` is always called with an argument list, never with `shell=True`.
- **Credential handling:** `registry_login` passes the password via `stdin` (`--password-stdin`) so it never appears in process arguments.
