# Apple Container 1.4.1 support plan

Date: 2026-09-17. Status: implemented and locally tested; approved for pull request. See [validation results](2026-09-17-cli-audit-results.md), including the remaining HTTP registry networking limitation.

## Objective and scope

Update AppleContainerMCP (currently package 0.6.0, validated against CLI 1.2.2) to support and recommend Apple Container 1.4.1. Cover both the MCP server and the bundled d2c translator. Preserve existing tool names and response envelopes where possible. Keep the existing 1.0+ compatibility policy, with feature-specific version checks and a clear recommendation to upgrade to 1.4.1; do not describe older versions as equally secure or fully validated.

Deliver compatibility fixes first, then expose the new clean operation. Kubernetes support, a general Docker flag translator, and unrelated dependency upgrades are outside this change.

## Findings and evidence

- Version detection in `src/apple_container_mcp/cli_wrapper.py` returns only `(major, minor)`, and the recommendation is `(1, 2)`. It cannot distinguish security patch releases. `tools/system.py` and `tools/machines.py` consume this result.
- The wrapper parses successful JSON responses but drops stdout on nonzero exits. `check_apiserver_status` identifies stopped services from exception text/stderr alone.
- Local read-only verification found `container CLI version 1.4.1`. `container system status --format json` returned `{"status":"unregistered"}`. Tagged upstream source confirms this response exits with code 1, as does `{"status":"not running"}`. No service was started during planning.
- Running status now contains `status`, `client`, `server`, `host`, `paths`, and optional `resources`. The existing passthrough can preserve these fields, but error handling and tests need updating. Resource counts can be absent and must not be fabricated as zero. [Tagged SystemStatus source](https://github.com/apple/container/blob/1.4.1/Sources/ContainerCommands/System/SystemStatus.swift)
- 1.3.0 removed registry scheme `auto` and changed the default to HTTPS. Current pull/push/run/login tools expose no scheme parameter. Existing local HTTP workflows can consequently fail. Installed `image pull --help` confirms only `http` and `https`; the tagged command reference still mentions `auto`, so source and installed help take precedence. [1.3.0 release](https://github.com/apple/container/releases/tag/1.3.0)
- 1.3.1 and 1.4.1 include upstream security fixes. 1.4.1 also adds `container clean`, changes status output, and stops escaping JSON forward slashes. Apple discarded the 1.4.0 release tag. [1.3.1 release](https://github.com/apple/container/releases/tag/1.3.1), [1.4.1 release](https://github.com/apple/container/releases/tag/1.4.1)
- `clean` reclaims unused filesystem space in running containers and their named volumes; it is different from deleting stopped containers or pruning unused resources. It requires explicit IDs and emits text. [Tagged clean source](https://github.com/apple/container/blob/1.4.1/Sources/ContainerCommands/Container/ContainerClean.swift), [command reference](https://github.com/apple/container/blob/1.4.1/docs/command-reference.md#container-clean)
- CI runs lint, formatting, mypy, and mocked tests with 90% MCP coverage. It does not install or exercise the container runtime.

## Implementation sequence

### 1. Establish the compatibility contract

Audit installed 1.4.1 help for every command emitted by `tools/*.py` and `src/d2c/registry.py`: aliases, flags, JSON support, positional arguments, and exit behavior. Record results in a dated CLI audit alongside this plan. Compare against tagged 1.2.2 source where behavior changed, rather than relying only on the command-reference diff.

Capture sanitized status fixtures for running, unregistered, and registered-but-stopped services. Use tagged-source-derived fixtures initially where runtime capture is unavailable, explicitly labeling their provenance. Preserve examples from the previous supported output format for regression testing.

Acceptance: every exposed command is classified as unchanged, changed, or pending live verification; no documentation-only assumption is presented as runtime validation.

### 2. Make version detection patch-aware

Files: `cli_wrapper.py`, `tools/system.py`, `tools/machines.py`, and their tests.

- Parse and cache `(major, minor, patch)`; check subprocess return code and distinguish unavailable/unparseable version output in diagnostics.
- Set the recommended version to `(1, 4, 1)` and report the complete version in `check_environment`, retaining `cli_major_version`.
- Update all tuple comparisons and mocks together, including the 1.1 machine virtualization gate. Keep the existing major-version compatibility warning behavior; do not introduce an unrelated global hard gate.
- Test 0.x, 1.0.0, 1.2.2, 1.3.1, 1.4.0, 1.4.1, newer versions, missing binary, unsuccessful probe, and malformed output. Test 1.4.0 only as a comparison boundary, not a supported released version.

Acceptance: 1.4.1 is reported exactly; older supported releases receive an actionable advisory; newer versions do not receive an upgrade warning.

### 3. Correct system status and error handling

Files: `cli_wrapper.py`, `tools/system.py`, `tests/test_cli_wrapper.py`, `tests/test_tools.py`.

- Extend `ContainerCLIError` with optional captured stdout while preserving current constructor callers. Keep nonzero exits as errors generally.
- Interpret known stopped-service JSON specifically for `system status`; do not turn arbitrary failed commands with JSON into successes.
- Preserve the `system_status` tool's outer response contract and full successful upstream payload. Include useful stopped-service details on failures. Keep the status resource consistent with that behavior.
- Make `check_apiserver_status` return `stopped` for both `unregistered` and `not running`, retain legacy error-text handling, and avoid reporting healthy status after a JSON parse failure or unknown status.
- Cover rich running output, optional fields, stopped JSON with empty stderr, malformed JSON, unrelated errors, and legacy fixtures.
- Test escaped and unescaped slashes as equivalent parsed values; no string replacement is needed because `json.loads` already supports both.

Acceptance: stopped services are correctly diagnosed and the richer successful payload is available without breaking established outer tool keys.

### 4. Support explicit registry transport

Files: `tools/images.py`, `tools/containers.py`, `tools/registry.py`, `tools/prompts.py`, associated tests and README.

- Verify exact scheme support on pull, push, run, registry login, and any other wrapped image-fetching commands.
- Add an optional `scheme` parameter to applicable tools, accepting only `http` or `https`. Omission preserves the installed CLI default; document that 1.4.1 defaults to HTTPS. Explicit HTTPS provides consistent behavior across supported versions.
- Pass explicit HTTP only when requested. Do not silently retry HTTPS failures over HTTP or reintroduce `auto`.
- Preserve password-via-stdin login and existing argument/path restrictions. Update the private-registry workflow to carry an explicitly selected scheme through login and image operations.
- Test default argument compatibility, explicit schemes, invalid inputs, and failure propagation. Smoke-test an isolated local HTTP registry and an HTTPS pull during runtime validation.

Acceptance: normal HTTPS operations remain unchanged; intentionally configured HTTP registries are usable through MCP.

### 5. Expose 1.4.1 space reclamation

Files: `tools/containers.py`, `tools/prompts.py`, tool exports if needed, and tests.

- Add `clean_container(container_id: str)` with a required nonempty ID, a 1.4.1 feature gate, and clear running-container requirements. A single-ID API avoids ambiguous partial success from upstream multi-ID execution.
- Use text output handling, without adding clean to the JSON allowlist. Use an explicit long-running timeout initially and verify it on representative data.
- Document the disk-mutating operation accurately; use conservative mutation annotations and never automatically start a stopped container to clean it.
- Extend cleanup guidance to distinguish filesystem space reclamation from prune/delete operations. Keep existing prune semantics intact.
- Test unsupported/unknown versions, empty ID, success, stopped-container failure, and timeout. For unknown versions, return a clear inability-to-verify message for this new feature.

Acceptance: callers can explicitly reclaim space on a running container without confusing the operation with resource deletion.

### 6. Validate d2c and run the release checks

Files: `src/d2c/registry.py`, `tests/d2c/*`, `.github/workflows/ci.yml`, README, CHANGELOG, package metadata if releasing.

- Audit all translator mappings, especially `info`, registry/image operations, load/save, and management groups. Preserve flag passthrough and child exit codes. Do not map Docker prune to Apple clean or invent a Docker clean command.
- Add regression tests for affected mappings and dry-run output; document HTTPS-default implications and existing flag-compatibility limits.
- Run existing CI commands: `uv run ruff check src/ tests/`, `uv run ruff format --check src/ tests/`, `uv run mypy src/`, and `uv run pytest tests/ --cov=apple_container_mcp --cov-report=term-missing --cov-fail-under=90`.
- Add an opt-in integration suite/checklist on Apple Silicon with macOS 26 and pinned CLI 1.4.1. Do not assume the current hosted CI runner can run virtualization; use a suitable runner or documented local validation.
- Exercise service status, image pull, run/list/inspect/exec/logs/stats, copy, stop/remove, build/status, network and volume lifecycle, and clean with writable/read-only named mounts. Validate d2c info/version and a basic lifecycle. Limit cleanup to uniquely named test resources.
- Capture genuine running/stopped status fixtures in the controlled integration environment. Do not stop a user's active service merely to generate fixtures.
- Update recommended/validated version, new parameters and capability list, status response examples, security-fix context, and changelog. Propose package 0.7.0 if shipping the additive clean tool and scheme parameters; update lockfile/package version metadata together.

Acceptance: all CI checks pass and the runtime checklist is recorded before claiming validation against 1.4.1. Older-version fixtures demonstrate compatibility intent, not live certification of every 1.x release.

## Suggested delivery

1. Compatibility commit: CLI audit, patch-aware versions, status handling, registry transport, d2c regressions.
2. Feature commit: clean tool and cleanup guidance.
3. Release commit: runtime validation evidence, fixtures, documentation, and version metadata.

Primary risks are lost nonzero-exit status payloads, changed HTTP defaults, and mock tests that do not match the real CLI. Running-runtime validation remains outstanding; planning used only read-only CLI probes and source review.
