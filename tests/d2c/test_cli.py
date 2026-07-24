import pytest
from unittest.mock import patch
from d2c.cli import main


def test_no_args_exits_with_usage(capsys: pytest.CaptureFixture[str]) -> None:
    with patch("sys.argv", ["d2c"]):
        with pytest.raises(SystemExit) as exc:
            main()
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "Usage" in out


def test_dry_run_ps_prints_translation(capsys: pytest.CaptureFixture[str]) -> None:
    with patch("sys.argv", ["d2c", "--dry-run", "ps"]):
        with pytest.raises(SystemExit):
            main()
    out = capsys.readouterr().out
    assert "container list" in out


def test_dry_run_images_prints_translation(capsys: pytest.CaptureFixture[str]) -> None:
    with patch("sys.argv", ["d2c", "--dry-run", "images"]):
        with pytest.raises(SystemExit):
            main()
    out = capsys.readouterr().out
    assert "container image list" in out


def test_unsupported_command_exits_1(capsys: pytest.CaptureFixture[str]) -> None:
    with patch("sys.argv", ["d2c", "commit", "mycontainer", "myimage"]):
        with pytest.raises(SystemExit) as exc:
            main()
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "not supported" in out
    assert "Hint" in out


def test_unsupported_command_prints_hint(capsys: pytest.CaptureFixture[str]) -> None:
    with patch("sys.argv", ["d2c", "pause", "mycontainer"]):
        with pytest.raises(SystemExit) as exc:
            main()
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "stop" in out


def test_unknown_command_exits_1(capsys: pytest.CaptureFixture[str]) -> None:
    with patch("sys.argv", ["d2c", "nonexistentcommand"]):
        with pytest.raises(SystemExit) as exc:
            main()
    assert exc.value.code == 1


def test_translates_and_executes(mocker) -> None:
    mock_execute = mocker.patch("d2c.cli.execute", return_value=0)
    with patch("sys.argv", ["d2c", "ps"]):
        with pytest.raises(SystemExit) as exc:
            main()
    mock_execute.assert_called_once_with(["container", "list"])
    assert exc.value.code == 0


def test_execute_exit_code_propagated(mocker) -> None:
    mocker.patch("d2c.cli.execute", return_value=2)
    with patch("sys.argv", ["d2c", "ps"]):
        with pytest.raises(SystemExit) as exc:
            main()
    assert exc.value.code == 2


def test_global_flag_abort_exits_1(capsys: pytest.CaptureFixture[str]) -> None:
    with patch("builtins.input", return_value="n"):
        with patch("sys.argv", ["d2c", "--host", "tcp://remote:2375", "ps"]):
            with pytest.raises(SystemExit) as exc:
                main()
    assert exc.value.code == 1


def test_global_flag_continue_executes(mocker) -> None:
    mock_execute = mocker.patch("d2c.cli.execute", return_value=0)
    with patch("builtins.input", return_value="y"):
        with patch("sys.argv", ["d2c", "--host", "tcp://remote:2375", "ps"]):
            with pytest.raises(SystemExit):
                main()
    mock_execute.assert_called_once_with(["container", "list"])


def test_debug_flag_prepended_to_command(mocker) -> None:
    mock_execute = mocker.patch("d2c.cli.execute", return_value=0)
    with patch("sys.argv", ["d2c", "--debug", "ps"]):
        with pytest.raises(SystemExit):
            main()
    mock_execute.assert_called_once_with(["container", "--debug", "list"])


def test_docker_management_namespace_stripped(mocker) -> None:
    mock_execute = mocker.patch("d2c.cli.execute", return_value=0)
    with patch("sys.argv", ["d2c", "container", "run", "nginx"]):
        with pytest.raises(SystemExit):
            main()
    mock_execute.assert_called_once_with(["container", "run", "nginx"])
