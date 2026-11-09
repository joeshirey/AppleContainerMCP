# Repository Review Pitfalls

Record concise, generalizable lessons caught during Gate 2 test audits, Gate 4 adversarial pull request reviews, and Gate 5 human reviews so future workers avoid repeating them.

Keep each bullet grounded in an area prefix (`[area:<name>]`) and state what to check or do instead.

## Architecture and Contracts
- `[area:contracts]` When adding configuration keys or schema fields, update starter templates and contract tests in the same commit rather than leaving defaults implicit.
- `[area:cli_wrapper]` Preserve `"daemon is not running"` in `_run_container_cmd` daemon/plugin error normalization strings because `check_apiserver_status` in `tools/system.py` matches `daemon_indicators` against `str(e)`.
- `[area:version]` Keep package version synchronized across `pyproject.toml`, `src/apple_container_mcp/__init__.py`, and `uv.lock` (`uv lock`) on release bumps.

## Testing and Falsifiability
- `[area:tests]` Assert observable outputs at public entrypoints rather than mocking internal helper methods or recomputing the implementation formula inside the test.
- `[area:tests]` Clear `_detect_cli_version.cache_clear()` before and after tests that mock `container --version` so `lru_cache` state never leaks across tests.
- `[area:tests]` Use synthetic low-entropy test credentials (`0000000000000001` or `test-token-placeholder`) so secret scanners never trip on test fixtures.

## Concurrency and State
- `[area:git]` Once a pull request is open, advance the branch with forward commits or `git merge origin/main` rather than rebasing or force-pushing.
