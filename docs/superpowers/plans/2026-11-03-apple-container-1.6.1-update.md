# Apple Container 1.6.1 Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade AppleContainerMCP to fully support Apple Container 1.6.1 by normalizing plugin-unavailability errors, recommending CLI 1.6.1, updating documentation for upstream changes (including `container k8s` to `container cluster` rename), and bumping to version 0.7.1.

**Architecture:** Extend subprocess error normalization in `cli_wrapper.py` to intercept plugin-unavailable failures when services are down. Bump `RECOMMENDED_CLI_VERSION` to `(1, 6, 1)` and update tests and documentation accordingly.

**Tech Stack:** Python 3.11+, FastMCP, pytest, pytest-mock, ruff, mypy, uv.

## Global Constraints

- Python compatibility: `>=3.11`
- Minimum Apple Container CLI major version: `1` (hard gate remains `1.0+`)
- Recommended Apple Container CLI version: `(1, 6, 1)`
- Package version bump: `0.7.0` -> `0.7.1` in `pyproject.toml` and `src/apple_container_mcp/__init__.py`
- All commands and code must pass `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, and `uv run mypy src/ tests/`
- Adhere strictly to TDD: test first, verify failure, implement, verify pass, commit.

---

### Task 1: Normalize Plugin Unavailability Errors in `cli_wrapper.py`

**Files:**
- Modify: `src/apple_container_mcp/cli_wrapper.py:192-200`
- Test: `tests/test_cli_wrapper.py`

**Interfaces:**
- Consumes: `_run_container_cmd`, `subprocess.CalledProcessError`
- Produces: Normalized `ContainerCLIError` when stderr indicates plugins are unavailable

- [ ] **Step 1: Write the failing test**

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

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli_wrapper.py -k "plugins_unavailable" -v`
Expected: FAIL (`Command failed with exit code 1` instead of normalized message).

- [ ] **Step 3: Write minimal implementation**

In `src/apple_container_mcp/cli_wrapper.py` lines 193-200:
Update to:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli_wrapper.py -k "plugins_unavailable" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apple_container_mcp/cli_wrapper.py tests/test_cli_wrapper.py
git commit -m "feat: normalize plugin availability errors in CLI wrapper"
```

---

### Task 2: Bump Recommended CLI Version to 1.6.1 and Update Version Tests

**Files:**
- Modify: `src/apple_container_mcp/cli_wrapper.py:43`
- Test: `tests/test_tools.py:220,257-268`
- Test: `tests/test_container_160.py:36,49,71`
- Test: `tests/test_container_141.py:30`

**Interfaces:**
- Consumes: `RECOMMENDED_CLI_VERSION`
- Produces: `RECOMMENDED_CLI_VERSION = (1, 6, 1)`

- [ ] **Step 1: Write the failing tests**

In `tests/test_tools.py`:
Update `test_check_environment_ok_when_version_current`:
```python
def test_check_environment_ok_when_version_current(mocker):
    from apple_container_mcp.tools import system

    mocker.patch.object(system, "_detect_cli_version", return_value=(1, 6, 1))

    result = system.check_environment()

    assert result["status"] == "ok"
    assert result["cli_major_version"] == 1
    assert result.get("warning") is None
```

Update `test_check_environment_recommends_upgrade_on_older_minor`:
```python
def test_check_environment_recommends_upgrade_on_older_minor(mocker):
    from apple_container_mcp.tools import system

    mocker.patch.object(system, "_detect_cli_version", return_value=(1, 6, 0))

    result = system.check_environment()

    assert result["status"] == "ok"
    assert result["cli_version"] == "1.6.0"
    assert "1.6.1" in result["recommendation"]
```

Update `test_check_environment_no_recommendation_on_current_minor`:
```python
def test_check_environment_no_recommendation_on_current_minor(mocker):
    from apple_container_mcp.tools import system

    mocker.patch.object(system, "_detect_cli_version", return_value=(1, 6, 1))

    result = system.check_environment()

    assert result["status"] == "ok"
    assert result["cli_version"] == "1.6.1"
    assert result.get("recommendation") is None
```

In `tests/test_container_141.py` line 30:
Update:
```python
    assert ("recommendation" in result) == ((1, 0, 0) <= parts < (1, 6, 1))
```

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run pytest tests/test_tools.py -k "check_environment" tests/test_container_141.py -v`
Expected: FAIL

- [ ] **Step 3: Update `RECOMMENDED_CLI_VERSION` in `cli_wrapper.py`**

In `src/apple_container_mcp/cli_wrapper.py` line 43:
```python
RECOMMENDED_CLI_VERSION = (1, 6, 1)
```

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest tests/test_tools.py -k "check_environment" tests/test_container_141.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apple_container_mcp/cli_wrapper.py tests/test_tools.py tests/test_container_141.py
git commit -m "feat: bump recommended Apple Container CLI version to 1.6.1"
```

---

### Task 3: Version Bump, Validation Doc, Documentation, and Final Checks

**Files:**
- Modify: `pyproject.toml:3`
- Modify: `src/apple_container_mcp/__init__.py:1`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/TDD.md`
- Modify: `scripts/smoke_test.py:3`
- Create: `docs/superpowers/plans/2026-11-03-apple-container-1.6.1-validation.md`

**Interfaces:**
- Release: `applecontainermcp v0.7.1`

- [ ] **Step 1: Bump version to 0.7.1**

In `pyproject.toml`:
```toml
version = "0.7.1"
```

In `src/apple_container_mcp/__init__.py`:
```python
__version__ = "0.7.1"
```

- [ ] **Step 2: Update documentation**

In `README.md`:
- Change `Requires container CLI 1.0+; 1.6.0 is recommended and locally tested.` to `Requires container CLI 1.0+; 1.6.1 is recommended and locally tested.`
- Note that Apple Container 1.6.1 infers platform and runtime from OCI images, fixes signal passing to container processes, and renames `container k8s` to `container cluster`.

In `CHANGELOG.md`:
Add entry:
```markdown
## [0.7.1] - 2026-11-03

### Added
- Apple Container 1.6.1 support, validated against the installed 1.6.1 CLI and daemon.
- Normalization of "Plugins are unavailable" CLI errors when `container system start` has not been run.

### Compatibility
- The minimum CLI policy remains 1.0+; 1.6.1 is now recommended for upstream signal forwarding fixes, cluster concurrency fixes, and OCI platform/runtime auto-introspection.
- Upstream renamed the Kubernetes CLI plugin from `container k8s` to `container cluster`.
```

In `docs/TDD.md`:
Add section recording 1.6.1 changes.

In `scripts/smoke_test.py`:
Update docstring: `Requires a running Apple Container 1.6.1+ service.`

In `docs/superpowers/plans/2026-11-03-apple-container-1.6.1-validation.md`:
Create the validation log documenting test runs, CLI version outputs, and observations.

- [ ] **Step 3: Run comprehensive verification**

Run:
```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src/ tests/
```
Expected: All tests pass, no lint errors, strict mypy passes.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml src/apple_container_mcp/__init__.py README.md CHANGELOG.md docs/TDD.md scripts/smoke_test.py docs/superpowers/plans/2026-11-03-apple-container-1.6.1-validation.md
git commit -m "chore(release): bump to v0.7.1 for Apple Container 1.6.1 support"
```
