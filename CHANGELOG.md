# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.5.0] - 2026-07-29

### Added

- Apple Container 1.2 support, validated against the installed 1.2.0 binary. The
  minimum supported CLI version remains 1.0.0; 1.2 introduced no breaking changes.
- `system_df` tool wrapping `container system df`. Reports per-category disk usage
  (images, containers, volumes) with reclaimable byte counts, so cleanup decisions
  are informed rather than blind. `("system", "df")` added to the `--format json`
  allowlist after verifying the output shape on 1.2.0.
- `system_logs` tool wrapping `container system logs --last <window>`. Reads logs
  from the `container` system services rather than from a single container, for
  diagnosing a daemon that will not start. Always non-streaming (`--follow` would
  block until the subprocess timeout killed it), and `last` is validated against
  `^\d+[mhd]?$` so no extra tokens can be smuggled into the argument list.
- `check_environment` now reports the full `major.minor` version and recommends
  upgrading when the installed CLI predates 1.2. This is an advisory only — the
  hard version gate is unchanged.
- Documentation for the `d2c` Docker translator, which shipped without any. The
  README gains a usage section (dry-run, translated command coverage, unsupported
  commands, global-flag handling); docs/PRD.md gains problem framing and
  requirements DR1–DR4; docs/TDD.md gains a module breakdown and the rationale
  behind the design decisions that are easy to undo by accident — checking
  `UNSUPPORTED` before translating, stopping global-flag scanning at the first
  positional, and defaulting the confirmation prompt to no.

### Fixed

- `d2c` translated `docker rmi` to `container image remove`, which is not a
  subcommand; the CLI spells it `image delete` (alias `rm`) and rejected the call
  with "2 unexpected arguments". The test asserted the broken mapping, so it never
  went red. The MCP server's own `remove_image` tool was always correct.

### Security

- `--kernel-arg` (new in Apple Container 1.2) added to the `args_override`
  blocklist. It appends raw arguments to the guest kernel command line, so a value
  like `init=/bin/sh` subverts the VM before any container process starts. Same
  class as `--kernel`, which was already blocked. It is also not exposed as a tool
  parameter.

### Notes

- The 1.1 → 1.2 CLI delta contains exactly one new user-facing flag, `--kernel-arg`
  on `run` and `create`. Everything else in the release is Swift API work (OCI
  `maskedPaths` / `readonlyPaths`), upstream hardening (XPC container-ID
  validation, kernel archive integrity, no symlink following when copying user
  configuration), and test infrastructure.
- Every existing `--format json` allowlist entry was re-run against the 1.2.0
  binary and still emits parseable JSON. The version-probe regex still matches
  1.2.0's `container CLI version 1.2.0` output.
- The `args_override` blocklist is defense in depth, not the only barrier.
  `args_override` is appended after the image name, and the CLI parses post-image
  tokens as container init-process arguments rather than `run` options — verified
  by observing that `container run <image> --totallyfakeflag` reaches image fetch
  instead of erroring on an unknown option. The blocklist stays because that
  positional behaviour is an undocumented implementation detail. The README and
  docs/TDD.md now say so rather than implying the blocklist is load-bearing.
- `system kernel set` and `system dns create` / `delete` remain unexposed: the
  first is the `--kernel` vector again, the second requires administrator rights.

## [0.4.0] - 2026-07-14

### Added

- Apple Container 1.1 support (validated against the 1.1.0 command reference and
  release notes; the minimum supported CLI version remains 1.0.0 — 1.1 introduced
  no breaking changes).
- Nested virtualization on container machines: `virtualization` parameter on
  create_machine (`--virtualization`) and set_machine (`virtualization=<bool>`).
  Both are version-gated with a clear error when the installed CLI is older
  than 1.1. Requires Apple Silicon M3+, macOS 15+, and a guest kernel built
  with CONFIG_KVM=y.
- CLI version probe now captures (major, minor) so tools can gate on minor
  releases.

### Changed

- copy_to_container / copy_from_container resolve host paths to absolute paths
  (realpath) before invoking `container cp`, sidestepping the 1.0.0 CLI bug with
  relative host paths (fixed upstream in 1.1.0).

### Notes

- The 1.1 kernel override (`machine create --kernel`, `machine set kernel=`) is
  deliberately NOT exposed: loading an arbitrary host path as guest kernel code
  is the same privilege-escalation vector as run's `--kernel`, which remains
  blocklisted. See docs/TDD.md "Security Model".
- `--stop-signal` is still absent from `container run` in the 1.1.0 binary's
  command reference; it remains unexposed.
- The full 1.0 → 1.1 CLI delta was audited via the command-reference diff; the
  machine virtualization/kernel options are the only additions. All other 1.1.0
  changes are behavioral fixes (unix socket mounts in non-root containers,
  cp relative paths, exec empty-argument crash).

## [0.3.0] - 2026-06-09

### Added

- Apple Container 1.0 support; minimum CLI version raised to 1.0.0.
- `container machine` tool suite: create_machine, run_machine, list_machines,
  inspect_machine, set_machine, set_default_machine, machine_logs, stop_machine,
  delete_machine.
- File transfer tools: copy_to_container, copy_from_container (host paths restricted
  to the home directory in both directions).
- `system_property_list` tool (replaces the removed `system property get`/`set`).
- `check_environment` tool and a version warning on `system_version`.
- `--shm-size` option on run_container.
- Cached CLI version probe with a clear error when the binary is missing and a soft
  warning when the major version is below 1.0.

### Changed

- Minimum supported Apple Container CLI is now 1.0.0 (the 1.0 daemon dropped XPC v0
  compatibility, so older clients cannot interoperate).
- Extracted a shared home-directory path-validation helper used by run_container,
  build_image, and the cp tools.

### Notes

- `--stop-signal` was listed in the 1.0 release notes but is not present on
  `container run` in the 1.0.0 binary; it is not exposed.
- Structured (ls/inspect) output shapes were re-validated against 1.0; JSON is still
  passed through to clients unchanged.

## [0.2.0] - 2026-04-28

Apple Container 0.12 support.

### Added

- `system_version` tool wrapping `container system version` (Apple Container 0.12+). Returns CLI and apiserver versions as a JSON array. Works without the daemon, so it can serve as a lightweight environment probe before issuing commands that require the daemon.
- `stats_container` tool wrapping `container stats --no-stream` (Apple Container 0.12+). Returns a one-shot resource-usage snapshot for one or more containers. Always non-streaming to fit the request/response model.
- JSON output allowlist (`cli_wrapper.FORMAT_JSON_COMMANDS`) expanded with `("system", "version")`, `("system", "status")`, `("builder", "status")`, and `("stats",)` — all verified in the 0.12 CLI audit.
- Regression tests for `--cap-drop`, `--kernel` (long and short forms), and `--ssh` blocked from `args_override`.

### Changed

- Minimum required Apple Container CLI version is now **0.12.0**.
- `export_container` documentation no longer references version-specific behavior; the OCI-layout tar export is stable across 0.11 and 0.12.
- `cli_wrapper.FORMAT_JSON_COMMANDS` no longer contains `("builder", "ls")` — that subcommand does NOT exist in 0.12 (`container builder` only has `start`/`status`/`stop`/`delete`). The previous "if supported" hedge resolved to "not supported" and the dead entry was removed.
- Package version bumped from `0.1.0` to `0.2.0`.

### Security

- `--cap-add` and `--cap-drop` (promoted to documented public flags in Apple Container 0.12) are intentionally **not** exposed as tool parameters and remain blocked from `run_container(args_override=…)`. Capability selection meaningfully weakens process isolation; this MCP treats it as advanced configuration that should be applied via the CLI directly when truly needed. See the README's Security Model section.
- Two additional `container run` flags surfaced by the 0.12 CLI audit are now blocked from `args_override`:
  - `--kernel` / `-k`: allows specifying an arbitrary host filesystem path as the guest VM kernel — a privilege-escalation vector.
  - `--ssh`: forwards the host SSH agent socket into the container — a credential-leak vector that any process inside the container could use silently.

### Investigated and deferred

These items appeared in the original 0.12 release notes but, per the CLI audit, are not actually present as documented public surfaces in the installed `container 0.12.0` CLI. They are deferred to a future release once Apple exposes them as first-class flags or subcommands:

- `--journal` for `container volume create`. The 0.12 release notes mention a journal option, but `container volume create --help` shows only `--label`, `--opt`, `-s`, `--debug`. The closest available mechanism is the generic `--opt`, which would require separate verification before being surfaced as a typed parameter.
- `container restart`, `container pause`, `container unpause`, `container rename`, `container events`, `container cp`, `container history`. Each returns `Plugin '<name>' not found` in 0.12.0.
