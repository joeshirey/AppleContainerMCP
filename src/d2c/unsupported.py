from dataclasses import dataclass


@dataclass(frozen=True)
class UnsupportedCommand:
    hint: str


UNSUPPORTED: dict[str, UnsupportedCommand] = {
    "commit": UnsupportedCommand(
        hint="Build from a Dockerfile instead — Apple Container doesn't support creating images from running containers."
    ),
    "diff": UnsupportedCommand(
        hint="No equivalent — use 'container exec' to inspect the filesystem manually."
    ),
    "events": UnsupportedCommand(
        hint="No equivalent in Apple Container."
    ),
    "history": UnsupportedCommand(
        hint="No equivalent — check your Dockerfile for layer history."
    ),
    "import": UnsupportedCommand(
        hint="No equivalent — build from a Dockerfile or use 'container image pull'."
    ),
    "pause": UnsupportedCommand(
        hint="No equivalent — use 'container stop' to halt a container."
    ),
    "unpause": UnsupportedCommand(
        hint="No equivalent — use 'container start' to resume."
    ),
    "port": UnsupportedCommand(
        hint="No equivalent — check your 'container run -p' arguments."
    ),
    "rename": UnsupportedCommand(
        hint="No equivalent — remove the container and recreate it with the desired name."
    ),
    "restart": UnsupportedCommand(
        hint="No direct equivalent — use 'container stop' then 'container start'."
    ),
    "search": UnsupportedCommand(
        hint="No equivalent — browse registries directly (e.g. hub.docker.com)."
    ),
    "attach": UnsupportedCommand(
        hint="No equivalent — use 'container exec -it <name> /bin/sh' to get an interactive shell."
    ),
    "wait": UnsupportedCommand(
        hint="No equivalent in Apple Container."
    ),
    "manifest": UnsupportedCommand(
        hint="No equivalent in Apple Container."
    ),
    "checkpoint": UnsupportedCommand(
        hint="Not applicable to Apple Container."
    ),
    "context": UnsupportedCommand(
        hint="Apple Container has no context switching."
    ),
    # Swarm commands
    "node": UnsupportedCommand(
        hint="Docker Swarm commands are not applicable to Apple Container."
    ),
    "service": UnsupportedCommand(
        hint="Docker Swarm commands are not applicable to Apple Container."
    ),
    "stack": UnsupportedCommand(
        hint="Docker Swarm commands are not applicable to Apple Container."
    ),
    "swarm": UnsupportedCommand(
        hint="Docker Swarm commands are not applicable to Apple Container."
    ),
    "config": UnsupportedCommand(
        hint="Docker Swarm commands are not applicable to Apple Container."
    ),
    "secret": UnsupportedCommand(
        hint="Docker Swarm commands are not applicable to Apple Container."
    ),
    "plugin": UnsupportedCommand(
        hint="Not applicable to Apple Container."
    ),
}
