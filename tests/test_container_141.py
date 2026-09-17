"""Regression coverage for the 1.4.1 CLI boundary and MCP responses."""

import json
import subprocess

import pytest

from apple_container_mcp import cli_wrapper
from apple_container_mcp.tools import containers, images, registry, system, prompts, machines
from d2c.registry import translate


@pytest.fixture(autouse=True)
def clear_version_cache():
    cli_wrapper._detect_cli_version.cache_clear()
    yield
    cli_wrapper._detect_cli_version.cache_clear()


@pytest.mark.parametrize("version", ["0.12.0", "1.0.0", "1.2.2", "1.3.1", "1.4.0", "1.4.1", "1.5.0", "2.0.0"])
def test_version_detection_and_recommendation(mocker, version):
    probe = mocker.patch(
        "subprocess.run",
        return_value=subprocess.CompletedProcess([], 0, f"container CLI version {version} (build: release)", ""),
    )
    parts = tuple(map(int, version.split(".")))
    assert cli_wrapper._detect_cli_version() == parts
    result = system.check_environment()
    assert result["cli_version"] == version
    assert ("recommendation" in result) == ((1, 0, 0) <= parts < (1, 4, 1))
    assert probe.call_count == 1


def test_unsuccessful_version_probe_is_not_trusted(mocker):
    mocker.patch(
        "subprocess.run", return_value=subprocess.CompletedProcess([], 1, "container CLI version 1.4.1", "failed")
    )
    assert cli_wrapper._detect_cli_version() is None


@pytest.mark.parametrize("state", ["unregistered", "not running"])
def test_failed_status_stdout_survives_through_tools(mocker, state):
    payload = {"status": state}
    mocker.patch(
        "subprocess.run",
        side_effect=subprocess.CalledProcessError(
            1, ["container", "system", "status"], output=json.dumps(payload), stderr=""
        ),
    )
    assert system.check_apiserver_status()["status"] == "stopped"
    result = system.system_status()
    assert result["status"] == "error"
    assert result["system_status"] == payload
    assert json.loads(system.get_system_status_resource()) == payload


@pytest.mark.parametrize("payload", [{}, {"status": "unknown"}, {"error": "Failed to parse JSON output"}, []])
def test_unrecognized_status_never_reports_healthy(mocker, payload):
    mocker.patch.object(system, "_run_container_cmd", return_value=payload)
    assert system.check_apiserver_status()["status"] == "error"


@pytest.mark.parametrize("stdout", ["not json", "[]"])
def test_invalid_failure_payload_is_not_a_stopped_service(mocker, stdout):
    mocker.patch.object(
        system, "_run_container_cmd", side_effect=cli_wrapper.ContainerCLIError("failed", 1, "other error", stdout)
    )
    assert system.check_apiserver_status()["status"] == "error"
    assert "system_status" not in system.system_status()


@pytest.mark.parametrize("escaped", [False, True])
def test_rich_status_and_optional_fields(mocker, escaped):
    payload = {
        "status": "running",
        "client": {"version": "1.4.1"},
        "server": {"version": "1.4.1"},
        "host": {"architecture": "arm64"},
        "paths": {"appRoot": "/Users/test/container/"},
    }
    output = json.dumps(payload)
    if escaped:
        output = output.replace("/", r"\/")
    mocker.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, output, ""))
    assert system.system_status()["system_status"] == payload
    assert system.check_apiserver_status()["status"] == "ok"
    assert "resources" not in system.system_status()["system_status"]


@pytest.mark.parametrize("scheme", [None, "http", "https"])
@pytest.mark.parametrize("action", ["pull", "push", "run", "login", "machine"])
def test_registry_scheme_arguments_and_credentials(mocker, action, scheme):
    process = mocker.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, "", ""))
    if action == "login":
        result = registry.registry_login("localhost:5000", "test", "secret", scheme=scheme)
        assert process.call_args.kwargs["input"] == "secret"
        assert "secret" not in process.call_args.args[0]
    elif action == "machine":
        result = machines.create_machine("localhost:5000/test", scheme=scheme, no_boot=True)
        assert process.call_args.args[0][-1] == "localhost:5000/test"
    elif action == "run":
        result = containers.run_container("localhost:5000/test", scheme=scheme, args_override=["echo", "hello"])
        args = process.call_args.args[0]
        assert args[-3:] == ["localhost:5000/test", "echo", "hello"]
    else:
        result = getattr(images, f"{action}_image")("localhost:5000/test", scheme=scheme)
    assert result["status"] == "ok"
    args = process.call_args.args[0]
    assert ("--scheme" in args) == (scheme is not None)
    if scheme:
        assert args[args.index("--scheme") + 1] == scheme


@pytest.mark.parametrize("scheme", ["auto", "", "HTTP", "https --debug"])
def test_invalid_scheme_never_executes(mocker, scheme):
    process = mocker.patch("subprocess.run")
    assert machines.create_machine("test", scheme=scheme)["status"] == "error"
    assert images.pull_image("test", scheme=scheme)["status"] == "error"
    assert images.push_image("test", scheme=scheme)["status"] == "error"
    assert containers.run_container("test", scheme=scheme)["status"] == "error"
    assert registry.registry_login("test", "u", "p", scheme=scheme)["status"] == "error"
    with pytest.raises(ValueError):
        prompts.setup_private_registry("test", scheme=scheme)
    process.assert_not_called()


def test_private_registry_prompt_carries_scheme():
    assert prompts.setup_private_registry("localhost:5000", "http").count('scheme="http"') == 3


@pytest.mark.parametrize("version", [None, (1, 3, 1), (1, 4, 0)])
def test_clean_requires_supported_version(mocker, version):
    mocker.patch.object(containers, "_detect_cli_version", return_value=version)
    run = mocker.patch.object(containers, "_run_container_cmd")
    assert containers.clean_container("test")["status"] == "error"
    run.assert_not_called()


@pytest.mark.parametrize("container_id", ["", "  ", "--debug"])
def test_clean_requires_explicit_id(mocker, container_id):
    probe = mocker.patch.object(containers, "_detect_cli_version")
    assert containers.clean_container(container_id)["status"] == "error"
    probe.assert_not_called()


def test_clean_uses_text_and_extended_timeout(mocker):
    mocker.patch.object(containers, "_detect_cli_version", return_value=(1, 4, 1))
    process = mocker.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, "test\n", ""))
    assert containers.clean_container("test")["status"] == "ok"
    assert process.call_args.args[0] == ["container", "clean", "test"]
    assert process.call_args.kwargs["timeout"] == 300


@pytest.mark.parametrize(
    "failure",
    [
        subprocess.CalledProcessError(1, ["container", "clean"], stderr="container is not running"),
        subprocess.TimeoutExpired(["container", "clean"], 300),
    ],
)
def test_clean_failure_and_timeout(mocker, failure):
    mocker.patch.object(containers, "_detect_cli_version", return_value=(1, 4, 1))
    mocker.patch("subprocess.run", side_effect=failure)
    result = containers.clean_container("test")
    assert result["status"] == "error"
    assert result["details"]


def test_d2c_preserves_new_status_and_explicit_transport():
    assert translate(["info", "--format", "json"])[0] == ["container", "system", "status", "--format", "json"]
    assert translate(["pull", "--scheme", "http", "localhost:5000/test"])[0] == [
        "container",
        "image",
        "pull",
        "--scheme",
        "http",
        "localhost:5000/test",
    ]
    with pytest.raises(KeyError):
        translate(["clean", "test"])
