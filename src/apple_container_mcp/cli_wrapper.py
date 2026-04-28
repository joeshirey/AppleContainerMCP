import json
import logging
import subprocess
from typing import Any, List, Optional

logger = logging.getLogger("apple-container-mcp")


class ContainerCLIError(Exception):
    """
    Exception raised for errors during container CLI execution.

    Attributes:
        message (str): Human-readable error message.
        exit_code (int): The process exit code returned by the container CLI.
        stderr (str): The raw error output from the CLI.
    """

    def __init__(self, message: str, exit_code: int, stderr: str):
        super().__init__(message)
        self.exit_code = exit_code
        self.stderr = stderr


# Default timeout for quick commands (status checks, rm, stop, ls, inspect, etc.)
DEFAULT_TIMEOUT_SECONDS = 30

# Long-running timeout for commands that may legitimately take several minutes (pull, push, start, build, etc.)
LONG_RUNNING_TIMEOUT_SECONDS = 300

# Commands (any token in args) that indicate a long-running operation deserving the extended timeout.
LONG_RUNNING_COMMANDS = {"pull", "push", "start", "build"}


def _run_container_cmd(args: List[str], timeout: Optional[int] = None) -> Any:
    """
    Executes a container CLI command and processes its output.

    This function handles:
    1. Mapping specific commands to the --format json flag where supported.
    2. Heuristic-based timeout selection (longer for pull, push, build, etc.).
    3. Parsing JSON output into Python objects.
    4. Fallback to raw text output for commands that don't emit JSON.
    5. Normalizing error messages for common failure modes (e.g., daemon not running).

    Args:
        args: List of command-line arguments to pass to the 'container' binary.
        timeout: Optional explicit timeout in seconds.

    Returns:
        The parsed JSON result (dict or list), or a dict with 'raw_output' if not JSON.

    Raises:
        ContainerCLIError: If the command fails, times out, or the daemon is unreachable.
    """
    full_cmd = ["container"] + args

    # The `container` CLI is inconsistent with `--format json` support.
    # We use an allowlist of (command, subcommand?) tuples that are known to support --format json cleanly.
    # Entries are matched against the leading tokens of `args` (excluding the "container" binary itself).
    FORMAT_JSON_COMMANDS = {
        ("ls",),  # container ls
        ("image", "ls"),  # container image ls
        ("network", "ls"),  # container network ls
        ("volume", "ls"),  # container volume ls
        # `container builder ls` does NOT exist in Apple Container 0.12
        # (verified in 2026-04-28 CLI audit). Builder subcommands are only
        # start / status / stop / delete. Do NOT re-add this entry.
        ("system", "version"),  # container system version (added in 0.12)
        ("system", "status"),  # container system status (verified in 0.12)
        ("builder", "status"),  # container builder status (verified in 0.12)
        ("stats",),  # container stats (verified in 0.12)
    }
    leading = tuple(args)
    # Check if the start of the current command matches any entry in our JSON-capable allowlist.
    matches_allowlist = any(leading[: len(prefix)] == prefix for prefix in FORMAT_JSON_COMMANDS)
    if "--format" not in full_cmd and matches_allowlist:
        full_cmd.extend(["--format", "json"])

    # Determine effective timeout: explicit override > long-running heuristic > default.
    # Check all tokens in args (not just args[0]) so subcommand forms like
    # ["image", "push", ...], ["system", "start"], ["builder", "start"], ["build", ...]
    # all correctly receive the extended timeout.
    if timeout is None:
        timeout = (
            LONG_RUNNING_TIMEOUT_SECONDS if any(a in LONG_RUNNING_COMMANDS for a in args) else DEFAULT_TIMEOUT_SECONDS
        )

    logger.debug("Executing: %s (timeout=%ss)", " ".join(full_cmd), timeout)

    try:
        # Execute the command and capture output.
        process = subprocess.run(full_cmd, capture_output=True, text=True, check=True, timeout=timeout)

        # Handle completely empty output (e.g., successful 'rm' or 'stop').
        stdout = process.stdout.strip()
        if not stdout:
            return {}
        try:
            # Attempt to natively parse the stdout as JSON.
            return json.loads(stdout)
        except json.JSONDecodeError:
            # Commands in FORMAT_JSON_COMMANDS are expected to return valid JSON — flag parse failures.
            # `inspect` is a special case: it also always returns JSON (it is not in FORMAT_JSON_COMMANDS
            # because it doesn't need --format json appended), so a parse failure is also flagged there.
            # All other commands return raw text by design — return as raw_output without error.
            if matches_allowlist or args[0] == "inspect":
                return {"raw_output": stdout, "error": "Failed to parse JSON output"}
            return {"raw_output": stdout}
    except subprocess.TimeoutExpired as e:
        logger.error("Command timed out after %ss: %s", timeout, " ".join(full_cmd))
        # Re-raise as a domain-specific error with the command context.
        raise ContainerCLIError(
            f"Command timed out after {timeout}s: {' '.join(full_cmd)}",
            -1,
            f"Timed out after {timeout} seconds.",
        ) from e
    except subprocess.CalledProcessError as e:
        logger.warning("Command failed (exit %d): %s — %s", e.returncode, " ".join(full_cmd), e.stderr.strip())
        # Detect and normalize 'daemon not running' errors which often have specific stderr signatures.
        stderr_msg = e.stderr.strip().lower()
        if "connection refused" in stderr_msg or "cannot connect to the container daemon" in stderr_msg:
            raise ContainerCLIError(
                "The container-apiserver daemon is not running. Please start the system service first.",
                e.returncode,
                e.stderr,
            ) from e

        # Generic failure fallback.
        raise ContainerCLIError(f"Command failed with exit code {e.returncode}", e.returncode, e.stderr) from e
