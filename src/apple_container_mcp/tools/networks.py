"""Network management tools."""

from typing import Dict, Any, Optional

from . import mcp, _DESTRUCTIVE, _normalize_list_result, _run_container_cmd, ContainerCLIError


@mcp.tool()
def create_network(name: str, subnet: Optional[str] = None) -> Dict[str, Any]:
    """
    Creates a new network with the given name and optional subnet.

    `container network create` has no --mtu flag. MTU is set per attachment instead,
    e.g. run_container(..., network="my-net,mtu=1400").
    """
    args = ["network", "create"]
    if subnet:
        args.extend(["--subnet", subnet])
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
