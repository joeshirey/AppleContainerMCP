# Apple Container 1.5.0 validation

Date: 2026-09-30. Host: Apple Silicon, macOS 27. CLI and daemon: 1.5.0.
This is local validation, not certification on every supported macOS/CLI release.

## Upstream changes reviewed (1.4.1 → 1.5.0)

- Security: GHSA-44v5-vx46-ghv6 sanitizes guest kubeconfig values before they are merged into the host kubeconfig.
- Breaking CLI change: `container k8s start` was removed. `k8s create` gained `--cni`. This server does not wrap the Kubernetes plugin, so no tools are affected.
- Core fixes: commands run when an image entrypoint is empty, egress survives localhost DNS changes, and the error for unknown commands is clearer (`unknown command 'X'` replaces `Plugin 'container-X' not found`). The server does not parse either message.
- The upstream command reference was re-synced. Its registry `--scheme` docs now match the 1.4.1 behavior: `http`/`https`, default `https`. `--kernel-arg` appears in the reference, but the flag dates from 0.10 and stays unexposed on purpose (see `tools/__init__.py`).
- The upstream `Sources/ContainerCommands` diff touches only help text and the unknown-command message. No flags or JSON output changed on commands the server wraps.

## Changes

- `RECOMMENDED_CLI_VERSION` is now 1.5.0. `check_environment` recommends an upgrade for 1.0.0–1.4.x, and the message names the new security fix.
- The `clean_container` gate stays at 1.4.1+.

## Results

- All 54 command help probes from the 1.4.1 audit exited successfully on 1.5.0.
- Installed help confirms registry `--scheme` still accepts `(http, https)` and defaults to `https`.
- `system status --format json` reports running, with client and server both 1.5.0. Keys are unchanged: status, client, server, host, paths, resources.
- Unit suite: 337 passed, 94.43% coverage. Ruff lint/format and strict mypy pass.
- Live default smoke script passed: pull; network/volume create and inspect; run/list/inspect/logs/stats/exec; copy round trip; clean with writable and read-only volumes; data preserved after clean; clean rejected on a stopped container; stop/start; builder start and async build; d2c info/version/ps; cleanup of all test resources.
- MCP initialization over stdio: 57 tools registered. `check_environment`, `system_status`, and `list_containers` succeed, and `check_environment` reports 1.5.0 with no recommendation.

The optional `--registry` smoke check was not re-run. The host-to-container connectivity limitation recorded in the 1.4.1 audit still applies.
