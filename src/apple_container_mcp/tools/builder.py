"""Builder management tools."""

from typing import Dict, Any

from . import mcp, _run_container_cmd, ContainerCLIError


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
