from apple_container_mcp.tools import (
    check_apiserver_status,
    run_container,
    stop_container,
    start_container,
    get_logs,
    active_builds,
    build_image,
    check_build_status,
    create_network,
    create_volume,
    prune_images,
)
from apple_container_mcp.cli_wrapper import ContainerCLIError


def test_check_apiserver_status_running(mocker):
    # Mock the internal wrapper used by tools
    mock_cmd = mocker.patch("apple_container_mcp.tools._run_container_cmd")
    mock_cmd.return_value = {"version": "1.0.0"}

    result = check_apiserver_status()
    assert result["status"] == "ok"
    assert "running" in result["message"]
    mock_cmd.assert_called_once_with(["system", "status"])


def test_check_apiserver_status_stopped(mocker):
    mock_cmd = mocker.patch("apple_container_mcp.tools._run_container_cmd")
    mock_cmd.side_effect = ContainerCLIError("The container-apiserver daemon is not running.", 1, "connection refused")

    result = check_apiserver_status()
    assert result == {"status": "stopped", "error": "The container-apiserver daemon is not reachable."}


def test_run_container_basic(mocker):
    mock_cmd = mocker.patch("apple_container_mcp.tools._run_container_cmd")
    mock_cmd.return_value = {"raw_output": "12345"}

    result = run_container("debian")
    assert result == {"status": "ok", "id": "12345"}
    mock_cmd.assert_called_once_with(["run", "-d", "debian"])


def test_run_container_with_options(mocker):
    mock_cmd = mocker.patch("apple_container_mcp.tools._run_container_cmd")
    mock_cmd.return_value = {"raw_output": "67890"}

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
    mock_cmd.assert_called_once_with(
        [
            "run",
            "--name",
            "my-ubuntu",
            "--cpus",
            "2",
            "--memory",
            "4g",
            "--network",
            "my-net",
            "-p",
            "8080:80",
            "-e",
            "DEBUG=1",
            "-v",
            "/tmp/host:/tmp/container",
            "ubuntu",
        ]
    )


def test_run_container_error(mocker):
    mock_cmd = mocker.patch("apple_container_mcp.tools._run_container_cmd")
    mock_cmd.side_effect = ContainerCLIError("Command failed", 125, "Image not found")

    result = run_container("missing-image")
    assert result == {
        "status": "error",
        "message": "Failed to run container",
        "details": "Image not found",
        "exit_code": 125,
    }


def test_stop_container_graceful(mocker):
    mock_cmd = mocker.patch("apple_container_mcp.tools._run_container_cmd")

    result = stop_container("12345", force=False)
    assert "Successfully executed 'stop' on container 12345." in result["message"]
    mock_cmd.assert_called_once_with(["stop", "12345"])


def test_stop_container_force(mocker):
    mock_cmd = mocker.patch("apple_container_mcp.tools._run_container_cmd")

    result = stop_container("12345", force=True)
    assert "Successfully executed 'kill' on container 12345." in result["message"]
    mock_cmd.assert_called_once_with(["kill", "12345"])


def test_start_container(mocker):
    mock_cmd = mocker.patch("apple_container_mcp.tools._run_container_cmd")

    result = start_container("12345")
    assert "Successfully started container 12345." in result["message"]
    mock_cmd.assert_called_once_with(["start", "12345"])


def test_get_logs_success(mocker):
    mock_cmd = mocker.patch("apple_container_mcp.tools._run_container_cmd")
    mock_cmd.return_value = {"raw_output": "line 1\nline 2"}

    result = get_logs("12345", limit=50)
    assert result == "line 1\nline 2"
    mock_cmd.assert_called_once_with(["logs", "-n", "50", "12345"])


def test_get_logs_error(mocker):
    mock_cmd = mocker.patch("apple_container_mcp.tools._run_container_cmd")
    mock_cmd.side_effect = ContainerCLIError("Failed to fetch logs", 1, "No such container")

    result = get_logs("invalid")
    assert "Failed to fetch logs: No such container" in result


def test_build_image_async_behavior(mocker):
    import threading

    mock_thread_start = mocker.patch.object(threading.Thread, "start")
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("os.path.isdir", return_value=True)

    # Reset globals for test isolation if needed, though they don't break logic
    result = build_image(".")

    assert "Build started asynchronously" in result["message"]
    assert "build_" in result["message"]
    mock_thread_start.assert_called_once()

    # We won't block tests to test the active thread completion, but we verify it's registered
    last_build_id = list(active_builds.keys())[-1]
    status_result = check_build_status(last_build_id)
    assert status_result["status"] == "ok"
    assert status_result["build_status"] == "In progress..."


def test_create_network(mocker):
    mock_cmd = mocker.patch("apple_container_mcp.tools._run_container_cmd")
    result = create_network("my-net", subnet="192.168.1.0/24")
    assert "Successfully created network 'my-net'" in result["message"]
    mock_cmd.assert_called_once_with(["network", "create", "--subnet", "192.168.1.0/24", "my-net"])


def test_create_volume(mocker):
    mock_cmd = mocker.patch("apple_container_mcp.tools._run_container_cmd")
    result = create_volume("my-vol", size="10G")
    assert "Successfully created volume 'my-vol'" in result["message"]
    mock_cmd.assert_called_once_with(["volume", "create", "-s", "10G", "my-vol"])


def test_prune_images_all(mocker):
    mock_cmd = mocker.patch("apple_container_mcp.tools._run_container_cmd")
    result = prune_images(all=True)
    assert "Successfully pruned unused images." in result["message"]
    mock_cmd.assert_called_once_with(["image", "prune", "-a"])
