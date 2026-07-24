from d2c.global_flags import strip_global_flags, GLOBAL_FLAGS, prompt_continue
from unittest.mock import patch


def test_no_global_flags_unchanged() -> None:
    remaining, warned, prepend = strip_global_flags(["ps", "-a"])
    assert remaining == ["ps", "-a"]
    assert warned == []
    assert prepend == []


def test_host_flag_detected_and_removed() -> None:
    remaining, warned, prepend = strip_global_flags(["--host", "tcp://remote:2375", "ps"])
    assert "--host" in warned
    assert "ps" in remaining
    assert "tcp://remote:2375" not in remaining


def test_short_host_flag_detected() -> None:
    remaining, warned, prepend = strip_global_flags(["-H", "tcp://remote:2375", "ps"])
    assert "-H" in warned
    assert "ps" in remaining


def test_debug_flag_translated_not_warned() -> None:
    remaining, warned, prepend = strip_global_flags(["--debug", "ps"])
    assert "--debug" in prepend
    assert warned == []
    assert "ps" in remaining
    assert "--debug" not in remaining


def test_short_debug_flag_translated() -> None:
    remaining, warned, prepend = strip_global_flags(["-D", "ps"])
    assert "--debug" in prepend
    assert warned == []


def test_equals_form_host_flag() -> None:
    remaining, warned, prepend = strip_global_flags(["--host=tcp://remote:2375", "ps"])
    assert "--host" in warned
    assert "ps" in remaining


def test_context_flag_detected_and_value_consumed() -> None:
    remaining, warned, prepend = strip_global_flags(["--context", "myctx", "images"])
    assert "--context" in warned
    assert "myctx" not in remaining
    assert "images" in remaining


def test_tls_flags_detected() -> None:
    remaining, warned, prepend = strip_global_flags(["--tls", "ps"])
    assert "--tls" in warned
    assert "ps" in remaining


def test_log_level_flag_detected_and_value_consumed() -> None:
    remaining, warned, prepend = strip_global_flags(["--log-level", "debug", "ps"])
    assert "--log-level" in warned
    assert "debug" not in remaining
    assert "ps" in remaining


def test_multiple_global_flags() -> None:
    remaining, warned, prepend = strip_global_flags(["--host", "tcp://r:2375", "--tls", "ps"])
    assert "--host" in warned
    assert "--tls" in warned
    assert "ps" in remaining


def test_prompt_continue_yes() -> None:
    with patch("builtins.input", return_value="y"):
        result = prompt_continue("--host", "some hint")
    assert result is True


def test_prompt_continue_no() -> None:
    with patch("builtins.input", return_value="n"):
        result = prompt_continue("--host", "some hint")
    assert result is False


def test_prompt_continue_empty_defaults_no() -> None:
    with patch("builtins.input", return_value=""):
        result = prompt_continue("--host", "some hint")
    assert result is False


def test_all_global_flags_have_hints() -> None:
    for flag, gf in GLOBAL_FLAGS.items():
        assert gf.hint.strip(), f"hint for '{flag}' is empty"


def test_equals_form_puts_bare_flag_name_in_warned() -> None:
    remaining, warned, prepend = strip_global_flags(["--host=tcp://remote:2375", "ps"])
    assert warned == ["--host"]   # not "--host=tcp://remote:2375"
    assert "ps" in remaining


def test_short_flags_in_exec_args_not_consumed() -> None:
    remaining, warned, prepend = strip_global_flags(
        ["exec", "mycontainer", "bash", "-c", "echo hi"]
    )
    assert warned == []
    assert remaining == ["exec", "mycontainer", "bash", "-c", "echo hi"]
