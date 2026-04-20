import subprocess

from apple_container_mcp.tools import (
    # system
    check_apiserver_status,
    start_system,
    stop_system,
    system_status,
    # container lifecycle
    run_container,
    list_containers,
    start_container,
    stop_container,
    remove_container,
    export_container,
    prune_containers,
    # exec & logs & inspect
    exec_in_container,
    get_logs,
    inspect_container,
    # image management
    build_image,
    check_build_status,
    list_builds,
    list_images,
    pull_image,
    remove_image,
    prune_images,
    tag_image,
    push_image,
    inspect_image,
    # registry
    registry_login,
    registry_logout,
    # builder
    builder_start,
    builder_stop,
    builder_status,
    # network
    create_network,
    remove_network,
    list_networks,
    inspect_network,
    prune_networks,
    # volume
    create_volume,
    remove_volume,
    list_volumes,
    inspect_volume,
    prune_volumes,
    # prompts
    troubleshoot_container,
    build_and_run_workflow,
    cleanup_environment,
    setup_private_registry,
    # resource
    get_system_status_resource,
)
from apple_container_mcp.cli_wrapper import ContainerCLIError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_cmd(mocker):
    return mocker.patch("apple_container_mcp.tools._run_container_cmd")


# ---------------------------------------------------------------------------
# System tools
# ---------------------------------------------------------------------------


def test_system_status_ok(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = {"version": "1.0", "state": "running"}
    result = system_status()
    assert result["status"] == "ok"
    assert result["system_status"]["version"] == "1.0"
    mock.assert_called_once_with(["system", "status"])


def test_system_status_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("daemon down", 1, "connection refused")
    result = system_status()
    assert result["status"] == "error"


def test_check_apiserver_status_running(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = {"version": "1.0.0"}
    result = check_apiserver_status()
    assert result["status"] == "ok"
    assert "running" in result["message"]


def test_check_apiserver_status_stopped(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("daemon not running", 1, "connection refused")
    result = check_apiserver_status()
    assert result["status"] == "stopped"


def test_start_system_ok(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = {}
    result = start_system()
    assert result["status"] == "ok"
    mock.assert_called_once_with(["system", "start"])


def test_start_system_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("failed", 1, "permission denied")
    result = start_system()
    assert result["status"] == "error"
    assert "permission denied" in result["details"]


def test_stop_system_ok(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = {}
    result = stop_system()
    assert result["status"] == "ok"
    mock.assert_called_once_with(["system", "stop"])


def test_stop_system_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("failed", 1, "not running")
    result = stop_system()
    assert result["status"] == "error"


# ---------------------------------------------------------------------------
# Container lifecycle
# ---------------------------------------------------------------------------


def test_run_container_basic(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = {"raw_output": "12345"}
    result = run_container("debian")
    assert result == {"status": "ok", "id": "12345"}
    mock.assert_called_once_with(["run", "-d", "debian"])


def test_run_container_with_options(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = {"raw_output": "67890"}
    result = run_container(
        "ubuntu",
        cpus=2,
        memory="4g",
        name="my-ubuntu",
        detach=False,
        ports=["8080:80"],
        env=["DEBUG=1"],
        volumes=["/tmp/host:/tmp/container"],
        network="my-net",
    )
    assert result == {"status": "ok", "id": "67890"}
    called_args = mock.call_args[0][0]
    assert "run" in called_args
    assert "--name" in called_args
    assert "my-ubuntu" in called_args
    assert "--cpus" in called_args
    assert "ubuntu" in called_args


def test_run_container_with_init_image(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = {"raw_output": "67890"}
    result = run_container("ubuntu", init_image="my-init-image")
    assert result == {"status": "ok", "id": "67890"}
    called_args = mock.call_args[0][0]
    assert "--init-image" in called_args
    assert "my-init-image" in called_args


def test_run_container_new_flags(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = {"raw_output": "abc"}
    result = run_container(
        "myapp",
        rm=True,
        rosetta=True,
        platform="linux/amd64",
        entrypoint="/bin/sh",
        workdir="/app",
        user="root",
        labels=["env=prod"],
        args_override=["echo", "hi"],
    )
    assert result["status"] == "ok"
    called_args = mock.call_args[0][0]
    assert "--rm" in called_args
    assert "--rosetta" in called_args
    assert "--platform" in called_args
    assert "linux/amd64" in called_args
    assert "--entrypoint" in called_args
    assert "-w" in called_args
    assert "-u" in called_args
    assert "--label" in called_args
    assert "echo" in called_args


def test_run_container_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("Command failed", 125, "Image not found")
    result = run_container("missing-image")
    assert result == {
        "status": "error",
        "message": "Failed to run container",
        "details": "Image not found",
        "exit_code": 125,
    }


def test_run_container_invalid_port(mocker):
    result = run_container("debian", ports=["  "])
    assert result["status"] == "error"
    assert "Port mapping" in result["message"]


def test_run_container_invalid_env(mocker):
    result = run_container("debian", env=["NOEQUALS"])
    assert result["status"] == "error"
    assert "KEY=VALUE" in result["message"]


def test_run_container_invalid_volume(mocker):
    result = run_container("debian", volumes=["/nocopath"])
    assert result["status"] == "error"
    assert "HOST:CONTAINER" in result["message"]


def test_list_containers_with_results(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = [{"id": "abc", "name": "web"}]
    result = list_containers()
    assert result["status"] == "ok"
    assert result["count"] == 1
    assert result["containers"][0]["id"] == "abc"


def test_list_containers_empty(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = {}  # Empty output — the bug case
    result = list_containers()
    assert result["status"] == "ok"
    assert result["containers"] == []
    assert result["count"] == 0


def test_list_containers_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("failed", 1, "daemon down")
    result = list_containers()
    assert result["status"] == "error"


def test_start_container(mocker):
    mock = _mock_cmd(mocker)
    result = start_container("12345")
    assert "Successfully started container 12345." in result["message"]
    mock.assert_called_once_with(["start", "12345"])


def test_start_container_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("failed", 1, "no such container")
    result = start_container("bad-id")
    assert result["status"] == "error"


def test_stop_container_graceful(mocker):
    mock = _mock_cmd(mocker)
    result = stop_container("12345", force=False)
    assert "Successfully executed 'stop' on container 12345." in result["message"]
    mock.assert_called_once_with(["stop", "12345"])


def test_stop_container_force(mocker):
    mock = _mock_cmd(mocker)
    result = stop_container("12345", force=True)
    assert "Successfully executed 'kill' on container 12345." in result["message"]
    mock.assert_called_once_with(["kill", "12345"])


def test_remove_container(mocker):
    mock = _mock_cmd(mocker)
    result = remove_container("12345")
    assert result["status"] == "ok"
    mock.assert_called_once_with(["rm", "12345"])


def test_remove_container_force(mocker):
    mock = _mock_cmd(mocker)
    result = remove_container("12345", force=True)
    assert result["status"] == "ok"
    called_args = mock.call_args[0][0]
    assert "-f" in called_args


def test_remove_container_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("failed", 1, "no such container")
    result = remove_container("bad-id")
    assert result["status"] == "error"


def test_export_container(mocker):
    mock = _mock_cmd(mocker)
    result = export_container("12345", output_file="my-file.tar")
    assert "Successfully exported container 12345 to my-file.tar." in result["message"]
    mock.assert_called_once_with(["export", "-o", "my-file.tar", "12345"])


def test_export_container_no_output_file(mocker):
    result = export_container("12345")
    assert result["status"] == "error"
    assert "output_file is required" in result["message"]


def test_export_container_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("failed", 1, "no such container")
    result = export_container("bad-id", output_file="out.tar")
    assert result["status"] == "error"
    assert "Failed to export" in result["message"]
    assert "no such container" in result["details"]


def test_prune_containers(mocker):
    mock = _mock_cmd(mocker)
    result = prune_containers()
    assert result["status"] == "ok"
    mock.assert_called_once_with(["prune"])


def test_prune_containers_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("failed", 1, "daemon down")
    result = prune_containers()
    assert result["status"] == "error"


# ---------------------------------------------------------------------------
# exec / logs / inspect
# ---------------------------------------------------------------------------


def test_exec_in_container_basic(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = {"raw_output": "uid=0(root)"}
    result = exec_in_container("mycontainer", ["id"])
    assert result["status"] == "ok"
    assert "uid=0" in result["output"]
    called_args = mock.call_args[0][0]
    assert "exec" in called_args
    assert "mycontainer" in called_args
    assert "id" in called_args


def test_exec_in_container_with_options(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = {"raw_output": "hello"}
    result = exec_in_container("c1", ["echo", "hello"], user="root", workdir="/app", env=["X=1"])
    assert result["status"] == "ok"
    called_args = mock.call_args[0][0]
    assert "-u" in called_args
    assert "root" in called_args
    assert "-w" in called_args
    assert "/app" in called_args
    assert "-e" in called_args


def test_exec_in_container_empty_command(mocker):
    result = exec_in_container("c1", [])
    assert result["status"] == "error"
    assert "non-empty" in result["message"]


def test_exec_in_container_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("failed", 127, "command not found")
    result = exec_in_container("c1", ["badcmd"])
    assert result["status"] == "error"
    assert result["exit_code"] == 127


def test_get_logs_success(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = {"raw_output": "line 1\nline 2"}
    result = get_logs("12345", limit=50)
    assert result["status"] == "ok"
    assert result["logs"] == "line 1\nline 2"
    mock.assert_called_once_with(["logs", "-n", "50", "12345"])


def test_get_logs_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("Failed to fetch logs", 1, "No such container")
    result = get_logs("invalid")
    assert result["status"] == "error"
    assert "No such container" in result["details"]
    assert result["exit_code"] == 1


def test_inspect_container_ok(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = {"id": "abc", "state": "running"}
    result = inspect_container("abc")
    assert result["status"] == "ok"
    assert result["inspection"]["id"] == "abc"
    mock.assert_called_once_with(["inspect", "abc"])


def test_inspect_container_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("failed", 1, "no such container")
    result = inspect_container("bad")
    assert result["status"] == "error"


# ---------------------------------------------------------------------------
# Image management
# ---------------------------------------------------------------------------


def test_list_images_with_results(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = [{"repository": "debian", "tag": "latest"}]
    result = list_images()
    assert result["status"] == "ok"
    assert result["count"] == 1


def test_list_images_empty(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = {}
    result = list_images()
    assert result["status"] == "ok"
    assert result["images"] == []
    assert result["count"] == 0


def test_list_images_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("failed", 1, "daemon down")
    result = list_images()
    assert result["status"] == "error"


def test_pull_image_ok(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = {}
    result = pull_image("debian:latest")
    assert result["status"] == "ok"
    assert "debian:latest" in result["message"]
    mock.assert_called_once_with(["image", "pull", "debian:latest"])


def test_pull_image_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("failed", 1, "pull access denied")
    result = pull_image("private/image:tag")
    assert result["status"] == "error"
    assert "pull access denied" in result["details"]


def test_remove_image(mocker):
    mock = _mock_cmd(mocker)
    result = remove_image("debian:latest")
    assert result["status"] == "ok"
    mock.assert_called_once_with(["image", "rm", "debian:latest"])


def test_remove_image_force(mocker):
    mock = _mock_cmd(mocker)
    result = remove_image("debian:latest", force=True)
    assert result["status"] == "ok"
    called_args = mock.call_args[0][0]
    assert "-f" in called_args


def test_remove_image_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("failed", 1, "no such image")
    result = remove_image("bad:image")
    assert result["status"] == "error"


def test_prune_images_all(mocker):
    mock = _mock_cmd(mocker)
    result = prune_images(remove_all=True)
    assert "Successfully pruned unused images." in result["message"]
    mock.assert_called_once_with(["image", "prune", "-a"])


def test_prune_images_default(mocker):
    mock = _mock_cmd(mocker)
    result = prune_images()
    assert result["status"] == "ok"
    mock.assert_called_once_with(["image", "prune"])


def test_prune_images_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("failed", 1, "daemon down")
    result = prune_images()
    assert result["status"] == "error"


def test_tag_image(mocker):
    mock = _mock_cmd(mocker)
    result = tag_image("myapp:latest", "registry.example.com/myapp:v1")
    assert result["status"] == "ok"
    mock.assert_called_once_with(["image", "tag", "myapp:latest", "registry.example.com/myapp:v1"])


def test_tag_image_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("failed", 1, "no such image")
    result = tag_image("bad:src", "dest:tag")
    assert result["status"] == "error"


def test_push_image(mocker):
    mock = _mock_cmd(mocker)
    result = push_image("registry.example.com/myapp:v1")
    assert result["status"] == "ok"
    mock.assert_called_once_with(["image", "push", "registry.example.com/myapp:v1"])


def test_push_image_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("failed", 1, "unauthorized")
    result = push_image("private/image:tag")
    assert result["status"] == "error"


def test_inspect_image_ok(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = {"id": "sha256:abc", "repoTags": ["debian:latest"]}
    result = inspect_image("debian:latest")
    assert result["status"] == "ok"
    assert result["inspection"]["id"] == "sha256:abc"
    mock.assert_called_once_with(["image", "inspect", "debian:latest"])


def test_inspect_image_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("failed", 1, "no such image")
    result = inspect_image("bad:image")
    assert result["status"] == "error"


# ---------------------------------------------------------------------------
# Build tools
# ---------------------------------------------------------------------------


def test_build_image_async_behavior(mocker):
    import threading

    mock_thread_start = mocker.patch.object(threading.Thread, "start")
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("os.path.isdir", return_value=True)
    mocker.patch("os.path.realpath", side_effect=lambda p: p)
    mocker.patch("os.path.expanduser", return_value="/Users/test")

    result = build_image("/Users/test/myproject", secrets=["id=shh,src=secret.txt"])

    assert result["status"] == "ok"
    assert "Build started asynchronously" in result["message"]
    assert "build_" in result["build_id"]
    mock_thread_start.assert_called_once()

    last_build_id = result["build_id"]
    status_result = check_build_status(last_build_id)
    assert status_result["status"] == "ok"
    assert status_result["build_status"]["state"] == "in_progress"


def test_build_image_missing_context(mocker):
    mocker.patch("os.path.exists", return_value=False)
    result = build_image("/nonexistent/path")
    assert result["status"] == "error"
    assert "does not exist" in result["message"]


def test_build_image_not_a_directory(mocker):
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("os.path.isdir", return_value=False)
    result = build_image("/some/file.tar")
    assert result["status"] == "error"
    assert "not a directory" in result["message"]


def test_build_image_path_traversal_blocked(mocker):
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("os.path.isdir", return_value=True)
    mocker.patch("os.path.realpath", side_effect=lambda p: p)
    mocker.patch("os.path.expanduser", return_value="/Users/test")
    result = build_image("/etc/passwd_dir")
    assert result["status"] == "error"
    assert "home directory" in result["message"]


def test_build_image_path_traversal_sibling_prefix(mocker):
    """Ensure /Users/tester doesn't pass the check when home is /Users/test."""
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("os.path.isdir", return_value=True)
    mocker.patch("os.path.realpath", side_effect=lambda p: p)
    mocker.patch("os.path.expanduser", return_value="/Users/test")
    result = build_image("/Users/tester/evil")
    assert result["status"] == "error"
    assert "home directory" in result["message"]


def test_check_build_status_not_found(mocker):
    result = check_build_status("build_nonexistent_xyz")
    assert result["status"] == "error"
    assert "No build found" in result["message"]


def test_list_builds(mocker):
    import threading

    mocker.patch.object(threading.Thread, "start")
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("os.path.isdir", return_value=True)
    mocker.patch("os.path.realpath", side_effect=lambda p: p)
    mocker.patch("os.path.expanduser", return_value="/Users/test")

    build_image("/Users/test/proj")
    result = list_builds()
    assert result["status"] == "ok"
    assert result["count"] == 1


# ---------------------------------------------------------------------------
# Registry tools
# ---------------------------------------------------------------------------


def test_registry_logout(mocker):
    mock = _mock_cmd(mocker)
    result = registry_logout("registry.example.com")
    assert result["status"] == "ok"
    mock.assert_called_once_with(["registry", "logout", "registry.example.com"])


def test_registry_logout_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("failed", 1, "not logged in")
    result = registry_logout("registry.example.com")
    assert result["status"] == "error"


# ---------------------------------------------------------------------------
# Builder tools
# ---------------------------------------------------------------------------


def test_builder_start(mocker):
    mock = _mock_cmd(mocker)
    result = builder_start()
    assert result["status"] == "ok"
    mock.assert_called_once_with(["builder", "start"])


def test_builder_start_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("failed", 1, "already running")
    result = builder_start()
    assert result["status"] == "error"


def test_builder_stop(mocker):
    mock = _mock_cmd(mocker)
    result = builder_stop()
    assert result["status"] == "ok"
    mock.assert_called_once_with(["builder", "stop"])


def test_builder_stop_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("failed", 1, "builder not running")
    result = builder_stop()
    assert result["status"] == "error"
    assert "builder not running" in result["details"]


def test_builder_status(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = {"state": "running"}
    result = builder_status()
    assert result["status"] == "ok"
    assert result["builder_status"]["state"] == "running"
    mock.assert_called_once_with(["builder", "status"])


def test_builder_status_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("failed", 1, "not running")
    result = builder_status()
    assert result["status"] == "error"


# ---------------------------------------------------------------------------
# Network tools
# ---------------------------------------------------------------------------


def test_create_network(mocker):
    mock = _mock_cmd(mocker)
    result = create_network("my-net", subnet="192.168.1.0/24")
    assert "Successfully created network 'my-net'" in result["message"]
    mock.assert_called_once_with(["network", "create", "--subnet", "192.168.1.0/24", "my-net"])


def test_create_network_with_mtu(mocker):
    mock = _mock_cmd(mocker)
    result = create_network("my-net", mtu=1500)
    assert "Successfully created network 'my-net'" in result["message"]
    mock.assert_called_once_with(["network", "create", "--mtu", "1500", "my-net"])


def test_create_network_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("failed", 1, "already exists")
    result = create_network("my-net")
    assert result["status"] == "error"


def test_remove_network(mocker):
    mock = _mock_cmd(mocker)
    result = remove_network("my-net")
    assert result["status"] == "ok"
    mock.assert_called_once_with(["network", "rm", "my-net"])


def test_remove_network_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("failed", 1, "not found")
    result = remove_network("missing-net")
    assert result["status"] == "error"


def test_list_networks_with_results(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = [{"name": "bridge"}]
    result = list_networks()
    assert result["status"] == "ok"
    assert result["count"] == 1


def test_list_networks_empty(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = {}
    result = list_networks()
    assert result["status"] == "ok"
    assert result["networks"] == []
    assert result["count"] == 0


def test_list_networks_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("failed", 1, "daemon down")
    result = list_networks()
    assert result["status"] == "error"


def test_inspect_network_ok(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = {"name": "bridge", "subnet": "10.0.0.0/24"}
    result = inspect_network("bridge")
    assert result["status"] == "ok"
    assert result["inspection"]["name"] == "bridge"
    mock.assert_called_once_with(["network", "inspect", "bridge"])


def test_inspect_network_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("failed", 1, "not found")
    result = inspect_network("bad-net")
    assert result["status"] == "error"


def test_prune_networks(mocker):
    mock = _mock_cmd(mocker)
    result = prune_networks()
    assert result["status"] == "ok"
    mock.assert_called_once_with(["network", "prune"])


def test_prune_networks_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("failed", 1, "daemon down")
    result = prune_networks()
    assert result["status"] == "error"


# ---------------------------------------------------------------------------
# Volume tools
# ---------------------------------------------------------------------------


def test_create_volume(mocker):
    mock = _mock_cmd(mocker)
    result = create_volume("my-vol", size="10G")
    assert "Successfully created volume 'my-vol'" in result["message"]
    mock.assert_called_once_with(["volume", "create", "-s", "10G", "my-vol"])


def test_create_volume_no_size(mocker):
    mock = _mock_cmd(mocker)
    result = create_volume("bare-vol")
    assert result["status"] == "ok"
    mock.assert_called_once_with(["volume", "create", "bare-vol"])


def test_create_volume_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("failed", 1, "already exists")
    result = create_volume("my-vol")
    assert result["status"] == "error"


def test_remove_volume(mocker):
    mock = _mock_cmd(mocker)
    result = remove_volume("my-vol")
    assert result["status"] == "ok"
    mock.assert_called_once_with(["volume", "rm", "my-vol"])


def test_remove_volume_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("failed", 1, "not found")
    result = remove_volume("missing-vol")
    assert result["status"] == "error"


def test_list_volumes_with_results(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = [{"name": "data"}]
    result = list_volumes()
    assert result["status"] == "ok"
    assert result["count"] == 1


def test_list_volumes_empty(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = {}
    result = list_volumes()
    assert result["status"] == "ok"
    assert result["volumes"] == []
    assert result["count"] == 0


def test_list_volumes_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("failed", 1, "daemon down")
    result = list_volumes()
    assert result["status"] == "error"


def test_inspect_volume_ok(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = {"name": "data", "size": "10G"}
    result = inspect_volume("data")
    assert result["status"] == "ok"
    assert result["inspection"]["name"] == "data"
    mock.assert_called_once_with(["volume", "inspect", "data"])


def test_inspect_volume_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("failed", 1, "not found")
    result = inspect_volume("bad-vol")
    assert result["status"] == "error"


def test_prune_volumes(mocker):
    mock = _mock_cmd(mocker)
    result = prune_volumes()
    assert result["status"] == "ok"
    mock.assert_called_once_with(["volume", "prune"])


def test_prune_volumes_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("failed", 1, "daemon down")
    result = prune_volumes()
    assert result["status"] == "error"


# ---------------------------------------------------------------------------
# registry_login
# ---------------------------------------------------------------------------


def test_registry_login_success(mocker):
    mock_run = mocker.patch("apple_container_mcp.tools.subprocess.run")
    mock_proc = mocker.Mock()
    mock_proc.returncode = 0
    mock_proc.stderr = ""
    mock_run.return_value = mock_proc

    result = registry_login("registry.example.com", "user", "secret")

    assert result["status"] == "ok"
    assert "registry.example.com" in result["message"]
    mock_run.assert_called_once_with(
        ["container", "registry", "login", "--username", "user", "--password-stdin", "registry.example.com"],
        input="secret",
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_registry_login_failure(mocker):
    mock_run = mocker.patch("apple_container_mcp.tools.subprocess.run")
    mock_proc = mocker.Mock()
    mock_proc.returncode = 1
    mock_proc.stderr = "unauthorized: incorrect username or password"
    mock_run.return_value = mock_proc

    result = registry_login("registry.example.com", "user", "wrongpass")

    assert result["status"] == "error"
    assert "registry.example.com" in result["message"]
    assert "unauthorized" in result["details"]


def test_registry_login_timeout(mocker):
    mock_run = mocker.patch("apple_container_mcp.tools.subprocess.run")
    mock_run.side_effect = subprocess.TimeoutExpired(cmd=["container"], timeout=30)

    result = registry_login("registry.example.com", "user", "pass")

    assert result["status"] == "error"
    assert "timed out" in result["message"].lower()


def test_registry_login_cli_not_found(mocker):
    mock_run = mocker.patch("apple_container_mcp.tools.subprocess.run")
    mock_run.side_effect = FileNotFoundError

    result = registry_login("registry.example.com", "user", "pass")

    assert result["status"] == "error"
    assert "not found" in result["message"].lower()


# ---------------------------------------------------------------------------
# args_override validation
# ---------------------------------------------------------------------------


def test_run_container_args_override_blocked_privileged(mocker):
    result = run_container("debian", args_override=["--privileged"])
    assert result["status"] == "error"
    assert "--privileged" in result["message"]


def test_run_container_args_override_blocked_cap_add(mocker):
    result = run_container("debian", args_override=["--cap-add", "NET_ADMIN"])
    assert result["status"] == "error"
    assert "--cap-add" in result["message"]


def test_run_container_args_override_safe_passthrough(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = {"raw_output": "abc"}
    result = run_container("debian", args_override=["bash", "-c", "echo hi"])
    assert result["status"] == "ok"
    called_args = mock.call_args[0][0]
    assert "bash" in called_args
    assert "echo hi" in called_args


# ---------------------------------------------------------------------------
# list_containers — include_stopped parameter rename
# ---------------------------------------------------------------------------


def test_list_containers_include_stopped_false(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = []
    result = list_containers(include_stopped=False)
    assert result["status"] == "ok"
    # Should NOT have -a in the args
    called_args = mock.call_args[0][0]
    assert "-a" not in called_args


def test_list_containers_include_stopped_true(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = []
    result = list_containers(include_stopped=True)
    assert result["status"] == "ok"
    called_args = mock.call_args[0][0]
    assert "-a" in called_args


# ---------------------------------------------------------------------------
# _normalize_list_result — third branch (non-list, non-empty dict)
# ---------------------------------------------------------------------------


def test_list_containers_single_dict_result(mocker):
    """If the CLI returns a single dict (not a list), it should be wrapped."""
    mock = _mock_cmd(mocker)
    mock.return_value = {"id": "abc", "name": "solo"}
    result = list_containers()
    assert result["status"] == "ok"
    assert result["count"] == 1
    assert result["containers"][0]["id"] == "abc"


def test_list_images_single_dict_result(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = {"repository": "myapp", "tag": "latest"}
    result = list_images()
    assert result["status"] == "ok"
    assert result["count"] == 1


def test_list_networks_single_dict_result(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = {"name": "mynet"}
    result = list_networks()
    assert result["status"] == "ok"
    assert result["count"] == 1


def test_list_volumes_single_dict_result(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = {"name": "myvol"}
    result = list_volumes()
    assert result["status"] == "ok"
    assert result["count"] == 1


# ---------------------------------------------------------------------------
# check_apiserver_status — improved error routing
# ---------------------------------------------------------------------------


def test_check_apiserver_status_other_error(mocker):
    """An error that is not a daemon-not-running error should return 'error', not 'stopped'."""
    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("something unexpected", 1, "internal error")
    result = check_apiserver_status()
    assert result["status"] == "error"
    assert result.get("error") != "The container-apiserver daemon is not reachable."


# ---------------------------------------------------------------------------
# _run_build_thread integration — actual build execution
# ---------------------------------------------------------------------------


def test_build_thread_records_completion(mocker):
    """_run_build_thread should mark the build as 'completed' on success."""
    import threading
    from apple_container_mcp.tools import _run_build_thread, active_builds, _builds_lock
    import time

    build_id = "test_build_complete"
    with _builds_lock:
        active_builds[build_id] = {"state": "in_progress", "updated_at": time.monotonic()}

    mock = _mock_cmd(mocker)
    mock.return_value = {"raw_output": "sha256:abc"}

    thread = threading.Thread(target=_run_build_thread, args=(build_id, "/some/path"))
    thread.start()
    thread.join(timeout=5)

    with _builds_lock:
        assert active_builds[build_id]["state"] == "completed"


def test_build_thread_records_failure(mocker):
    """_run_build_thread should mark the build as 'failed' on ContainerCLIError."""
    import threading
    from apple_container_mcp.tools import _run_build_thread, active_builds, _builds_lock
    import time

    build_id = "test_build_fail"
    with _builds_lock:
        active_builds[build_id] = {"state": "in_progress", "updated_at": time.monotonic()}

    mock = _mock_cmd(mocker)
    mock.side_effect = ContainerCLIError("build failed", 1, "Dockerfile not found")

    thread = threading.Thread(target=_run_build_thread, args=(build_id, "/some/path"))
    thread.start()
    thread.join(timeout=5)

    with _builds_lock:
        assert active_builds[build_id]["state"] == "failed"
        assert "Dockerfile not found" in active_builds[build_id]["error"]


# ---------------------------------------------------------------------------
# MCP resource
# ---------------------------------------------------------------------------


def test_get_system_status_resource_ok(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = {"state": "running", "version": "1.0"}
    result = get_system_status_resource()
    assert "running" in result
    assert "version" in result


def test_get_system_status_resource_error(mocker):
    mock = _mock_cmd(mocker)
    mock.side_effect = Exception("unexpected crash")
    result = get_system_status_resource()
    assert "Error" in result
    assert "unexpected crash" in result


# ---------------------------------------------------------------------------
# MCP prompts — smoke tests
# ---------------------------------------------------------------------------


def test_prompt_troubleshoot_container():
    result = troubleshoot_container("my-container")
    assert "my-container" in result
    assert "inspect_container" in result


def test_prompt_build_and_run_workflow():
    result = build_and_run_workflow("/home/user/proj", "myapp:v1", port="8080:80")
    assert "/home/user/proj" in result
    assert "myapp:v1" in result
    assert "8080:80" in result


def test_prompt_build_and_run_workflow_no_port():
    result = build_and_run_workflow("/home/user/proj", "myapp:v1")
    assert "myapp:v1" in result
    assert "builder_status" in result


def test_prompt_cleanup_environment():
    result = cleanup_environment()
    assert "prune" in result.lower()
    assert "list_containers" in result


def test_prompt_setup_private_registry():
    result = setup_private_registry("registry.example.com")
    assert "registry.example.com" in result
    assert "registry_login" in result


# ---------------------------------------------------------------------------
# run_container — env_file and mount paths
# ---------------------------------------------------------------------------


def test_run_container_with_env_file(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = {"raw_output": "abc"}
    mocker.patch("os.path.expanduser", return_value="/Users/test")
    mocker.patch("os.path.realpath", side_effect=lambda p: p)
    result = run_container("debian", env_file="/Users/test/.env")
    assert result["status"] == "ok"
    called_args = mock.call_args[0][0]
    assert "--env-file" in called_args
    assert "/Users/test/.env" in called_args


def test_run_container_env_file_outside_home_blocked(mocker):
    mocker.patch("os.path.expanduser", return_value="/Users/test")
    mocker.patch("os.path.realpath", side_effect=lambda p: p)
    result = run_container("debian", env_file="/etc/passwd")
    assert result["status"] == "error"
    assert "home directory" in result["message"]


def test_run_container_env_file_sibling_prefix_blocked(mocker):
    """Ensure /Users/tester/.env doesn't pass when home is /Users/test."""
    mocker.patch("os.path.expanduser", return_value="/Users/test")
    mocker.patch("os.path.realpath", side_effect=lambda p: p)
    result = run_container("debian", env_file="/Users/tester/.env")
    assert result["status"] == "error"
    assert "home directory" in result["message"]


def test_run_container_with_mount(mocker):
    mock = _mock_cmd(mocker)
    mock.return_value = {"raw_output": "abc"}
    result = run_container("debian", mount=["type=bind,src=/tmp,dst=/data"])
    assert result["status"] == "ok"
    called_args = mock.call_args[0][0]
    assert "--mount" in called_args
    assert "type=bind,src=/tmp,dst=/data" in called_args
