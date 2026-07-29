"""System management tools and the system-status MCP resource."""

import json
import re
from typing import Dict, Any

from . import mcp, _DESTRUCTIVE, _run_container_cmd, ContainerCLIError
from ..cli_wrapper import (
    _detect_cli_version,
    version_warning,
    MINIMUM_CLI_MAJOR_VERSION,
    RECOMMENDED_CLI_VERSION,
)

# Accepted `container system logs --last` window: a number with an optional
# m/h/d suffix (bare numbers are seconds). Anything else is rejected rather than
# forwarded, so an LLM cannot smuggle extra tokens into the argument list.
_LOG_WINDOW_RE = re.compile(r"^\d+[mhd]?$")


# --- Resources ---


@mcp.resource("apple-container://system/status")
def get_system_status_resource() -> str:
    """Provides the current system status as a resource."""
    try:
        status = _run_container_cmd(["system", "status"])
        return json.dumps(status, indent=2)
    except Exception as e:
        return f"Error retrieving system status: {str(e)}"


# --- System Management ---


@mcp.tool()
def check_apiserver_status() -> Dict[str, Any]:
    """
    Check if the Apple container-apiserver daemon is running.
    Returns a standardized dictionary with 'status' (ok/stopped/error).
    Prefer `system_status` for richer output; this tool is kept for backwards compatibility.
    """
    try:
        _run_container_cmd(["system", "status"])
        return {"status": "ok", "message": "The container-apiserver daemon is running."}
    except ContainerCLIError as e:
        # _run_container_cmd normalises daemon-not-running errors into a well-known message string.
        # We search both the exception message and the raw stderr to catch daemon-not-reachable
        # errors regardless of how the caller constructed the ContainerCLIError.
        combined = (str(e) + " " + e.stderr).lower()
        daemon_indicators = ("daemon is not running", "daemon not running", "connection refused", "cannot connect")
        if any(indicator in combined for indicator in daemon_indicators):
            return {"status": "stopped", "error": "The container-apiserver daemon is not reachable."}
        return {"status": "error", "message": "Failed to retrieve system status", "details": str(e)}


@mcp.tool()
def start_system() -> Dict[str, Any]:
    """Start the Apple container system service."""
    try:
        _run_container_cmd(["system", "start"])
        return {"status": "ok", "message": "System service started successfully."}
    except ContainerCLIError as e:
        return {
            "status": "error",
            "message": "Failed to start system service. Ensure you have the right permissions.",
            "details": e.stderr,
        }


@mcp.tool(annotations=_DESTRUCTIVE)
def stop_system() -> Dict[str, Any]:
    """Stop the Apple container system service. WARNING: this stops all running containers."""
    try:
        _run_container_cmd(["system", "stop"])
        return {"status": "ok", "message": "System service stopped successfully."}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to stop system service.", "details": e.stderr}


@mcp.tool()
def system_status() -> Dict[str, Any]:
    """
    Retrieve system-wide status (version, driver status).
    Returns a dictionary containing 'status' and 'system_status'.
    """
    try:
        result = _run_container_cmd(["system", "status"])
        return {"status": "ok", "system_status": result}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to retrieve system status", "details": str(e)}


@mcp.tool()
def system_version() -> Dict[str, Any]:
    """
    Return version information for the Apple Container CLI and (when running) the apiserver daemon.

    Requires Apple Container 0.12+ (the `system version` subcommand was introduced in 0.12).

    This tool does NOT require the daemon to be running — it can be used as a lightweight
    environment probe before issuing commands that DO require the daemon. When the daemon
    is down, the response contains only the CLI's own version entry; when the daemon is up,
    it also includes the container-apiserver entry.

    Returns:
        On success: {"status": "ok", "version": <list of version entries>}
            Each entry is a dict with keys: appName, buildType, version, commit.
            The element with appName="container" is the CLI itself.
            The element with appName="container-apiserver" (present only when the daemon
            is running) is the apiserver daemon.
        On error:   {"status": "error", "message": str, "details": str}
    """
    try:
        result = _run_container_cmd(["system", "version"])
        response: Dict[str, Any] = {"status": "ok", "version": result}
        warning = version_warning()
        if warning:
            response["warning"] = warning
        return response
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to retrieve system version", "details": str(e)}


@mcp.tool()
def system_property_list() -> Dict[str, Any]:
    """
    List Apple Container system property values (TOML-backed config introduced in 1.0).

    Replaces the removed `system property get`/`set` subcommands. Requires the
    container system service to be running.
    """
    try:
        result = _run_container_cmd(["system", "property", "list"])
        properties = result if isinstance(result, list) else ([] if result == {} else [result])
        return {"status": "ok", "properties": properties}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to list system properties", "details": str(e)}


@mcp.tool()
def system_df() -> Dict[str, Any]:
    """
    Report disk usage for images, containers, and volumes.

    Use this before pruning to see how much space each category is holding and how
    much of it is reclaimable. Requires the container system service to be running.

    Returns:
        On success: {"status": "ok", "disk_usage": {...}}
            The payload has "containers", "images", and "volumes" keys, each with
            active / total counts and sizeInBytes / reclaimable byte counts.
        On error:   {"status": "error", "message": str, "details": str}
    """
    try:
        result = _run_container_cmd(["system", "df"])
        return {"status": "ok", "disk_usage": result}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to retrieve disk usage", "details": e.stderr}


@mcp.tool()
def system_logs(last: str = "5m") -> Dict[str, Any]:
    """
    Fetch recent log output from the `container` system services (the apiserver and
    its helpers), as opposed to a single container's logs.

    Reach for this when the daemon itself is misbehaving: containers that will not
    start, a system service that fails to come up, or errors that never surface in
    per-container logs. For one container's stdout/stderr, use `get_logs` instead.

    This tool never passes `--follow`; streaming would block until the subprocess
    timeout killed it. Widen the window instead.

    Args:
        last: How far back to read, as a number with an optional m/h/d suffix
            (a bare number means seconds). Defaults to "5m".

    Returns:
        On success: {"status": "ok", "logs": str}
        On error:   {"status": "error", "message": str, "details": str}
    """
    if not _LOG_WINDOW_RE.match(last):
        return {
            "status": "error",
            "message": f"Invalid 'last' window: {last!r}. Use a number with an optional m, h, or d suffix (e.g. '5m').",
        }
    try:
        result = _run_container_cmd(["system", "logs", "--last", last])
        logs = result.get("raw_output", "") if isinstance(result, dict) else str(result)
        return {"status": "ok", "logs": logs}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to retrieve system logs", "details": e.stderr}


@mcp.tool()
def check_environment() -> Dict[str, Any]:
    """
    Probe the local Apple Container CLI: report whether it is installed, whether it
    meets the minimum supported major version (1.0+), and whether an upgrade is
    recommended. Use this as a first step when diagnosing setup problems. Does not
    require the daemon to be running.
    """
    version = _detect_cli_version()
    if version is None:
        return {
            "status": "error",
            "message": "The Apple Container CLI ('container') was not found on PATH. "
            "Install Apple Container 1.0+ from https://github.com/apple/container.",
        }
    major, minor = version
    if major < MINIMUM_CLI_MAJOR_VERSION:
        return {
            "status": "warning",
            "cli_major_version": major,
            "cli_version": f"{major}.{minor}",
            "warning": version_warning(major),
        }
    result: Dict[str, Any] = {
        "status": "ok",
        "cli_major_version": major,
        "cli_version": f"{major}.{minor}",
        "message": f"Apple Container CLI {major}.{minor} detected (meets the {MINIMUM_CLI_MAJOR_VERSION}.0+ minimum).",
    }
    if version < RECOMMENDED_CLI_VERSION:
        recommended = f"{RECOMMENDED_CLI_VERSION[0]}.{RECOMMENDED_CLI_VERSION[1]}"
        result["recommendation"] = (
            f"Apple Container {recommended} is recommended (you have {major}.{minor}). "
            f"It adds XPC request validation, kernel archive integrity checks, and a fix for "
            f"symlink following when copying user configuration. Upgrade with `brew upgrade container`."
        )
    return result
