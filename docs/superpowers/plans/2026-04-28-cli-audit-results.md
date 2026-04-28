# Apple Container 0.12 CLI Audit Results

Run on: 2026-04-28
Installed CLI version: `container CLI version 0.12.0 (build: release, commit: unspeci)`

All findings below are derived from running the installed `container` 0.12.0 CLI on macOS (Darwin, arm64) with the daemon running, except where noted (Section B explicitly tests daemon-down behavior).

## A. JSON allowlist candidates

| Command | `--format json` supported? | Parses as JSON? | Add to `FORMAT_JSON_COMMANDS`? |
|---|---|---|---|
| `container system version` | yes | yes | **yes** |
| `container system status` | yes | yes | **yes** |
| `container builder ls` | **no** (subcommand does not exist in 0.12) | n/a | **no** — entry must be REMOVED from the existing allowlist |
| `container builder status` | yes | yes (when builder is running) | **yes** |
| `container inspect <id>` | n/a — `--format` flag is not exposed; output is JSON-by-default | yes | N/A — already JSON-by-default; no allowlist entry needed |

Notes / evidence:

- `container system version --help` shows `--format <format>` accepting `json|table|yaml` (default: `table`). Sample output: `[{"appName":"container","buildType":"release","version":"0.12.0","commit":"unspecified"},{"buildType":"release","version":"container-apiserver version 0.12.0 ...","appName":"container-apiserver","commit":"unspecified"}]`. Parses cleanly.
- `container system status --format json` returns a single JSON object (top-level keys: `apiServerBuild`, `appRoot`, `apiServerCommit`, `installRoot`, `status`, `apiServerVersion`, `apiServerAppName`). Parses cleanly.
- `container builder ls` does NOT exist in 0.12. `container builder --help` lists only `start`, `status`, `stop`, `delete`. Running `container builder ls --format json` errors with `Error: Unknown option '--format'` (because `ls` is being interpreted as an unknown positional). The existing `("builder", "ls")` entry in `FORMAT_JSON_COMMANDS` is dead code — it cannot match a real invocation since no tool issues `container builder ls`.
- `container builder status --format json` returns a JSON array with the builder's full configuration and network details when the builder is running. When the builder is NOT running it instead emits the plain-text string `builder is not running` (NOT JSON), regardless of `--format`. Tools calling this must tolerate that string fallback or pre-check status.
- `container inspect <id>` has no `--format` option in its `--help`; the output is JSON by default. The existing wrapper handles this as a special case (see `cli_wrapper.py:97-98`); no allowlist entry is required or possible.

For each "yes/yes" row above, the `cli_wrapper.FORMAT_JSON_COMMANDS` set must gain the corresponding tuple. The `("builder", "ls")` entry must be removed (and its hedge comment with it) since the subcommand does not exist.

## B. system version

- Subcommand exists: **yes** (`container system version`).
- Requires daemon to be running: **no**. Verified by stopping the daemon (`container system stop`), then running `container system version --format json` — exit 0, output `[{"buildType":"release","commit":"unspecified","version":"0.12.0","appName":"container"}]`. With the daemon down the response degrades gracefully: only the CLI's own version object is returned (no `container-apiserver` element). With the daemon up, both elements are present.
- Sample JSON output keys (top-level): the response is a JSON **array** (not an object). Each array element has the keys: `appName`, `buildType`, `version`, `commit`. Element 0 is always `appName=container` (the CLI). Element 1 (present only when the daemon is running) is `appName=container-apiserver`.
- The daemon's running state was preserved at the end of this audit (it was up before, was stopped only for the daemon-down test, then restarted with `container system start` and re-verified via `container system status`).

This means `system_version` MAY be invoked without the daemon — its docstring should reflect that explicitly (so callers can use it as a lightweight environment probe before issuing `system_status`).

## C. volume create --journal

**Finding contradicts the spec/plan assumption.** Apple Container 0.12.0's `container volume create` does NOT expose a `--journal` flag.

Full `container volume create --help` output:

```
OVERVIEW: Create a new volume

USAGE: container volume create [--label <label> ...] [--opt <opt> ...] [-s <s>] [--debug] <name>

ARGUMENTS:
  <name>                  Volume name

OPTIONS:
  --label <label>         Set metadata for a volume
  --opt <opt>             Set driver specific options
  -s <s>                  Size of the volume in bytes, with optional K, M, G,
                          T, or P suffix
  --debug                 Enable debug output [environment: CONTAINER_DEBUG]
  --version               Show the version.
  -h, --help              Show help information.
```

Specifically:

- Flag spelling: **N/A — no `--journal` flag is exposed.**
- Position relative to volume name: **N/A.**
- Default behavior (when flag omitted): **N/A.**
- Closest mechanism: `--opt <opt>` ("Set driver specific options"). Whether the local driver accepts an option named `journal` (e.g., `--opt journal=true`) is not documented in `--help` and was not exercised in this audit because (a) it would be guesswork, and (b) any such option's exact spelling and default behavior would still need separate verification before being surfaced as a typed parameter.

**Implication for Task 7 (`Add journal parameter to create_volume`):** The originally planned implementation (append `--journal` when `journal=True`) cannot ship as written. Options for the spec author to choose between:

1. Drop the `journal` parameter from this release entirely — the underlying CLI flag does not exist.
2. Implement `journal` as a thin pass-through over `--opt journal=...` after explicitly verifying with `container volume inspect` that the option is honored by the local driver. This requires an additional small audit step before Task 7 can proceed.
3. Defer the parameter until a future Apple Container release exposes a first-class flag.

This finding should be flagged to the spec/plan owner before Task 7 starts.

## D. Gap-fill tool candidates — definitive existence check

Each row was verified by running `container <subcommand> --help`. "Plugin not found" responses are definitive non-existence (the CLI auto-discovers plugins from `libexec/container-plugins/<name>` and `libexec/container/plugins/<name>`; both paths are empty for the missing names).

| Subcommand | Exists in 0.12? | Has bounded (non-streaming) form? | Include in plan? |
|---|---|---|---|
| `container restart` | **no** (`Plugin 'container-restart' not found`) | n/a | **no** |
| `container pause` | **no** (`Plugin 'container-pause' not found`) | n/a | **no** |
| `container unpause` | **no** (`Plugin 'container-unpause' not found`) | n/a | **no** |
| `container stats` | **yes** (top-level subcommand, listed in `container --help`) | yes — `--no-stream` flag | **yes** |
| `container events` | **no** (`Plugin 'container-events' not found`) | n/a | **no** |
| `container rename` | **no** (`Plugin 'container-rename' not found`) | n/a | **no** |
| `container cp` | **no** (`Plugin 'container-cp' not found`) | n/a | **no** |
| `container history` | **no** (`Plugin 'container-history' not found` at top level; also no `container image history` subcommand — `container image --help` lists only `delete/inspect/list/load/prune/pull/push/save/tag`) | n/a | **no** |

Only **one** gap-fill candidate (`stats`) is actually present in 0.12.0. Detail for the included tool:

### `container stats`

Full `--help`:

```
OVERVIEW: Display resource usage statistics for containers

USAGE: container stats [<containers> ...] [--format <format>] [--no-stream] [--debug]

ARGUMENTS:
  <containers>            Container ID or name (optional, shows all running
                          containers if not specified)

OPTIONS:
  --format <format>       Format of the output (values: json, table, yaml;
                          default: table)
  --no-stream             Disable streaming stats and only pull the first result
  --debug                 Enable debug output [environment: CONTAINER_DEBUG]
```

- Exact CLI invocation form for the MCP tool: `container stats --no-stream --format json [<container> ...]`.
- Required flags: `--no-stream` is REQUIRED for the MCP wrapper (the streaming default would block the subprocess indefinitely). `--format json` is required for parseable output.
- Optional positional: zero or more container IDs / names. With none supplied, the CLI returns stats for all running containers. The MCP tool should accept `containers: Optional[List[str]] = None` and only append IDs if provided.
- Non-streaming flag spelling: **`--no-stream`** (boolean, no value).
- Allowlist consequence: `("stats",)` should be added to `FORMAT_JSON_COMMANDS` IF the wrapper is used with no explicit `--format` argument. However, since the implementation will pass `--format json` and `--no-stream` explicitly (because the bare `container stats` default streams), it is **not strictly required** for the allowlist — but adding it is harmless and consistent with the existing pattern (`("ls",)`, `("image", "ls")`, etc.) and makes ad-hoc CLI passthrough usage safe too. **Recommendation: include `("stats",)` in `FORMAT_JSON_COMMANDS` for consistency.**

## E. Other 0.12 changes worth noting

### `container run --help` flags vs. what we already pass through

Observed full flag set, grouped:

- **Process options:** `-e/--env`, `--env-file`, `--gid`, `-i/--interactive`, `-t/--tty`, `-u/--user`, `--uid`, `-w/--workdir/--cwd`, `--ulimit`.
- **Resource options:** `-c/--cpus`, `-m/--memory`.
- **Management options:** `-a/--arch`, `--cap-add`, `--cap-drop`, `--cidfile`, `-d/--detach`, `--dns`, `--dns-domain`, `--dns-option`, `--dns-search`, `--entrypoint`, `--init`, `--init-image`, `-k/--kernel`, `-l/--label`, `--mount`, `--name`, `--network`, `--no-dns`, `--os`, `-p/--publish`, `--platform`, `--publish-socket`, `--read-only`, `--rm/--remove`, `--rosetta`, `--runtime`, `--ssh`, `--tmpfs`, `--virtualization`, `-v/--volume`.
- **Registry options:** `--scheme`.
- **Progress options:** `--progress`.
- **Image fetch options:** `--max-concurrent-downloads`.

Security-sensitive flags worth attention:

- **`--cap-add` / `--cap-drop`:** Already in `_DANGEROUS_FLAGS`. The spec/plan (Task 4) deliberately keeps them blocked — confirmed correct: 0.12 still exposes them and they remain capability-grant primitives.
- **`--runtime`:** Allows selecting an alternate container runtime handler (e.g. away from `container-runtime-linux`). This is a privilege/sandbox-relevant escape hatch — consider adding to `_DANGEROUS_FLAGS` for the same rationale as capabilities.
- **`-k/--kernel`:** Allows specifying an arbitrary kernel image path on the host. This is a high-trust input (a host path the daemon will load as a kernel) — strong candidate for `_DANGEROUS_FLAGS`.
- **`--init-image`:** Custom init image — supply-chain sensitive (can replace the pid-1 process inside the container with arbitrary OCI content). Worth considering for `_DANGEROUS_FLAGS`, though arguably less severe than `--kernel` since it runs inside the guest sandbox.
- **`--virtualization`:** Exposes virtualization capabilities to the container (nested virt). Noted but not obviously a privilege-escalation vector at the host level; left as a recommendation only.
- **`--ssh`:** Forwards the host SSH agent socket into the container. Credential-leak vector — strong candidate for `_DANGEROUS_FLAGS` (or at minimum a documented warning).
- **`--mount` / `-v/--volume` / `--tmpfs`:** Already supported by the existing wrapper logic via the typed `mounts`/`volumes` parameters. Not in `_DANGEROUS_FLAGS` — consistent with existing policy that typed bind/volume mounts are exposed but raw passthrough strings still go through arg-validation.
- **`--publish-socket`:** New in the observed surface (publishes a host UNIX socket into the container). Bind-mount-of-socket semantics are similar to volumes; not obviously dangerous but worth a follow-up tracking note.

### `container build --help`

Full observed flags: `-a/--arch`, `--build-arg`, `-c/--cpus`, `-f/--file`, `-l/--label`, `-m/--memory`, `--no-cache`, `-o/--output`, `--os`, `--platform`, `--progress`, `-q/--quiet`, `--secret`, `-t/--tag`, `--target`, `--vsock-port`, `--debug`, `--dns`, `--dns-domain`, `--dns-option`, `--dns-search`, `--pull`.

Notable items:

- `--secret` (`id=<key>[,env=<ENV_VAR>|,src=<local/path>]`) — secret material can be sourced from env vars or arbitrary local paths. Not an obvious _privilege_ escalation but a credential-handling surface. Not flagged for `_DANGEROUS_FLAGS`; should be documented if/when build secrets are surfaced.
- `--vsock-port` — internal builder shim communication; no security concern.
- `--pull` — toggles "always pull latest". Behavior change vector but not dangerous.
- No `--cap-add`/`--cap-drop` on build (unlike `run`); no new cap-related surface.

## Summary: actionable inputs to subsequent tasks

- **`FORMAT_JSON_COMMANDS` additions:** `("system", "version")`, `("system", "status")`, `("builder", "status")`, `("stats",)` (the last one is recommended-not-required; see §D).
- **`FORMAT_JSON_COMMANDS` removals:** `("builder", "ls")` — subcommand does not exist in 0.12 (resolves the existing `# if supported` hedge by removing the entry entirely).
- **`("builder", "ls")` hedge resolution:** **remove** the entry and its comment.
- **`system_version` requires daemon:** **no** (works without the daemon; returns CLI-only info when the daemon is down). Docstring should call this out so it can be used as a lightweight environment probe.
- **Journal flag spelling:** **does not exist in 0.12.** Section C above documents the discrepancy; Task 7 cannot proceed as originally written. Spec/plan owner must decide between dropping the parameter, implementing it via `--opt`, or deferring.
- **Gap-fill tools to implement:** **`stats_container`** (or whatever name aligns with the existing naming convention) only. The plan's other candidates (`restart`, `pause`, `unpause`, `events`, `rename`, `cp`, `history`) are NOT in 0.12.0 and must be dropped from the plan. Tasks 6 and any plan/spec references to those tools need a corresponding revision.
- **New `_DANGEROUS_FLAGS` additions (recommended):**
  - `--kernel` / `-k` — host kernel-path injection.
  - `--runtime` — alternative runtime handler.
  - `--ssh` — host SSH-agent forwarding (credential leak).
  - `--init-image` — supply-chain risk for the container's pid-1 image.
  
  Adding any of these is out of scope for this audit task; raised here so the spec author can decide whether to expand Task 4's scope.
