# Design: Apple Container 0.12 Support Update

**Date:** 2026-04-28
**Target package version:** `0.2.0`
**Target Apple Container CLI version:** `0.12.0` (released 2026-04-27)
**Status:** Approved (pending implementation plan)

## 1. Background

AppleContainerMCP is a Python MCP server (FastMCP-based) that wraps Apple's
`container` CLI as a set of MCP tools, prompts, and resources. The project
currently targets **Apple Container 0.11.0**: the README declares
`Tested with **v0.11.0**`, the `export_container` tool's docstring says
`Requires an output_file path in 0.11.0`, and the most recent feature commit
(`13c4620`) is titled "update tools and docs for Apple Container CLI v0.11.0".

Apple released `container 0.12.0` on 2026-04-27. This spec defines the changes
required for AppleContainerMCP to support 0.12.

## 2. Goals

1. AppleContainerMCP works correctly with `container 0.12.0` and is documented
   as requiring 0.12.0 or later.
2. New 0.12 surfaces (the `system version` subcommand, the `--journal` flag on
   `volume create`, and any verified-existing subcommands not previously
   exposed) are accessible as MCP tools, with the same standardized
   `{"status": "ok"|"error", ...}` return shape used everywhere else.
3. Existing security guarantees are preserved or strengthened — in particular,
   the new Linux capability flags (`--cap-add`, `--cap-drop`) introduced in
   0.12 remain blocked from `args_override` and are not exposed as tool
   parameters.
4. Documentation (README, PRD, TDD, CHANGELOG) accurately reflects the new
   target version and the rationale for security choices.

## 3. Non-goals (deferred to future specs)

- Exposing `--cap-add` / `--cap-drop` as tool parameters. (Deliberate
  security choice — see §6.3.)
- YAML output support (`--format yaml`). The MCP returns structured Python
  dicts to LLMs from JSON output; YAML adds a dependency for no consumer
  benefit.
- Streaming build / pull / push progress. The new `plain`/`color` progress
  modes in 0.12 are useful for live UIs but our async build state machine
  captures stdout in bulk on completion. Refactoring to incremental progress
  is a separable, larger change.
- Runtime version detection / hard version gate. Documented minimum is
  sufficient.
- Comprehensive coverage of every `container` subcommand. Only verified
  gap-fill candidates that exist in 0.12 and are clearly useful are added
  here.

## 4. Apple Container 0.12 changes relevant to this MCP

Drawn from the [0.12.0 release notes](https://github.com/apple/container/releases/tag/0.12.0):

| 0.12 change | Impact on this MCP |
|---|---|
| `--cap-add` / `--cap-drop` for `container run` (#1260, #1383) | Deliberately not exposed. Capabilities remain in `_DANGEROUS_FLAGS` blocklist. Documented as a security choice. |
| Consolidated `--format` handling (#1385) + YAML format (#1156) | JSON-only stance retained; allowlist audited and expanded where 0.12 newly supports `--format json`. |
| `container system version` with `--format` (#1353) | New tool: `system_version`. |
| `plain` / `color` progress, plain auto-selected when stderr is not TTY (#1365, #1366, #113) | No code change needed — our subprocess invocation has no TTY, so 0.12 auto-selects `plain`, naturally producing cleaner build logs. |
| `--journal` for `container volume create` (#1411) | New parameter `journal: bool = False` on `create_volume`. |
| Builder API → grpc-swift-2 (#1416) | Internal protocol change. Affects users mid-upgrade only — no MCP code change. Documented as a minimum-version requirement. |
| TOML plugin configs (#1422) | Internal — no MCP impact. |
| `container stop` no longer has XPC timeout coupled to SIGTERM (#1387) | Existing `stop_container` benefits with no change. |
| Single-file mounts, `ARG` parsing, archive write under `/Users/`, `SSH_AUTH_SOCK` propagation fixes | Reliability improvements for existing tools. No code change. |

## 5. Scope

### In scope

1. **Documentation refresh.** Bump all "0.11.0" references to "0.12.0";
   update README minimum version; remove the version-specific qualifier on
   `export_container` (the OCI-tar export behavior is now stable across
   0.11+).
2. **New tool `system_version`** in `tools/system.py`, wrapping
   `container system version --format json`.
3. **New parameter `journal: bool = False`** on `create_volume` in
   `tools/volumes.py`, appending `--journal` when true.
4. **JSON allowlist audit and expansion** in `cli_wrapper.py`. At minimum
   adds `("system", "version")`. Other commands (`("system", "status")`,
   `("inspect",)`, `("builder", "ls")`, `("builder", "status")`) are added
   only if verified in §7 to support `--format json` against installed
   0.12. The current "if supported" hedge comment on `("builder", "ls")` is
   resolved (kept or removed per audit results).
5. **Subcommand gap-fill, audit-driven.** Tools added for 0.12 subcommands
   from the candidate set `{stats, events, restart, pause, unpause, rename,
   cp, history}` that (a) actually exist in installed 0.12 and (b) fit the
   capture-and-return subprocess model (i.e., have a non-streaming form).
6. **Capabilities security note.** Code comment in `tools/__init__.py` near
   `_DANGEROUS_FLAGS` and a Security Model section in `README.md` and
   `docs/TDD.md` documenting the deliberate omission.
7. **Package version bump** `0.1.0` → `0.2.0` in `pyproject.toml` and
   `src/apple_container_mcp/__init__.py`.
8. **Tests.** Unit tests for every new tool / parameter; allowlist tests
   for new entries; security regression tests confirming `--cap-add` and
   `--cap-drop` remain rejected via `args_override`.
9. **`CHANGELOG.md`** (new file, Keep-a-Changelog format) documenting the
   0.12 update.

### Out of scope

Listed in §3.

## 6. Design

### 6.1 Architectural impact

**None.** The existing modular layout in `src/apple_container_mcp/tools/`
already cleanly accommodates these additions: each new tool is a single
decorated function in the appropriate domain module, and the wrapper changes
are confined to one tuple-set in `cli_wrapper.py`.

### 6.2 File-level change list

| File | Change |
|---|---|
| `README.md` (line 18) | `Tested with **v0.11.0**` → `Requires **v0.12.0 or later**`. Add Security Model subsection. List new tools and the `journal` parameter. |
| `docs/PRD.md` | Mention `system_version` under FR1 (System); `journal` under FR4 (Networks/Volumes); each verified gap-fill tool under the appropriate FR. |
| `docs/TDD.md` | Update Tool Mapping table (new rows; remove "in 0.11.0" qualifier on `export_container`); update `FORMAT_JSON_COMMANDS` listing; add Security Model bullet on capabilities. |
| `CHANGELOG.md` (new) | `[0.2.0]` heading per Keep-a-Changelog. Template in §6.5. |
| `pyproject.toml` | `version = "0.2.0"`. |
| `src/apple_container_mcp/__init__.py` | `__version__ = "0.2.0"`. |
| `src/apple_container_mcp/cli_wrapper.py` | Expand `FORMAT_JSON_COMMANDS` per §7 audit. No other logic changes. |
| `src/apple_container_mcp/tools/system.py` | Add `system_version` tool. |
| `src/apple_container_mcp/tools/volumes.py` | Add `journal: bool = False` parameter to `create_volume`. |
| `src/apple_container_mcp/tools/containers.py` | Add gap-fill tools verified to exist in 0.12 (final list per §7). |
| `src/apple_container_mcp/tools/__init__.py` | Comment near `_DANGEROUS_FLAGS` documenting deliberate capabilities omission. No code change to the set itself. |
| `tests/test_tools.py` | Tests for each new tool / parameter; assert capabilities flags still rejected via `args_override`. |
| `tests/test_cli_wrapper.py` | Tests asserting newly-allowlisted commands receive `--format json`. |

### 6.3 Capability flags policy (security)

`--cap-add` and `--cap-drop` are listed in `_DANGEROUS_FLAGS`
(`tools/__init__.py:27-40`). They were already rejected from `args_override`
before 0.12 because they did not exist as documented public flags; under
0.12 they remain rejected by deliberate choice. Rationale:

- Capabilities meaningfully weaken process isolation. Even apparently
  innocuous additions (e.g., `NET_RAW`, `SYS_PTRACE`) expand attack surface.
- Selecting an appropriate capability set is workload-specific configuration
  that does not generalize well to LLM-driven invocation.
- Users with a legitimate need can use `container run` directly. The MCP
  does not need to be a complete CLI replacement.

A code comment in `tools/__init__.py` will document this rationale; the
README and TDD will carry the user-facing version of the same note.

### 6.4 Tool specifications

#### 6.4.1 `system_version` (system.py)

```python
@mcp.tool()
def system_version() -> Dict[str, Any]:
    """Return version info for the Apple Container CLI, builder, kernel,
    and containerization library.

    Returns:
        On success: {"status": "ok", "version": <parsed JSON>}
        On error:   {"status": "error", "message": str, "exit_code": int}
    """
```

- Adds `("system", "version")` to `FORMAT_JSON_COMMANDS`.
- Useful for diagnostics and for the `troubleshoot_container` prompt
  (which can include version info in its rendered context).

#### 6.4.2 `create_volume` extended (volumes.py)

```python
@mcp.tool()
def create_volume(
    name: str,
    size: Optional[str] = None,
    journal: bool = False,
) -> Dict[str, Any]:
```

- When `journal=True`, append `--journal` to the args list. Exact flag
  syntax (`--journal` vs. `--journal=true`) is verified in §7.
- Default `False` preserves current behavior — strictly additive.
- Docstring notes that journaling is recommended for write-heavy or
  crash-sensitive workloads (databases) at a small write-amplification cost.

#### 6.4.3 Gap-fill tools — final list determined by §7 audit

Likely candidates and their proposed signatures *if they exist in 0.12*:

| Tool | CLI invocation | Destructive? | Notes |
|---|---|---|---|
| `restart_container(container_id)` | `container restart <id>` | no (state transition only) | |
| `pause_container(container_id)` | `container pause <id>` | no | |
| `unpause_container(container_id)` | `container unpause <id>` | no | |
| `stats_container(container_id=None)` | `container stats --no-stream [<id>]` | no | Requires non-streaming form to fit subprocess model. Skip if `--no-stream` (or equivalent) is unsupported. |
| `events(since=None, until=None, limit=100)` | `container events --since X --until Y` | no | Same constraint — must be a bounded query, not an indefinite stream. Skip if not supported. |
| `rename_container(container_id, new_name)` | `container rename <id> <name>` | no | |
| `container_history(image)` | `container history <image>` | no | |

All tools follow existing conventions: `@mcp.tool()` decorator, standardized
return shape, input validation matching peers (e.g., empty-string ID checks),
full happy-path + error-path test coverage.

### 6.5 CHANGELOG.md template

Keep-a-Changelog format. Date and the angle-bracketed lists below are
placeholders to be filled in during implementation, after the §7 audit
determines the final list of tools and allowlist commands.

```
# Changelog

All notable changes to this project will be documented in this file. The
format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.2.0] - YYYY-MM-DD

### Added
- `system_version` tool (requires Apple Container 0.12+)
- `journal` parameter on `create_volume`
- <verified gap-fill tools>
- Expanded JSON output allowlist for <verified commands>

### Changed
- Minimum Apple Container CLI version is now 0.12.0
- `export_container` documentation no longer references version-specific
  behavior

### Security
- `--cap-add` and `--cap-drop` (introduced in container 0.12) are
  intentionally not exposed as tool parameters and remain blocked from
  `args_override` overrides
```

## 7. CLI verification gate

Before any implementation, the installed `container 0.12.0` is queried to
convert assumptions into facts. The following commands are run and their
output recorded as inputs to the implementation plan:

```
container --version
container --help
container system --help
container system version --help
container system version --format json
container system status --format json
container builder ls --format json
container builder status --format json
container inspect --help
container volume create --help
container stats --help
container events --help
container restart --help
container pause --help
container unpause --help
container rename --help
container cp --help
container history --help
container run --help
container build --help
```

Audit results determine three concrete decisions:

1. The final additions to `FORMAT_JSON_COMMANDS`.
2. The final list of gap-fill tools to add (only verified-existing,
   subprocess-compatible ones).
3. The exact flag names / syntax for new options (e.g., the precise spelling
   of the journal flag).

This audit is the first task in the implementation plan; its outputs feed
the rest of the plan.

## 8. Testing strategy

Follows existing patterns in `tests/test_tools.py` (1230 lines, full per-tool
coverage with mocked `_run_container_cmd`) and `tests/test_cli_wrapper.py`
(unit tests for the wrapper).

### Unit tests for new tools (`tests/test_tools.py`)

- `test_system_version_success` — mocks `_run_container_cmd` to return version
  JSON; asserts return shape.
- `test_system_version_error` — mocks `ContainerCLIError`; asserts standard
  error return shape.
- `test_create_volume_with_journal` — asserts `--journal` is appended when
  `journal=True`.
- `test_create_volume_without_journal` — asserts no `--journal` when default.
- For each verified gap-fill tool: happy path + error path + input-validation
  tests (empty `container_id`, missing required args).

### Wrapper tests (`tests/test_cli_wrapper.py`)

- For each new entry in `FORMAT_JSON_COMMANDS`: assert `--format json` is
  appended to that command's args.
- Existing negative-case tests (commands not in allowlist don't get
  `--format json`) continue to pass unchanged.

### Security regression tests (`tests/test_tools.py`)

- `test_args_override_rejects_cap_add` — confirm `--cap-add` rejected via
  `run_container(args_override=[...])`.
- `test_args_override_rejects_cap_drop` — same for `--cap-drop`.

### Manual smoke test (documented in plan, not automated)

Against an actual installed `container 0.12`:
1. Start the MCP server.
2. Invoke `system_version` and verify the output.
3. Invoke `create_volume name=test-journal journal=True`; verify the volume
   was created with journaling (e.g., via `container volume inspect`).
4. Invoke one verified gap-fill tool end-to-end.

### Coverage target

Maintain or improve the existing `pytest --cov` percentage. New code targets
≥ 90% line coverage.

## 9. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Audit (§7) reveals fewer commands support `--format json` than expected. | Allowlist remains conservative — only add what works. Document the limitation. |
| A gap-fill subcommand exists but only as a streaming command (e.g., `stats`, `events`) without a bounded form. | Skip exposing it. Stream handling is out of scope per §3. |
| User has only `container 0.11` installed and runs the new MCP. | README requires 0.12+. New-only commands will surface as `ContainerCLIError` with the existing daemon-down-style normalization improving the error UX. Acceptable failure mode given the documented requirement. |
| `--journal` flag changes semantics in a future release. | Default remains `False` (current behavior). Easy to update the docstring without breaking callers. |
| Capabilities decision is reversed later. | The blocklist removal is a one-line change. Adding parameter exposure is straightforward additive work in a follow-up spec. No design lock-in. |

## 10. Acceptance criteria

The update is complete when:

- All "0.11.0" references in code and docs are updated to "0.12.0".
- `system_version`, `create_volume(journal=...)`, and all verified gap-fill
  tools are implemented with full test coverage and standardized return
  shapes.
- `FORMAT_JSON_COMMANDS` is expanded per the §7 audit results.
- `_DANGEROUS_FLAGS` carries the documenting comment about capabilities;
  README and TDD carry the user-facing version.
- `CHANGELOG.md` exists with a `[0.2.0]` entry.
- `pyproject.toml` and `src/apple_container_mcp/__init__.py` show
  `version = "0.2.0"`.
- `pytest` passes; `pytest --cov` shows no regression in coverage.
- `ruff` and `mypy` pass per the project's existing CI configuration.
- Manual smoke test against `container 0.12` succeeds.
