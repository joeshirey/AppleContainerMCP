# Apple Container 1.6.1 Validation

Date: 2026-11-03. Host: Apple Silicon (arm64), macOS 27.2 build 26B123. CLI: 1.6.1 (`container CLI version 1.6.1 (build: release, commit: unspeci)`).
This is local validation, not certification on every supported macOS/CLI release.

## Upstream Changes Reviewed (1.6.0 → 1.6.1)

- **OCI Image Platform and Runtime Introspection:** Apple Container 1.6.1 automatically infers the target platform and runtime from the OCI image manifest/configuration.
- **Signal Forwarding Fixes:** Improved signal handling ensures process signals (e.g. SIGTERM, SIGINT) are reliably delivered to container guest processes.
- **Kubernetes Plugin Renamed to Cluster:** Upstream renamed the experimental `container k8s` plugin to `container cluster`, addressing multi-cluster concurrency. Validated locally that `/opt/homebrew/Cellar/container/1.6.1/libexec/container-plugins/cluster` exists (replacing `k8s`). AppleContainerMCP deliberately does not wrap cluster/k8s plugin tools, so existing tools remain unaffected.
- **Plugin Unavailable CLI Behavior:** When container background services are stopped or unregistered, running plugin-backed subcommands (`build`, `builder`, `cluster`) produces:
  ```
  Error: Plugins are unavailable. Start the container system services and retry:

      container system start
  ```
  with exit code 64.

## MCP Server Changes

- **Plugin Error Normalization:** Extended `cli_wrapper.py` error handling so that "plugins are unavailable" outputs are normalized into clear guidance directing the user to start system services via `container system start`.
- **Recommended CLI Version:** Bumped `RECOMMENDED_CLI_VERSION` from `(1, 6, 0)` to `(1, 6, 1)`. `check_environment` recommends upgrading on any CLI older than 1.6.1.
- **Version Bump:** Package bumped to `0.7.1` in `pyproject.toml` and `src/apple_container_mcp/__init__.py`.
- **Documentation & Scripts:** Updated `README.md`, `CHANGELOG.md`, `docs/TDD.md`, and `scripts/smoke_test.py`.

## Validation Results

- **CLI Probing:**
  - `container --version` returned `container CLI version 1.6.1 (build: release, commit: unspeci)`.
  - Plugin directory inspection confirmed `build`, `builder`, `cluster`, `container-core-images`, `container-network-vmnet`, `container-runtime-linux`, and `machine-apiserver` in `/opt/homebrew/Cellar/container/1.6.1/libexec/container-plugins/`.
- **Unit & Regression Suite:**
  - `uv run pytest` executed 360 tests, all passing.
  - Normalization test `test_run_container_cmd_plugins_unavailable_normalized` passed.
  - Version upgrade recommendation tests updated and passing.
- **Static Analysis & Formatting:**
  - `uv run ruff check .` passed with 0 errors.
  - `uv run ruff format --check .` passed with all files formatted.
  - `uv run mypy src/ tests/` passed in strict mode with 0 errors across 25 source files.
