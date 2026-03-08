import json
import subprocess
from typing import Any, List


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


def _run_container_cmd(args: List[str]) -> Any:
    """
    Executes a container CLI command.
    Returns the parsed JSON output as a dictionary or list,
    or a raw output dictionary if the command does not support JSON.
    Raises ContainerCLIError if the command fails.
    """
    full_cmd = ["container"] + args

    # The `container` CLI is inconsistent with `--format json` support.
    # Rather than maintaining a blocklist of commands that don't support it (fragile as tools grow),
    # we use an allowlist of the commands that are known to support it cleanly.
    # Any command not in this set will never have --format json appended.
    FORMAT_JSON_COMMANDS = {"ls"}
    if "--format" not in full_cmd and (len(args) > 0 and args[0] in FORMAT_JSON_COMMANDS):
        full_cmd.extend(["--format", "json"])

    try:
        process = subprocess.run(full_cmd, capture_output=True, text=True, check=True)
        # Handle completely empty output
        stdout = process.stdout.strip()
        if not stdout:
            return {}
        try:
            # Attempt to natively parse the stdout as JSON
            return json.loads(stdout)
        except json.JSONDecodeError:
            # Commands in FORMAT_JSON_COMMANDS are expected to return valid JSON — flag parse failures.
            # `inspect` is a special case: it also always returns JSON (it is not in FORMAT_JSON_COMMANDS
            # because it doesn't need --format json appended), so a parse failure is also flagged there.
            # All other commands return raw text by design — return as raw_output without error.
            if args[0] in FORMAT_JSON_COMMANDS or args[0] == "inspect":
                return {"raw_output": stdout, "error": "Failed to parse JSON output"}
            return {"raw_output": stdout}
    except subprocess.CalledProcessError as e:
        # Check for daemon not running cases.
        stderr_msg = e.stderr.strip().lower()
        if "connection refused" in stderr_msg or "cannot connect to the container daemon" in stderr_msg:
            raise ContainerCLIError(
                "The container-apiserver daemon is not running. Please start the system service first.",
                e.returncode,
                e.stderr,
            ) from e

        raise ContainerCLIError(f"Command failed with exit code {e.returncode}", e.returncode, e.stderr) from e
