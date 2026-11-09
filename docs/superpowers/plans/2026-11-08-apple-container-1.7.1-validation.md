# Apple Container 1.7.1 Validation

Date: 2026-11-08. Host: Apple Silicon (`arm64`), macOS `27.2` build `26B123`. CLI: `1.7.1` (`container CLI version 1.7.1 (build: release, commit: unspeci)`).
This is local validation, not certification on every supported macOS/CLI release.

## Upstream Changes Reviewed (1.6.1 → 1.7.1)

- **Additive `cpuUtilization` in `container stats` (`StatsReport`):** `container stats --format json` adds a core-fraction float `cpuUtilization` (`1.0` equals one full core), omitted when the second sample fails.
- **Cluster-Node Lifecycle Boundary:** `container list` hides `cluster` nodes even with `-a` / `--all`, and `start`, `stop`, `kill`, and `delete` report named cluster nodes as not found (`inspect`, `logs`, `exec`, `stats`, and `clean` continue to work on named cluster nodes; cluster lifecycles are managed via `container cluster`).
- **`[dns]` Defaults in `config.toml`:** `~/.config/container/config.toml` adds `[dns]` defaults (`dns`, `dns-search`, `dns-option`, `dns-domain`).
- **Storage, BuildKit, and Runtime Updates:** Container data volumes are excluded from Time Machine snapshots, BuildKit gRPC `:authority` header and build-context regressions are fixed, and guest virtualization dependencies advance to Kata kernel `4.3.1` and Containerization `0.54.0`.

## MCP Server & `d2c` Changes (`v0.7.2`)

- **Recommended CLI Version:** Bumped `RECOMMENDED_CLI_VERSION` from `(1, 6, 1)` to `(1, 7, 1)` in `src/apple_container_mcp/cli_wrapper.py` and updated `check_environment()` upgrade recommendations in `src/apple_container_mcp/tools/system.py`.
- **Tool Contracts:** Updated `stats_container`, `list_containers`, `start_container`, `stop_container`, `remove_container`, and `system_property_list` docstrings and added `tests/test_container_171.py`.
- **`d2c` Plugin Hint & Smoke Script:** Updated `UNSUPPORTED["plugin"]` in `src/d2c/unsupported.py` to explain automatic discovery of bundled CLI plugins (`build`, `builder`, `cluster`) when `container system start` is running, and updated `scripts/smoke_test.py` (`tests/test_smoke_test.py`) to validate `StatsReport` `cpuUtilization` payloads on `1.7.1+`.
- **Release Bump:** Synchronized package version at `0.7.2` across `pyproject.toml`, `src/apple_container_mcp/__init__.py`, and `uv.lock`.

## Live Host CLI Validation (`1.7.1`)

### 1. Version Probe & `system_version()`

```console
$ container --version
container CLI version 1.7.1 (build: release, commit: unspeci)
```

`system_version()` executed without a running daemon:

```json
{
  "status": "ok",
  "version": [
    {
      "appName": "container",
      "buildType": "release",
      "commit": "unspecified",
      "version": "1.7.1"
    }
  ]
}
```

### 2. Bundled Plugin Binaries

Inspected `/opt/homebrew/Cellar/container/1.7.1/libexec/container-plugins/*/bin/*`:

```text
/opt/homebrew/Cellar/container/1.7.1/libexec/container-plugins/build/bin/build
/opt/homebrew/Cellar/container/1.7.1/libexec/container-plugins/builder/bin/builder
/opt/homebrew/Cellar/container/1.7.1/libexec/container-plugins/cluster/bin/cluster
/opt/homebrew/Cellar/container/1.7.1/libexec/container-plugins/container-core-images/bin/container-core-images
/opt/homebrew/Cellar/container/1.7.1/libexec/container-plugins/container-network-vmnet/bin/container-network-vmnet
/opt/homebrew/Cellar/container/1.7.1/libexec/container-plugins/container-runtime-linux/bin/container-runtime-linux
/opt/homebrew/Cellar/container/1.7.1/libexec/container-plugins/machine-apiserver/bin/machine-apiserver
```

### 3. `check_environment()` & MCP Tool Registration

Registered MCP tool count via `mcp.list_tools()`: `58` tools.

```console
$ uv run python -c "import json; from apple_container_mcp.tools.system import check_environment; print(json.dumps(check_environment(), indent=2))"
{
  "status": "ok",
  "cli_major_version": 1,
  "cli_version": "1.7.1",
  "message": "Apple Container CLI 1.7.1 detected (meets the 1.0+ minimum)."
}
```

No `"recommendation"` or `"warning"` field is emitted on `1.7.1`.

### 4. `d2c plugin` Output

```console
$ uv run d2c plugin ls
✗  'docker plugin' is not supported by Apple Container.
   Hint: No equivalent to Docker-style plugin management ('docker plugin install/enable/ls') — Apple Container discovers bundled CLI plugins ('build', 'builder', 'cluster') automatically when system services are running ('container system start').
# exit_code=1
```

### 5. Daemon Status & Non-Destructive Smoke Policy

Probing the host daemon state via `container system status --format json` returned exit code `1` with `{"status":"unregistered"}` (daemon stopped on the host):

- `check_apiserver_status()`: `{"status": "stopped", "error": "The container-apiserver daemon is not reachable."}`
- `system_status()`: `{"status": "error", "message": "Failed to retrieve system status", "details": "Command failed with exit code 1", "system_status": {"status": "unregistered"}}`
- `container build --help` / `builder_status()` with stopped services exited `64` with `Error: Plugins are unavailable. Start the container system services and retry: container system start` (confirming live `1.7.1` plugin-unavailability behavior).

Per non-destructive host validation rules, the stopped host system service was left untouched rather than starting background daemons unexpectedly; `scripts/smoke_test.py` requires an active `container` service, and its `1.7.1` `StatsReport` `cpuUtilization` validation logic was verified via `tests/test_smoke_test.py`.

## Full CI Gate Results

```console
$ uv run ruff check src/ tests/
All checks passed!

$ uv run ruff format --check src/ tests/
33 files already formatted

$ uv run mypy src/
Success: no issues found in 20 source files

$ uv run pytest tests/ --cov=apple_container_mcp --cov-report=term-missing --cov-fail-under=90
393 passed in 0.72s
Required test coverage of 90% reached. Total coverage: 94.77%

$ uv lock --check
Resolved 46 packages in 3ms
```
