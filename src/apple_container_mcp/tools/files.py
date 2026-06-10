"""Host<->container file transfer tools (container cp / copy)."""

import os
from typing import Dict, Any

from . import mcp, _run_container_cmd, ContainerCLIError, _validate_home_path


@mcp.tool()
def copy_to_container(source: str, container_id: str, dest: str) -> Dict[str, Any]:
    """
    Copy a file or folder from the host into a container.

    The host ``source`` path must be within your home directory. ``dest`` is the
    path inside the container.
    Example: copy_to_container("~/project/config.yaml", "web", "/etc/app/config.yaml")
    """
    source = os.path.expanduser(source)
    path_error = _validate_home_path(source)
    if path_error:
        return {"status": "error", "message": f"source invalid: {path_error}"}
    try:
        _run_container_cmd(["cp", source, f"{container_id}:{dest}"])
        return {"status": "ok", "message": f"Copied '{source}' to {container_id}:{dest}."}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to copy file into container", "details": e.stderr}


@mcp.tool()
def copy_from_container(container_id: str, source: str, dest: str) -> Dict[str, Any]:
    """
    Copy a file or folder out of a container onto the host.

    ``source`` is the path inside the container. The host ``dest`` path must be
    within your home directory.
    Example: copy_from_container("web", "/var/log/app.log", "~/logs/app.log")
    """
    dest = os.path.expanduser(dest)
    path_error = _validate_home_path(dest)
    if path_error:
        return {"status": "error", "message": f"dest invalid: {path_error}"}
    try:
        _run_container_cmd(["cp", f"{container_id}:{source}", dest])
        return {"status": "ok", "message": f"Copied {container_id}:{source} to '{dest}'."}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to copy file from container", "details": e.stderr}
