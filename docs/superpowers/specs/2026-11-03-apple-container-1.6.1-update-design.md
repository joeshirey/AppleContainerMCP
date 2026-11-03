# Design Specification: Apple Container 1.6.1 Compatibility & Feature Support

**Date:** 2026-11-03  
**Target:** Apple Container 1.6.1 (with coverage of 1.3.0 - 1.6.1 changes)  
**Package:** `applecontainermcp` (bump from 0.6.0 to 0.7.0)  

---

## 1. Context and Problem Statement

Apple has released `container` CLI version 1.6.1 (and earlier 1.3–1.6 releases). AppleContainerMCP currently claims recommendation and testing up to Apple Container 1.2.2.

Upstream changes between 1.2.2 and 1.6.1 introduce new capabilities, architectural reorganizations, and security advisories:
1. **`container commit` (1.6.0)**: Ability to create a new OCI image reference from a running or stopped container's filesystem.
2. **`container clean` (1.4.1)**: Runs an in-guest one-shot filesystem trim (`fstrim`) across container root filesystems and named volumes to reclaim host sparse disk space.
3. **CLI Plugin System (1.6.0 / 1.6.1)**: Commands such as `build`, `builder`, and `cluster` (formerly `k8s`) were extracted as CLI plugins. When the system service is not running, invoking these commands produces `Error: Plugins are unavailable. Start the container system services and retry: container system start`.
4. **`d2c` translation gaps**: In `d2c`, `commit` was previously hardcoded in `UNSUPPORTED` with a hint stating that Apple Container does not support committing images. With 1.6.0, `docker commit` can be translated directly to `container commit`.
5. **Version recommendations & Environment checking**: `cli_wrapper.py` still recommends `(1, 2)`. It should be bumped to `(1, 6)` to advise users of the latest security fixes (GHSA/CVE advisories from 1.3 through 1.6) and capabilities.
6. **Rename of Kubernetes plugin**: The upstream plugin `container k8s` was renamed to `container cluster` in 1.6.1.

---

## 2. Goals & Non-Goals

### Goals
- Expose `commit_container` as an MCP tool in `apple_container_mcp.tools.containers`.
- Expose `clean_containers` as an MCP tool in `apple_container_mcp.tools.containers`.
- Enable `d2c commit` command translation in `d2c.registry`.
- Enhance CLI error normalization in `cli_wrapper.py` to detect plugin unavailability when `container system start` is needed.
- Update `RECOMMENDED_CLI_VERSION` to `(1, 6)` and update `check_environment` recommendation guidance.
- Maintain full test coverage with 100% pass rate across unit tests and strict type checking (`mypy`).
- Bump project version to `0.7.0`.

### Non-Goals
- Wrapping the `container cluster` (Kubernetes) plugin as MCP tools in this iteration (Kubernetes lifecycle requires its own dedicated tool group and multi-node orchestrator semantics; will be scoped in a future release if requested).
- Wrapping `container system dns` (admin/sudo privileges required for creation/deletion).

---

## 3. Detailed Component Design

### 3.1 New MCP Tool: `commit_container`

- **Module**: `src/apple_container_mcp/tools/containers.py`
- **Decorator**: `@mcp.tool()`
- **Signature**:
  ```python
  @mcp.tool()
  def commit_container(
      container_id: str,
      target_image: str,
  ) -> Dict[str, Any]:
      """
      Create a new OCI image from a container's filesystem (Apple Container 1.6.0+).

      Args:
          container_id: ID or name of the container to commit.
          target_image: Target image reference (e.g. "my-image:latest" or "user/repo:v1").

      Returns:
          Dictionary with status 'ok' and image reference or 'error'.
      """
  ```
- **Validation**:
  - `container_id` must be non-empty after trimming whitespace; otherwise return `{"status": "error", "message": "Container ID cannot be empty."}`.
  - `target_image` must be non-empty after trimming whitespace; otherwise return `{"status": "error", "message": "Target image reference cannot be empty."}`.
- **Execution**:
  - `result = _run_container_cmd(["commit", container_id.strip(), target_image.strip()])`
  - Returns `{"status": "ok", "message": f"Successfully committed container '{container_id}' to image '{target_image}'.", "image": target_image}`.
- **Re-export**: Re-export `commit_container` in `src/apple_container_mcp/tools/__init__.py`.

### 3.2 New MCP Tool: `clean_containers`

- **Module**: `src/apple_container_mcp/tools/containers.py`
- **Decorator**: `@mcp.tool()`
- **Signature**:
  ```python
  @mcp.tool()
  def clean_containers(
      container_ids: Optional[List[str]] = None,
  ) -> Dict[str, Any]:
      """
      Trim unused filesystem blocks in running containers and their named volumes
      to reclaim host disk space (Apple Container 1.4.1+).

      Args:
          container_ids: Optional list of container IDs to clean. If omitted, cleans all running containers.

      Returns:
          Dictionary with status 'ok' and clean output or 'error'.
      """
  ```
- **Execution**:
  - Command: `cmd = ["clean"]`
  - If `container_ids` provided: filter out blanks, validate at least one valid ID if non-empty list was supplied. Append IDs to `cmd`.
  - `result = _run_container_cmd(cmd)`
  - Returns `{"status": "ok", "message": "Container cleanup completed successfully.", "details": result}`.
- **Re-export**: Re-export `clean_containers` in `src/apple_container_mcp/tools/__init__.py`.

### 3.3 `d2c` Command Translation Update

- **Module**: `src/d2c/unsupported.py` and `src/d2c/registry.py`
- **Changes**:
  - Remove `"commit"` from `UNSUPPORTED` mapping in `unsupported.py`.
  - Add to `COMMANDS` mapping in `registry.py`:
    ```python
    "commit": CommandTranslation(container_cmd=["container", "commit"]),
    ```
- **CLI Behavior**:
  - `d2c commit webapp webapp:v2` translates to `container commit webapp webapp:v2`.
  - `d2c commit --dry-run webapp webapp:v2` prints the translated command without running it.

### 3.4 CLI Wrapper Error Normalization & Version Updates

- **Module**: `src/apple_container_mcp/cli_wrapper.py`
- **Changes**:
  - Update `RECOMMENDED_CLI_VERSION = (1, 6)`.
  - In `_run_container_cmd`:
    ```python
    stderr_msg = e.stderr.strip().lower()
    if (
        "connection refused" in stderr_msg
        or "cannot connect to the container daemon" in stderr_msg
        or "plugins are unavailable" in stderr_msg
    ):
        raise ContainerCLIError(
            "The container-apiserver daemon or plugins are unavailable. "
            "Please start the system service first ('container system start').",
            e.returncode,
            e.stderr,
        ) from e
    ```

### 3.5 System Tool Environment Recommendation

- **Module**: `src/apple_container_mcp/tools/system.py`
- **Changes**:
  - In `check_environment()`:
    Update recommendation text for `version < RECOMMENDED_CLI_VERSION`:
    ```python
    result["recommendation"] = (
        f"Apple Container {recommended} is recommended (you have {major}.{minor}). "
        f"It adds container commit, disk trimming (container clean), CLI plugin architecture, "
        f"DNS aliases, and important OCI security fixes. Upgrade with `brew upgrade container`."
    )
    ```

### 3.6 Project Metadata & Documentation

- **`pyproject.toml`**: Bump version to `0.7.0`.
- **`src/apple_container_mcp/__init__.py`**: Bump `__version__ = "0.7.0"`.
- **`README.md`**: Update version recommendations to 1.6.1, document `commit_container` and `clean_containers`, update `d2c` command tables, and note the rename of `container k8s` to `container cluster`.
- **`docs/TDD.md`**: Add section for Apple Container 1.6.1 support and architectural decisions.
- **`CHANGELOG.md`**: Document `v0.7.0` additions and improvements.

---

## 4. Testing & Verification Plan

1. **Unit Tests (`tests/test_tools.py`)**:
   - `test_commit_container_success`: mocks `_run_container_cmd(["commit", "c1", "img1"])`.
   - `test_commit_container_validation_errors`: empty container ID or empty target image.
   - `test_commit_container_cli_error`: handling `ContainerCLIError`.
   - `test_clean_containers_all_success`: mocks `_run_container_cmd(["clean"])`.
   - `test_clean_containers_specific_ids`: mocks `_run_container_cmd(["clean", "c1", "c2"])`.
   - `test_clean_containers_cli_error`: handling `ContainerCLIError`.
   - `test_check_environment_recommends_upgrade_on_older_minor`: update mock to return `(1, 5)` or `(1, 2)` and assert recommendation appears mentioning `1.6`.
   - `test_check_environment_no_recommendation_on_current_minor`: mock returns `(1, 6)` and verify no recommendation.

2. **Wrapper Tests (`tests/test_cli_wrapper.py`)**:
   - `test_run_container_cmd_plugins_unavailable_error`: simulates CLI returning exit code 1 with stderr `"Error: Plugins are unavailable. Start the container system services and retry: container system start"` and verifies clean normalization.

3. **`d2c` Tests (`tests/d2c/`)**:
   - `tests/d2c/test_unsupported.py`: remove commit assertions; verify other unsupported commands remain intact.
   - `tests/d2c/test_registry.py`: assert `commit` translates `["commit", "c1", "img:v1"]` to `["container", "commit", "c1", "img:v1"]`.
   - `tests/d2c/test_cli.py`: test CLI execution with `commit`.

4. **Integration/Static Checks**:
   - `uv run pytest` (all existing + new tests passing).
   - `uv run ruff check .`
   - `uv run ruff format --check .`
   - `uv run mypy src/ tests/`
