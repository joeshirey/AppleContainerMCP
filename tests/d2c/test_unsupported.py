import dataclasses

from d2c.unsupported import UNSUPPORTED


def test_commit_is_unsupported() -> None:
    assert "commit" in UNSUPPORTED


def test_commit_hint_mentions_dockerfile() -> None:
    assert "Dockerfile" in UNSUPPORTED["commit"].hint


def test_pause_is_unsupported() -> None:
    assert "pause" in UNSUPPORTED


def test_pause_hint_mentions_stop() -> None:
    assert "stop" in UNSUPPORTED["pause"].hint


def test_unpause_hint_mentions_start() -> None:
    assert "start" in UNSUPPORTED["unpause"].hint


def test_attach_is_unsupported() -> None:
    assert "attach" in UNSUPPORTED


def test_attach_hint_mentions_exec() -> None:
    assert "exec" in UNSUPPORTED["attach"].hint


def test_rename_hint_mentions_remove_and_recreate() -> None:
    hint = UNSUPPORTED["rename"].hint
    assert "remove" in hint and "recreate" in hint


def test_restart_hint_mentions_stop_and_start() -> None:
    hint = UNSUPPORTED["restart"].hint
    assert "stop" in hint and "start" in hint


def test_search_hint_mentions_registry() -> None:
    assert "registr" in UNSUPPORTED["search"].hint.lower()


def test_swarm_commands_unsupported() -> None:
    for cmd in ("node", "service", "stack", "swarm", "config", "secret"):
        assert cmd in UNSUPPORTED, f"'{cmd}' should be unsupported"


def test_all_hints_are_nonempty() -> None:
    for cmd, entry in UNSUPPORTED.items():
        assert entry.hint.strip(), f"hint for '{cmd}' is empty"


def test_unsupported_command_is_immutable() -> None:
    import pytest

    with pytest.raises(dataclasses.FrozenInstanceError):
        UNSUPPORTED["commit"].hint = "changed"  # type: ignore[misc]


def test_compose_is_unsupported() -> None:
    assert "compose" in UNSUPPORTED


def test_compose_hint_mentions_run() -> None:
    assert "run" in UNSUPPORTED["compose"].hint
