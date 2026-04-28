# Apple Container 0.12 Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update AppleContainerMCP from supporting Apple Container 0.11.0 to 0.12.0, adding `system_version`, the `journal` parameter on `create_volume`, verified gap-fill tools, an expanded JSON allowlist, and a documented capabilities-policy decision — without exposing `--cap-add` / `--cap-drop` as tool parameters.

**Architecture:** Strictly additive. New tools follow the existing `@mcp.tool()` pattern in the appropriate domain module under `src/apple_container_mcp/tools/`. The `cli_wrapper` `FORMAT_JSON_COMMANDS` set is expanded based on a CLI audit run as the first task. No structural / refactoring changes.

**Tech Stack:** Python 3.11+, `mcp` (FastMCP), pytest + pytest-mock + pytest-cov, ruff, mypy. Project uses `uv` for environment management.

**Spec:** `docs/superpowers/specs/2026-04-28-apple-container-0.12-support-design.md`

---

## Task 1: CLI verification audit

The audit results drive Tasks 5, 6, 7, and 8. Run the installed `container 0.12` CLI and record outputs in an audit document that subsequent tasks consume.

**Files:**
- Create: `docs/superpowers/plans/2026-04-28-cli-audit-results.md`

- [ ] **Step 1: Verify `container 0.12.0` is installed**

Run: `container --version`
Expected: Version string contains `0.12.0` (or higher).
If not 0.12+: STOP. Install/update the CLI before continuing — `brew upgrade container`.

- [ ] **Step 2: Capture all relevant `--help` output to a scratch file**

Run the following commands. Save *each* command's full stdout+stderr verbatim (do not summarize) to a temporary scratch file you'll consume in Step 3.

```bash
container --version
container --help
container system --help
container system version --help 2>&1 || echo "MISSING: system version"
container system version --format json 2>&1 | head -40 || echo "MISSING"
container system status --format json 2>&1 | head -40
container builder ls --format json 2>&1 | head -40
container builder status --format json 2>&1 | head -40
container inspect --help 2>&1 | head -40
container volume create --help 2>&1
container stats --help 2>&1 || echo "MISSING: stats"
container events --help 2>&1 || echo "MISSING: events"
container restart --help 2>&1 || echo "MISSING: restart"
container pause --help 2>&1 || echo "MISSING: pause"
container unpause --help 2>&1 || echo "MISSING: unpause"
container rename --help 2>&1 || echo "MISSING: rename"
container cp --help 2>&1 || echo "MISSING: cp"
container history --help 2>&1 || echo "MISSING: history"
container run --help 2>&1
container build --help 2>&1
```

For each `--format json` command, also test that the output is parseable JSON:
```bash
container system status --format json | python3 -c 'import json,sys; json.load(sys.stdin); print("PARSE OK")' 2>&1
container builder ls --format json | python3 -c 'import json,sys; json.load(sys.stdin); print("PARSE OK")' 2>&1
container builder status --format json | python3 -c 'import json,sys; json.load(sys.stdin); print("PARSE OK")' 2>&1
```

For `container system version --format json`, also verify it works WITHOUT a daemon (it should — version info is local). Test by stopping the system, then re-running:
```bash
container system stop
container system version --format json
container system start  # restart for subsequent tasks
```
Note whether `system version` requires the daemon; this matters for tool documentation.

- [ ] **Step 3: Write the audit results document**

Create `docs/superpowers/plans/2026-04-28-cli-audit-results.md` with the following template, filled in from Step 2's outputs. **Every "RESULT" line must be a definitive answer derived from observed CLI output, not a guess.**

```markdown
# Apple Container 0.12 CLI Audit Results

Run on: <YYYY-MM-DD>
Installed CLI version: <output of `container --version`>

## A. JSON allowlist candidates

For each command, record whether it accepts `--format json` AND emits parseable JSON.

| Command | --format json supported? | Parses as JSON? | Add to FORMAT_JSON_COMMANDS? |
|---|---|---|---|
| `container system version` | yes/no | yes/no | yes/no |
| `container system status` | yes/no | yes/no | yes/no |
| `container builder ls` | yes/no | yes/no | yes/no (currently has `# if supported` hedge — resolve) |
| `container builder status` | yes/no | yes/no | yes/no |
| `container inspect <id>` | yes/no | yes/no | N/A — already JSON-by-default; no allowlist entry needed |

For each "yes/yes" row above, the `cli_wrapper.FORMAT_JSON_COMMANDS` set must gain the corresponding tuple: e.g. `("system", "version")`, `("system", "status")`, `("builder", "status")`. Also resolve the `("builder", "ls")` hedge comment based on the result.

## B. system version

- Subcommand exists: yes/no
- Requires daemon to be running: yes/no (if "no", tool docstring should say so)
- Sample JSON output keys (top-level): <list keys observed, e.g. ["cli_version", "builder_version", "kernel_version", ...]>

## C. volume create --journal

- Flag spelling: `--journal` (boolean), or `--journal=true`, or other? RECORD EXACT FLAG: <e.g. `--journal`>
- Position relative to volume name: <e.g. flag before name; same as `-s`>
- Default behavior (when flag omitted): <e.g. journaling off>

## D. Gap-fill tool candidates — definitive existence check

| Subcommand | Exists in 0.12? | Has bounded (non-streaming) form? | Include in plan? |
|---|---|---|---|
| `container restart` | yes/no | always bounded | yes/no |
| `container pause` | yes/no | always bounded | yes/no |
| `container unpause` | yes/no | always bounded | yes/no |
| `container stats` | yes/no | yes (`--no-stream`) / no | yes/no |
| `container events` | yes/no | yes (`--since`/`--until`) / no | yes/no |
| `container rename` | yes/no | always bounded | yes/no |
| `container cp` | yes/no | always bounded | yes/no |
| `container history` | yes/no | always bounded | yes/no |

For each "include = yes" tool, also record:
- Exact CLI invocation form (e.g. `container restart <id>`).
- Required vs optional flags.
- For `stats` / `events`: the exact non-streaming flag spelling (e.g. `--no-stream`, `--since`, `--until`).

## E. Other 0.12 changes worth noting

- `container run --help`: list any new flags observed beyond what we already support (init-image, rosetta, platform, mount, etc.). Flag any that look security-sensitive — they may need to join `_DANGEROUS_FLAGS`.
- `container build --help`: list any new flags observed.

## Summary: actionable inputs to subsequent tasks

- **FORMAT_JSON_COMMANDS additions:** <list, e.g. `("system", "version")`, `("system", "status")`>
- **`("builder", "ls")` hedge resolution:** keep / remove comment
- **system_version requires daemon:** yes/no
- **Journal flag spelling:** `<flag>`
- **Gap-fill tools to implement:** <list, e.g. `restart_container`, `pause_container`, `unpause_container`, `rename_container`>
- **New `_DANGEROUS_FLAGS` additions (if any):** <list or "none">
```

- [ ] **Step 4: Commit the audit document**

```bash
git add docs/superpowers/plans/2026-04-28-cli-audit-results.md
git commit -m "docs(plan): record container 0.12 CLI audit results"
```

---

## Task 2: Bump package version to 0.2.0

Strictly mechanical. Done early so subsequent commits show `0.2.0` in any auto-generated metadata.

**Files:**
- Modify: `pyproject.toml:3`
- Modify: `src/apple_container_mcp/__init__.py:3`

- [ ] **Step 1: Update `pyproject.toml`**

Edit `pyproject.toml` — change line 3 from:

```toml
version = "0.1.0"
```

to:

```toml
version = "0.2.0"
```

- [ ] **Step 2: Update `src/apple_container_mcp/__init__.py`**

Edit `src/apple_container_mcp/__init__.py` — change line 3 from:

```python
__version__ = "0.1.0"
```

to:

```python
__version__ = "0.2.0"
```

- [ ] **Step 3: Run the test suite to confirm nothing broke**

Run: `uv run pytest -q`
Expected: All existing tests pass (no version-coupled test failures).

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml src/apple_container_mcp/__init__.py
git commit -m "chore: bump package version to 0.2.0 for Apple Container 0.12 support"
```

---

## Task 3: Remove version-specific qualifier from `export_container`

The `export_container` docstring and error message still say "in 0.11.0" — this behavior is now stable across 0.11+ and the version qualifier is misleading.

**Files:**
- Modify: `src/apple_container_mcp/tools/containers.py:184-187`
- Modify: `tests/test_tools.py:343` (assertion text)

- [ ] **Step 1: Update the test to match the new error message (write failing test first)**

Edit `tests/test_tools.py`. Find the `test_export_container_no_output_file` test (around line 340-343):

```python
def test_export_container_no_output_file(mocker):
    result = export_container("12345")
    assert result["status"] == "error"
    assert "output_file is required" in result["message"]
```

Change the assertion to match the new wording (we're removing the "in 0.11.0"):

```python
def test_export_container_no_output_file(mocker):
    result = export_container("12345")
    assert result["status"] == "error"
    assert "output_file is required" in result["message"]
    # Should not reference any specific Apple Container CLI version
    assert "0.11.0" not in result["message"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_tools.py::test_export_container_no_output_file -v`
Expected: FAIL — current message still contains "0.11.0".

- [ ] **Step 3: Update the source**

Edit `src/apple_container_mcp/tools/containers.py` lines 183-194. Change from:

```python
@mcp.tool()
def export_container(container_id: str, output_file: Optional[str] = None) -> Dict[str, Any]:
    """Export a container's filesystem as a tar archive. Requires an output_file path in 0.11.0."""
    if not output_file:
        return {"status": "error", "message": "output_file is required in 0.11.0 to save the tar archive."}

    args = ["export", "-o", output_file, container_id]
    try:
        _run_container_cmd(args)
        return {"status": "ok", "message": f"Successfully exported container {container_id} to {output_file}."}
    except ContainerCLIError as e:
        return {"status": "error", "message": f"Failed to export container {container_id}.", "details": e.stderr}
```

to:

```python
@mcp.tool()
def export_container(container_id: str, output_file: Optional[str] = None) -> Dict[str, Any]:
    """Export a container's filesystem as a tar archive (OCI layout). Requires an output_file path."""
    if not output_file:
        return {"status": "error", "message": "output_file is required to save the tar archive."}

    args = ["export", "-o", output_file, container_id]
    try:
        _run_container_cmd(args)
        return {"status": "ok", "message": f"Successfully exported container {container_id} to {output_file}."}
    except ContainerCLIError as e:
        return {"status": "error", "message": f"Failed to export container {container_id}.", "details": e.stderr}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/test_tools.py::test_export_container_no_output_file -v`
Expected: PASS.

Then run the full test file to confirm no regressions:
Run: `uv run pytest tests/test_tools.py -q`
Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/apple_container_mcp/tools/containers.py tests/test_tools.py
git commit -m "docs: remove version-specific 0.11.0 qualifier from export_container

The OCI-tar export behavior is stable across 0.11 and 0.12; the
version-specific note in the docstring and error message was
misleading. Wording is now version-agnostic."
```

---

## Task 4: Document capabilities policy in `_DANGEROUS_FLAGS`

Add a code comment near `_DANGEROUS_FLAGS` documenting the deliberate decision to leave `--cap-add` and `--cap-drop` blocked even though 0.12 promotes them to documented public flags. No code/behavior change.

**Files:**
- Modify: `src/apple_container_mcp/tools/__init__.py:25-40`

- [ ] **Step 1: Add the policy comment**

Edit `src/apple_container_mcp/tools/__init__.py`. Replace lines 25-40:

```python
# Blocklist of flags that must never be passed via args_override in run_container.
# These flags escalate privileges or grant capabilities that an LLM should not control.
_DANGEROUS_FLAGS: frozenset[str] = frozenset(
    {
        "--privileged",
        "--cap-add",
        "--cap-drop",
        "--security-opt",
        "--device",
        "--pid",
        "--ipc",
        "--userns",
        "--cgroupns",
        "--no-new-privileges",
    }
)
```

with:

```python
# Blocklist of flags that must never be passed via args_override in run_container.
# These flags escalate privileges or grant capabilities that an LLM should not control.
#
# Policy note on --cap-add / --cap-drop (Apple Container 0.12+):
#   Container 0.12 promoted Linux capability flags to documented public flags.
#   We deliberately keep them in this blocklist and do NOT expose them as tool
#   parameters. Capability selection is workload-specific configuration that
#   meaningfully weakens process isolation; we treat it as advanced use that
#   should be applied via the `container` CLI directly when truly needed.
#   See README "Security model" and docs/TDD.md.
_DANGEROUS_FLAGS: frozenset[str] = frozenset(
    {
        "--privileged",
        "--cap-add",
        "--cap-drop",
        "--security-opt",
        "--device",
        "--pid",
        "--ipc",
        "--userns",
        "--cgroupns",
        "--no-new-privileges",
    }
)
```

- [ ] **Step 2: Run the security regression tests to confirm capabilities are still blocked**

Run: `uv run pytest tests/test_tools.py::test_run_container_args_override_blocked_cap_add tests/test_tools.py::test_run_container_args_override_blocked_privileged -v`
Expected: Both PASS (behavior unchanged — this is a comment-only edit).

- [ ] **Step 3: Add an explicit `--cap-drop` regression test**

There's an existing test for `--cap-add` but not `--cap-drop`. Add one to prevent silent regressions if someone removes a flag from the blocklist later.

Edit `tests/test_tools.py`. Find `test_run_container_args_override_blocked_cap_add` (around line 991). Add immediately after it:

```python
def test_run_container_args_override_blocked_cap_drop(mocker):
    result = run_container("debian", args_override=["--cap-drop", "ALL"])
    assert result["status"] == "error"
    assert "--cap-drop" in result["message"]
```

- [ ] **Step 4: Run the new test**

Run: `uv run pytest tests/test_tools.py::test_run_container_args_override_blocked_cap_drop -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/apple_container_mcp/tools/__init__.py tests/test_tools.py
git commit -m "feat(security): document capabilities policy and add cap-drop regression test

Container 0.12 promotes --cap-add/--cap-drop to documented public flags.
We deliberately keep them blocked from args_override and do not expose
them as tool parameters. A code comment documents the policy and an
explicit regression test guards --cap-drop alongside the existing
--cap-add test."
```

---

## Task 5: Expand `FORMAT_JSON_COMMANDS` per audit results

Read the audit document from Task 1 and apply the recommended additions/removals.

**Files:**
- Modify: `src/apple_container_mcp/cli_wrapper.py:61-67`
- Modify: `tests/test_cli_wrapper.py` (add per-addition assertion)

- [ ] **Step 1: Read the audit's "FORMAT_JSON_COMMANDS additions" line**

Open `docs/superpowers/plans/2026-04-28-cli-audit-results.md` and read the "Summary: actionable inputs" section. Note the exact list of tuples to add and whether to keep or remove the `("builder", "ls")` hedge comment.

- [ ] **Step 2: Write failing tests for each addition**

Edit `tests/test_cli_wrapper.py`. Append the following test. **Edit the parametrize list to contain exactly one entry per allowlist addition the audit recommended in its "Summary: actionable inputs" line.** For example, if the audit's summary says additions are `("system", "version")` and `("system", "status")`, your parametrize list MUST be:

```python
@pytest.mark.parametrize("subcmd", [
    ["system", "version"],
    ["system", "status"],
])
```

Do not include any entry the audit did not recommend, and do not omit any entry the audit did recommend. Then add the test using your final list:

```python
import pytest


@pytest.mark.parametrize("subcmd", [
    ["system", "version"],
    # ... one entry per audit-confirmed addition; see instructions above
])
def test_run_container_cmd_new_allowlist_entries_get_json_format(mocker, subcmd):
    """Verify each newly allowlisted command receives --format json."""
    mock_run = mocker.patch("subprocess.run")
    mock_result = mocker.Mock()
    mock_result.stdout = "{}"
    mock_result.returncode = 0
    mock_run.return_value = mock_result

    _run_container_cmd(subcmd)

    called_cmd = mock_run.call_args[0][0]
    assert "--format" in called_cmd, f"--format missing for {subcmd}"
    assert "json" in called_cmd, f"json missing for {subcmd}"
```

If `pytest` isn't already imported at the top of the file, add `import pytest` at the top.

**Adapt the parametrize list to match the audit results exactly — do NOT include entries the audit said are unsupported.**

- [ ] **Step 3: Run the new test to verify it fails**

Run: `uv run pytest tests/test_cli_wrapper.py::test_run_container_cmd_new_allowlist_entries_get_json_format -v`
Expected: FAIL — the new tuples aren't in `FORMAT_JSON_COMMANDS` yet.

- [ ] **Step 4: Update `FORMAT_JSON_COMMANDS`**

Edit `src/apple_container_mcp/cli_wrapper.py` lines 61-67. The existing block:

```python
    FORMAT_JSON_COMMANDS = {
        ("ls",),  # container ls
        ("image", "ls"),  # container image ls
        ("network", "ls"),  # container network ls
        ("volume", "ls"),  # container volume ls
        ("builder", "ls"),  # container builder ls (if supported)
    }
```

Apply per the audit results. As an example, if the audit said to add `("system", "version")` and to remove the hedge comment on `("builder", "ls")` (because it definitively works), the result is:

```python
    FORMAT_JSON_COMMANDS = {
        ("ls",),  # container ls
        ("image", "ls"),  # container image ls
        ("network", "ls"),  # container network ls
        ("volume", "ls"),  # container volume ls
        ("builder", "ls"),  # container builder ls
        ("system", "version"),  # container system version (added in 0.12)
        # Add other entries verified in the 0.12 CLI audit
    }
```

**Use the audit's exact recommendations.** If the audit said `("builder", "ls")` does NOT work and should be removed instead, remove it.

- [ ] **Step 5: Run the new test to verify it passes**

Run: `uv run pytest tests/test_cli_wrapper.py -v`
Expected: All cli_wrapper tests pass, including the new parametrized test.

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest -q`
Expected: All tests pass.

- [ ] **Step 7: Commit**

```bash
git add src/apple_container_mcp/cli_wrapper.py tests/test_cli_wrapper.py
git commit -m "feat(cli_wrapper): expand FORMAT_JSON_COMMANDS for Apple Container 0.12

Audit (see docs/superpowers/plans/2026-04-28-cli-audit-results.md)
confirmed which 0.12 subcommands cleanly support --format json.
Expanded the allowlist accordingly and resolved the (builder, ls)
'if supported' hedge."
```

---

## Task 6: Implement `system_version` tool

Adds the new tool wrapping `container system version`.

**Files:**
- Modify: `src/apple_container_mcp/tools/system.py`
- Modify: `src/apple_container_mcp/tools/__init__.py:76-82` (re-export)
- Modify: `tests/test_tools.py:1-58` (import) and append new tests

- [ ] **Step 1: Write failing tests for `system_version`**

Append to `tests/test_tools.py` in the "System tools" section (after `test_stop_system_error`, around line 153). Add:

```python
def test_system_version_ok(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = {
        "cliVersion": "0.12.0",
        "builderVersion": "0.12.0",
        "kernelVersion": "kata-3.28.0",
    }
    result = system_version()
    assert result["status"] == "ok"
    assert result["version"]["cliVersion"] == "0.12.0"
    mock.assert_called_once_with(["system", "version"])


def test_system_version_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("failed", 1, "unknown subcommand")
    result = system_version()
    assert result["status"] == "error"
    assert "Failed to retrieve" in result["message"]
```

The keys in the success mock (`cliVersion`, `builderVersion`, `kernelVersion`) are illustrative — the real shape is whatever the CLI emits. The wrapper just round-trips the parsed JSON, so the test only needs to assert that the dict is passed through under the `version` key.

Also update the `from apple_container_mcp.tools import (...)` import block at the top of the file (lines 3-58). Find the `# system` group:

```python
    # system
    check_apiserver_status,
    start_system,
    stop_system,
    system_status,
```

and change it to:

```python
    # system
    check_apiserver_status,
    start_system,
    stop_system,
    system_status,
    system_version,
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `uv run pytest tests/test_tools.py::test_system_version_ok tests/test_tools.py::test_system_version_error -v`
Expected: FAIL — `ImportError: cannot import name 'system_version'` (or similar).

- [ ] **Step 3: Implement the tool**

Edit `src/apple_container_mcp/tools/system.py`. Append at the end of the file (after `system_status`, line 80):

```python


@mcp.tool()
def system_version() -> Dict[str, Any]:
    """
    Return version info for the Apple Container CLI, builder, kernel, and
    containerization library.

    Requires Apple Container 0.12+ (the `system version` subcommand was
    introduced in 0.12). Useful for diagnostics and for clients that need
    to confirm the toolchain version they are talking to.

    Returns:
        On success: {"status": "ok", "version": <parsed JSON dict>}
        On error:   {"status": "error", "message": str, "details": str}
    """
    try:
        result = _run_container_cmd(["system", "version"])
        return {"status": "ok", "version": result}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to retrieve system version", "details": str(e)}
```

- [ ] **Step 4: Re-export from `tools/__init__.py`**

Edit `src/apple_container_mcp/tools/__init__.py`. Find the `from .system import (...)` block (lines 76-82):

```python
from .system import (  # noqa: E402, F401
    get_system_status_resource,
    check_apiserver_status,
    start_system,
    stop_system,
    system_status,
)
```

Change it to:

```python
from .system import (  # noqa: E402, F401
    get_system_status_resource,
    check_apiserver_status,
    start_system,
    stop_system,
    system_status,
    system_version,
)
```

- [ ] **Step 5: Run the new tests to verify they pass**

Run: `uv run pytest tests/test_tools.py::test_system_version_ok tests/test_tools.py::test_system_version_error -v`
Expected: PASS.

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest -q`
Expected: All tests pass.

- [ ] **Step 7: Commit**

```bash
git add src/apple_container_mcp/tools/system.py src/apple_container_mcp/tools/__init__.py tests/test_tools.py
git commit -m "feat(system): add system_version tool

Wraps \`container system version\` (added in Apple Container 0.12) to
return CLI/builder/kernel/containerization versions as structured JSON.
Auto-formatted via the FORMAT_JSON_COMMANDS allowlist."
```

---

## Task 7: Add `journal` parameter to `create_volume`

Adds the new `--journal` flag (per audit) as an optional boolean parameter on `create_volume`.

**Files:**
- Modify: `src/apple_container_mcp/tools/volumes.py:8-19`
- Modify: `tests/test_tools.py` (new tests near existing `test_create_volume*` tests)

- [ ] **Step 1: Confirm the exact flag spelling from the audit**

Open `docs/superpowers/plans/2026-04-28-cli-audit-results.md`, section C ("volume create --journal"). Note the EXACT flag spelling. The implementation below assumes `--journal` (a boolean flag with no value). If the audit shows a different form (e.g. `--journal=true`), adapt all code samples in this task accordingly.

- [ ] **Step 2: Write failing tests**

Edit `tests/test_tools.py`. Find the `# Volume tools` section and the existing `test_create_volume*` tests (around lines 832-851). After `test_create_volume_error` (around line 851), append:

```python
def test_create_volume_with_journal(mocker):
    mock = _mock_cmd(mocker)
    result = create_volume("journal-vol", journal=True)
    assert result["status"] == "ok"
    called_args = mock.call_args[0][0]
    assert "--journal" in called_args
    # name must still appear last
    assert called_args[-1] == "journal-vol"


def test_create_volume_with_journal_and_size(mocker):
    mock = _mock_cmd(mocker)
    result = create_volume("journal-vol", size="20G", journal=True)
    assert result["status"] == "ok"
    called_args = mock.call_args[0][0]
    assert "--journal" in called_args
    assert "-s" in called_args
    assert "20G" in called_args
    assert called_args[-1] == "journal-vol"


def test_create_volume_journal_false_omits_flag(mocker):
    """Default (journal=False) must NOT add --journal to the args."""
    mock = _mock_cmd(mocker)
    result = create_volume("plain-vol", journal=False)
    assert result["status"] == "ok"
    called_args = mock.call_args[0][0]
    assert "--journal" not in called_args
```

- [ ] **Step 3: Run the new tests to verify they fail**

Run: `uv run pytest tests/test_tools.py::test_create_volume_with_journal tests/test_tools.py::test_create_volume_with_journal_and_size tests/test_tools.py::test_create_volume_journal_false_omits_flag -v`
Expected: FAIL — `journal` is not a valid keyword argument.

- [ ] **Step 4: Update `create_volume`**

Edit `src/apple_container_mcp/tools/volumes.py` lines 8-19. Replace:

```python
@mcp.tool()
def create_volume(name: str, size: Optional[str] = None) -> Dict[str, Any]:
    """Creates a new named volume with an optional size (e.g., '10G')."""
    args = ["volume", "create"]
    if size:
        args.extend(["-s", size])
    args.append(name)
    try:
        _run_container_cmd(args)
        return {"status": "ok", "message": f"Successfully created volume '{name}'."}
    except ContainerCLIError as e:
        return {"status": "error", "message": f"Failed to create volume '{name}'.", "details": e.stderr}
```

with:

```python
@mcp.tool()
def create_volume(name: str, size: Optional[str] = None, journal: bool = False) -> Dict[str, Any]:
    """
    Creates a new named volume.

    Args:
        name: Volume name.
        size: Optional volume size (e.g. '10G').
        journal: If True, enable filesystem journaling on the volume.
            Recommended for write-heavy or crash-sensitive workloads
            (e.g. databases) at a small write-amplification cost.
            Requires Apple Container 0.12+ (added in 0.12).
    """
    args = ["volume", "create"]
    if size:
        args.extend(["-s", size])
    if journal:
        args.append("--journal")
    args.append(name)
    try:
        _run_container_cmd(args)
        return {"status": "ok", "message": f"Successfully created volume '{name}'."}
    except ContainerCLIError as e:
        return {"status": "error", "message": f"Failed to create volume '{name}'.", "details": e.stderr}
```

**If the audit recorded a different flag spelling** (e.g. `--journal=true`), use that exact form on the `args.append(...)` line.

- [ ] **Step 5: Run the new tests to verify they pass**

Run: `uv run pytest tests/test_tools.py -k "create_volume" -v`
Expected: All `create_volume*` tests pass — both new and existing.

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest -q`
Expected: All tests pass.

- [ ] **Step 7: Commit**

```bash
git add src/apple_container_mcp/tools/volumes.py tests/test_tools.py
git commit -m "feat(volumes): add journal parameter to create_volume

Apple Container 0.12 added the --journal flag to \`container volume
create\`. Expose it as an optional bool parameter; default False
preserves current behavior. Useful for write-heavy or crash-sensitive
workloads."
```

---

## Task 8: Implement verified gap-fill tools

For each tool the audit confirmed exists in 0.12, add it as a separate sub-task. The template below covers the simple lifecycle commands (`restart`, `pause`, `unpause`, `rename`). For `stats`, `events`, `cp`, and `history` see the variations at the end.

**Conditional execution:** Skip any sub-task whose corresponding "include" cell in the audit (Section D) is "no". Implement only the ones the audit confirmed.

**Files (template — paths same for all gap-fill tools):**
- Modify: `src/apple_container_mcp/tools/containers.py` (append new tool)
- Modify: `src/apple_container_mcp/tools/__init__.py` (re-export)
- Modify: `tests/test_tools.py` (import + new tests)

### Task 8a: `restart_container` — IF audit confirmed

- [ ] **Step 1: Write failing tests**

Edit `tests/test_tools.py`. In the "Container lifecycle" section (after `test_stop_container_force` around line 308), append:

```python
def test_restart_container(mocker):
    mock = _mock_cmd(mocker)
    result = restart_container("12345")
    assert result["status"] == "ok"
    assert "12345" in result["message"]
    mock.assert_called_once_with(["restart", "12345"])


def test_restart_container_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("failed", 1, "no such container")
    result = restart_container("bad-id")
    assert result["status"] == "error"


def test_restart_container_empty_id(mocker):
    result = restart_container("")
    assert result["status"] == "error"
    assert "container_id" in result["message"]
```

Also update the `from apple_container_mcp.tools import (...)` import block at the top — find the `# container lifecycle` group and add `restart_container,` to the list.

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `uv run pytest tests/test_tools.py::test_restart_container tests/test_tools.py::test_restart_container_error tests/test_tools.py::test_restart_container_empty_id -v`
Expected: FAIL — `ImportError`.

- [ ] **Step 3: Implement the tool**

Edit `src/apple_container_mcp/tools/containers.py`. Append at the end of the file (after `prune_containers`):

```python


@mcp.tool()
def restart_container(container_id: str) -> Dict[str, Any]:
    """Restart a container (stop then start). Requires Apple Container 0.12+."""
    if not container_id:
        return {"status": "error", "message": "container_id must be a non-empty string."}
    try:
        _run_container_cmd(["restart", container_id])
        return {"status": "ok", "message": f"Successfully restarted container {container_id}."}
    except ContainerCLIError as e:
        return {
            "status": "error",
            "message": f"Failed to restart container {container_id}.",
            "details": e.stderr,
        }
```

- [ ] **Step 4: Re-export from `tools/__init__.py`**

Edit `src/apple_container_mcp/tools/__init__.py`. Find the `from .containers import (...)` block (lines 83-94) and add `restart_container,` to it:

```python
from .containers import (  # noqa: E402, F401
    run_container,
    list_containers,
    stop_container,
    start_container,
    remove_container,
    restart_container,
    export_container,
    get_logs,
    inspect_container,
    exec_in_container,
    prune_containers,
)
```

- [ ] **Step 5: Run the new tests to verify they pass**

Run: `uv run pytest tests/test_tools.py -k restart_container -v`
Expected: PASS.

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest -q`
Expected: All tests pass.

- [ ] **Step 7: Commit**

```bash
git add src/apple_container_mcp/tools/containers.py src/apple_container_mcp/tools/__init__.py tests/test_tools.py
git commit -m "feat(containers): add restart_container tool

Wraps \`container restart <id>\` (verified available in Apple Container 0.12).
Returns standard {status, message, details} shape and validates non-empty
container_id."
```

### Task 8b: `pause_container` — IF audit confirmed

Identical structure to 8a. Replace every occurrence of `restart` with `pause` in code, and `restarted` with `paused` in messages. Tests:

```python
def test_pause_container(mocker):
    mock = _mock_cmd(mocker)
    result = pause_container("12345")
    assert result["status"] == "ok"
    mock.assert_called_once_with(["pause", "12345"])


def test_pause_container_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("failed", 1, "no such container")
    result = pause_container("bad-id")
    assert result["status"] == "error"


def test_pause_container_empty_id(mocker):
    result = pause_container("")
    assert result["status"] == "error"
```

Implementation:

```python
@mcp.tool()
def pause_container(container_id: str) -> Dict[str, Any]:
    """Pause all processes in a running container. Requires Apple Container 0.12+."""
    if not container_id:
        return {"status": "error", "message": "container_id must be a non-empty string."}
    try:
        _run_container_cmd(["pause", container_id])
        return {"status": "ok", "message": f"Successfully paused container {container_id}."}
    except ContainerCLIError as e:
        return {"status": "error", "message": f"Failed to pause container {container_id}.", "details": e.stderr}
```

Re-export and commit message follow the same pattern as 8a (substitute `pause` for `restart`).

- [ ] **Steps 1-7:** Apply the same TDD cycle as 8a with the substitutions above.

### Task 8c: `unpause_container` — IF audit confirmed

Identical structure to 8b. Substitute `unpause` for `pause` everywhere. Implementation:

```python
@mcp.tool()
def unpause_container(container_id: str) -> Dict[str, Any]:
    """Resume all processes in a paused container. Requires Apple Container 0.12+."""
    if not container_id:
        return {"status": "error", "message": "container_id must be a non-empty string."}
    try:
        _run_container_cmd(["unpause", container_id])
        return {"status": "ok", "message": f"Successfully unpaused container {container_id}."}
    except ContainerCLIError as e:
        return {"status": "error", "message": f"Failed to unpause container {container_id}.", "details": e.stderr}
```

Tests follow the same pattern as 8b. Apply the same TDD cycle.

### Task 8d: `rename_container` — IF audit confirmed

Two-arg version of the lifecycle pattern.

- [ ] **Step 1: Write failing tests**

Append to the Container lifecycle section of `tests/test_tools.py`:

```python
def test_rename_container(mocker):
    mock = _mock_cmd(mocker)
    result = rename_container("12345", "new-name")
    assert result["status"] == "ok"
    assert "new-name" in result["message"]
    mock.assert_called_once_with(["rename", "12345", "new-name"])


def test_rename_container_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("failed", 1, "name already in use")
    result = rename_container("12345", "taken-name")
    assert result["status"] == "error"


def test_rename_container_empty_id(mocker):
    result = rename_container("", "new-name")
    assert result["status"] == "error"


def test_rename_container_empty_new_name(mocker):
    result = rename_container("12345", "")
    assert result["status"] == "error"
    assert "new_name" in result["message"]
```

Add `rename_container,` to the test file's import block.

- [ ] **Step 2: Run new tests** — Expected: FAIL (ImportError).

- [ ] **Step 3: Implement**

Append to `containers.py`:

```python


@mcp.tool()
def rename_container(container_id: str, new_name: str) -> Dict[str, Any]:
    """Rename a container. Requires Apple Container 0.12+."""
    if not container_id:
        return {"status": "error", "message": "container_id must be a non-empty string."}
    if not new_name:
        return {"status": "error", "message": "new_name must be a non-empty string."}
    try:
        _run_container_cmd(["rename", container_id, new_name])
        return {
            "status": "ok",
            "message": f"Successfully renamed container {container_id} to '{new_name}'.",
        }
    except ContainerCLIError as e:
        return {
            "status": "error",
            "message": f"Failed to rename container {container_id} to '{new_name}'.",
            "details": e.stderr,
        }
```

Re-export from `tools/__init__.py` (add `rename_container,` to the containers re-export block).

- [ ] **Steps 4-7:** Run tests, run full suite, commit (commit message: `feat(containers): add rename_container tool`).

### Task 8e: `stats_container` — ONLY IF audit confirmed AND audit confirmed a non-streaming form

Skip if the audit shows `stats` doesn't exist or only supports streaming. The implementation needs the exact non-streaming flag (e.g. `--no-stream`) from the audit.

Template (assuming audit shows `--no-stream`):

```python
@mcp.tool()
def stats_container(container_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Get a one-shot resource-usage snapshot for a container (or all containers
    if container_id is omitted). Requires Apple Container 0.12+.

    This MCP tool always uses the non-streaming form to fit the request/response
    model. For continuous streaming, use the `container stats` CLI directly.
    """
    args = ["stats", "--no-stream"]
    if container_id:
        args.append(container_id)
    try:
        result = _run_container_cmd(args)
        return {"status": "ok", "stats": result}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to retrieve container stats", "details": e.stderr}
```

Tests:

```python
def test_stats_container_all(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = [{"id": "abc", "cpu": "0.5%"}]
    result = stats_container()
    assert result["status"] == "ok"
    called_args = mock.call_args[0][0]
    assert "stats" in called_args
    assert "--no-stream" in called_args


def test_stats_container_specific(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = {"id": "abc", "cpu": "0.5%"}
    result = stats_container("abc")
    assert result["status"] == "ok"
    called_args = mock.call_args[0][0]
    assert "abc" in called_args


def test_stats_container_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("failed", 1, "no such container")
    result = stats_container("bad-id")
    assert result["status"] == "error"
```

Apply the same TDD cycle and commit.

### Task 8f: `events` — ONLY IF audit confirmed AND audit confirmed bounded `--since`/`--until` form

Skip if events is streaming-only.

Template (assuming `--since` / `--until`):

```python
@mcp.tool()
def events(since: Optional[str] = None, until: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieve historical container events between two timestamps. Requires
    Apple Container 0.12+.

    Args:
        since: Lower bound (e.g. ISO timestamp like "2026-04-28T00:00:00Z").
        until: Upper bound. Both bounds are required to keep this a bounded
            query — pass timestamps only minutes apart for fast results.

    This MCP tool requires both `since` and `until` to keep the call bounded;
    streaming use must go through the CLI directly.
    """
    if not since or not until:
        return {
            "status": "error",
            "message": "Both `since` and `until` are required to keep the query bounded.",
        }
    try:
        result = _run_container_cmd(["events", "--since", since, "--until", until])
        return {"status": "ok", "events": result}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to retrieve events", "details": e.stderr}
```

Tests:

```python
def test_events_requires_bounds(mocker):
    result = events()
    assert result["status"] == "error"
    assert "since" in result["message"]
    assert "until" in result["message"]


def test_events_with_bounds(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = [{"type": "create", "id": "abc"}]
    result = events(since="2026-04-28T00:00:00Z", until="2026-04-28T00:05:00Z")
    assert result["status"] == "ok"
    called_args = mock.call_args[0][0]
    assert "events" in called_args
    assert "--since" in called_args
    assert "--until" in called_args


def test_events_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("failed", 1, "invalid timestamp")
    result = events(since="invalid", until="invalid")
    assert result["status"] == "error"
```

Apply the same TDD cycle and commit.

### Task 8g: `container_history` — IF audit confirmed

Image-history command (if it exists). Single-arg pattern. Note this likely lives under `images.py` rather than `containers.py` — it operates on images. Place accordingly. Test pattern follows `test_inspect_image*`.

```python
@mcp.tool()
def container_history(image: str) -> Dict[str, Any]:
    """Show the layer history for an image. Requires Apple Container 0.12+."""
    if not image:
        return {"status": "error", "message": "image must be a non-empty string."}
    try:
        result = _run_container_cmd(["image", "history", image])
        return {"status": "ok", "history": result}
    except ContainerCLIError as e:
        return {"status": "error", "message": f"Failed to retrieve history for '{image}'.", "details": e.stderr}
```

(Adjust the CLI invocation if the audit shows it's `container history` rather than `container image history`.)

If implemented, place in `tools/images.py` and add to the `from .images import (...)` block in `tools/__init__.py`.

### Task 8h: `cp` (copy files in/out) — IF audit confirmed

The `cp` semantics involve host filesystem paths, which raises the same path-traversal concerns as `env_file` and `build_image`'s `context_path`. **Defer this tool to a separate spec rather than rushing it into this update.** Skip Task 8h for this plan and note in the audit document that `cp` was deliberately deferred.

If you choose to include it anyway, you MUST replicate the home-dir realpath check from `containers.py:58-65` (the `env_file` validator) for the host-side path. Do not omit it.

---

## Task 9: Update `troubleshoot_container` prompt to mention new tools

If gap-fill tools (`restart_container`, `inspect_container`, `system_version`) make sense to mention in the troubleshooting prompt, update it. Otherwise skip.

**Files:**
- Modify: `src/apple_container_mcp/tools/prompts.py`

- [ ] **Step 1: Read the current prompt and decide if updates add value**

Run: `cat src/apple_container_mcp/tools/prompts.py`
Decide: would mentioning `system_version` (for diagnostics) or `restart_container` (for the recovery step) genuinely help an LLM following the prompt? If yes, proceed. If the prompt is already complete, skip this task.

- [ ] **Step 2: If updating, write a smoke test first**

In `tests/test_tools.py`, find `test_prompt_troubleshoot_container` (around line 1158). If you've decided to add `restart_container` to the prompt, update the test:

```python
def test_prompt_troubleshoot_container():
    result = troubleshoot_container("my-container")
    assert "my-container" in result
    assert "inspect_container" in result
    assert "restart_container" in result  # added in 0.12 support update
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `uv run pytest tests/test_tools.py::test_prompt_troubleshoot_container -v`
Expected: FAIL.

- [ ] **Step 4: Update the prompt body**

Edit `src/apple_container_mcp/tools/prompts.py` and add a step mentioning `restart_container` (or `system_version`, or both) in the natural-language workflow body.

- [ ] **Step 5: Run the test to verify it passes**

Run: `uv run pytest tests/test_tools.py::test_prompt_troubleshoot_container -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/apple_container_mcp/tools/prompts.py tests/test_tools.py
git commit -m "docs(prompts): mention 0.12 tools in troubleshoot_container workflow"
```

---

## Task 10: Update README.md

Bump version reference, add Security Model subsection, list new tools.

**Files:**
- Modify: `README.md` (lines 18, 271-282)

- [ ] **Step 1: Update the prerequisites version reference**

Edit `README.md` line 18. Change:

```markdown
3. **Apple Container CLI**: Provided by Apple's virtualization framework. Tested with **v0.11.0**. Install via Homebrew, then start the system service:
```

to:

```markdown
3. **Apple Container CLI**: Provided by Apple's virtualization framework. **Requires v0.12.0 or later.** Install via Homebrew, then start the system service:
```

- [ ] **Step 2: Add Security Model subsection**

Edit `README.md`. After the "## 🛠 Active Capabilities" section (which currently ends around line 292), append:

```markdown

---

## 🔒 Security Model

This server applies several deliberate restrictions to keep LLM-driven container operations safe:

- **Path validation:** `build_image`'s `context_path` and `run_container`'s `env_file` are restricted to paths inside your home directory. The check uses `os.path.realpath` and a trailing-separator suffix test to prevent prefix-match bypasses (e.g. `/Users/joe` vs `/Users/joey`).
- **Argument blocklist:** `run_container`'s `args_override` parameter rejects flags that escalate privilege or weaken isolation: `--privileged`, `--cap-add`, `--cap-drop`, `--security-opt`, `--device`, `--pid`, `--ipc`, `--userns`, `--cgroupns`, `--no-new-privileges`.
- **Linux capabilities:** Apple Container 0.12 added `--cap-add` / `--cap-drop` as documented public flags. **This MCP deliberately does NOT expose them as tool parameters.** Capability selection meaningfully weakens process isolation; if you need it, invoke `container run` directly. We may revisit this in a future release with an allowlist mechanism.
- **No shell injection:** `subprocess.run` is always called with an argument list, never with `shell=True`.
- **Credential handling:** `registry_login` passes the password via `stdin` (`--password-stdin`) so it never appears in process arguments.
```

- [ ] **Step 3: Update the Tools Exposed list**

Edit `README.md` lines 275-282. Update the **System** and **Containers** lines (and any other group whose tools changed per the audit). Example showing all conceivable additions — keep only the tools the audit said to add:

```markdown
- **System**: `check_apiserver_status`, `start_system`, `stop_system`, `system_status`, `system_version`
- **Containers**: `run_container` (supports `--init-image`, rosetta, platform, labels, and more), `list_containers`, `start_container`, `stop_container`, `restart_container`, `pause_container`, `unpause_container`, `rename_container`, `remove_container`, `export_container`, `inspect_container`, `exec_in_container`, `get_logs`, `prune_containers`, `stats_container`, `events`
- **Images**: `list_images`, `pull_image`, `build_image`, `check_build_status`, `list_builds`, `tag_image`, `push_image`, `inspect_image`, `remove_image`, `prune_images`, `container_history`
- **Networks**: `create_network`, `remove_network`, `list_networks`, `inspect_network`, `prune_networks`
- **Volumes**: `create_volume` (supports `journal`), `remove_volume`, `list_volumes`, `inspect_volume`, `prune_volumes`
- **Registry**: `registry_login`, `registry_logout`
- **Builder**: `builder_start`, `builder_stop`, `builder_status`
```

**Trim this list to match what was actually implemented in Tasks 6, 7, and 8.**

- [ ] **Step 4: Render-check the README**

Run: `uv run python -c "import pathlib; content = pathlib.Path('README.md').read_text(); assert 'v0.12.0' in content; assert 'Security Model' in content; assert 'system_version' in content; print('README updated correctly')"`
Expected: prints `README updated correctly`.

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: update README for Apple Container 0.12 support

- Bump minimum CLI version to 0.12.0
- Add Security Model subsection documenting path validation,
  args_override blocklist, and the deliberate non-exposure of
  --cap-add/--cap-drop
- Update tool inventory with new 0.12 tools"
```

---

## Task 11: Update docs/PRD.md

**Files:**
- Modify: `docs/PRD.md`

- [ ] **Step 1: Add new tools to functional requirements**

Edit `docs/PRD.md`. Update the bullet lists in FR1, FR2, FR3, and FR4 to mention each tool that was actually added in Tasks 6, 7, and 8.

For example, in FR1 (line 35-37), add:
```markdown
* Retrieve detailed version information (CLI, builder, kernel, containerization).
```

In FR2 (around lines 39-47), add bullets for the gap-fill lifecycle tools that were implemented (e.g. restart, pause, unpause, rename), only those that were actually added.

In FR3 (around lines 49-57), add a bullet for `container_history` if it was implemented.

In FR4 (around lines 59-62), update the volumes bullet to mention `journal`:
```markdown
* **Volumes:** Create (with optional size and journaling), list, inspect, remove, and prune volumes.
```

If `stats_container` and/or `events` were added, add them under FR5 (Inspection & Logs).

**Only add bullets for tools that were actually implemented. Do not promise functionality that doesn't exist.**

- [ ] **Step 2: Commit**

```bash
git add docs/PRD.md
git commit -m "docs(prd): document new tools added for Apple Container 0.12 support"
```

---

## Task 12: Update docs/TDD.md

**Files:**
- Modify: `docs/TDD.md`

- [ ] **Step 1: Update Tool Mapping table**

Edit `docs/TDD.md`. Find the Tool Mapping Strategy table (lines 81-97).

(a) Update the `export_container` row (line 86) — remove the "in 0.11.0" qualifier:

```markdown
| export_container | container export -o [file] [id] | Export container filesystem as an OCI-layout tar archive. |
```

(b) Add new rows for each tool implemented in Tasks 6, 7, 8 (only the ones actually added):

```markdown
| system_version | container system version | Returns CLI/builder/kernel/containerization versions (Apple Container 0.12+). |
| create_volume | container volume create | Supports `-s` (size) and `--journal` (0.12+). |
| restart_container | container restart [id] | Restart a container. (0.12+) |
| pause_container | container pause [id] | Pause processes in a container. (0.12+) |
| unpause_container | container unpause [id] | Resume processes in a paused container. (0.12+) |
| rename_container | container rename [id] [name] | Rename a container. (0.12+) |
| stats_container | container stats --no-stream [id?] | Snapshot resource usage (non-streaming). (0.12+) |
| events | container events --since X --until Y | Bounded historical event query. (0.12+) |
| container_history | container image history [image] | Show image layer history. (0.12+) |
```

**Trim to what was actually implemented.**

- [ ] **Step 2: Update the embedded `_run_container_cmd` example**

Edit `docs/TDD.md`. Find the `FORMAT_JSON_COMMANDS = {...}` snippet (lines 41-44):

```python
    FORMAT_JSON_COMMANDS = {
        ("ls",), ("image", "ls"), ("network", "ls"),
        ("volume", "ls"), ("builder", "ls"),
    }
```

Replace it with the actual final set after Task 5 (read from `cli_wrapper.py`):

```python
    FORMAT_JSON_COMMANDS = {
        ("ls",), ("image", "ls"), ("network", "ls"),
        ("volume", "ls"), ("builder", "ls"),
        ("system", "version"),  # 0.12+
        # ... whatever else Task 5 added
    }
```

- [ ] **Step 3: Update the Security Model section**

Edit `docs/TDD.md` around line 119-124 (Security Model section). Update the "Argument Sanitization" bullet to mention the capabilities-policy decision:

```markdown
* **Argument Sanitization:** `subprocess.run` is called with a list of arguments (never `shell=True`) to prevent shell injection. `run_container`'s `args_override` parameter is validated against a blocklist of dangerous flags (`--privileged`, `--cap-add`, `--cap-drop`, `--security-opt`, `--device`, `--pid`, `--ipc`, `--userns`, `--cgroupns`, `--no-new-privileges`) to prevent privilege escalation via LLM prompt injection.
* **Capabilities (0.12+):** Apple Container 0.12 promoted `--cap-add` / `--cap-drop` to documented public flags. This MCP deliberately keeps them in the `args_override` blocklist and does NOT expose them as tool parameters. Capability selection is workload-specific, meaningfully weakens isolation, and is left to direct CLI use.
```

- [ ] **Step 4: Commit**

```bash
git add docs/TDD.md
git commit -m "docs(tdd): document 0.12 tool additions, JSON allowlist, and capabilities policy"
```

---

## Task 13: Create CHANGELOG.md

**Files:**
- Create: `CHANGELOG.md`

- [ ] **Step 1: Write the changelog file**

Create `CHANGELOG.md` with the following content. **Replace the angle-bracketed lists with the actual tools added in Tasks 5-8 — read your previous commit log if needed (`git log --oneline`).**

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-04-28

Apple Container 0.12 support.

### Added

- `system_version` tool wrapping `container system version` (Apple Container 0.12+).
- `journal: bool` parameter on `create_volume` for filesystem journaling (0.12+).
- <List the gap-fill tools actually added in Task 8 — e.g. restart_container, pause_container, unpause_container, rename_container, stats_container, events, container_history>
- Expanded JSON output allowlist in `cli_wrapper.FORMAT_JSON_COMMANDS` for <list the audit-confirmed additions, e.g. `system version`>.
- Regression test for `--cap-drop` blocked from `args_override` (alongside the existing `--cap-add` test).

### Changed

- Minimum required Apple Container CLI version is now **0.12.0**.
- `export_container` documentation no longer references version-specific behavior; the OCI-layout tar export is stable across 0.11+ and 0.12.
- Package version bumped from `0.1.0` to `0.2.0`.

### Security

- `--cap-add` and `--cap-drop` (promoted to documented public flags in Apple Container 0.12) are intentionally **not** exposed as tool parameters and remain blocked from `run_container(args_override=…)`. Capability selection meaningfully weakens process isolation; this MCP treats it as advanced configuration that should be applied via the CLI directly when truly needed. See the README's Security Model section.
```

- [ ] **Step 2: Verify the file exists and has expected content**

Run: `uv run python -c "import pathlib; c = pathlib.Path('CHANGELOG.md').read_text(); assert '[0.2.0]' in c; assert 'system_version' in c; assert '--cap-add' in c; print('CHANGELOG OK')"`
Expected: prints `CHANGELOG OK`.

- [ ] **Step 3: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: add CHANGELOG.md with [0.2.0] release notes"
```

---

## Task 14: Final verification

End-to-end checks before declaring the work complete.

**Files:**
- (no edits — verification only)

- [ ] **Step 1: Full test suite with coverage**

Run: `uv run pytest --cov=apple_container_mcp --cov-report=term-missing -q`
Expected: All tests pass. Coverage of new code (system_version, create_volume w/ journal, gap-fill tools) is ≥ 90% lines. Total coverage is at or above the pre-existing baseline.

If any new code is < 90% covered, add tests until it is, then re-run.

- [ ] **Step 2: Lint**

Run: `uv run ruff check src tests`
Expected: No errors.

If errors appear, fix them inline and re-run.

- [ ] **Step 3: Type check**

Run: `uv run mypy src`
Expected: No errors.

If errors appear (most likely on new tool signatures missing return-type annotations or `Optional` imports), fix them and re-run.

- [ ] **Step 4: Format check (if pre-commit configured)**

Run: `uv run ruff format --check src tests`
Expected: No formatting changes needed.

If reformatting is needed, run `uv run ruff format src tests` and commit the formatting changes:
```bash
git add -A
git commit -m "style: ruff format"
```

- [ ] **Step 5: Manual smoke test — `system_version`**

Requires `container 0.12` running.

Run:
```bash
container system start  # ensure daemon is up
uv run python -c "from apple_container_mcp.tools import system_version; import json; print(json.dumps(system_version(), indent=2))"
```
Expected: prints a JSON object with `"status": "ok"` and a `"version"` field containing the parsed version output.

- [ ] **Step 6: Manual smoke test — `create_volume(journal=True)`**

Run:
```bash
uv run python -c "from apple_container_mcp.tools import create_volume, remove_volume, inspect_volume; import json; print(json.dumps(create_volume('mcp-smoke-journal-vol', journal=True), indent=2)); print(json.dumps(inspect_volume('mcp-smoke-journal-vol'), indent=2))"
```
Expected: First call returns `{"status": "ok", ...}`. Inspect output shows the volume was created (verify the journaling option is reflected in the inspect output if surfaced there).

Then clean up:
```bash
uv run python -c "from apple_container_mcp.tools import remove_volume; import json; print(json.dumps(remove_volume('mcp-smoke-journal-vol'), indent=2))"
```

- [ ] **Step 7: Manual smoke test — one gap-fill tool**

Pick one gap-fill tool that was added (e.g. `restart_container`). Run a smoke test against an actual running container:
```bash
container run -d --name mcp-smoke-restart debian:latest sleep 60
uv run python -c "from apple_container_mcp.tools import restart_container; import json; print(json.dumps(restart_container('mcp-smoke-restart'), indent=2))"
container rm -f mcp-smoke-restart
```
Expected: JSON shows `"status": "ok"` and the container restarts successfully.

If multiple gap-fill tools were added, smoke-test at least one of each TYPE (lifecycle, info, mutation).

- [ ] **Step 8: Verify CHANGELOG and version are consistent**

Run: `uv run python -c "import tomllib, pathlib; pyp = tomllib.loads(pathlib.Path('pyproject.toml').read_text()); init = pathlib.Path('src/apple_container_mcp/__init__.py').read_text(); changelog = pathlib.Path('CHANGELOG.md').read_text(); v = pyp['project']['version']; assert v == '0.2.0', f'pyproject version = {v}'; assert '0.2.0' in init, 'init version missing'; assert '[0.2.0]' in changelog, 'changelog entry missing'; print('All version references consistent at 0.2.0')"`
Expected: prints `All version references consistent at 0.2.0`.

- [ ] **Step 9: Review the full commit log**

Run: `git log --oneline main..HEAD`  *(if you've been on a branch)*
or: `git log --oneline -20`  *(if working on main)*

Expected: Each task in this plan corresponds to one or more commits. No commits are missing. No tasks were silently skipped (other than ones the audit explicitly said to skip — those should be noted in the audit document, not silently dropped).

- [ ] **Step 10: Acceptance criteria check**

Walk through the spec's §10 Acceptance Criteria (`docs/superpowers/specs/2026-04-28-apple-container-0.12-support-design.md`) and confirm each item is satisfied. The criteria are:

1. All "0.11.0" references in code and docs are updated to "0.12.0". → Verify with: `uv run python -c "import pathlib; offenders = [str(p) for p in pathlib.Path('.').rglob('*') if p.is_file() and p.suffix in {'.py', '.md', '.toml'} and '.venv' not in str(p) and '.git' not in str(p) and '0.11.0' in p.read_text(errors='ignore')]; print('REMAINING 0.11.0 references:', offenders) if offenders else print('OK — no remaining 0.11.0 references')"`
2. `system_version`, `create_volume(journal=...)`, and all verified gap-fill tools are implemented with full test coverage and standardized return shapes. → Already verified by Steps 1, 5, 6, 7.
3. `FORMAT_JSON_COMMANDS` is expanded per §7 audit results. → Verified in Task 5.
4. `_DANGEROUS_FLAGS` carries the documenting comment about capabilities; README and TDD carry the user-facing version. → Verified in Tasks 4, 10, 12.
5. `CHANGELOG.md` exists with a `[0.2.0]` entry. → Verified in Step 8.
6. `pyproject.toml` and `src/apple_container_mcp/__init__.py` show `version = "0.2.0"`. → Verified in Step 8.
7. `pytest` passes; `pytest --cov` shows no regression. → Verified in Step 1.
8. `ruff` and `mypy` pass. → Verified in Steps 2, 3.
9. Manual smoke test against `container 0.12` succeeds. → Verified in Steps 5, 6, 7.

If any item is not satisfied, fix it before declaring complete.

- [ ] **Step 11: Commit any final fixes from Step 10**

If Step 10's grep found stray "0.11.0" references, fix and commit:

```bash
# Edit the offending files first
git add -A
git commit -m "docs: clean up remaining 0.11.0 version references"
```

---

## Self-Review Notes (from plan author)

**Spec coverage:** Every §6 file in the spec's change list is touched by an explicit task: README.md (10), docs/PRD.md (11), docs/TDD.md (12), CHANGELOG.md (13), pyproject.toml (2), `__init__.py` (2), `cli_wrapper.py` (5), `tools/system.py` (6), `tools/volumes.py` (7), `tools/containers.py` (3, 4, 8), `tools/__init__.py` (4, 6, 8), `tests/test_tools.py` (3, 4, 6, 7, 8), `tests/test_cli_wrapper.py` (5).

**Spec §7 (CLI verification gate):** Task 1 explicitly runs the audit and writes the results to a sibling document (`2026-04-28-cli-audit-results.md`) that Tasks 5-8 read. This is the mechanism for handling audit-driven decisions in a written-ahead plan.

**Conditional tasks:** Tasks 8a-8h are explicitly conditional on audit results. The plan tells the implementer to skip any sub-task whose audit row says "no". This is intentional and not a placeholder — the audit is a real preceding step, not a TBD.

**Type consistency:** All new function signatures use `Dict[str, Any]` returns and `Optional[str]`/`Optional[List[str]]` parameters matching the existing codebase patterns. The `_DANGEROUS_FLAGS` set type (`frozenset[str]`) is preserved.

**Naming consistency:** Verified across tasks — `restart_container` (not `container_restart`), `pause_container`, `unpause_container`, `rename_container`, `stats_container` (not `container_stats`) — all follow the existing `<verb>_container` pattern used by `start_container`, `stop_container`, `remove_container`, `inspect_container`, `exec_in_container`. The exception is `events` (matches the CLI subcommand verbatim — there's no `events_container` because the command is system-wide). `container_history` lives under `images.py` (it operates on images, not containers) and uses the `container_<noun>` form to avoid confusion with `inspect_container`-style names.

**No placeholders:** Every code block contains the actual content. The "fill in from audit" instructions in Tasks 5-8 reference a concrete file (`2026-04-28-cli-audit-results.md`) that Task 1 produces. Tasks 11 and 12 instruct the implementer to "trim to what was actually implemented" — the prior commit log is the source of truth, not a TBD.
