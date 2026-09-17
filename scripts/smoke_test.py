"""Opt-in live smoke test: uv run python scripts/smoke_test.py.

Requires a running Apple Container 1.4.1+ service. Creates uniquely named
resources and removes only those resources; never stops the system or prunes.
"""

import argparse
import json
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

from apple_container_mcp import tools


def check(result):
    if result.get("status") != "ok":
        raise RuntimeError(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--registry",
        action="store_true",
        help="Also test HTTP push/pull through a local registry (requires host-to-container networking)",
    )
    options = parser.parse_args()
    prefix = "mcp-smoke-" + uuid.uuid4().hex[:10]
    created_containers = []
    created_volumes = []
    created_networks = []
    image = prefix + ":test"
    built = False
    registry_image = None

    def step(name, result):
        check(result)
        print(f"PASS {name}", flush=True)
        return result

    try:
        step("environment", tools.check_environment())
        step("status", tools.system_status())
        step("HTTPS pull", tools.pull_image("alpine:3.22", scheme="https"))
        step("network create", tools.create_network(prefix))
        created_networks.append(prefix)
        step("network inspect", tools.inspect_network(prefix))
        for suffix in ("rw", "ro"):
            volume = prefix + "-" + suffix
            step("volume create " + suffix, tools.create_volume(volume))
            created_volumes.append(volume)
            step("volume inspect " + suffix, tools.inspect_volume(volume))
        step(
            "run",
            tools.run_container(
                "alpine:3.22",
                name=prefix,
                network=prefix,
                volumes=[f"{prefix}-rw:/data", f"{prefix}-ro:/readonly:ro"],
                args_override=["sh", "-c", "echo smoke-ready; sleep 600"],
            ),
        )
        created_containers.append(prefix)
        step("list", tools.list_containers())
        step("inspect", tools.inspect_container(prefix))
        step("logs", tools.get_logs(prefix))
        step("stats", tools.stats_container([prefix]))
        step("exec", tools.exec_in_container(prefix, ["sh", "-c", "echo smoke > /data/check; cat /data/check"]))
        with tempfile.TemporaryDirectory(prefix=prefix, dir=Path.home()) as temp:
            context = Path(temp)
            source = context / "input.txt"
            source.write_text("copy-round-trip\n")
            step("copy to", tools.copy_to_container(str(source), prefix, "/tmp/input.txt"))
            dest = context / "output.txt"
            step("copy from", tools.copy_from_container(prefix, "/tmp/input.txt", str(dest)))
            assert dest.read_text() == source.read_text()
            step("clean with writable/read-only volumes", tools.clean_container(prefix))
            step("data after clean", tools.exec_in_container(prefix, ["cat", "/data/check"]))
            step("stop", tools.stop_container(prefix))
            assert tools.clean_container(prefix)["status"] == "error"
            print("PASS clean rejects stopped container", flush=True)
            step("start", tools.start_container(prefix))
            step("builder start", tools.builder_start())
            (context / "Dockerfile").write_text('FROM alpine:3.22\nRUN echo built > /built\nCMD ["cat", "/built"]\n')
            result = step("build submitted", tools.build_image(str(context), tag=image))
            deadline = time.monotonic() + 300
            while time.monotonic() < deadline:
                status = tools.check_build_status(result["build_id"])
                state = check(status)["build_status"]["state"]
                if state == "completed":
                    built = True
                    print("PASS build completed", flush=True)
                    break
                if state == "failed":
                    raise RuntimeError(status)
                time.sleep(1)
            else:
                raise TimeoutError("build did not finish")
        if options.registry:
            step("registry image pull", tools.pull_image("registry:3"))
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
            registry_name = prefix + "-registry"
            step(
                "run HTTP registry",
                tools.run_container("registry:3", name=registry_name, ports=[f"127.0.0.1:{port}:5000"]),
            )
            created_containers.append(registry_name)
            target = f"localhost:{port}/{prefix}:test"
            step("tag for HTTP registry", tools.tag_image(image, target))
            registry_image = target
            step("HTTP push", tools.push_image(registry_image, scheme="http"))
            step("remove local registry tag", tools.remove_image(registry_image))
            registry_image = None
            step("HTTP pull", tools.pull_image(target, scheme="http"))
            registry_image = target
        for args in (["info", "--format", "json"], ["version", "--format", "json"], ["ps", "--format", "json"]):
            result = subprocess.run(["d2c", *args], check=True, capture_output=True, text=True)
            json.loads(result.stdout)
            print("PASS d2c " + args[0], flush=True)
    finally:
        cleanup_errors = []

        def cleanup(label, result):
            if result.get("status") != "ok":
                cleanup_errors.append((label, result))
                print(f"FAIL cleanup {label}: {result}", file=sys.stderr, flush=True)
            else:
                print(f"PASS {label}", flush=True)

        for name in created_containers:
            cleanup("remove container", tools.remove_container(name, force=True))
        for name in created_volumes:
            cleanup("remove volume", tools.remove_volume(name))
        for name in created_networks:
            cleanup("remove network", tools.remove_network(name))
        if registry_image:
            cleanup("remove registry tag", tools.remove_image(registry_image))
        if built:
            cleanup("remove built image", tools.remove_image(image))
        if cleanup_errors and sys.exc_info()[0] is None:
            raise RuntimeError(f"Smoke test cleanup failed: {cleanup_errors}")


if __name__ == "__main__":
    main()
