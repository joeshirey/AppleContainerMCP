"""
Apple Container MCP Server — tool registry.

This package splits the MCP tools into domain-specific submodules.
The shared ``mcp`` FastMCP instance lives here and is imported by every
submodule so that tools, prompts, and resources all register against the
same server.

Submodules are imported at the bottom of this file to trigger tool
registration via their ``@mcp.tool()`` / ``@mcp.prompt()`` /
``@mcp.resource()`` decorators.
"""

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from typing import Any, List

from ..cli_wrapper import _run_container_cmd as _run_container_cmd  # noqa: F401 — re-exported for submodules
from ..cli_wrapper import ContainerCLIError as ContainerCLIError  # noqa: F401 — re-exported for submodules

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
    Normalise the raw output from a ``container … ls`` command into a plain list.

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


# ---------------------------------------------------------------------------
# Import submodules to trigger tool/prompt/resource registration.
# The order does not matter — each submodule registers against ``mcp``.
# ---------------------------------------------------------------------------
from . import system  # noqa: E402, F401
from . import containers  # noqa: E402, F401
from . import images  # noqa: E402, F401
from . import networks  # noqa: E402, F401
from . import volumes  # noqa: E402, F401
from . import registry  # noqa: E402, F401
from . import builder  # noqa: E402, F401
from . import prompts  # noqa: E402, F401

# ---------------------------------------------------------------------------
# Re-export every public symbol so that existing ``from … .tools import X``
# continues to work for both ``server.py`` and the test suite.
# ---------------------------------------------------------------------------
from .system import (  # noqa: E402, F401
    get_system_status_resource,
    check_apiserver_status,
    start_system,
    stop_system,
    system_status,
)
from .containers import (  # noqa: E402, F401
    run_container,
    list_containers,
    stop_container,
    start_container,
    remove_container,
    export_container,
    get_logs,
    inspect_container,
    exec_in_container,
    prune_containers,
)
from .images import (  # noqa: E402, F401
    active_builds,
    _builds_lock,
    _build_id_counter,
    _run_build_thread,
    pull_image,
    build_image,
    check_build_status,
    list_builds,
    list_images,
    remove_image,
    prune_images,
    tag_image,
    push_image,
    inspect_image,
)
from .networks import (  # noqa: E402, F401
    create_network,
    remove_network,
    list_networks,
    inspect_network,
    prune_networks,
)
from .volumes import (  # noqa: E402, F401
    create_volume,
    remove_volume,
    list_volumes,
    inspect_volume,
    prune_volumes,
)
from .registry import (  # noqa: E402, F401
    registry_login,
    registry_logout,
)
from .builder import (  # noqa: E402, F401
    builder_start,
    builder_stop,
    builder_status,
)
from .prompts import (  # noqa: E402, F401
    troubleshoot_container,
    build_and_run_workflow,
    cleanup_environment,
    setup_private_registry,
)
