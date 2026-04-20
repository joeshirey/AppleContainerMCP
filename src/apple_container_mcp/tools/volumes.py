"""Volume management tools."""

from typing import Dict, Any, Optional

from . import mcp, _DESTRUCTIVE, _normalize_list_result, _run_container_cmd, ContainerCLIError


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
