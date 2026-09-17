# Apple Container 1.4.1 validation

Date: 2026-09-17. Host: Apple Silicon, macOS 27.0 build 26A428. CLI and daemon: 1.4.1.
This is local validation, not certification on every supported macOS/CLI release.

## Results

- All 54 command help probes below exited successfully. Existing command names/aliases remain valid.
- Installed help confirms `http`/`https` (default HTTPS) for image pull/push, run, registry login, and machine create. Added explicit scheme parameters to all five corresponding MCP tools. The tagged command reference still mentions `auto`; installed help and upstream release notes take precedence.
- Clean accepts explicit IDs, emits text, and requires running containers. The new tool uses one ID, an explicit long timeout, and a 1.4.1 version gate.
- Observed unregistered status before starting the service: stdout `{"status":"unregistered"}`. Upstream source establishes exit code 1. Registered-but-stopped status is source-derived and covered by regression tests; the user's running service was not stopped to capture it.
- Observed running status keys: status, client, server, host, paths, resources. Client and server report 1.4.1. Existing JSON format handling supports the new payload.
- Unit suite: 337 passed; MCP coverage exceeds 94%. Ruff lint/format and strict mypy pass.
- Live default smoke script passed: HTTPS pull; network/volume creation and inspection; run/list/inspect/logs/stats/exec; file copy round trip; clean with writable/read-only named volumes; preserved data after clean; rejection of stopped-container clean; stop/start/remove; asynchronous image build; d2c info/version/ps JSON; cleanup of all uniquely named test resources.
- Real MCP initialization, tool listing, schema inspection, and check_environment/system_status/list_containers calls passed over stdio and loopback Streamable HTTP. 57 tools registered.
- Security/path restrictions and password-via-stdin behavior remain covered by tests. New scheme tests reject `auto`, malformed strings, and empty values before executing subprocesses.

## Remaining runtime limitation

The optional `scripts/smoke_test.py --registry` check could not complete its HTTP push/pull round trip on this host. Registry 3 started and logged that it was listening on port 5000, but direct host requests to both the published loopback port and the container's IPv4 address timed out; the CLI push ended with a connection-reset error. The test was repeated after the reset with the same result. An HTTP request executed inside the registry container returned `{}`, confirming that the registry itself was serving requests. This failure also occurs outside MCP. No automatic HTTPS-to-HTTP retry was added. HTTP argument handling is tested for all applicable tools, but successful HTTP push/pull and authenticated registry login still require validation in an environment with working host-to-container connectivity. Test registry containers and temporary tags were removed.

macOS 26 and older CLI versions were not live-tested here. Older version gates and legacy status payloads have regression coverage. No prune operations or changes to existing application containers were performed. The builder and pulled shared base images remain available for user testing.

## Command help audit

Help success establishes command availability; it does not claim every flag/operation was runtime-tested. Runtime coverage is listed above. JSON-producing status/list calls were additionally exercised through the wrapper and smoke tests.

| Command | Help result |
| --- | --- |
| `run` | Pass |
| `ls` | Pass |
| `start` | Pass |
| `stop` | Pass |
| `kill` | Pass |
| `rm` | Pass |
| `export` | Pass |
| `inspect` | Pass |
| `exec` | Pass |
| `logs` | Pass |
| `prune` | Pass |
| `stats` | Pass |
| `clean` | Pass |
| `copy` | Pass |
| `build` | Pass |
| `image ls` | Pass |
| `image pull` | Pass |
| `image push` | Pass |
| `image tag` | Pass |
| `image inspect` | Pass |
| `image rm` | Pass |
| `image prune` | Pass |
| `image load` | Pass |
| `image save` | Pass |
| `network create` | Pass |
| `network rm` | Pass |
| `network ls` | Pass |
| `network inspect` | Pass |
| `network prune` | Pass |
| `volume create` | Pass |
| `volume rm` | Pass |
| `volume ls` | Pass |
| `volume inspect` | Pass |
| `volume prune` | Pass |
| `builder start` | Pass |
| `builder stop` | Pass |
| `builder status` | Pass |
| `registry login` | Pass |
| `registry logout` | Pass |
| `system start` | Pass |
| `system stop` | Pass |
| `system status` | Pass |
| `system version` | Pass |
| `system df` | Pass |
| `system logs` | Pass |
| `machine create` | Pass |
| `machine run` | Pass |
| `machine ls` | Pass |
| `machine inspect` | Pass |
| `machine set` | Pass |
| `machine logs` | Pass |
| `machine stop` | Pass |
| `machine delete` | Pass |
| `system property list` | Pass |
