from dataclasses import dataclass, field


@dataclass(frozen=True)
class CommandTranslation:
    container_cmd: list[str]
    flag_map: dict[str, str] = field(default_factory=dict)
    note: str | None = None


COMMANDS: dict[str, CommandTranslation] = {
    # Container lifecycle
    "ps": CommandTranslation(container_cmd=["container", "list"]),
    "run": CommandTranslation(container_cmd=["container", "run"]),
    "exec": CommandTranslation(container_cmd=["container", "exec"]),
    "stop": CommandTranslation(container_cmd=["container", "stop"]),
    "start": CommandTranslation(container_cmd=["container", "start"]),
    "kill": CommandTranslation(container_cmd=["container", "kill"]),
    "rm": CommandTranslation(container_cmd=["container", "delete"], note="'rm' maps to 'delete' in Apple Container"),
    "logs": CommandTranslation(container_cmd=["container", "logs"]),
    "inspect": CommandTranslation(container_cmd=["container", "inspect"]),
    "cp": CommandTranslation(container_cmd=["container", "copy"]),
    "create": CommandTranslation(container_cmd=["container", "create"]),
    "export": CommandTranslation(container_cmd=["container", "export"]),
    "stats": CommandTranslation(container_cmd=["container", "stats"]),
    # Image commands
    "images": CommandTranslation(container_cmd=["container", "image", "list"]),
    "pull": CommandTranslation(container_cmd=["container", "image", "pull"]),
    "push": CommandTranslation(container_cmd=["container", "image", "push"]),
    "rmi": CommandTranslation(
        container_cmd=["container", "image", "delete"],
        note="'rmi' maps to Apple Container's 'image delete' subcommand",
    ),
    "tag": CommandTranslation(container_cmd=["container", "image", "tag"]),
    "build": CommandTranslation(container_cmd=["container", "build"]),
    "load": CommandTranslation(
        container_cmd=["container", "image", "load"],
        note="'load' maps to Apple Container's 'image load' subcommand",
    ),
    "save": CommandTranslation(
        container_cmd=["container", "image", "save"],
        note="'save' maps to Apple Container's 'image save' subcommand",
    ),
    # Registry
    "login": CommandTranslation(container_cmd=["container", "registry", "login"]),
    "logout": CommandTranslation(container_cmd=["container", "registry", "logout"]),
    # System
    "info": CommandTranslation(
        container_cmd=["container", "system", "status"],
        note="'info' maps to 'system status' — Apple Container has no direct 'info' equivalent",
    ),
    "version": CommandTranslation(container_cmd=["container", "system", "version"]),
    # Management command groups (subcommand passed through)
    "network": CommandTranslation(container_cmd=["container", "network"]),
    "volume": CommandTranslation(container_cmd=["container", "volume"]),
    "system": CommandTranslation(container_cmd=["container", "system"]),
    "image": CommandTranslation(container_cmd=["container", "image"]),
    "builder": CommandTranslation(container_cmd=["container", "builder"]),
}


def translate(docker_args: list[str]) -> tuple[list[str], str | None]:
    """Translate Docker CLI args into Apple Container CLI args.

    Handles the Docker management namespace (e.g. 'docker container run' -> look up 'run').
    Raises KeyError if the command is not found in the registry.
    Returns (container_args, note).
    """
    if not docker_args:
        raise KeyError("no command provided")

    cmd = docker_args[0]
    remaining = docker_args[1:]

    # Strip the Docker management namespace: `docker container run` -> look up `run`
    if cmd == "container" and remaining:
        cmd = remaining[0]
        remaining = remaining[1:]

    translation = COMMANDS[cmd]  # raises KeyError if not found

    # flag_map is reserved for future flag renames (e.g. --format differences).
    # No current command uses it, but the code path is tested below.
    translated_remaining = (
        [translation.flag_map.get(arg, arg) for arg in remaining] if translation.flag_map else list(remaining)
    )

    return translation.container_cmd + translated_remaining, translation.note
