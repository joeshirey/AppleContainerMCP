# Apple Container 1.6.0 validation

Date: 2026-10-23. Host: Apple Silicon, macOS 27.0.1 build 26A434. CLI and daemon: 1.6.0.
This is local validation, not certification on every supported macOS/CLI release.

## Upstream changes reviewed (1.5.0 → 1.6.0)

- Security: GHSA-vgrw-36j7-r93w (a pull by digest now verifies that the registry returned the pinned digest) and GHSA-fqxg-rrf3-358v (`container build` could serve files outside the build context when a symlink was swapped during a read).
- New `container commit <id> <reference>`. Wrapped as `commit_container`.
- New `alias=` option on `--network` attachments (exact and leading-dot subtree DNS aliases). Wrapped as `run_container(network_aliases=...)`.
- `container build` and `container builder` are now a CLI plugin. Help text drops the `container` prefix, but subcommands, flags, and `builder status --format json` output are unchanged.
- Machine user extension points were removed upstream. `machine create` still lists the same flags this server passes, and the user options were never exposed.
- Multi-worker `container k8s` clusters and k8s fixes do not affect this server, which does not wrap the Kubernetes plugin.

## Pre-existing bug found during the audit

`create_network` passed `--mtu`, but `container network create` has no such flag in 0.12.0, 1.0.0, 1.2.0, 1.3.0, 1.5.0, or 1.6.0 (checked in upstream source and with the installed CLI). Every call with `mtu` failed with `Unknown option '--mtu'`. Earlier audits only checked that commands exist, not each flag. The parameter is removed. MTU works per attachment: `--network name,mtu=1400` gave eth0 an MTU of 1400 on 1.6.0.

## Changes

- `RECOMMENDED_CLI_VERSION` is now 1.6.0. The `check_environment` recommendation names the new security fixes.
- `commit_container` requires a detectable 1.6.0+ CLI (same pattern as `clean_container`), rejects empty or `-`-prefixed arguments, and uses the long-running timeout.
- `network_aliases` rejects empty aliases and aliases containing `,`, `=`, or whitespace, so they cannot inject other attachment options. It is blocked on a detected CLI older than 1.6.0 and allowed when the version cannot be detected (same pattern as machine `virtualization`). With no `network`, aliases attach to `default`.
- `d2c commit` translates to `container commit`, with a note about the 1.6 requirement and unsupported Docker options.

## Live observations

- `commit` prints the resolved reference (e.g. `docker.io/library/name:tag`). It works on running and stopped containers. A missing container or an invalid reference exits 1 with a clear message.
- The committed image records the container's process as its entrypoint and command (`sh -c ...` became Entrypoint `["sh"]`, Cmd `["-c", ...]`). Running another command needs an `--entrypoint` override. This is documented in the tool docstring.
- Aliases are stored in `inspect` under `configuration.networks[].options.aliases`. With no DNS domain configured, a subtree alias must sit below an exact alias, because the hostname has no domain. Querying the container DNS service (`dig @127.0.0.1 -p 2053`) resolved both the exact alias and a name below the subtree alias, and an unrelated name did not resolve.

## Results

- 56 command help probes (the 54 from the 1.4.1 audit plus `commit` and `machine set-default`) exited successfully on 1.6.0.
- `system status --format json` reports running, with client and server both 1.6.0. Keys are unchanged.
- Unit suite: 359 passed, 94% coverage across `apple_container_mcp` and `d2c`. Ruff lint/format and strict mypy pass.
- Live default smoke script passed. It now also covers network aliases recorded on the attachment, committing a running container, and running the committed image with an entrypoint override to read a file written before the commit. All test resources were cleaned up.
- MCP initialization over stdio: 58 tools registered. `commit_container` and `network_aliases` appear in the schemas, and `create_network` exposes only `name` and `subnet`. `check_environment` reports 1.6.0 with no recommendation.

The optional `--registry` smoke check was not re-run. Alias resolution from the Mac's resolver was not tested because that needs `sudo container system dns create`.
