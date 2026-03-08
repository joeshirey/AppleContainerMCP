from fastmcp import FastMCP
from typing import Dict, Any, List, Optional
import json
import logging
import threading
import subprocess
import itertools
from .cli_wrapper import _run_container_cmd, ContainerCLIError

# Set up logging for the MCP server
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("apple-container-mcp")

mcp = FastMCP("apple-container-mcp")

# --- System Management ---

@mcp.tool()
def check_apiserver_status() -> Dict[str, Any]:
    """Check if the Apple container-apiserver daemon is running."""
    try:
        # system info expects to connect to the daemon
        return _run_container_cmd(["system", "status"])
    except ContainerCLIError as e:
        if "daemon is not running" in str(e).lower() or "connection refused" in str(e).lower():
            return {"status": "stopped", "error": "The container-apiserver daemon is not reachable."}
        return {"status": "error", "error": str(e), "stderr": e.stderr}

@mcp.tool()
def start_system() -> str:
    """Start the Apple container system service."""
    # Starting the service usually requires launchctl or an Apple-specific boot command
    # Assuming `container system start` or similar based on typical CLI design.
    # The actual command depends heavily on the specific Apple CLI implementation.
    # Note: If it requires sudo, we should return instructions instead of failing silently.
    try:
        result = _run_container_cmd(["system", "start"])
        return f"System service started successfully: {json.dumps(result)}"
    except ContainerCLIError as e:
        return f"Failed to start system service. Ensure you have the right permissions. Error: {e.stderr}"

@mcp.tool()
def stop_system() -> str:
    """Stop the Apple container system service."""
    try:
        result = _run_container_cmd(["system", "stop"])
        return f"System service stopped successfully: {json.dumps(result)}"
    except ContainerCLIError as e:
        return f"Failed to stop system service. Error: {e.stderr}"

@mcp.tool()
def system_status() -> Dict[str, Any]:
    """Retrieve system-wide status (version, driver status)."""
    try:
        return _run_container_cmd(["system", "status"])
    except ContainerCLIError as e:
         return {"error": str(e)}

# --- Container Lifecycle ---

@mcp.tool()
def run_container(image: str, cpus: Optional[int] = None, memory: Optional[str] = None, name: Optional[str] = None, detach: bool = True, ports: Optional[List[str]] = None, env: Optional[List[str]] = None, volumes: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Start a container from an image with optional resource constraints, ports, env vars, and volume mounts.
    Examples: run_container("debian", memory="4g", cpus=2, ports=["8080:8080"], env=["PORT=8080"], volumes=["/host/path:/container/path"])
    """
    args = ["run"]
    if detach:
        args.append("-d")
    if name:
        args.extend(["--name", name])
    if cpus:
        args.extend(["--cpus", str(cpus)])
    if memory:
        args.extend(["--memory", memory])
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
        if isinstance(result, dict) and "raw_output" in result:
             return {"id": result["raw_output"]}
        return result if isinstance(result, dict) else {"result": result}
    except ContainerCLIError as e:
        return {"error": "Failed to run container", "details": e.stderr, "exit_code": e.exit_code}

@mcp.tool()
def list_containers(all: bool = True) -> Dict[str, Any]:
    """View running (and optionally stopped) containers."""
    args = ["ls"]
    if all:
        args.append("-a")
        
    try:
        result = _run_container_cmd(args)
        # Assuming the CLI returns a valid JSON array or object
        return {"containers": result, "count": len(result) if isinstance(result, list) else 1}
    except ContainerCLIError as e:
        return {"error": "Failed to list containers", "details": e.stderr}

@mcp.tool()
def stop_container(container_id: str, force: bool = False) -> str:
    """Gracefully or forcefully terminate a container."""
    cmd = "kill" if force else "stop"
    try:
        _run_container_cmd([cmd, container_id])
        return f"Successfully executed '{cmd}' on container {container_id}."
    except ContainerCLIError as e:
        return f"Failed to {cmd} container {container_id}. Error: {e.stderr}"

@mcp.tool()
def start_container(container_id: str) -> str:
    """Start a stopped container."""
    try:
        _run_container_cmd(["start", container_id])
        return f"Successfully started container {container_id}."
    except ContainerCLIError as e:
        return f"Failed to start container {container_id}. Error: {e.stderr}"

@mcp.tool()
def remove_container(container_id: str, force: bool = False) -> str:
    """Clean up container resources by removing a container."""
    args = ["rm"]
    if force:
        args.append("-f")
    args.append(container_id)
    
    try:
        _run_container_cmd(args)
        return f"Successfully removed container {container_id}."
    except ContainerCLIError as e:
        return f"Failed to remove container {container_id}. Error: {e.stderr}"

# --- Image Management ---

@mcp.tool()
def pull_image(image: str) -> str:
    """Download an image from a registry."""
    try:
        _run_container_cmd(["pull", image])
        return f"Successfully pulled image '{image}'."
    except ContainerCLIError as e:
        return f"Failed to pull image '{image}'. Error: {e.stderr}"


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
def build_image(context_path: str, tag: Optional[str] = None) -> str:
    """
    Build an image from a local context path.
    Runs asynchronously since builds can be long-running.
    Returns a build_id you can use to check status with check_build_status.
    """
    build_id = f"build_{next(_build_id_counter)}"
    
    with _builds_lock:
        active_builds[build_id] = "In progress..."
    
    thread = threading.Thread(target=_run_build_thread, args=(build_id, context_path, tag))
    thread.daemon = True
    thread.start()
    
    return f"Build started asynchronously with ID '{build_id}'. Check status later."

@mcp.tool()
def check_build_status(build_id: str) -> str:
    """Check the status of an asynchronous image build."""
    with _builds_lock:
        return active_builds.get(build_id, f"No build found with ID '{build_id}'.")

@mcp.tool()
def list_images() -> Dict[str, Any]:
    """View available local images."""
    try:
        result = _run_container_cmd(["image", "ls"])
        return {"images": result} if isinstance(result, list) else result
    except ContainerCLIError as e:
        return {"error": "Failed to list images", "details": e.stderr}

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
        return _run_container_cmd(["inspect", container_id])
    except ContainerCLIError as e:
         return {"error": "Failed to inspect container", "details": e.stderr}

# --- Network Management ---

@mcp.tool()
def create_network(name: str, subnet: Optional[str] = None) -> str:
    """Creates a new network with the given name and optional subnet (e.g., 192.168.100.0/24)."""
    args = ["network", "create"]
    if subnet:
        args.extend(["--subnet", subnet])
    args.append(name)
    try:
        _run_container_cmd(args)
        return f"Successfully created network '{name}'."
    except ContainerCLIError as e:
        return f"Failed to create network '{name}'. Error: {e.stderr}"

@mcp.tool()
def remove_network(name: str) -> str:
    """Deletes a network."""
    try:
        _run_container_cmd(["network", "rm", name])
        return f"Successfully removed network '{name}'."
    except ContainerCLIError as e:
        return f"Failed to remove network '{name}'. Error: {e.stderr}"

@mcp.tool()
def list_networks() -> Dict[str, Any]:
    """Lists user-defined networks."""
    try:
        result = _run_container_cmd(["network", "ls"])
        return {"networks": result} if isinstance(result, list) else result
    except ContainerCLIError as e:
        return {"error": "Failed to list networks", "details": e.stderr}

@mcp.tool()
def inspect_network(name: str) -> Dict[str, Any]:
    """Shows detailed information about a network."""
    try:
        return _run_container_cmd(["network", "inspect", name])
    except ContainerCLIError as e:
        return {"error": f"Failed to inspect network '{name}'", "details": e.stderr}

@mcp.tool()
def prune_networks() -> str:
    """Removes networks not connected to any containers."""
    try:
        _run_container_cmd(["network", "prune"])
        return "Successfully pruned unused networks."
    except ContainerCLIError as e:
        return f"Failed to prune networks. Error: {e.stderr}"

# --- Volume Management ---

@mcp.tool()
def create_volume(name: str, size: Optional[str] = None) -> str:
    """Creates a new named volume with an optional size (e.g., '10G')."""
    args = ["volume", "create"]
    if size:
        args.extend(["-s", size])
    args.append(name)
    try:
        _run_container_cmd(args)
        return f"Successfully created volume '{name}'."
    except ContainerCLIError as e:
        return f"Failed to create volume '{name}'. Error: {e.stderr}"

@mcp.tool()
def remove_volume(name: str) -> str:
    """Deletes a volume by name."""
    try:
        _run_container_cmd(["volume", "rm", name])
        return f"Successfully removed volume '{name}'."
    except ContainerCLIError as e:
        return f"Failed to remove volume '{name}'. Error: {e.stderr}"

@mcp.tool()
def list_volumes() -> Dict[str, Any]:
    """Lists volumes."""
    try:
        result = _run_container_cmd(["volume", "ls"])
        return {"volumes": result} if isinstance(result, list) else result
    except ContainerCLIError as e:
        return {"error": "Failed to list volumes", "details": e.stderr}

@mcp.tool()
def inspect_volume(name: str) -> Dict[str, Any]:
    """Displays detailed information for a volume."""
    try:
        return _run_container_cmd(["volume", "inspect", name])
    except ContainerCLIError as e:
        return {"error": f"Failed to inspect volume '{name}'", "details": e.stderr}

@mcp.tool()
def prune_volumes() -> str:
    """Removes all volumes that have no container references."""
    try:
        _run_container_cmd(["volume", "prune"])
        return "Successfully pruned unused volumes."
    except ContainerCLIError as e:
        return f"Failed to prune volumes. Error: {e.stderr}"

# --- Cleanup & Prune ---

@mcp.tool()
def prune_containers() -> str:
    """Removes stopped containers to reclaim disk space."""
    try:
        _run_container_cmd(["prune"])
        return "Successfully pruned stopped containers."
    except ContainerCLIError as e:
        return f"Failed to prune containers. Error: {e.stderr}"

@mcp.tool()
def prune_images(all: bool = False) -> str:
    """Removes unused images to reclaim disk space. Set `all=True` to remove all unreferenced images (not just dangling ones)."""
    args = ["image", "prune"]
    if all:
        args.append("-a")
    try:
        _run_container_cmd(args)
        return "Successfully pruned unused images."
    except ContainerCLIError as e:
        return f"Failed to prune images. Error: {e.stderr}"

@mcp.tool()
def remove_image(image: str, force: bool = False) -> str:
    """Deletes one or more images from local storage."""
    args = ["image", "rm"]
    if force:
        args.append("-f")
    args.append(image)
    try:
        _run_container_cmd(args)
        return f"Successfully removed image '{image}'."
    except ContainerCLIError as e:
        return f"Failed to remove image '{image}'. Error: {e.stderr}"
