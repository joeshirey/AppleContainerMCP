from fastmcp import FastMCP
from typing import Dict, Any, List, Optional
import json
import logging
import threading
import itertools
import os
from .cli_wrapper import _run_container_cmd, ContainerCLIError

# Set up logging for the MCP server
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("apple-container-mcp")

mcp = FastMCP("apple-container-mcp")

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
    """
    try:
        # system info expects to connect to the daemon
        _run_container_cmd(["system", "status"])
        return {"status": "ok", "message": "The container-apiserver daemon is running."}
    except ContainerCLIError as e:
        if "daemon is not running" in str(e).lower() or "connection refused" in str(e).lower():
            return {"status": "stopped", "error": "The container-apiserver daemon is not reachable."}
        return {"status": "error", "error": str(e), "stderr": e.stderr}


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


@mcp.tool()
def stop_system() -> Dict[str, Any]:
    """Stop the Apple container system service."""
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


# --- Container Lifecycle ---


@mcp.tool()
def run_container(
    image: str,
    cpus: Optional[int] = None,
    memory: Optional[str] = None,
    name: Optional[str] = None,
    detach: bool = True,
    ports: Optional[List[str]] = None,
    env: Optional[List[str]] = None,
    volumes: Optional[List[str]] = None,
    network: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Start a container from an image with optional resource constraints, networking, ports, env vars, and volume mounts.
    Examples: run_container("debian", memory="4g", cpus=2, ports=["8080:8080"], env=["PORT=8080"], volumes=["/host/path:/container/path"], network="my_net")
    """
    # Lightweight input validation
    if ports:
        for p in ports:
            if not p.strip():
                return {"status": "error", "message": "Port mapping cannot be empty."}

    if env:
        for e in env:
            if "=" not in e:
                return {"status": "error", "message": f"Invalid env format: {e}. Expected 'KEY=VALUE'."}

    if volumes:
        for v in volumes:
            if ":" not in v:
                return {"status": "error", "message": f"Invalid volume format: {v}. Expected 'HOST:CONTAINER'."}

    args = ["run"]
    if detach:
        args.append("-d")
    if name:
        args.extend(["--name", name])
    if cpus:
        args.extend(["--cpus", str(cpus)])
    if memory:
        args.extend(["--memory", memory])
    if network:
        args.extend(["--network", network])
    if ports:
        for p in ports:
            args.extend(["-p", p])
    if env:
        for e in env:
            args.extend(["-e", e])
    if volumes:
        for v in volumes:
            args.extend(["-v", v])

    args.append(image)

    try:
        result = _run_container_cmd(args)
        container_id = result.get("raw_output") if isinstance(result, dict) else str(result)
        return {"status": "ok", "id": container_id}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to run container", "details": e.stderr, "exit_code": e.exit_code}


@mcp.tool()
def list_containers(all: bool = True) -> Dict[str, Any]:
    """View running (and optionally stopped) containers."""
    args = ["ls"]
    if all:
        args.append("-a")

    try:
        result = _run_container_cmd(args)
        containers = result if isinstance(result, list) else [result]
        return {"status": "ok", "containers": containers, "count": len(containers)}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to list containers", "details": e.stderr}


@mcp.tool()
def stop_container(container_id: str, force: bool = False) -> Dict[str, Any]:
    """Gracefully or forcefully terminate a container."""
    cmd = "kill" if force else "stop"
    try:
        _run_container_cmd([cmd, container_id])
        return {"status": "ok", "message": f"Successfully executed '{cmd}' on container {container_id}."}
    except ContainerCLIError as e:
        return {"status": "error", "message": f"Failed to {cmd} container {container_id}.", "details": e.stderr}


@mcp.tool()
def start_container(container_id: str) -> Dict[str, Any]:
    """Start a stopped container."""
    try:
        _run_container_cmd(["start", container_id])
        return {"status": "ok", "message": f"Successfully started container {container_id}."}
    except ContainerCLIError as e:
        return {"status": "error", "message": f"Failed to start container {container_id}.", "details": e.stderr}


@mcp.tool()
def remove_container(container_id: str, force: bool = False) -> Dict[str, Any]:
    """Clean up container resources by removing a container."""
    args = ["rm"]
    if force:
        args.append("-f")
    args.append(container_id)

    try:
        _run_container_cmd(args)
        return {"status": "ok", "message": f"Successfully removed container {container_id}."}
    except ContainerCLIError as e:
        return {"status": "error", "message": f"Failed to remove container {container_id}.", "details": e.stderr}


# --- Image Management ---


@mcp.tool()
def pull_image(image: str) -> Dict[str, Any]:
    """Download an image from a registry."""
    try:
        _run_container_cmd(["pull", image])
        return {"status": "ok", "message": f"Successfully pulled image '{image}'."}
    except ContainerCLIError as e:
        return {"status": "error", "message": f"Failed to pull image '{image}'.", "details": e.stderr}


# Thread-safe storage and counter for active builds.
# active_builds: maps build_id to status strings.
# _builds_lock: guards access to active_builds to prevent race conditions.
# _build_id_counter: provides unique incrementing IDs for builds.
active_builds: Dict[str, str] = {}
_builds_lock = threading.Lock()
_build_id_counter = itertools.count()


def _run_build_thread(build_id: str, context_path: str, tag: Optional[str] = None):
    """
    Internal worker function executed in a background thread to run container builds.
    Updates the global active_builds dictionary with the outcome.
    """
    args = ["build"]
    if tag:
        args.extend(["-t", tag])
    args.append(context_path)

    try:
        result = _run_container_cmd(args)
        with _builds_lock:
            active_builds[build_id] = f"Completed successfully. Output: {json.dumps(result)}"
    except ContainerCLIError as e:
        with _builds_lock:
            active_builds[build_id] = f"Failed with exit code {e.exit_code}. Error: {e.stderr}"
    except Exception as e:
        with _builds_lock:
            active_builds[build_id] = f"Unexpected error during build: {str(e)}"


@mcp.tool()
def build_image(context_path: str, tag: Optional[str] = None) -> Dict[str, str]:
    """
    Build an image from a local context path.
    Runs asynchronously since builds can be long-running.
    Returns a build_id you can use to check status with check_build_status.
    """
    if not os.path.exists(context_path):
        return {"status": "error", "message": f"Context path does not exist: {context_path}"}
    if not os.path.isdir(context_path):
        return {"status": "error", "message": f"Context path is not a directory: {context_path}"}

    build_id = f"build_{next(_build_id_counter)}"

    with _builds_lock:
        active_builds[build_id] = "In progress..."

    thread = threading.Thread(target=_run_build_thread, args=(build_id, context_path, tag))
    thread.daemon = True
    thread.start()

    return {
        "status": "ok",
        "message": f"Build started asynchronously with ID '{build_id}'. Check status later.",
        "build_id": build_id,
    }


@mcp.tool()
def check_build_status(build_id: str) -> Dict[str, Any]:
    """Check the status of an asynchronous image build."""
    with _builds_lock:
        status = active_builds.get(build_id)
        if status:
            return {"status": "ok", "build_status": status}
        return {"status": "error", "message": f"No build found with ID '{build_id}'."}


@mcp.tool()
def list_images() -> Dict[str, Any]:
    """View available local images."""
    try:
        result = _run_container_cmd(["image", "ls"])
        images = result if isinstance(result, list) else [result]
        return {"status": "ok", "images": images, "count": len(images)}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to list images", "details": e.stderr}


# --- Inspection & Logs ---


@mcp.tool()
def get_logs(container_id: str, limit: int = 100) -> str:
    """Fetch recent stdout/stderr from a specific container."""
    try:
        # Pass -n and container_id to the CLI via our wrapper
        result = _run_container_cmd(["logs", "-n", str(limit), container_id])

        # If the command returns raw output (as expected for logs), return it.
        # Otherwise, return it as a string if it was parsed as JSON for some reason.
        if isinstance(result, dict):
            return result.get("raw_output", str(result))
        return str(result)
    except ContainerCLIError as e:
        return f"Failed to fetch logs: {e.stderr}"


@mcp.tool()
def inspect_container(container_id: str) -> Dict[str, Any]:
    """Get detailed low-level configuration of a container."""
    try:
        result = _run_container_cmd(["inspect", container_id])
        return {"status": "ok", "inspection": result}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to inspect container", "details": e.stderr}


# --- Network Management ---


@mcp.tool()
def create_network(name: str, subnet: Optional[str] = None) -> Dict[str, Any]:
    """Creates a new network with the given name and optional subnet (e.g., 192.168.100.0/24)."""
    args = ["network", "create"]
    if subnet:
        args.extend(["--subnet", subnet])
    args.append(name)
    try:
        _run_container_cmd(args)
        return {"status": "ok", "message": f"Successfully created network '{name}'."}
    except ContainerCLIError as e:
        return {"status": "error", "message": f"Failed to create network '{name}'.", "details": e.stderr}


@mcp.tool()
def remove_network(name: str) -> Dict[str, Any]:
    """Deletes a network."""
    try:
        _run_container_cmd(["network", "rm", name])
        return {"status": "ok", "message": f"Successfully removed network '{name}'."}
    except ContainerCLIError as e:
        return {"status": "error", "message": f"Failed to remove network '{name}'.", "details": e.stderr}


@mcp.tool()
def list_networks() -> Dict[str, Any]:
    """Lists user-defined networks."""
    try:
        result = _run_container_cmd(["network", "ls"])
        networks = result if isinstance(result, list) else [result]
        return {"status": "ok", "networks": networks, "count": len(networks)}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to list networks", "details": e.stderr}


@mcp.tool()
def inspect_network(name: str) -> Dict[str, Any]:
    """Shows detailed information about a network."""
    try:
        result = _run_container_cmd(["network", "inspect", name])
        return {"status": "ok", "inspection": result}
    except ContainerCLIError as e:
        return {"status": "error", "message": f"Failed to inspect network '{name}'", "details": e.stderr}


@mcp.tool()
def prune_networks() -> Dict[str, Any]:
    """Removes networks not connected to any containers."""
    try:
        _run_container_cmd(["network", "prune"])
        return {"status": "ok", "message": "Successfully pruned unused networks."}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to prune networks.", "details": e.stderr}


# --- Volume Management ---


@mcp.tool()
def create_volume(name: str, size: Optional[str] = None) -> Dict[str, Any]:
    """Creates a new named volume with an optional size (e.g., '10G')."""
    args = ["volume", "create"]
    if size:
        args.extend(["-s", size])
    args.append(name)
    try:
        _run_container_cmd(args)
        return {"status": "ok", "message": f"Successfully created volume '{name}'."}
    except ContainerCLIError as e:
        return {"status": "error", "message": f"Failed to create volume '{name}'.", "details": e.stderr}


@mcp.tool()
def remove_volume(name: str) -> Dict[str, Any]:
    """Deletes a volume by name."""
    try:
        _run_container_cmd(["volume", "rm", name])
        return {"status": "ok", "message": f"Successfully removed volume '{name}'."}
    except ContainerCLIError as e:
        return {"status": "error", "message": f"Failed to remove volume '{name}'.", "details": e.stderr}


@mcp.tool()
def list_volumes() -> Dict[str, Any]:
    """Lists volumes."""
    try:
        result = _run_container_cmd(["volume", "ls"])
        volumes = result if isinstance(result, list) else [result]
        return {"status": "ok", "volumes": volumes, "count": len(volumes)}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to list volumes", "details": e.stderr}


@mcp.tool()
def inspect_volume(name: str) -> Dict[str, Any]:
    """Displays detailed information for a volume."""
    try:
        result = _run_container_cmd(["volume", "inspect", name])
        return {"status": "ok", "inspection": result}
    except ContainerCLIError as e:
        return {"status": "error", "message": f"Failed to inspect volume '{name}'", "details": e.stderr}


@mcp.tool()
def prune_volumes() -> Dict[str, Any]:
    """Removes all volumes that have no container references."""
    try:
        _run_container_cmd(["volume", "prune"])
        return {"status": "ok", "message": "Successfully pruned unused volumes."}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to prune volumes.", "details": e.stderr}


# --- Cleanup & Prune ---


@mcp.tool()
def prune_containers() -> Dict[str, Any]:
    """Removes stopped containers to reclaim disk space."""
    try:
        _run_container_cmd(["prune"])
        return {"status": "ok", "message": "Successfully pruned stopped containers."}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to prune containers.", "details": e.stderr}


@mcp.tool()
def prune_images(all: bool = False) -> Dict[str, Any]:
    """Removes unused images to reclaim disk space. Set `all=True` to remove all unreferenced images (not just dangling ones)."""
    args = ["image", "prune"]
    if all:
        args.append("-a")
    try:
        _run_container_cmd(args)
        return {"status": "ok", "message": "Successfully pruned unused images."}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to prune images.", "details": e.stderr}


@mcp.tool()
def remove_image(image: str, force: bool = False) -> Dict[str, Any]:
    """Delete a single image from local storage by name or ID."""
    args = ["image", "rm"]
    if force:
        args.append("-f")
    args.append(image)
    try:
        _run_container_cmd(args)
        return {"status": "ok", "message": f"Successfully removed image '{image}'."}
    except ContainerCLIError as e:
        return {"status": "error", "message": f"Failed to remove image '{image}'.", "details": e.stderr}
