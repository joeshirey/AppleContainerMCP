from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from typing import Dict, Any, List, Optional
import json
import subprocess
import threading
import itertools
import os
import time
from .cli_wrapper import _run_container_cmd, ContainerCLIError

_DESTRUCTIVE = ToolAnnotations(destructiveHint=True)

mcp = FastMCP("apple-container-mcp")

# Blocklist of flags that must never be passed via args_override in run_container.
# These flags escalate privileges or grant capabilities that an LLM should not control.
_DANGEROUS_FLAGS: frozenset[str] = frozenset(
    {
        "--privileged",
        "--cap-add",
        "--cap-drop",
        "--security-opt",
        "--device",
        "--pid",
        "--ipc",
        "--userns",
        "--cgroupns",
        "--no-new-privileges",
    }
)


def _normalize_list_result(result: Any) -> List[Any]:
    """
    Normalise the raw output from a `container … ls` command into a plain list.

    _run_container_cmd returns:
      - a list  → when the CLI emits a JSON array (the happy path)
      - {}      → when the CLI emits empty output (nothing to list)
      - a dict  → in edge-cases where a single object is returned
    """
    if isinstance(result, list):
        return result
    if isinstance(result, dict) and not result:
        return []
    return [result]


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
    env_file: Optional[str] = None,
    volumes: Optional[List[str]] = None,
    network: Optional[str] = None,
    init_image: Optional[str] = None,
    entrypoint: Optional[str] = None,
    rm: bool = False,
    rosetta: bool = False,
    platform: Optional[str] = None,
    mount: Optional[List[str]] = None,
    workdir: Optional[str] = None,
    user: Optional[str] = None,
    labels: Optional[List[str]] = None,
    args_override: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Start a container from an image with optional resource constraints, networking, ports, env vars,
    volume mounts, and more. Pass a command to run via args_override.
    Examples:
      run_container("debian", memory="4g", cpus=2, ports=["8080:8080"])
      run_container("ubuntu", rm=True, detach=False, args_override=["bash", "-c", "echo hi"])
      run_container("my-app", rosetta=True, platform="linux/amd64")
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

    cmd_args = ["run"]
    if detach:
        cmd_args.append("-d")
    if rm:
        cmd_args.append("--rm")
    if name:
        cmd_args.extend(["--name", name])
    if cpus is not None:
        cmd_args.extend(["--cpus", str(cpus)])
    if memory:
        cmd_args.extend(["--memory", memory])
    if network:
        cmd_args.extend(["--network", network])
    if entrypoint:
        cmd_args.extend(["--entrypoint", entrypoint])
    if platform:
        cmd_args.extend(["--platform", platform])
    if rosetta:
        cmd_args.append("--rosetta")
    if workdir:
        cmd_args.extend(["-w", workdir])
    if user:
        cmd_args.extend(["-u", user])
    if env_file:
        cmd_args.extend(["--env-file", env_file])
    if ports:
        for p in ports:
            cmd_args.extend(["-p", p])
    if env:
        for e in env:
            cmd_args.extend(["-e", e])
    if volumes:
        for v in volumes:
            cmd_args.extend(["-v", v])
    if mount:
        for m in mount:
            cmd_args.extend(["--mount", m])
    if labels:
        for label in labels:
            cmd_args.extend(["--label", label])
    if init_image:
        cmd_args.extend(["--init-image", init_image])

    cmd_args.append(image)

    if args_override:
        # Reject any flags from the danger list to prevent privilege escalation
        # by a malicious prompt or an LLM acting on injected instructions.
        blocked = [flag for flag in args_override if flag in _DANGEROUS_FLAGS]
        if blocked:
            return {
                "status": "error",
                "message": f"Rejected dangerous flag(s) in args_override: {', '.join(blocked)}. "
                "These flags escalate container privileges and are not permitted.",
            }
        cmd_args.extend(args_override)

    try:
        result = _run_container_cmd(cmd_args)
        container_id = result.get("raw_output") if isinstance(result, dict) else str(result)
        return {"status": "ok", "id": container_id}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to run container", "details": e.stderr, "exit_code": e.exit_code}


@mcp.tool()
def list_containers(include_stopped: bool = True) -> Dict[str, Any]:
    """View running (and optionally stopped) containers."""
    args = ["ls"]
    if include_stopped:
        args.append("-a")

    try:
        result = _run_container_cmd(args)
        containers = _normalize_list_result(result)
        return {"status": "ok", "containers": containers, "count": len(containers)}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to list containers", "details": e.stderr}


@mcp.tool(annotations=_DESTRUCTIVE)
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


@mcp.tool(annotations=_DESTRUCTIVE)
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


@mcp.tool()
def export_container(container_id: str, output_file: Optional[str] = None) -> Dict[str, Any]:
    """Export a container's filesystem as a tar archive. Requires an output_file path in 0.11.0."""
    if not output_file:
        return {"status": "error", "message": "output_file is required in 0.11.0 to save the tar archive."}

    args = ["export", "-o", output_file, container_id]
    try:
        _run_container_cmd(args)
        return {"status": "ok", "message": f"Successfully exported container {container_id} to {output_file}."}
    except ContainerCLIError as e:
        return {"status": "error", "message": f"Failed to export container {container_id}.", "details": e.stderr}


# --- Image Management ---


@mcp.tool()
def pull_image(image: str) -> Dict[str, Any]:
    """Download an image from a registry."""
    try:
        _run_container_cmd(["image", "pull", image])
        return {"status": "ok", "message": f"Successfully pulled image '{image}'."}
    except ContainerCLIError as e:
        return {"status": "error", "message": f"Failed to pull image '{image}'.", "details": e.stderr}


# Thread-safe storage and counter for active builds.
# active_builds: maps unique build_id (str) to a dict with 'status' and 'updated_at' (epoch float).
# _builds_lock: guards all access to active_builds to prevent race conditions from background threads.
# _build_id_counter: provides unique incrementing IDs for each asynchronous build operation.
# BUILD_TTL_SECONDS: completed/failed builds are evicted after this many seconds to prevent memory leaks.
BUILD_TTL_SECONDS = 3600  # 1 hour

active_builds: Dict[str, Dict[str, Any]] = {}
_builds_lock = threading.Lock()
_build_id_counter = itertools.count()


def _evict_stale_builds() -> None:
    """Remove completed/failed builds older than BUILD_TTL_SECONDS. Must be called with _builds_lock held."""
    cutoff = time.monotonic() - BUILD_TTL_SECONDS
    stale = [
        bid
        for bid, info in active_builds.items()
        if info.get("updated_at", 0) < cutoff and info.get("state") != "in_progress"
    ]
    for bid in stale:
        del active_builds[bid]


def _run_build_thread(
    build_id: str,
    context_path: str,
    tag: Optional[str] = None,
    secrets: Optional[List[str]] = None,
    dockerfile: Optional[str] = None,
    build_args: Optional[List[str]] = None,
    no_cache: bool = False,
    platform: Optional[str] = None,
    target: Optional[str] = None,
) -> None:
    """
    Internal worker function executed in a background thread to run container builds.
    Updates the global active_builds dictionary with the outcome.
    """
    args = ["build"]
    if tag:
        args.extend(["-t", tag])
    if dockerfile:
        args.extend(["-f", dockerfile])
    if no_cache:
        args.append("--no-cache")
    if platform:
        args.extend(["--platform", platform])
    if target:
        args.extend(["--target", target])
    if secrets:
        for secret in secrets:
            args.extend(["--secret", secret])
    if build_args:
        for ba in build_args:
            args.extend(["--build-arg", ba])
    args.append(context_path)

    try:
        result = _run_container_cmd(args)
        with _builds_lock:
            active_builds[build_id] = {"state": "completed", "result": result, "updated_at": time.monotonic()}
            _evict_stale_builds()
    except ContainerCLIError as e:
        with _builds_lock:
            active_builds[build_id] = {
                "state": "failed",
                "exit_code": e.exit_code,
                "error": e.stderr,
                "updated_at": time.monotonic(),
            }
            _evict_stale_builds()
    except Exception as e:
        with _builds_lock:
            active_builds[build_id] = {"state": "failed", "error": str(e), "updated_at": time.monotonic()}
            _evict_stale_builds()


@mcp.tool()
def build_image(
    context_path: str,
    tag: Optional[str] = None,
    secrets: Optional[List[str]] = None,
    dockerfile: Optional[str] = None,
    build_args: Optional[List[str]] = None,
    no_cache: bool = False,
    platform: Optional[str] = None,
    target: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build an image from a local context path (runs asynchronously — builds can be long).
    Returns a build_id to poll with check_build_status.

    Args:
      context_path: Path to the build context directory.
      tag: Image name and tag, e.g. "myapp:v1".
      secrets: Secret specs, e.g. ["id=mysecret,src=secret.txt"].
      dockerfile: Path to a custom Dockerfile (default: Dockerfile in context_path).
      build_args: Build-time variables, e.g. ["VERSION=1.0"].
      no_cache: Disable layer cache.
      platform: Target platform, e.g. "linux/amd64".
      target: Multi-stage build target stage name.
    """
    if not os.path.exists(context_path):
        return {"status": "error", "message": f"Context path does not exist: {context_path}"}
    if not os.path.isdir(context_path):
        return {"status": "error", "message": f"Context path is not a directory: {context_path}"}

    # Boundary check: only allow paths within the user's home directory.
    home = os.path.expanduser("~")
    real_path = os.path.realpath(context_path)
    if not real_path.startswith(os.path.realpath(home)):
        return {"status": "error", "message": f"context_path must be within your home directory ({home})."}

    # Generate a unique ID and initialise state before launching the thread.
    build_id = f"build_{next(_build_id_counter)}"

    with _builds_lock:
        active_builds[build_id] = {"state": "in_progress", "updated_at": time.monotonic()}

    # Start build in daemon thread so it doesn't block the MCP server from shutting down.
    thread = threading.Thread(
        target=_run_build_thread,
        args=(build_id, context_path, tag, secrets, dockerfile, build_args, no_cache, platform, target),
    )
    thread.daemon = True
    thread.start()

    return {
        "status": "ok",
        "message": f"Build started asynchronously with ID '{build_id}'. Use check_build_status('{build_id}') to poll.",
        "build_id": build_id,
    }


@mcp.tool()
def check_build_status(build_id: str) -> Dict[str, Any]:
    """Check the status of an asynchronous image build started with build_image."""
    with _builds_lock:
        info = active_builds.get(build_id)
        if info is None:
            return {
                "status": "error",
                "message": f"No build found with ID '{build_id}'. It may have expired or the server restarted.",
            }
        return {"status": "ok", "build_id": build_id, "build_status": info}


@mcp.tool()
def list_builds() -> Dict[str, Any]:
    """List all active or recently completed/failed image builds tracked by this server session."""
    with _builds_lock:
        _evict_stale_builds()
        builds = [{"build_id": bid, **info} for bid, info in active_builds.items()]
    return {"status": "ok", "builds": builds, "count": len(builds)}


@mcp.tool()
def list_images() -> Dict[str, Any]:
    """View available local images."""
    try:
        result = _run_container_cmd(["image", "ls"])
        images = _normalize_list_result(result)
        return {"status": "ok", "images": images, "count": len(images)}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to list images", "details": e.stderr}


# --- Inspection & Logs ---


@mcp.tool()
def get_logs(container_id: str, limit: int = 100) -> Dict[str, Any]:
    """Fetch recent stdout/stderr from a specific container."""
    try:
        result = _run_container_cmd(["logs", "-n", str(limit), container_id])
        # Logs are raw text; extract the raw_output field when available.
        if isinstance(result, dict):
            output = result.get("raw_output", "")
        else:
            output = str(result)
        return {"status": "ok", "logs": output}
    except ContainerCLIError as e:
        return {
            "status": "error",
            "message": f"Failed to fetch logs for container {container_id}.",
            "details": e.stderr,
            "exit_code": e.exit_code,
        }


@mcp.tool()
def inspect_container(container_id: str) -> Dict[str, Any]:
    """Get detailed low-level configuration of a container."""
    try:
        result = _run_container_cmd(["inspect", container_id])
        return {"status": "ok", "inspection": result}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to inspect container", "details": e.stderr}


@mcp.tool()
def exec_in_container(
    container_id: str,
    command: List[str],
    env: Optional[List[str]] = None,
    user: Optional[str] = None,
    workdir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run a command inside a running container and return its output.
    `command` is a list of strings, e.g. ["ls", "-la", "/app"].
    Use `env` for extra environment variables (KEY=VALUE format),
    `user` to override the user (e.g. "root"), and `workdir` for the working directory.
    Examples:
      exec_in_container("myapp", ["cat", "/etc/os-release"])
      exec_in_container("db", ["psql", "-U", "postgres", "-c", "SELECT 1"], user="postgres")
    """
    if not command:
        return {"status": "error", "message": "command must be a non-empty list."}

    args = ["exec"]
    if user:
        args.extend(["-u", user])
    if workdir:
        args.extend(["-w", workdir])
    if env:
        for e in env:
            args.extend(["-e", e])
    args.append(container_id)
    args.extend(command)

    try:
        result = _run_container_cmd(args)
        output = result.get("raw_output", "") if isinstance(result, dict) else str(result)
        return {"status": "ok", "output": output}
    except ContainerCLIError as e:
        return {
            "status": "error",
            "message": f"Failed to exec in container {container_id}.",
            "details": e.stderr,
            "exit_code": e.exit_code,
        }


# --- Network Management ---


@mcp.tool()
def create_network(name: str, subnet: Optional[str] = None, mtu: Optional[int] = None) -> Dict[str, Any]:
    """Creates a new network with the given name, optional subnet, and optional MTU."""
    args = ["network", "create"]
    if subnet:
        args.extend(["--subnet", subnet])
    if mtu:
        args.extend(["--mtu", str(mtu)])
    args.append(name)
    try:
        _run_container_cmd(args)
        return {"status": "ok", "message": f"Successfully created network '{name}'."}
    except ContainerCLIError as e:
        return {"status": "error", "message": f"Failed to create network '{name}'.", "details": e.stderr}


@mcp.tool(annotations=_DESTRUCTIVE)
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
        networks = _normalize_list_result(result)
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


@mcp.tool(annotations=_DESTRUCTIVE)
def prune_networks() -> Dict[str, Any]:
    """Removes all networks not connected to any containers. WARNING: irreversible."""
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


@mcp.tool(annotations=_DESTRUCTIVE)
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
        volumes = _normalize_list_result(result)
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


@mcp.tool(annotations=_DESTRUCTIVE)
def prune_volumes() -> Dict[str, Any]:
    """Removes all volumes that have no container references. WARNING: irreversible, data will be lost."""
    try:
        _run_container_cmd(["volume", "prune"])
        return {"status": "ok", "message": "Successfully pruned unused volumes."}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to prune volumes.", "details": e.stderr}


# --- Cleanup & Prune ---


@mcp.tool(annotations=_DESTRUCTIVE)
def prune_containers() -> Dict[str, Any]:
    """Removes all stopped containers to reclaim disk space. WARNING: this is irreversible."""
    try:
        _run_container_cmd(["prune"])
        return {"status": "ok", "message": "Successfully pruned stopped containers."}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to prune containers.", "details": e.stderr}


@mcp.tool(annotations=_DESTRUCTIVE)
def prune_images(remove_all: bool = False) -> Dict[str, Any]:
    """Removes unused images to reclaim disk space. WARNING: irreversible. Set `remove_all=True` to remove all unreferenced images (not just dangling ones)."""
    args = ["image", "prune"]
    if remove_all:
        args.append("-a")
    try:
        _run_container_cmd(args)
        return {"status": "ok", "message": "Successfully pruned unused images."}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to prune images.", "details": e.stderr}


@mcp.tool(annotations=_DESTRUCTIVE)
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


@mcp.tool()
def tag_image(source: str, target: str) -> Dict[str, Any]:
    """
    Tag a local image with a new name/tag.
    Example: tag_image("myapp:latest", "registry.example.com/myapp:v1.0")
    """
    try:
        _run_container_cmd(["image", "tag", source, target])
        return {"status": "ok", "message": f"Successfully tagged '{source}' as '{target}'."}
    except ContainerCLIError as e:
        return {"status": "error", "message": f"Failed to tag image '{source}'.", "details": e.stderr}


@mcp.tool()
def push_image(image: str) -> Dict[str, Any]:
    """
    Push a local image to a container registry.
    The image name should include the registry host for non-Docker Hub registries.
    Example: push_image("registry.example.com/myapp:v1.0")
    """
    try:
        _run_container_cmd(["image", "push", image])
        return {"status": "ok", "message": f"Successfully pushed image '{image}'."}
    except ContainerCLIError as e:
        return {"status": "error", "message": f"Failed to push image '{image}'.", "details": e.stderr}


@mcp.tool()
def inspect_image(image: str) -> Dict[str, Any]:
    """Get detailed metadata about a local image by name or ID."""
    try:
        result = _run_container_cmd(["image", "inspect", image])
        return {"status": "ok", "inspection": result}
    except ContainerCLIError as e:
        return {"status": "error", "message": f"Failed to inspect image '{image}'.", "details": e.stderr}


# --- Registry Management ---


@mcp.tool()
def registry_login(server: str, username: str, password: str) -> Dict[str, Any]:
    """
    Log in to a container registry so that pull/push operations can authenticate.
    Example: registry_login("registry.example.com", "myuser", "mypassword")
    Note: credentials are passed via stdin to avoid exposing them in process arguments.
    """
    full_cmd = ["container", "registry", "login", "--username", username, "--password-stdin", server]
    try:
        process = subprocess.run(
            full_cmd,
            input=password,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if process.returncode != 0:
            return {"status": "error", "message": f"Failed to log in to '{server}'.", "details": process.stderr.strip()}
        return {"status": "ok", "message": f"Successfully logged in to '{server}'."}
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": f"Login to '{server}' timed out."}
    except FileNotFoundError:
        return {"status": "error", "message": "The 'container' CLI was not found on PATH."}


@mcp.tool()
def registry_logout(server: str) -> Dict[str, Any]:
    """
    Log out from a container registry, removing stored credentials.
    Example: registry_logout("registry.example.com")
    """
    try:
        _run_container_cmd(["registry", "logout", server])
        return {"status": "ok", "message": f"Successfully logged out from '{server}'."}
    except ContainerCLIError as e:
        return {"status": "error", "message": f"Failed to log out from '{server}'.", "details": e.stderr}


# --- Builder Management ---


@mcp.tool()
def builder_start() -> Dict[str, Any]:
    """
    Start the container image builder. The builder must be running before `build_image` can succeed.
    This is a prerequisite for all image build operations.
    """
    try:
        _run_container_cmd(["builder", "start"])
        return {"status": "ok", "message": "Builder started successfully."}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to start builder.", "details": e.stderr}


@mcp.tool()
def builder_stop() -> Dict[str, Any]:
    """Stop the container image builder."""
    try:
        _run_container_cmd(["builder", "stop"])
        return {"status": "ok", "message": "Builder stopped successfully."}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to stop builder.", "details": e.stderr}


@mcp.tool()
def builder_status() -> Dict[str, Any]:
    """Check whether the container image builder is running and retrieve its status."""
    try:
        result = _run_container_cmd(["builder", "status"])
        return {"status": "ok", "builder_status": result}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to retrieve builder status.", "details": e.stderr}


# --- Prompts ---


@mcp.prompt()
def troubleshoot_container(container_id: str) -> str:
    """
    Generate a troubleshooting workflow for a failing or misbehaving container.
    Inspects the container, fetches its recent logs, and provides guided next steps.
    """
    return f"""You are helping troubleshoot a container with ID or name: {container_id!r}.

Please follow these steps in order:
1. Call `inspect_container("{container_id}")` to get its current state and configuration.
2. Call `get_logs("{container_id}", limit=200)` to see recent stdout/stderr output.
3. Based on the state and logs:
   - If the container has exited, check the exit code and last log lines for error messages.
   - If the container is running but unhealthy, look for crash loops, OOM signals, or port conflicts.
   - If there are permission errors, check the user and volume mount configuration.
4. Suggest concrete remediation steps (restart, fix config, rebuild image, etc.).

Start by calling inspect_container now."""


@mcp.prompt()
def build_and_run_workflow(context_path: str, image_tag: str, port: Optional[str] = None) -> str:
    """
    Guide through the full build-tag-run workflow for a local project.
    Ensures the builder is running, builds the image, then runs it.
    """
    port_hint = f" with port mapping {port!r}" if port else ""
    return f"""You are helping build and run a container image from a local project.

Context path: {context_path!r}
Image tag: {image_tag!r}

Please follow these steps:
1. Call `builder_status()` to check if the image builder is running.
   - If not running, call `builder_start()` first and wait for confirmation.
2. Call `system_status()` to verify the container system service is active.
   - If not running, call `start_system()`.
3. Call `build_image("{context_path}", tag="{image_tag}")` to start an async build.
   - Note the returned build_id.
4. Poll `check_build_status(build_id)` every 10–15 seconds until state is "completed" or "failed".
   - If failed, show the error details and suggest fixes.
5. Once built successfully, call `run_container("{image_tag}"{f', ports=["{port}"]' if port else ""})`{port_hint}.
6. Confirm the container is running with `list_containers()`.

Start by checking builder_status now."""


@mcp.prompt()
def cleanup_environment() -> str:
    """
    Guide through safely cleaning up stopped containers, unused images, and orphaned volumes/networks.
    Reviews what exists before removing anything.
    """
    return """You are helping clean up a container environment to reclaim disk space.

Please follow these steps carefully — cleanup operations are irreversible:

1. Call `list_containers(all=True)` to see all containers including stopped ones.
   - Identify which stopped containers can be safely removed.
2. Call `list_images()` to see all local images.
   - Note which images are not referenced by any container.
3. Call `list_volumes()` and `list_networks()` to survey storage and networks.
4. Ask the user to confirm before running any prune operations.
5. With confirmation, run:
   - `prune_containers()` to remove stopped containers.
   - `prune_images()` (or `prune_images(all=True)`) to remove unused images.
   - `prune_volumes()` only if the user explicitly confirms all orphaned volumes can be deleted.
   - `prune_networks()` to remove unused networks.
6. Run `list_containers()`, `list_images()`, `list_volumes()` again to confirm the cleanup.

Start by listing all containers now."""


@mcp.prompt()
def setup_private_registry(registry_url: str) -> str:
    """
    Guide through logging into a private registry and pulling or pushing an image.
    """
    return f"""You are helping set up authentication with a private container registry.

Registry: {registry_url!r}

Steps:
1. Ask the user for their registry username and password (do not log or store them).
2. Call `registry_login("{registry_url}", username="<username>", password="<password>")`.
3. If login succeeds, confirm and proceed with the user's intended operation:
   - To pull an image: call `pull_image("<registry>/<image>:<tag>")`.
   - To push an image: first `tag_image("local:tag", "{registry_url}/<image>:<tag>")`,
     then `push_image("{registry_url}/<image>:<tag>")`.
4. If login fails, show the error and suggest checking credentials or network access.

Start by asking the user for their credentials."""
