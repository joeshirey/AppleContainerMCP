"""Image management tools and the asynchronous build state machine."""

import itertools
import os
import threading
import time
from typing import Dict, Any, List, Optional

from . import mcp, _DESTRUCTIVE, _normalize_list_result, _run_container_cmd, ContainerCLIError


@mcp.tool()
def pull_image(image: str) -> Dict[str, Any]:
    """Download an image from a registry."""
    try:
        _run_container_cmd(["image", "pull", image])
        return {"status": "ok", "message": f"Successfully pulled image '{image}'."}
    except ContainerCLIError as e:
        return {"status": "error", "message": f"Failed to pull image '{image}'.", "details": e.stderr}


# ---------------------------------------------------------------------------
# Asynchronous build state machine
# ---------------------------------------------------------------------------

# Thread-safe storage and counter for active builds.
# active_builds: maps unique build_id (str) to a dict with 'state' and 'updated_at' (epoch float).
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
    # Use os.sep suffix to prevent prefix-match bypasses (e.g. /Users/joe vs /Users/joey).
    home = os.path.expanduser("~")
    real_path = os.path.realpath(context_path)
    home_real = os.path.realpath(home)
    if not (real_path == home_real or real_path.startswith(home_real + os.sep)):
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


# --- Cleanup & Prune ---


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
