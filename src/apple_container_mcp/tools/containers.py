"""Container lifecycle tools: run, list, start, stop, remove, export, exec, logs, inspect, prune."""

import os
from typing import Dict, Any, List, Optional

from . import mcp, _DESTRUCTIVE, _DANGEROUS_FLAGS, _normalize_list_result, _run_container_cmd, ContainerCLIError


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

    # Restrict env_file to paths within the user's home directory to prevent
    # an LLM (or prompt injection) from reading arbitrary system files.
    if env_file:
        home_real = os.path.realpath(os.path.expanduser("~"))
        env_file_real = os.path.realpath(env_file)
        if not (env_file_real == home_real or env_file_real.startswith(home_real + os.sep)):
            return {
                "status": "error",
                "message": f"env_file must be within your home directory ({home_real}).",
            }

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
    """Export a container's filesystem as a tar archive (OCI layout). Requires an output_file path."""
    if not output_file:
        return {"status": "error", "message": "output_file is required to save the tar archive."}

    args = ["export", "-o", output_file, container_id]
    try:
        _run_container_cmd(args)
        return {"status": "ok", "message": f"Successfully exported container {container_id} to {output_file}."}
    except ContainerCLIError as e:
        return {"status": "error", "message": f"Failed to export container {container_id}.", "details": e.stderr}


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


# --- Cleanup ---


@mcp.tool(annotations=_DESTRUCTIVE)
def prune_containers() -> Dict[str, Any]:
    """Removes all stopped containers to reclaim disk space. WARNING: this is irreversible."""
    try:
        _run_container_cmd(["prune"])
        return {"status": "ok", "message": "Successfully pruned stopped containers."}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to prune containers.", "details": e.stderr}


@mcp.tool()
def stats_container(containers: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Get a one-shot resource-usage snapshot for one or more containers.

    Requires Apple Container 0.12+ (the `stats` subcommand was added in 0.12).

    This MCP tool always uses the non-streaming form (`--no-stream`) to fit the
    request/response model. The CLI's default streaming mode would block the
    subprocess until killed by our timeout. For continuous streaming, use the
    `container stats` CLI directly.

    Args:
        containers: Optional list of container IDs or names.
            - None or empty list: return stats for ALL running containers.
            - Non-empty list: return stats for the named containers.

            For a single container, pass a single-element list, e.g. ["abc"].

    Returns:
        On success: {"status": "ok", "stats": <list of per-container stats>}
            Each entry is the parsed JSON object the CLI emits per container.
        On error:   {"status": "error", "message": str, "details": str}
    """
    args = ["stats", "--no-stream"]
    if containers:
        args.extend(containers)
    try:
        result = _run_container_cmd(args)
        return {"status": "ok", "stats": result}
    except ContainerCLIError as e:
        return {"status": "error", "message": "Failed to retrieve container stats", "details": e.stderr}
