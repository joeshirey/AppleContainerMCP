# Apple Container 1.6.1 Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade AppleContainerMCP to fully support Apple Container 1.6.1 by adding `commit_container` and `clean_containers` MCP tools, enabling `d2c commit` translation, normalizing plugin-availability errors, bumping recommended CLI version to 1.6, and updating documentation.

**Architecture:** Add native container lifecycle subcommands in `apple_container_mcp.tools.containers`, re-exported via `apple_container_mcp.tools`. Migrate `commit` from unsupported commands to command translations in `d2c.registry`. Enhance `cli_wrapper.py` subprocess error handling to normalize CLI plugin unavailability strings when background services are stopped.

**Tech Stack:** Python 3.11+, FastMCP, pytest, pytest-mock, ruff, mypy, uv.

## Global Constraints

- Python compatibility: `>=3.11`
- Minimum Apple Container CLI major version: `1` (hard gate remains `1.0+`)
- Recommended Apple Container CLI version: `(1, 6)`
- Package version bump: `0.6.0` -> `0.7.0` in `pyproject.toml` and `src/apple_container_mcp/__init__.py`
- All commands and code must pass `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, and `uv run mypy src/ tests/`
- Adhere strictly to TDD: test first, verify failure, implement, verify pass, commit.

---

### Task 1: Enable `commit` Translation in `d2c`

**Files:**
- Modify: `src/d2c/unsupported.py:9-12`
- Modify: `src/d2c/registry.py:25-27`
- Test: `tests/d2c/test_unsupported.py`
- Test: `tests/d2c/test_registry.py`
- Test: `tests/d2c/test_cli.py`

**Interfaces:**
- Consumes: `d2c.registry.COMMANDS`, `d2c.registry.CommandTranslation`, `d2c.unsupported.UNSUPPORTED`
- Produces: `COMMANDS["commit"] = CommandTranslation(container_cmd=["container", "commit"])`

- [ ] **Step 1: Write the failing tests**

Update `tests/d2c/test_unsupported.py` to remove the obsolete tests that asserted `commit` was unsupported:
Replace:
```python
def test_commit_is_unsupported() -> None:
    assert "commit" in UNSUPPORTED


def test_commit_hint_mentions_dockerfile() -> None:
    assert "Dockerfile" in UNSUPPORTED["commit"].hint
```
With:
```python
def test_commit_not_in_unsupported() -> None:
    assert "commit" not in UNSUPPORTED
```
And in `tests/d2c/test_unsupported.py` line 62, change the immutability test from `UNSUPPORTED["commit"].hint = "changed"` to use another unsupported command (e.g. `UNSUPPORTED["compose"].hint = "changed"`).

In `tests/d2c/test_cli.py`, change line 32:
Replace:
```python
def test_unsupported_command_exits_with_hint(capsys: pytest.CaptureFixture[str]) -> None:
    with patch("sys.argv", ["d2c", "commit", "mycontainer", "myimage"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "commit" in captured.err
    assert "not supported" in captured.err
```
With:
```python
def test_unsupported_command_exits_with_hint(capsys: pytest.CaptureFixture[str]) -> None:
    with patch("sys.argv", ["d2c", "pause", "mycontainer"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "pause" in captured.err
    assert "not supported" in captured.err
```

In `tests/d2c/test_registry.py`, add the test:
```python
def test_commit_translates_to_container_commit() -> None:
    cmd, note = translate(["commit", "mycontainer", "myimage:tag"])
    assert cmd == ["container", "commit", "mycontainer", "myimage:tag"]
    assert note is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/d2c/ -v`
Expected: FAIL (`test_commit_not_in_unsupported` fails because `commit` is still in `UNSUPPORTED`, and `test_commit_translates_to_container_commit` fails with `KeyError: 'commit'`).

- [ ] **Step 3: Write minimal implementation**

In `src/d2c/unsupported.py`:
Delete lines 10-12:
```python
    "commit": UnsupportedCommand(
        hint="Build from a Dockerfile instead — Apple Container doesn't support creating images from running containers."
    ),
```

In `src/d2c/registry.py`:
Add to `COMMANDS`:
```python
    "commit": CommandTranslation(container_cmd=["container", "commit"]),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/d2c/ -v`
Expected: PASS (all tests in `tests/d2c/` pass).

- [ ] **Step 5: Commit**

```bash
git add src/d2c/unsupported.py src/d2c/registry.py tests/d2c/
git commit -m "feat(d2c): translate docker commit to container commit"
```

---

### Task 2: CLI Wrapper Plugin Error Normalization & Recommended Version Bump

**Files:**
- Modify: `src/apple_container_mcp/cli_wrapper.py:40-46,190-202`
- Modify: `src/apple_container_mcp/tools/system.py:226-233`
- Test: `tests/test_cli_wrapper.py`
- Test: `tests/test_tools.py`

**Interfaces:**
- Consumes: `_run_container_cmd`, `check_environment`
- Produces: `RECOMMENDED_CLI_VERSION = (1, 6)`

- [ ] **Step 1: Write the failing tests**

In `tests/test_cli_wrapper.py`, add:
```python
def test_run_container_cmd_plugins_unavailable_normalized(mocker):
    from apple_container_mcp.cli_wrapper import _run_container_cmd, ContainerCLIError

    mock_run = mocker.patch("subprocess.run")
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=1,
        cmd=["container", "build", "."],
        stderr="Error: Plugins are unavailable. Start the container system services and retry:\n\n    container system start\n",
    )

    with pytest.raises(ContainerCLIError) as exc_info:
        _run_container_cmd(["build", "."])

    assert "plugins are unavailable" in str(exc_info.value).lower()
    assert "container system start" in str(exc_info.value).lower()
```

In `tests/test_tools.py`, update `test_check_environment_ok_when_version_current`, `test_check_environment_recommends_upgrade_on_older_minor`, and `test_check_environment_no_recommendation_on_current_minor`:
```python
def test_check_environment_ok_when_version_current(mocker):
    from apple_container_mcp.tools import system

    mocker.patch.object(system, "_detect_cli_version", return_value=(1, 6))

    result = system.check_environment()

    assert result["status"] == "ok"
    assert result["cli_major_version"] == 1
    assert result.get("warning") is None


def test_check_environment_recommends_upgrade_on_older_minor(mocker):
    from apple_container_mcp.tools import system

    mocker.patch.object(system, "_detect_cli_version", return_value=(1, 2))

    result = system.check_environment()

    assert result["status"] == "ok"
    assert result["cli_version"] == "1.2"
    assert "1.6" in result["recommendation"]
    assert "commit" in result["recommendation"]


def test_check_environment_no_recommendation_on_current_minor(mocker):
    from apple_container_mcp.tools import system

    mocker.patch.object(system, "_detect_cli_version", return_value=(1, 6))

    result = system.check_environment()

    assert result["status"] == "ok"
    assert result["cli_version"] == "1.6"
    assert result.get("recommendation") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli_wrapper.py -k "plugins_unavailable" tests/test_tools.py -k "check_environment"`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

In `src/apple_container_mcp/cli_wrapper.py`:
Update:
```python
RECOMMENDED_CLI_VERSION = (1, 6)
```
And in `_run_container_cmd`:
```python
    except subprocess.CalledProcessError as e:
        logger.warning("Command failed (exit %d): %s — %s", e.returncode, " ".join(full_cmd), e.stderr.strip())
        # Detect and normalize 'daemon not running' or 'plugins unavailable' errors.
        stderr_msg = e.stderr.strip().lower()
        if (
            "connection refused" in stderr_msg
            or "cannot connect to the container daemon" in stderr_msg
            or "plugins are unavailable" in stderr_msg
        ):
            raise ContainerCLIError(
                "The container-apiserver daemon or CLI plugins are unavailable. Please start the system service first ('container system start').",
                e.returncode,
                e.stderr,
            ) from e

        # Generic failure fallback.
        raise ContainerCLIError(f"Command failed with exit code {e.returncode}", e.returncode, e.stderr) from e
```

In `src/apple_container_mcp/tools/system.py`:
Update `check_environment`:
```python
    if version < RECOMMENDED_CLI_VERSION:
        recommended = f"{RECOMMENDED_CLI_VERSION[0]}.{RECOMMENDED_CLI_VERSION[1]}"
        result["recommendation"] = (
            f"Apple Container {recommended} is recommended (you have {major}.{minor}). "
            f"It adds container commit, disk trimming (container clean), CLI plugin architecture, "
            f"DNS aliases, and important OCI security fixes. Upgrade with `brew upgrade container`."
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli_wrapper.py tests/test_tools.py -k "check_environment or plugins_unavailable"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apple_container_mcp/cli_wrapper.py src/apple_container_mcp/tools/system.py tests/test_cli_wrapper.py tests/test_tools.py
git commit -m "feat: normalize plugin availability errors and bump recommended version to 1.6"
```

---

### Task 3: Implement `commit_container` and `clean_containers` MCP Tools

**Files:**
- Modify: `src/apple_container_mcp/tools/containers.py`
- Modify: `src/apple_container_mcp/tools/__init__.py`
- Test: `tests/test_tools.py`

**Interfaces:**
- Consumes: `_run_container_cmd`, `ContainerCLIError`, `mcp.tool()`
- Produces:
  - `commit_container(container_id: str, target_image: str) -> Dict[str, Any]`
  - `clean_containers(container_ids: Optional[List[str]] = None) -> Dict[str, Any]`

- [ ] **Step 1: Write the failing tests**

In `tests/test_tools.py`, add:
```python
def test_commit_container_success(mocker):
    from apple_container_mcp.tools import containers

    mock = _mock_cmd(mocker)
    mock.return_value = {"raw_output": "Committed image test-img:latest"}

    result = containers.commit_container("my-container", "test-img:latest")

    assert result["status"] == "ok"
    assert result["image"] == "test-img:latest"
    mock.assert_called_once_with(["commit", "my-container", "test-img:latest"])


def test_commit_container_validation_empty_id():
    from apple_container_mcp.tools import containers

    result = containers.commit_container("", "test-img:latest")
    assert result["status"] == "error"
    assert "Container ID cannot be empty" in result["message"]


def test_commit_container_validation_empty_image():
    from apple_container_mcp.tools import containers

    result = containers.commit_container("my-container", "   ")
    assert result["status"] == "error"
    assert "Target image reference cannot be empty" in result["message"]


def test_commit_container_cli_error(mocker):
    from apple_container_mcp.tools import containers

    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("commit failed", 1, "container not found")

    result = containers.commit_container("nonexistent", "test-img:latest")
    assert result["status"] == "error"
    assert "Failed to commit container" in result["message"]


def test_clean_containers_all_success(mocker):
    from apple_container_mcp.tools import containers

    mock = _mock_cmd(mocker)
    mock.return_value = {"raw_output": "Cleaned containers"}

    result = containers.clean_containers()
    assert result["status"] == "ok"
    mock.assert_called_once_with(["clean"])


def test_clean_containers_specific_ids_success(mocker):
    from apple_container_mcp.tools import containers

    mock = _mock_cmd(mocker)
    mock.return_value = {"raw_output": "Cleaned container c1"}

    result = containers.clean_containers(container_ids=["c1", "c2"])
    assert result["status"] == "ok"
    mock.assert_called_once_with(["clean", "c1", "c2"])


def test_clean_containers_cli_error(mocker):
    from apple_container_mcp.tools import containers

    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("clean failed", 1, "disk error")

    result = containers.clean_containers()
    assert result["status"] == "error"
    assert "Failed to clean containers" in result["message"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_tools.py -k "commit_container or clean_containers"`
Expected: FAIL with `AttributeError: module 'apple_container_mcp.tools.containers' has no attribute 'commit_container'`.

- [ ] **Step 3: Write minimal implementation**

In `src/apple_container_mcp/tools/containers.py`:
Add implementations:
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
        target_image: Target image reference for the committed image (e.g. "my-image:latest").

    Returns:
        Dictionary with status 'ok' and target image reference, or 'error' on failure.
    """
    if not container_id or not container_id.strip():
        return {"status": "error", "message": "Container ID cannot be empty."}
    if not target_image or not target_image.strip():
        return {"status": "error", "message": "Target image reference cannot be empty."}

    cid = container_id.strip()
    img = target_image.strip()
    try:
        result = _run_container_cmd(["commit", cid, img])
        return {
            "status": "ok",
            "message": f"Successfully committed container '{cid}' to image '{img}'.",
            "image": img,
            "details": result,
        }
    except ContainerCLIError as e:
        return {"status": "error", "message": f"Failed to commit container '{cid}'", "details": str(e)}


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
        Dictionary with status 'ok' and cleanup details, or 'error' on failure.
    """
    cmd = ["clean"]
    if container_ids:
        cleaned_ids = [c.strip() for c in container_ids if c and c.strip()]
        if cleaned_ids:
            cmd.extend(cleaned_ids)

    try:
        result = _run_container_cmd(cmd)
        return {
            "status": "ok",
            "message": "Container cleanup completed successfully.",
            "details": result,
        }
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to clean containers", "details": str(e)}
```

In `src/apple_container_mcp/tools/__init__.py`:
Re-export `commit_container` and `clean_containers`:
In `from .containers import (` add:
```python
    commit_container,
    clean_containers,
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_tools.py -k "commit_container or clean_containers"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apple_container_mcp/tools/containers.py src/apple_container_mcp/tools/__init__.py tests/test_tools.py
git commit -m "feat: add commit_container and clean_containers MCP tools"
```

---

### Task 4: Version Bump, Documentation, and Full Verification

**Files:**
- Modify: `pyproject.toml:3`
- Modify: `src/apple_container_mcp/__init__.py:1`
- Modify: `README.md`
- Modify: `docs/TDD.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: All updated tools, `d2c`, and wrapper
- Produces: Release candidate for `v0.7.0`

- [ ] **Step 1: Bump version in configuration files**

In `pyproject.toml`:
```toml
version = "0.7.0"
```

In `src/apple_container_mcp/__init__.py`:
```python
__version__ = "0.7.0"
```

- [ ] **Step 2: Update documentation**

- In `README.md`:
  - Update prerequisite recommendation: `Requires container CLI 1.0+; validated against 1.6.1, which is the recommended version`.
  - Mention `commit_container` and `clean_containers` tools under Tools Reference.
  - Update `d2c` command tables to show `commit` as supported.
  - Update mention of `container k8s` to `container cluster` (1.6.1 rename).
- In `docs/TDD.md`:
  - Record the Apple Container 1.6.1 architectural decisions, security findings, plugin error normalization, and new tools.
- In `CHANGELOG.md`:
  - Add `[0.7.0]` entry documenting Apple Container 1.6.1 support, `commit_container`, `clean_containers`, `d2c commit`, and plugin error handling.

- [ ] **Step 3: Run comprehensive test suite and linters**

Run:
```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src/ tests/
```
Expected: All 290+ tests pass, 0 ruff errors, 0 format discrepancies, strict mypy passes.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml src/apple_container_mcp/__init__.py README.md docs/TDD.md CHANGELOG.md
git commit -m "chore(release): bump to v0.7.0 for Apple Container 1.6.1 support"
```
