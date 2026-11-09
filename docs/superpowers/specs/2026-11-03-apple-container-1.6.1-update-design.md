# Design Specification: Apple Container 1.6.1 Compatibility & Validation

**Date:** 2026-11-03  
**Target:** Apple Container 1.6.1 (on top of merged 1.6.0 baseline)  
**Package:** `applecontainermcp` (bump from 0.7.0 to 0.7.1)  

---

## 1. Context & Baseline Audit

`origin/main` includes support up to Apple Container 1.6.0 (which introduced `commit_container`, `network_aliases`, `d2c commit`, and `clean_container`).

Apple has released `container` CLI version 1.6.1. An audit of upstream changes between 1.6.0 and 1.6.1 reveals:

1. **Kubernetes Plugin Renamed to `container cluster` (PR #2427)**:
   - Upstream renamed the Kubernetes CLI plugin from `container k8s` to `container cluster`.
   - All references to `container k8s` in documentation, TDD notes, and changelogs should be updated to `container cluster`.
2. **OCI Image Platform & Runtime Introspection (PR #2422)**:
   - `container run` and `container create` now infer OS, architecture, and runtime directly from the image's OCI index/manifest + config.
   - Runtime defaults to `container-runtime-<os>` unless `--runtime` is explicitly set.
   - Users no longer need to supply redundant `--platform` or `--arch` flags for single-platform foreign images when Rosetta is active.
3. **Forwarded Process Signal Encoding & Passing (PR #1778, PR #2276, PR #1854)**:
   - Fixed forwarded process signal encoding so signals (e.g. SIGTERM, SIGINT) are properly delivered to container processes.
   - Removed SIGWINCH from signal kill set.
4. **Cluster Creation Concurrency & Host Port Conflicts (PR #2399)**:
   - Fixed host port conflicts and leftover failed nodes during concurrent cluster creation.
5. **Plugin Unavailability Error Normalization**:
   - In 1.6.0+, commands like `build`, `builder`, and `cluster` are CLI plugins under `/opt/homebrew/Cellar/container/1.6.1/libexec/container-plugins/`.
   - When the container service/daemon is stopped, running these commands fails with:
     `Error: Plugins are unavailable. Start the container system services and retry: container system start`
   - `_run_container_cmd` currently checks for `"connection refused"` or `"cannot connect to the container daemon"`. It must also recognize `"plugins are unavailable"` to normalize this into a clear, actionable error instructing the user to run `container system start`.
6. **Recommended Version Bump**:
   - Bump `RECOMMENDED_CLI_VERSION` from `(1, 6, 0)` to `(1, 6, 1)`.
   - `check_environment` recommends upgrading on versions older than 1.6.1 to ensure users have the signal passing and cluster fixes.

---

## 2. Goals & Non-Goals

### Goals
- Normalize `"plugins are unavailable"` errors in `_run_container_cmd` across CLI wrapper calls.
- Bump `RECOMMENDED_CLI_VERSION` to `(1, 6, 1)` and update `check_environment` tests and messaging.
- Update documentation and changelogs noting the upstream rename of `container k8s` to `container cluster`, OCI platform/runtime auto-introspection, and signal fixes.
- Create local validation document `docs/superpowers/plans/2026-11-03-apple-container-1.6.1-validation.md`.
- Bump package version to `0.7.1`.
- Ensure 100% test pass rate with full coverage across pytest, ruff, and mypy.

### Non-Goals
- Wrapping the `container cluster` plugin directly in MCP tools (Kubernetes multi-node management is outside current MCP container scope).

---

## 3. Detailed Component Changes

### 3.1 CLI Wrapper: Error Normalization & Version Bump
- **File**: `src/apple_container_mcp/cli_wrapper.py`
- Update:
  ```python
  RECOMMENDED_CLI_VERSION = (1, 6, 1)
  ```
- In `_run_container_cmd`:
  ```python
  stderr_msg = e.stderr.strip().lower()
  if (
      "connection refused" in stderr_msg
      or "cannot connect to the container daemon" in stderr_msg
      or "plugins are unavailable" in stderr_msg
  ):
      raise ContainerCLIError(
          "The container-apiserver daemon or CLI plugins are unavailable. "
          "Please start the system service first ('container system start').",
          e.returncode,
          e.stderr,
      ) from e
  ```

### 3.2 System Tools: Environment Recommendations
- **File**: `src/apple_container_mcp/tools/system.py`
- `check_environment` references `RECOMMENDED_CLI_VERSION` dynamically (`".".join(map(str, RECOMMENDED_CLI_VERSION))`), which will now report `1.6.1`.

### 3.3 Documentation & Notes
- **`README.md`**: Note recommendation of Apple Container 1.6.1; update `k8s` mentions to `container cluster`.
- **`CHANGELOG.md`**: Add `[0.7.1]` release entry for Apple Container 1.6.1 support and plugin error normalization.
- **`docs/TDD.md`**: Update version recommendations and notes on 1.6.1 changes.
- **`docs/superpowers/plans/2026-11-03-apple-container-1.6.1-validation.md`**: Record validation findings on Apple Container 1.6.1.

---

## 4. Verification Plan

1. **Unit Tests**:
   - Add test in `tests/test_cli_wrapper.py` verifying that stderr containing `"Error: Plugins are unavailable. Start the container system services and retry: container system start"` raises `ContainerCLIError` with normalized guidance.
   - Update `tests/test_tools.py` and `tests/test_container_160.py` to assert against `(1, 6, 1)`.
2. **Quality Gates**:
   - `uv run pytest` (all tests passing)
   - `uv run ruff check .`
   - `uv run ruff format --check .`
   - `uv run mypy src/ tests/`
