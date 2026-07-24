import subprocess


def dry_run(docker_args: list[str], container_args: list[str], note: str | None) -> None:
    """Print the Docker→Apple Container translation without executing."""
    docker_cmd = "docker " + " ".join(docker_args)
    container_cmd = " ".join(container_args)
    print(f"[d2c dry-run] {docker_cmd}")
    print(f"           → {container_cmd}")
    if note:
        print(f"           ℹ  {note}")


def execute(container_args: list[str]) -> int:
    """Run the translated Apple Container command. Returns the process exit code."""
    result = subprocess.run(container_args)
    return result.returncode
