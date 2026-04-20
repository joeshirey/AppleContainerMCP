"""MCP prompts — guided multi-step workflows for common tasks."""

from typing import Optional

from . import mcp


@mcp.prompt()
def troubleshoot_container(container_id: str) -> str:
    """
    Generate a troubleshooting workflow for a failing or misbehaving container.
    Inspects the container, fetches its recent logs, and provides guided next steps.
    """
    return f"""You are helping troubleshoot a container with ID or name: {container_id!r}.

Please follow these steps in order:
1. Call `inspect_container("{container_id}")` to get its current state and configuration.
2. Call `get_logs("{container_id}", limit=200)` to see recent stdout/stderr output.
3. Based on the state and logs:
   - If the container has exited, check the exit code and last log lines for error messages.
   - If the container is running but unhealthy, look for crash loops, OOM signals, or port conflicts.
   - If there are permission errors, check the user and volume mount configuration.
4. Suggest concrete remediation steps (restart, fix config, rebuild image, etc.).

Start by calling inspect_container now."""


@mcp.prompt()
def build_and_run_workflow(context_path: str, image_tag: str, port: Optional[str] = None) -> str:
    """
    Guide through the full build-tag-run workflow for a local project.
    Ensures the builder is running, builds the image, then runs it.
    """
    port_hint = f" with port mapping {port!r}" if port else ""
    return f"""You are helping build and run a container image from a local project.

Context path: {context_path!r}
Image tag: {image_tag!r}

Please follow these steps:
1. Call `builder_status()` to check if the image builder is running.
   - If not running, call `builder_start()` first and wait for confirmation.
2. Call `system_status()` to verify the container system service is active.
   - If not running, call `start_system()`.
3. Call `build_image("{context_path}", tag="{image_tag}")` to start an async build.
   - Note the returned build_id.
4. Poll `check_build_status(build_id)` every 10–15 seconds until state is "completed" or "failed".
   - If failed, show the error details and suggest fixes.
5. Once built successfully, call `run_container("{image_tag}"{f', ports=["{port}"]' if port else ""})`{port_hint}.
6. Confirm the container is running with `list_containers()`.

Start by checking builder_status now."""


@mcp.prompt()
def cleanup_environment() -> str:
    """
    Guide through safely cleaning up stopped containers, unused images, and orphaned volumes/networks.
    Reviews what exists before removing anything.
    """
    return """You are helping clean up a container environment to reclaim disk space.

Please follow these steps carefully — cleanup operations are irreversible:

1. Call `list_containers(include_stopped=True)` to see all containers including stopped ones.
   - Identify which stopped containers can be safely removed.
2. Call `list_images()` to see all local images.
   - Note which images are not referenced by any container.
3. Call `list_volumes()` and `list_networks()` to survey storage and networks.
4. Ask the user to confirm before running any prune operations.
5. With confirmation, run:
   - `prune_containers()` to remove stopped containers.
   - `prune_images()` (or `prune_images(remove_all=True)`) to remove unused images.
   - `prune_volumes()` only if the user explicitly confirms all orphaned volumes can be deleted.
   - `prune_networks()` to remove unused networks.
6. Run `list_containers()`, `list_images()`, `list_volumes()` again to confirm the cleanup.

Start by listing all containers now."""


@mcp.prompt()
def setup_private_registry(registry_url: str) -> str:
    """
    Guide through logging into a private registry and pulling or pushing an image.
    """
    return f"""You are helping set up authentication with a private container registry.

Registry: {registry_url!r}

Steps:
1. Ask the user for their registry username and password (do not log or store them).
2. Call `registry_login("{registry_url}", username="<username>", password="<password>")`.
3. If login succeeds, confirm and proceed with the user's intended operation:
   - To pull an image: call `pull_image("<registry>/<image>:<tag>")`.
   - To push an image: first `tag_image("local:tag", "{registry_url}/<image>:<tag>")`,
     then `push_image("{registry_url}/<image>:<tag>")`.
4. If login fails, show the error and suggest checking credentials or network access.

Start by asking the user for their credentials."""
