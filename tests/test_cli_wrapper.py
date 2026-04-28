import pytest
import subprocess
from apple_container_mcp.cli_wrapper import _run_container_cmd, ContainerCLIError, DEFAULT_TIMEOUT_SECONDS


def test_run_container_cmd_success(mocker):
    """Test successful command execution that returns valid JSON."""
    mock_run = mocker.patch("subprocess.run")
    mock_result = mocker.Mock()
    mock_result.stdout = '{"key": "value"}'
    mock_result.returncode = 0
    mock_run.return_value = mock_result

    result = _run_container_cmd(["inspect", "123"])

    # Ensure --format json was NOT appended for inspect
    mock_run.assert_called_once_with(
        ["container", "inspect", "123"], capture_output=True, text=True, check=True, timeout=30
    )
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

    mock_run.assert_called_once_with(
        ["container", "system", "status", "--format", "json"], capture_output=True, text=True, check=True, timeout=30
    )
    assert result == {"data": "exists"}


def test_run_container_cmd_daemon_down(mocker):
    """Test handling of daemon down error."""
    mock_run = mocker.patch("subprocess.run")
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=1,
        cmd=["container", "inspect"],
        stderr="Cannot connect to the container daemon at something. Is the docker daemon running?",
    )

    with pytest.raises(ContainerCLIError) as exc_info:
        _run_container_cmd(["inspect"])

    assert "daemon is not running" in str(exc_info.value)
    assert exc_info.value.exit_code == 1


def test_run_container_cmd_general_error(mocker):
    """Test handling of a general CLI error."""
    mock_run = mocker.patch("subprocess.run")
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=2, cmd=["container", "run", "ubuntu"], stderr="invalid argument"
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


def test_run_container_cmd_timeout(mocker):
    """Test that a timed-out command raises ContainerCLIError."""
    mock_run = mocker.patch("subprocess.run")
    mock_run.side_effect = subprocess.TimeoutExpired(cmd=["container", "pull", "big-image"], timeout=30)

    with pytest.raises(ContainerCLIError) as exc_info:
        _run_container_cmd(["pull", "big-image"])

    assert "timed out" in str(exc_info.value).lower()
    assert exc_info.value.exit_code == -1


def test_run_container_cmd_uses_default_timeout(mocker):
    """Test that the default timeout is applied for non-long-running commands."""
    mock_run = mocker.patch("subprocess.run")
    mock_result = mocker.Mock()
    mock_result.stdout = "{}"
    mock_result.returncode = 0
    mock_run.return_value = mock_result

    _run_container_cmd(["inspect", "abc"])

    _, kwargs = mock_run.call_args
    assert kwargs["timeout"] == DEFAULT_TIMEOUT_SECONDS


def test_run_container_cmd_long_running_uses_longer_timeout(mocker):
    """Test that pull/push/start use a longer timeout."""
    mock_run = mocker.patch("subprocess.run")
    mock_result = mocker.Mock()
    mock_result.stdout = ""
    mock_result.returncode = 0
    mock_run.return_value = mock_result

    _run_container_cmd(["pull", "debian"])

    _, kwargs = mock_run.call_args
    assert kwargs["timeout"] > DEFAULT_TIMEOUT_SECONDS


def test_run_container_cmd_subcommand_ls_gets_json_format(mocker):
    """Test that image ls, network ls, volume ls all get --format json appended."""
    mock_run = mocker.patch("subprocess.run")
    mock_result = mocker.Mock()
    mock_result.stdout = "[]"
    mock_result.returncode = 0
    mock_run.return_value = mock_result

    for subcmd in (["image", "ls"], ["network", "ls"], ["volume", "ls"]):
        _run_container_cmd(subcmd)
        called_cmd = mock_run.call_args[0][0]
        assert "--format" in called_cmd, f"--format missing for {subcmd}"
        assert "json" in called_cmd, f"json missing for {subcmd}"


@pytest.mark.parametrize("subcmd", [
    ["system", "version"],
    ["system", "status"],
    ["builder", "status"],
    ["stats"],
])
def test_run_container_cmd_new_allowlist_entries_get_json_format(mocker, subcmd):
    """Verify each newly allowlisted command (per Apple Container 0.12 audit) receives --format json."""
    mock_run = mocker.patch("subprocess.run")
    mock_result = mocker.Mock()
    mock_result.stdout = "{}"
    mock_result.returncode = 0
    mock_run.return_value = mock_result

    _run_container_cmd(subcmd)

    called_cmd = mock_run.call_args[0][0]
    assert "--format" in called_cmd, f"--format missing for {subcmd}"
    assert "json" in called_cmd, f"json missing for {subcmd}"


def test_run_container_cmd_builder_ls_no_longer_in_allowlist(mocker):
    """`container builder ls` does NOT exist in 0.12; the dead entry must have been removed.

    This test asserts that when ['builder', 'ls'] is passed to _run_container_cmd,
    --format json is NOT auto-appended (because the entry was removed from the
    allowlist). This guards against accidentally re-adding it.
    """
    mock_run = mocker.patch("subprocess.run")
    mock_result = mocker.Mock()
    mock_result.stdout = ""
    mock_result.returncode = 0
    mock_run.return_value = mock_result

    _run_container_cmd(["builder", "ls"])

    called_cmd = mock_run.call_args[0][0]
    # --format json must NOT have been auto-appended (entry was removed from allowlist)
    assert "--format" not in called_cmd, "builder ls should not auto-receive --format json"
