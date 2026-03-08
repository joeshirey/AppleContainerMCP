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
    
    # Apple's `container` CLI is inconsistent with the `--format json` flag.
    # We maintain an explicit list of commands that should *not* receive the flag
    # because they either don't support it or we want raw output (e.g., logs).
    no_format_commands = ["system", "logs", "run", "inspect", "rm", "stop", "kill", "pull", "build", "network", "volume", "prune", "image"]
    if "--format" not in full_cmd and not (len(args) > 0 and args[0] in no_format_commands):
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
            # If JSON parsing fails, but we know the command isn't supposed to return JSON 
            # (and isn't `inspect` which we strictly expect to be JSON), return it as raw output.
            if args[0] in no_format_commands and args[0] != "inspect":
                return {"raw_output": stdout}
            
            # For all other commands, failing to parse JSON is considered an error, 
            # though we still return the raw output for debugging.
            return {"raw_output": stdout, "error": "Failed to parse JSON output"}
    except subprocess.CalledProcessError as e:
        # Check for daemon not running cases.
        stderr_msg = e.stderr.strip().lower()
        if "connection refused" in stderr_msg or "cannot connect to the container daemon" in stderr_msg:
            raise ContainerCLIError(
                "The container-apiserver daemon is not running. Please start the system service first.",
                e.returncode,
                e.stderr
            ) from e
            
        raise ContainerCLIError(
            f"Command failed with exit code {e.returncode}",
            e.returncode,
            e.stderr
        ) from e
