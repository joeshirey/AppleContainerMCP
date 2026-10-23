"""Regression coverage for the 1.6.0 CLI boundary: commit and network aliases."""

import subprocess

import pytest

from apple_container_mcp import cli_wrapper
from apple_container_mcp.tools import containers, networks


@pytest.fixture(autouse=True)
def clear_version_cache():
    cli_wrapper._detect_cli_version.cache_clear()
    yield
    cli_wrapper._detect_cli_version.cache_clear()


@pytest.mark.parametrize("version", [None, (1, 4, 1), (1, 5, 0)])
def test_commit_requires_supported_version(mocker, version):
    mocker.patch.object(containers, "_detect_cli_version", return_value=version)
    run = mocker.patch.object(containers, "_run_container_cmd")
    result = containers.commit_container("web", "web-snapshot:v1")
    assert result["status"] == "error"
    assert "1.6.0" in result["message"]
    run.assert_not_called()


@pytest.mark.parametrize(("container_id", "reference"), [("", "img"), ("  ", "img"), ("--debug", "img"), ("web", "")])
def test_commit_requires_explicit_arguments(mocker, container_id, reference):
    probe = mocker.patch.object(containers, "_detect_cli_version")
    assert containers.commit_container(container_id, reference)["status"] == "error"
    probe.assert_not_called()


def test_commit_returns_resolved_reference_with_extended_timeout(mocker):
    mocker.patch.object(containers, "_detect_cli_version", return_value=(1, 6, 0))
    process = mocker.patch(
        "subprocess.run",
        return_value=subprocess.CompletedProcess([], 0, "docker.io/library/web-snapshot:v1\n", ""),
    )
    result = containers.commit_container("web", "web-snapshot:v1")
    assert result["status"] == "ok"
    assert result["image"] == "docker.io/library/web-snapshot:v1"
    assert process.call_args.args[0] == ["container", "commit", "web", "web-snapshot:v1"]
    assert process.call_args.kwargs["timeout"] == 300


def test_commit_failure_reports_cli_error(mocker):
    mocker.patch.object(containers, "_detect_cli_version", return_value=(1, 6, 0))
    mocker.patch(
        "subprocess.run",
        side_effect=subprocess.CalledProcessError(
            1, ["container", "commit"], stderr="Error: get failed: container web not found"
        ),
    )
    result = containers.commit_container("web", "web-snapshot:v1")
    assert result["status"] == "error"
    assert "not found" in result["details"]
    assert result["exit_code"] == 1


@pytest.mark.parametrize(
    ("network", "expected"),
    [
        ("app-net", "app-net,alias=api.test,alias=.gateway.test"),
        (None, "default,alias=api.test,alias=.gateway.test"),
        ("app-net,mtu=1400", "app-net,mtu=1400,alias=api.test,alias=.gateway.test"),
    ],
)
def test_network_aliases_extend_network_spec(mocker, network, expected):
    mocker.patch.object(containers, "_detect_cli_version", return_value=(1, 6, 0))
    run = mocker.patch.object(containers, "_run_container_cmd", return_value={"raw_output": "id"})
    result = containers.run_container("nginx", network=network, network_aliases=["api.test", ".gateway.test"])
    assert result["status"] == "ok"
    args = run.call_args.args[0]
    assert args.count("--network") == 1
    assert args[args.index("--network") + 1] == expected


@pytest.mark.parametrize("alias", ["", " ", "a,mtu=1", "a=b", "two words"])
def test_invalid_network_alias_never_executes(mocker, alias):
    probe = mocker.patch.object(containers, "_detect_cli_version")
    run = mocker.patch.object(containers, "_run_container_cmd")
    result = containers.run_container("nginx", network_aliases=[alias])
    assert result["status"] == "error"
    probe.assert_not_called()
    run.assert_not_called()


def test_network_aliases_rejected_on_older_cli(mocker):
    mocker.patch.object(containers, "_detect_cli_version", return_value=(1, 5, 0))
    run = mocker.patch.object(containers, "_run_container_cmd")
    result = containers.run_container("nginx", network_aliases=["api.test"])
    assert result["status"] == "error"
    assert "1.6.0" in result["message"]
    run.assert_not_called()


def test_network_aliases_proceed_on_unknown_version(mocker):
    # Undetectable version → don't block; the CLI reports unsupported options itself.
    mocker.patch.object(containers, "_detect_cli_version", return_value=None)
    run = mocker.patch.object(containers, "_run_container_cmd", return_value={"raw_output": "id"})
    assert containers.run_container("nginx", network_aliases=["api.test"])["status"] == "ok"
    assert "default,alias=api.test" in run.call_args.args[0]


def test_run_without_aliases_skips_version_probe(mocker):
    probe = mocker.patch.object(containers, "_detect_cli_version")
    run = mocker.patch.object(containers, "_run_container_cmd", return_value={"raw_output": "id"})
    containers.run_container("nginx", network="app-net")
    probe.assert_not_called()
    args = run.call_args.args[0]
    assert args[args.index("--network") + 1] == "app-net"


def test_create_network_has_no_mtu_parameter(mocker):
    # `container network create` has never accepted --mtu; MTU is per attachment.
    run = mocker.patch.object(networks, "_run_container_cmd", return_value={})
    with pytest.raises(TypeError):
        networks.create_network("app-net", mtu=1400)  # type: ignore[call-arg]
    run.assert_not_called()
