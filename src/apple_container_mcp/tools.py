from fastmcp import FastMCP
from typing import Dict, Any, List, Optional
import json
import logging
import threading
import subprocess
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


# In-memory store for active builds
active_builds: Dict[str, str] = {}
build_counter = 0

def _run_build_thread(build_id: str, context_path: str, tag: Optional[str] = None):
    args = ["build"]
    if tag:
        args.extend(["-t", tag])
    args.append(context_path)
    
    try:
        result = _run_container_cmd(args)
        active_builds[build_id] = f"Completed successfully. Output: {json.dumps(result)}"
    except ContainerCLIError as e:
        active_builds[build_id] = f"Failed with exit code {e.exit_code}. Error: {e.stderr}"
    except Exception as e:
        active_builds[build_id] = f"Unexpected error during build: {str(e)}"

@mcp.tool()
def build_image(context_path: str, tag: Optional[str] = None) -> str:
    """
    Build an image from a local context path.
    Runs asynchronously since builds can be long-running.
    Returns a build_id you can use to check status with check_build_status.
    """
    global build_counter
    build_id = f"build_{build_counter}"
    build_counter += 1
    
    active_builds[build_id] = "In progress..."
    
    thread = threading.Thread(target=_run_build_thread, args=(build_id, context_path, tag))
    thread.daemon = True
    thread.start()
    
    return f"Build started asynchronously with ID '{build_id}'. Check status later."

@mcp.tool()
def check_build_status(build_id: str) -> str:
    """Check the status of an asynchronous image build."""
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
    # Assuming there's no native JSON output for logs, or it wraps lines in JSON
    # If the underlying CLI doesn't support --format json for logs, our wrapper might complain.
    # We will invoke subprocess manually here to bypass --format json if it fails or use a direct command if available.
    try:
        # Some CLI tools support native tail via `-n`
        process = subprocess.run(["container", "logs", "-n", str(limit), container_id], capture_output=True, text=True, check=True)
        return process.stdout or process.stderr or "No logs available."
    except subprocess.CalledProcessError as e:
        return f"Failed to fetch logs: {e.stderr}"

@mcp.tool()
def inspect_container(container_id: str) -> Dict[str, Any]:
    """Get detailed low-level configuration of a container."""
    try:
        return _run_container_cmd(["inspect", container_id])
    except ContainerCLIError as e:
         return {"error": "Failed to inspect container", "details": e.stderr}
