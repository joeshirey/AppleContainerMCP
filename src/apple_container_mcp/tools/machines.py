"""Container machine tools — persistent Linux environments (Apple Container 1.0)."""

from typing import Dict, Any, List, Optional

from . import mcp, _DESTRUCTIVE, _normalize_list_result, _run_container_cmd, ContainerCLIError


@mcp.tool()
def create_machine(
    image: str,
    name: Optional[str] = None,
    cpus: Optional[int] = None,
    memory: Optional[str] = None,
    home_mount: Optional[str] = None,
    set_default: bool = False,
    no_boot: bool = False,
) -> Dict[str, Any]:
    """
    Create and boot a container machine (a persistent Linux environment) from an image.
    home_mount is one of 'ro', 'rw', 'none'.
    Example: create_machine("alpine:3.22", name="dev", cpus=4, memory="8G")
    """
    args = ["machine", "create"]
    if name:
        args.extend(["--name", name])
    if cpus is not None:
        args.extend(["--cpus", str(cpus)])
    if memory:
        args.extend(["--memory", memory])
    if home_mount:
        args.extend(["--home-mount", home_mount])
    if set_default:
        args.append("--set-default")
    if no_boot:
        args.append("--no-boot")
    args.append(image)
    try:
        _run_container_cmd(args)
        return {"status": "ok", "message": f"Created container machine from '{image}'."}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to create container machine", "details": e.stderr}


@mcp.tool()
def run_machine(
    command: List[str],
    name: Optional[str] = None,
    env: Optional[List[str]] = None,
    workdir: Optional[str] = None,
    user: Optional[str] = None,
    detach: bool = False,
    root: bool = False,
) -> Dict[str, Any]:
    """
    Run a command in a container machine (booting it if necessary). If name is omitted,
    the default machine is used.
    Example: run_machine(["uname", "-a"], name="dev")
    """
    args = ["machine", "run"]
    if name:
        args.extend(["-n", name])
    if detach:
        args.append("-d")
    if root:
        args.append("--root")
    if user:
        args.extend(["-u", user])
    if workdir:
        args.extend(["-w", workdir])
    if env:
        for e in env:
            args.extend(["-e", e])
    args.extend(command)
    try:
        result = _run_container_cmd(args)
        output = result.get("raw_output") if isinstance(result, dict) else result
        return {"status": "ok", "output": output}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to run command in container machine", "details": e.stderr}


@mcp.tool()
def list_machines() -> Dict[str, Any]:
    """List container machines."""
    try:
        result = _run_container_cmd(["machine", "ls"])
        machines = _normalize_list_result(result)
        return {"status": "ok", "machines": machines, "count": len(machines)}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to list container machines", "details": e.stderr}


@mcp.tool()
def inspect_machine(name: Optional[str] = None) -> Dict[str, Any]:
    """Display detailed information about a container machine (default machine if name omitted)."""
    args = ["machine", "inspect"]
    if name:
        args.append(name)
    try:
        result = _run_container_cmd(args)
        return {"status": "ok", "inspection": result}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to inspect container machine", "details": e.stderr}


@mcp.tool()
def set_machine(
    name: Optional[str] = None,
    cpus: Optional[int] = None,
    memory: Optional[str] = None,
    home_mount: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Set container machine configuration (takes effect after restart). home_mount is one
    of 'ro', 'rw', 'none'. Applies to the default machine if name is omitted.
    """
    args = ["machine", "set"]
    if name:
        args.extend(["-n", name])
    if cpus is not None:
        args.append(f"cpus={cpus}")
    if memory:
        args.append(f"memory={memory}")
    if home_mount:
        args.append(f"home-mount={home_mount}")
    try:
        _run_container_cmd(args)
        return {"status": "ok", "message": "Updated container machine configuration."}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to set container machine configuration", "details": e.stderr}


@mcp.tool()
def set_default_machine(name: str) -> Dict[str, Any]:
    """Set the default container machine by ID/name."""
    try:
        _run_container_cmd(["machine", "set-default", name])
        return {"status": "ok", "message": f"Set '{name}' as the default container machine."}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to set default container machine", "details": e.stderr}


@mcp.tool()
def machine_logs(name: Optional[str] = None, boot: bool = False, limit: Optional[int] = None) -> Dict[str, Any]:
    """
    Fetch container machine logs (default machine if name omitted). Set boot=True for the
    boot log; limit caps the number of trailing lines.
    """
    args = ["machine", "logs"]
    if boot:
        args.append("--boot")
    if limit is not None:
        args.extend(["-n", str(limit)])
    if name:
        args.append(name)
    try:
        result = _run_container_cmd(args)
        logs = result.get("raw_output", "") if isinstance(result, dict) else str(result)
        return {"status": "ok", "logs": logs}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to fetch container machine logs", "details": e.stderr}


@mcp.tool(annotations=_DESTRUCTIVE)
def stop_machine(name: Optional[str] = None) -> Dict[str, Any]:
    """Stop a running container machine (default machine if name omitted)."""
    args = ["machine", "stop"]
    if name:
        args.append(name)
    try:
        _run_container_cmd(args)
        return {"status": "ok", "message": "Stopped container machine."}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to stop container machine", "details": e.stderr}


@mcp.tool(annotations=_DESTRUCTIVE)
def delete_machine(name: str) -> Dict[str, Any]:
    """Delete a container machine by ID/name. WARNING: irreversible."""
    try:
        _run_container_cmd(["machine", "delete", name])
        return {"status": "ok", "message": f"Deleted container machine '{name}'."}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to delete container machine", "details": e.stderr}
