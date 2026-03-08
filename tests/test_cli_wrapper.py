import pytest
import subprocess
from apple_container_mcp.cli_wrapper import _run_container_cmd, ContainerCLIError

def test_run_container_cmd_success(mocker):
    """Test successful command execution that returns valid JSON."""
    mock_run = mocker.patch("subprocess.run")
    mock_result = mocker.Mock()
    mock_result.stdout = '{"key": "value"}'
    mock_result.returncode = 0
    mock_run.return_value = mock_result

    result = _run_container_cmd(["inspect", "123"])
    
    # Ensure --format json was NOT appended for inspect
    mock_run.assert_called_once_with(["container", "inspect", "123"], capture_output=True, text=True, check=True)
    # Ensure JSON was parsed
    assert result == {"key": "value"}

def test_run_container_cmd_empty_output(mocker):
    """Test successful command execution that returns empty output."""
    mock_run = mocker.patch("subprocess.run")
    mock_result = mocker.Mock()
    mock_result.stdout = ""
    mock_result.returncode = 0
    mock_run.return_value = mock_result

    result = _run_container_cmd(["ls"])
    assert result == {}

def test_run_container_cmd_with_existing_format_flag(mocker):
    """Test that --format json is not appended if --format is already present."""
    mock_run = mocker.patch("subprocess.run")
    mock_result = mocker.Mock()
    mock_result.stdout = '{"data": "exists"}'
    mock_result.returncode = 0
    mock_run.return_value = mock_result

    result = _run_container_cmd(["system", "status", "--format", "json"])
    
    mock_run.assert_called_once_with(["container", "system", "status", "--format", "json"], capture_output=True, text=True, check=True)
    assert result == {"data": "exists"}

def test_run_container_cmd_daemon_down(mocker):
    """Test handling of daemon down error."""
    mock_run = mocker.patch("subprocess.run")
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=1,
        cmd=["container", "inspect"],
        stderr="Cannot connect to the container daemon at something. Is the docker daemon running?"
    )

    with pytest.raises(ContainerCLIError) as exc_info:
        _run_container_cmd(["inspect"])
    
    assert "daemon is not running" in str(exc_info.value)
    assert exc_info.value.exit_code == 1

def test_run_container_cmd_general_error(mocker):
    """Test handling of a general CLI error."""
    mock_run = mocker.patch("subprocess.run")
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=2,
        cmd=["container", "run", "ubuntu"],
        stderr="invalid argument"
    )

    with pytest.raises(ContainerCLIError) as exc_info:
        _run_container_cmd(["run", "ubuntu"])
    
    assert "Command failed with exit code 2" in str(exc_info.value)
    assert exc_info.value.exit_code == 2
    assert "invalid argument" in exc_info.value.stderr

def test_run_container_cmd_invalid_json(mocker):
    """Test handling of invalid JSON output."""
    mock_run = mocker.patch("subprocess.run")
    mock_result = mocker.Mock()
    mock_result.stdout = "This is not JSON"
    mock_result.returncode = 0
    mock_run.return_value = mock_result

    result = _run_container_cmd(["logs", "123"])
    
    assert result == {"raw_output": "This is not JSON"}
