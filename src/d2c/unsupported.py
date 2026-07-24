from dataclasses import dataclass


@dataclass(frozen=True)
class UnsupportedCommand:
    hint: str


UNSUPPORTED: dict[str, UnsupportedCommand] = {
    "commit": UnsupportedCommand(
        hint="Build from a Dockerfile instead — Apple Container doesn't support creating images from running containers."
    ),
    "compose": UnsupportedCommand(
        hint="No equivalent — Apple Container has no orchestration layer. Run containers individually with 'container run'."
    ),
    "diff": UnsupportedCommand(
        hint="No equivalent — use 'container exec' to inspect the filesystem manually."
    ),
    "events": UnsupportedCommand(
        hint="No equivalent — use 'container logs <name>' for output or 'container inspect <name>' for state changes."
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
        hint="No equivalent — poll with 'container inspect <name>' and check the container state."
    ),
    "manifest": UnsupportedCommand(
        hint="No equivalent — use 'container image inspect <image>' for local image metadata."
    ),
    "checkpoint": UnsupportedCommand(
        hint="No equivalent — Apple Container doesn't support container checkpointing."
    ),
    "context": UnsupportedCommand(
        hint="No equivalent — Apple Container has no context switching; it always uses the local system service."
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
        hint="No equivalent — Apple Container has no plugin system."
    ),
}
