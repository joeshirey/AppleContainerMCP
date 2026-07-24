import pytest
from d2c.executor import dry_run, execute


def test_dry_run_prints_docker_command(capsys: pytest.CaptureFixture[str]) -> None:
    dry_run(["ps", "-a"], ["container", "list", "-a"], None)
    out = capsys.readouterr().out
    assert "[d2c dry-run] docker ps -a" in out


def test_dry_run_prints_container_command(capsys: pytest.CaptureFixture[str]) -> None:
    dry_run(["ps", "-a"], ["container", "list", "-a"], None)
    out = capsys.readouterr().out
    assert "→ container list -a" in out


def test_dry_run_no_note_omits_info_line(capsys: pytest.CaptureFixture[str]) -> None:
    dry_run(["ps"], ["container", "list"], None)
    out = capsys.readouterr().out
    assert "ℹ" not in out


def test_dry_run_prints_note_when_present(capsys: pytest.CaptureFixture[str]) -> None:
    dry_run(["rmi", "nginx"], ["container", "image", "remove", "nginx"], "rmi maps to image subcommand")
    out = capsys.readouterr().out
    assert "ℹ" in out
    assert "rmi maps to image subcommand" in out


def test_execute_returns_zero_exit_code(mocker) -> None:
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = mocker.Mock(returncode=0)
    result = execute(["container", "list"])
    mock_run.assert_called_once_with(["container", "list"])
    assert result == 0


def test_execute_passes_through_nonzero_exit(mocker) -> None:
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = mocker.Mock(returncode=1)
    result = execute(["container", "list"])
    assert result == 1


def test_execute_never_uses_shell(mocker) -> None:
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = mocker.Mock(returncode=0)
    execute(["container", "list"])
    call_kwargs = mock_run.call_args.kwargs
    assert call_kwargs.get("shell") is not True
