"""Regression coverage for the Apple Container 1.7.1 runtime and tool contracts."""

import asyncio
import json
import subprocess
from typing import Any

import pytest

from apple_container_mcp import cli_wrapper
from apple_container_mcp.tools import containers, mcp, system


@pytest.fixture(autouse=True)
def clear_version_cache():
    cli_wrapper._detect_cli_version.cache_clear()
    yield
    cli_wrapper._detect_cli_version.cache_clear()


def _tool_descriptions() -> dict[str, str]:
    tools = asyncio.run(mcp.list_tools())
    return {tool.name: tool.description or "" for tool in tools}


# ---------------------------------------------------------------------------
# AC1 — RECOMMENDED_CLI_VERSION == (1, 7, 1) & check_environment() boundary
# ---------------------------------------------------------------------------


def test_recommended_cli_version_constant_is_1_7_1():
    assert cli_wrapper.RECOMMENDED_CLI_VERSION == (1, 7, 1)


def test_check_environment_1_7_1_upgrade_boundary(mocker):
    older_versions = ["1.0.0", "1.4.1", "1.6.0", "1.6.1", "1.7.0"]
    current_or_newer_versions = ["1.7.1", "1.7.2", "1.8.0", "2.0.0"]

    for version in older_versions:
        cli_wrapper._detect_cli_version.cache_clear()
        mocker.patch(
            "subprocess.run",
            return_value=subprocess.CompletedProcess([], 0, f"container CLI version {version} (build: release)", ""),
        )
        result = system.check_environment()
        assert result["status"] == "ok"
        assert result["cli_version"] == version
        assert "recommendation" in result
        assert "1.7.1" in result["recommendation"]
        assert version in result["recommendation"]

    for version in current_or_newer_versions:
        cli_wrapper._detect_cli_version.cache_clear()
        mocker.patch(
            "subprocess.run",
            return_value=subprocess.CompletedProcess([], 0, f"container CLI version {version} (build: release)", ""),
        )
        result = system.check_environment()
        assert result["status"] == "ok"
        assert result["cli_version"] == version
        assert "recommendation" not in result


# ---------------------------------------------------------------------------
# AC2 — stats_container() cpuUtilization contract & StatsReport passthrough
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("report", "has_cpu_utilization"),
    [
        (
            {
                "id": "web-1",
                "cpuUsageUsec": 250000,
                "cpuUtilization": 1.25,
                "memoryUsageBytes": 104857600,
                "memoryLimitBytes": 536870912,
            },
            True,
        ),
        (
            {
                "id": "web-1",
                "cpuUsageUsec": 250000,
                "memoryUsageBytes": 104857600,
                "memoryLimitBytes": 536870912,
            },
            False,
        ),
    ],
)
def test_stats_container_171_cpu_utilization_contract_and_passthrough(
    mocker, report: dict[str, Any], has_cpu_utilization: bool
):
    process = mocker.patch(
        "subprocess.run",
        return_value=subprocess.CompletedProcess([], 0, json.dumps([report]), ""),
    )

    result = containers.stats_container(["web-1"])

    assert process.call_args.args[0] == ["container", "stats", "--no-stream", "web-1", "--format", "json"]
    assert result == {"status": "ok", "stats": [report]}
    assert ("cpuUtilization" in result["stats"][0]) is has_cpu_utilization
    if has_cpu_utilization:
        assert result["stats"][0]["cpuUtilization"] == 1.25

    description = _tool_descriptions()["stats_container"]
    assert "1.7.1" in description
    assert "StatsReport" in description
    assert "cpuUtilization" in description
    assert "1.0" in description
    assert "core" in description.lower()
    assert "second sample" in description.lower()


# ---------------------------------------------------------------------------
# AC3 — 1.7.1 cluster-node lifecycle boundary across container tools
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "tool_name",
    ["list_containers", "start_container", "stop_container", "remove_container"],
)
def test_cluster_node_lifecycle_boundary_documented_and_enforced(mocker, tool_name: str):
    if tool_name == "list_containers":
        mocker.patch(
            "subprocess.run",
            return_value=subprocess.CompletedProcess([], 0, json.dumps([{"id": "app-web"}]), ""),
        )
        result = containers.list_containers(include_stopped=True)
        assert result == {"status": "ok", "containers": [{"id": "app-web"}], "count": 1}
    elif tool_name == "start_container":
        mocker.patch(
            "subprocess.run",
            side_effect=subprocess.CalledProcessError(
                1,
                ["container", "start", "cluster-0-control-plane"],
                stderr="Error: container cluster-0-control-plane not found",
            ),
        )
        result = containers.start_container("cluster-0-control-plane")
        assert result["status"] == "error"
        assert "not found" in result["details"]
    elif tool_name == "stop_container":
        for force, expected_cmd in ((False, "stop"), (True, "kill")):
            mocker.patch(
                "subprocess.run",
                side_effect=subprocess.CalledProcessError(
                    1,
                    ["container", expected_cmd, "cluster-0-control-plane"],
                    stderr=f"Error: {expected_cmd} failed: container cluster-0-control-plane not found",
                ),
            )
            result = containers.stop_container("cluster-0-control-plane", force=force)
            assert result["status"] == "error"
            assert "not found" in result["details"]
    else:
        mocker.patch(
            "subprocess.run",
            side_effect=subprocess.CalledProcessError(
                1,
                ["container", "rm", "cluster-0-control-plane"],
                stderr="Error: delete failed: container cluster-0-control-plane not found",
            ),
        )
        result = containers.remove_container("cluster-0-control-plane")
        assert result["status"] == "error"
        assert "not found" in result["details"]

    description = _tool_descriptions()[tool_name]
    assert "1.7.1" in description
    assert "cluster" in description.lower()
    assert "--all" in description
    for blocked_op in ("`start`", "`stop`", "`kill`", "`delete`"):
        assert blocked_op in description.lower()
    assert "not found" in description.lower()
    for working_op in ("`inspect`", "`logs`", "`exec`", "`stats`", "`clean`"):
        assert working_op in description.lower()


def test_cluster_node_supported_commands_succeed_on_named_cluster_node(mocker):
    node = "cluster-0-control-plane"

    def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if cmd == ["container", "--version"]:
            return subprocess.CompletedProcess(cmd, 0, "container CLI version 1.7.1 (build: release)", "")
        if cmd == ["container", "inspect", node]:
            return subprocess.CompletedProcess(cmd, 0, json.dumps([{"id": node, "status": "running"}]), "")
        if cmd == ["container", "logs", "-n", "20", node]:
            return subprocess.CompletedProcess(cmd, 0, "kubelet ready\n", "")
        if cmd == ["container", "exec", node, "hostname"]:
            return subprocess.CompletedProcess(cmd, 0, f"{node}\n", "")
        if cmd == ["container", "stats", "--no-stream", node, "--format", "json"]:
            return subprocess.CompletedProcess(cmd, 0, json.dumps([{"id": node, "cpuUtilization": 0.5}]), "")
        if cmd == ["container", "clean", node]:
            return subprocess.CompletedProcess(cmd, 0, f"{node}\n", "")
        raise AssertionError(f"Unexpected CLI invocation: {cmd}")

    mocker.patch("subprocess.run", side_effect=fake_run)

    assert containers.inspect_container(node) == {
        "status": "ok",
        "inspection": [{"id": node, "status": "running"}],
    }
    assert containers.get_logs(node, limit=20) == {"status": "ok", "logs": "kubelet ready"}
    assert containers.exec_in_container(node, ["hostname"]) == {"status": "ok", "output": node}
    assert containers.stats_container([node]) == {
        "status": "ok",
        "stats": [{"id": node, "cpuUtilization": 0.5}],
    }
    assert containers.clean_container(node) == {
        "status": "ok",
        "message": f"Reclaimed unused filesystem space in '{node}'.",
    }

    descriptions = _tool_descriptions()
    for lifecycle_tool in ("list_containers", "start_container", "stop_container", "remove_container"):
        for working_op in ("`inspect`", "`logs`", "`exec`", "`stats`", "`clean`"):
            assert working_op in descriptions[lifecycle_tool].lower()


# ---------------------------------------------------------------------------
# AC4 — system_property_list() [dns] TOML defaults contract in 1.7.1
# ---------------------------------------------------------------------------


def test_system_property_list_documents_171_dns_toml_defaults(mocker):
    dns_properties = [
        {"id": "dns.domain", "value": "test"},
        {"id": "dns.nameservers", "value": ["1.1.1.1"]},
    ]
    process = mocker.patch(
        "subprocess.run",
        return_value=subprocess.CompletedProcess([], 0, json.dumps(dns_properties), ""),
    )

    result = system.system_property_list()

    assert process.call_args.args[0] == ["container", "system", "property", "list", "--format", "json"]
    assert result == {"status": "ok", "properties": dns_properties}

    description = _tool_descriptions()["system_property_list"]
    assert "1.7.1" in description
    assert "[dns]" in description
    assert "~/.config/container/config.toml" in description
    for key in ("`dns`", "`dns-search`", "`dns-option`", "`dns-domain`"):
        assert key in description
