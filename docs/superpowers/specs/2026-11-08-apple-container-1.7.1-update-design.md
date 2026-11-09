# Design Specification: Apple Container 1.7.1 Compatibility & Validation

**Date:** 2026-11-08  
**Target:** Apple Container 1.7.1 (on top of merged 1.6.1 baseline)  
**Package:** `applecontainermcp` (bump from `0.7.1` to `0.7.2`)  

---

## 1. Context & Baseline Audit

`origin/main` includes support up to Apple Container `1.6.1` (`applecontainermcp` `0.7.1`), which introduced `"plugins are unavailable"` CLI error normalization, bumped `RECOMMENDED_CLI_VERSION` to `(1, 6, 1)`, and documented the upstream rename from `container k8s` to `container cluster`.

Apple has released `container` CLI version `1.7.1`. An audit of upstream changes between `1.6.1` and `1.7.1` identifies the following behavioral, configuration, and runtime updates:

1. **Additive `cpuUtilization` Field in `container stats` (`StatsReport`)**:
   - `container stats --format json` (`StatsReport`) adds an optional `cpuUtilization` float representing core-fraction utilization (`1.0` equals one full CPU core).
   - When the second stats sample fails, upstream omits `cpuUtilization` rather than failing the snapshot.
   - `stats_container` parses and returns each `StatsReport` dictionary unchanged whether `cpuUtilization` is present or omitted.
2. **Cluster-Node Lifecycle Boundary**:
   - `container list` hides `cluster` nodes even when `-a` / `--all` is passed.
   - Lifecycle mutations (`start`, `stop`, `kill`, `delete` / `rm`) report named cluster nodes as not found.
   - Read and diagnostic operations (`inspect`, `logs`, `exec`, `stats`, `clean`) continue to succeed on named cluster nodes; cluster node lifecycles are managed exclusively via the `container cluster` CLI plugin.
3. **`[dns]` Defaults in `~/.config/container/config.toml`**:
   - Starting in `1.7.1`, `~/.config/container/config.toml` supports a `[dns]` table (`dns`, `dns-search`, `dns-option`, `dns-domain`) for default container DNS settings alongside `container system property list`.
4. **Storage, BuildKit, and Runtime Stack Updates**:
   - Container data volumes are excluded from macOS Time Machine snapshots to prevent backup bloat and snapshot contention.
   - BuildKit gRPC `:authority` header handling and build-context path regressions are fixed upstream.
   - Guest virtualization dependencies advance to Kata kernel `4.3.1` and Containerization `0.54.0`.
5. **`d2c` Unsupported `plugin` Command Hint Clarification**:
   - `src/d2c/unsupported.py` previously stated `"No equivalent — Apple Container has no plugin system."`
   - Since `1.6.0+`, Apple Container ships bundled CLI plugins (`build`, `builder`, `cluster`) under `libexec/container-plugins/`. What lacks an equivalent is Docker-style user plugin management (`docker plugin install/enable/ls`), because bundled CLI plugins are discovered automatically when `container system start` is running.
6. **Recommended CLI Version Bump**:
   - Bump `RECOMMENDED_CLI_VERSION` from `(1, 6, 1)` to `(1, 7, 1)` in `src/apple_container_mcp/cli_wrapper.py` and update `check_environment()` upgrade guidance in `src/apple_container_mcp/tools/system.py`.

---

## 2. Goals & Non-Goals

### Goals
- Bump `RECOMMENDED_CLI_VERSION` to `(1, 7, 1)` so `check_environment()` recommends upgrading on `1.6.1` and older `1.x` releases while returning no recommendation on `1.7.1+`.
- Document `StatsReport` `cpuUtilization` semantics on `stats_container` and verify passthrough in unit tests and `scripts/smoke_test.py`.
- Document the `1.7.1` `cluster`-node lifecycle boundary across `list_containers`, `start_container`, `stop_container`, and `remove_container`, and `[dns]` `~/.config/container/config.toml` defaults on `system_property_list`.
- Update `UNSUPPORTED["plugin"]` in `src/d2c/unsupported.py` to accurately explain bundled CLI plugin discovery (`build`, `builder`, `cluster`) when `container system start` is active.
- Bump package version in lockstep to `0.7.2` across `pyproject.toml`, `src/apple_container_mcp/__init__.py`, and `uv.lock`.
- Update `README.md`, `CHANGELOG.md` (`[0.7.2]` release notes and `[0.7.0]` `2026-10-23` release date), and `docs/TDD.md` (`1.7.1 audit` entry and recommended version references).
- Record live validation against the host's installed `container CLI version 1.7.1` in `docs/superpowers/plans/2026-11-08-apple-container-1.7.1-validation.md`.

### Non-Goals
- Wrapping the `container cluster` CLI plugin as MCP tools (cluster lifecycle management remains intentionally out of scope for `apple-container-mcp`).
- Mutating `~/.config/container/config.toml` directly from MCP tools (`system_property_list` remains read-only).

---

## 3. Detailed Component Changes

### 3.1 CLI Wrapper & Environment Check (`#29`)
- **`src/apple_container_mcp/cli_wrapper.py`**:
  - `RECOMMENDED_CLI_VERSION = (1, 7, 1)`
- **`src/apple_container_mcp/tools/system.py`**:
  - `check_environment()` recommends `1.7.1` when the detected `1.x` CLI version is below `(1, 7, 1)`, citing upstream security fixes plus `1.7.1` runtime and cluster lifecycle updates.
  - `system_property_list()` docstring notes `[dns]` TOML defaults (`dns`, `dns-search`, `dns-option`, `dns-domain`) in `~/.config/container/config.toml`.

### 3.2 Container Tool Contracts (`#29`)
- **`src/apple_container_mcp/tools/containers.py`**:
  - `stats_container()` documents `StatsReport` and the additive `cpuUtilization` core-fraction float (`1.0` = one core, omitted if the second sample fails) and returns parsed entries unchanged.
  - `list_containers()`, `start_container()`, `stop_container()`, and `remove_container()` document that `container list` hides `cluster` nodes even with `--all` (`-a`), `start`/`stop`/`kill`/`delete` report named cluster nodes as not found, and `inspect`/`logs`/`exec`/`stats`/`clean` continue to work on named cluster nodes.

### 3.3 `d2c` Plugin Hint & Live Smoke Script (`#30`)
- **`src/d2c/unsupported.py`**:
  - `UNSUPPORTED["plugin"]` explains that Docker-style `docker plugin install/enable/ls` management has no equivalent because Apple Container discovers bundled CLI plugins (`build`, `builder`, `cluster`) automatically when system services are running (`container system start`).
- **`scripts/smoke_test.py`**:
  - Updates module docstring target to Apple Container `1.7.1+`.
  - Validates `stats_container([prefix])` returns a non-empty list containing `id == prefix` and, when `cpuUtilization` is present, asserts it is a non-boolean `int | float >= 0`.

### 3.4 Release Packaging, Documentation & Live Validation (`#31`)
- **Version Lockstep (`0.7.2`)**:
  - `pyproject.toml`, `src/apple_container_mcp/__init__.py`, and `uv.lock` synchronized at `0.7.2`, verified by `tests/test_server.py` and `uv lock --check`.
- **Documentation Artifacts**:
  - `README.md`, `CHANGELOG.md`, and `docs/TDD.md` updated with full `1.7.1` behavioral, configuration, storage, BuildKit, and guest runtime details.
  - `docs/superpowers/plans/2026-11-08-apple-container-1.7.1-validation.md` captures live outputs from the installed `container CLI version 1.7.1` binary and full CI quality gates.

---

## 4. Verification Plan

1. **Unit & Contract Tests**:
   - `tests/test_container_171.py`, `tests/test_tools.py`, and `tests/test_container_141.py` cover `(1, 7, 1)` version boundaries, `cpuUtilization` passthrough, cluster-node lifecycle boundaries, and `[dns]` docstring contracts.
   - `tests/d2c/test_unsupported.py` and `tests/test_smoke_test.py` cover the `d2c plugin` hint and `smoke_test.py` `cpuUtilization` assertions.
   - `tests/test_server.py` verifies `0.7.2` version lockstep and release/spec/validation documentation completeness.
2. **Non-Destructive Host CLI Validation**:
   - Verify `container --version`, bundled plugin binaries under `/opt/homebrew/Cellar/container/1.7.1/libexec/container-plugins/`, `check_environment()`, `d2c plugin ls`, and daemon/smoke behavior without stopping running user services or mutating external workloads.
3. **Quality Gates**:
   - `uv run ruff check src/ tests/`
   - `uv run ruff format --check src/ tests/`
   - `uv run mypy src/`
   - `uv run pytest tests/ --cov=apple_container_mcp --cov-report=term-missing --cov-fail-under=90`
   - `uv lock --check`
