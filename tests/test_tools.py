import pytest
from apple_container_mcp.tools import check_apiserver_status, run_container, stop_container, get_logs, active_builds, build_image, check_build_status
from apple_container_mcp.cli_wrapper import ContainerCLIError

def test_check_apiserver_status_running(mocker):
    # Mock the internal wrapper used by tools
    mock_cmd = mocker.patch("apple_container_mcp.tools._run_container_cmd")
    mock_cmd.return_value = {"version": "1.0.0"}
    
    result = check_apiserver_status()
    assert result == {"version": "1.0.0"}
    mock_cmd.assert_called_once_with(["system", "status"])

def test_check_apiserver_status_stopped(mocker):
    mock_cmd = mocker.patch("apple_container_mcp.tools._run_container_cmd")
    mock_cmd.side_effect = ContainerCLIError("The container-apiserver daemon is not running.", 1, "connection refused")
    
    result = check_apiserver_status()
    assert result == {"status": "stopped", "error": "The container-apiserver daemon is not reachable."}

def test_run_container_basic(mocker):
    mock_cmd = mocker.patch("apple_container_mcp.tools._run_container_cmd")
    mock_cmd.return_value = {"id": "12345"}
    
    result = run_container("debian")
    assert result == {"id": "12345"}
    mock_cmd.assert_called_once_with(["run", "-d", "debian"])

def test_run_container_with_options(mocker):
    mock_cmd = mocker.patch("apple_container_mcp.tools._run_container_cmd")
    mock_cmd.return_value = {"id": "67890"}
    
    result = run_container("ubuntu", cpus=2, memory="4g", name="my-ubuntu", detach=False, ports=["8080:80"], env=["DEBUG=1"], volumes=["/tmp/host:/tmp/container"])
    assert result == {"id": "67890"}
    mock_cmd.assert_called_once_with(["run", "--name", "my-ubuntu", "--cpus", "2", "--memory", "4g", "-p", "8080:80", "-e", "DEBUG=1", "-v", "/tmp/host:/tmp/container", "ubuntu"])

def test_run_container_error(mocker):
    mock_cmd = mocker.patch("apple_container_mcp.tools._run_container_cmd")
    mock_cmd.side_effect = ContainerCLIError("Command failed", 125, "Image not found")
    
    result = run_container("missing-image")
    assert result == {"error": "Failed to run container", "details": "Image not found", "exit_code": 125}

def test_stop_container_graceful(mocker):
    mock_cmd = mocker.patch("apple_container_mcp.tools._run_container_cmd")
    
    result = stop_container("12345", force=False)
    assert "Successfully executed 'stop' on container 12345." in result
    mock_cmd.assert_called_once_with(["stop", "12345"])

def test_stop_container_force(mocker):
    mock_cmd = mocker.patch("apple_container_mcp.tools._run_container_cmd")
    
    result = stop_container("12345", force=True)
    assert "Successfully executed 'kill' on container 12345." in result
    mock_cmd.assert_called_once_with(["kill", "12345"])

def test_get_logs_success(mocker):
    mock_run = mocker.patch("subprocess.run")
    mock_result = mocker.Mock()
    mock_result.stdout = "line 1\nline 2"
    mock_result.stderr = ""
    mock_run.return_value = mock_result
    
    result = get_logs("12345", limit=50)
    assert result == "line 1\nline 2"
    mock_run.assert_called_once_with(["container", "logs", "-n", "50", "12345"], capture_output=True, text=True, check=True)

def test_get_logs_error(mocker):
    import subprocess
    mock_run = mocker.patch("subprocess.run")
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=1,
        cmd=["container", "logs", "-n", "100", "invalid"],
        stderr="No such container"
    )
    
    result = get_logs("invalid")
    assert "Failed to fetch logs: No such container" in result

def test_build_image_async_behavior(mocker):
    import threading
    mock_thread_start = mocker.patch.object(threading.Thread, 'start')
    
    # Reset globals for test isolation if needed, though they don't break logic
    result = build_image(".")
    
    assert "Build started asynchronously" in result
    assert "build_" in result
    mock_thread_start.assert_called_once()
    
    # We won't block tests to test the active thread completion, but we verify it's registered
    last_build_id = list(active_builds.keys())[-1]
    assert check_build_status(last_build_id) == "In progress..."
