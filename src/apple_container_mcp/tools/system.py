"""System management tools and the system-status MCP resource."""

import json
from typing import Dict, Any

from . import mcp, _DESTRUCTIVE, _run_container_cmd, ContainerCLIError


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
