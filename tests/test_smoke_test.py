from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

SMOKE_TEST_PATH = Path(__file__).resolve().parents[1] / "scripts" / "smoke_test.py"


def _load_smoke_test_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("smoke_test", SMOKE_TEST_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_smoke_main(
    smoke_test: ModuleType,
    tmp_path: Path,
    stats_factory: Any,
    cleaned: dict[str, list[str]] | None = None,
) -> dict[str, list[str]]:
    """Execute smoke_test.main() against stubbed external tool and subprocess boundaries."""
    if cleaned is None:
        cleaned = {
            "containers": [],
            "volumes": [],
            "networks": [],
            "images": [],
        }
    state = {"running": False, "container_name": ""}

    def run_container(image: str, **kwargs: Any) -> dict[str, Any]:
        if kwargs.get("detach", True) is False:
            return {"status": "ok", "id": "committed\n"}
        state["running"] = True
        state["container_name"] = kwargs["name"]
        return {"status": "ok", "id": kwargs["name"]}

    def inspect_container(container_id: str) -> dict[str, Any]:
        return {
            "status": "ok",
            "inspection": [
                {
                    "configuration": {
                        "networks": [
                            {
                                "options": {
                                    "aliases": [f"api-{container_id}.test", f".api-{container_id}.test"],
                                }
                            }
                        ]
                    }
                }
            ],
        }

    def stats_container(containers: list[str] | None = None) -> dict[str, Any]:
        assert containers == [state["container_name"]]
        return {"status": "ok", "stats": stats_factory(state["container_name"])}

    def copy_from_container(_cid: str, _src: str, dest: str) -> dict[str, Any]:
        Path(dest).write_text("copy-round-trip\n")
        return {"status": "ok"}

    def clean_container(_cid: str) -> dict[str, Any]:
        if not state["running"]:
            return {"status": "error", "message": "container is stopped"}
        return {"status": "ok"}

    def stop_container(_cid: str) -> dict[str, Any]:
        state["running"] = False
        return {"status": "ok"}

    def start_container(_cid: str) -> dict[str, Any]:
        state["running"] = True
        return {"status": "ok"}

    fake_tools = SimpleNamespace(
        check_environment=lambda: {"status": "ok"},
        system_status=lambda: {"status": "ok"},
        pull_image=lambda *_a, **_kw: {"status": "ok"},
        create_network=lambda _name: {"status": "ok"},
        inspect_network=lambda _name: {"status": "ok"},
        create_volume=lambda _name: {"status": "ok"},
        inspect_volume=lambda _name: {"status": "ok"},
        run_container=run_container,
        list_containers=lambda: {"status": "ok", "containers": []},
        inspect_container=inspect_container,
        get_logs=lambda _cid: {"status": "ok", "logs": "smoke-ready\n"},
        stats_container=stats_container,
        exec_in_container=lambda *_a, **_kw: {"status": "ok", "output": "smoke\n"},
        copy_to_container=lambda *_a, **_kw: {"status": "ok"},
        copy_from_container=copy_from_container,
        clean_container=clean_container,
        stop_container=stop_container,
        start_container=start_container,
        commit_container=lambda _cid, tag: {"status": "ok", "image": tag},
        builder_start=lambda: {"status": "ok"},
        build_image=lambda *_a, **_kw: {"status": "ok", "build_id": "0000000000000001"},
        check_build_status=lambda _bid: {"status": "ok", "build_status": {"state": "completed"}},
        remove_container=lambda name, **_kw: cleaned["containers"].append(name) or {"status": "ok"},
        remove_volume=lambda name: cleaned["volumes"].append(name) or {"status": "ok"},
        remove_network=lambda name: cleaned["networks"].append(name) or {"status": "ok"},
        remove_image=lambda name: cleaned["images"].append(name) or {"status": "ok"},
    )

    def fake_subprocess_run(cmd: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="[]", stderr="")

    home_dir = tmp_path / "home"
    home_dir.mkdir(exist_ok=True)

    with (
        patch.object(smoke_test, "tools", fake_tools),
        patch.object(smoke_test.subprocess, "run", side_effect=fake_subprocess_run),
        patch.object(smoke_test.Path, "home", return_value=home_dir),
        patch("sys.argv", ["smoke_test.py"]),
    ):
        smoke_test.main()

    return cleaned


def test_smoke_test_docstring_and_cli_help_require_1_7_1(capsys: pytest.CaptureFixture[str]) -> None:
    smoke_test = _load_smoke_test_module()
    doc = smoke_test.__doc__ or ""
    assert "Apple Container 1.7.1+" in doc
    assert "1.6.1+" not in doc

    with patch("sys.argv", ["smoke_test.py", "--help"]):
        with pytest.raises(SystemExit) as exc:
            smoke_test.main()
    assert exc.value.code == 0
    help_out = capsys.readouterr().out
    assert "Apple Container 1.7.1+" in help_out
    assert "1.6.1+" not in help_out


def test_smoke_test_stats_accepts_valid_shapes_and_rejects_empty_or_non_list(tmp_path: Path) -> None:
    smoke_test = _load_smoke_test_module()

    # Valid shapes: positive float cpuUtilization, zero int cpuUtilization, and omitted cpuUtilization
    _run_smoke_main(smoke_test, tmp_path, lambda cid: [{"id": cid, "cpuUtilization": 0.375}])
    _run_smoke_main(smoke_test, tmp_path, lambda cid: [{"id": cid, "cpuUtilization": 0}])
    _run_smoke_main(smoke_test, tmp_path, lambda cid: [{"id": cid, "memoryUsageBytes": 4096}])

    # Empty list must fail validation while still cleaning up created resources
    cleaned_on_empty: dict[str, list[str]] = {"containers": [], "volumes": [], "networks": [], "images": []}
    with pytest.raises(AssertionError):
        _run_smoke_main(smoke_test, tmp_path, lambda _cid: [], cleaned=cleaned_on_empty)
    assert len(cleaned_on_empty["containers"]) == 1
    assert len(cleaned_on_empty["volumes"]) == 2
    assert len(cleaned_on_empty["networks"]) == 1

    # Non-list payload must fail validation
    with pytest.raises(AssertionError):
        _run_smoke_main(smoke_test, tmp_path, lambda _cid: None)


def test_smoke_test_stats_requires_matching_container_id(tmp_path: Path) -> None:
    smoke_test = _load_smoke_test_module()

    # Multi-entry list containing the target container id succeeds
    _run_smoke_main(
        smoke_test,
        tmp_path,
        lambda cid: [
            {"id": "unrelated-container", "cpuUtilization": 0.1},
            {"id": cid, "cpuUtilization": 1.25},
        ],
    )

    # Non-empty list without an entry matching prefix fails validation
    with pytest.raises(AssertionError):
        _run_smoke_main(
            smoke_test,
            tmp_path,
            lambda _cid: [{"id": "unrelated-container", "cpuUtilization": 0.5}],
        )


@pytest.mark.parametrize("bool_cpu", [True, False])
def test_smoke_test_stats_rejects_boolean_cpu_utilization(tmp_path: Path, bool_cpu: bool) -> None:
    smoke_test = _load_smoke_test_module()
    with pytest.raises(AssertionError):
        _run_smoke_main(
            smoke_test,
            tmp_path,
            lambda cid: [{"id": cid, "cpuUtilization": bool_cpu}],
        )


@pytest.mark.parametrize("invalid_cpu", [-0.01, -1, "0.5", None])
def test_smoke_test_stats_rejects_negative_or_non_numeric_cpu_utilization(
    tmp_path: Path,
    invalid_cpu: Any,
) -> None:
    smoke_test = _load_smoke_test_module()
    with pytest.raises(AssertionError):
        _run_smoke_main(
            smoke_test,
            tmp_path,
            lambda cid: [{"id": cid, "cpuUtilization": invalid_cpu}],
        )
