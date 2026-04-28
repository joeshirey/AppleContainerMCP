# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

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
