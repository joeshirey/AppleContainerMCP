import importlib.metadata
from pathlib import Path
import re
import tomllib

import pytest

import apple_container_mcp
from apple_container_mcp import server

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "args, transport, port",
    [([], "stdio", 8000), (["--transport", "streamable-http", "--port", "8765"], "streamable-http", 8765)],
)
def test_server_transport(mocker, args, transport, port):
    mocker.patch("sys.argv", ["apple-container-mcp", *args])
    run = mocker.patch.object(server.mcp, "run")
    server.main()
    run.assert_called_once_with(transport=transport)
    assert server.mcp.settings.host == "127.0.0.1"
    assert server.mcp.settings.port == port


def test_invalid_port(mocker):
    mocker.patch("sys.argv", ["apple-container-mcp", "--port", "0"])
    run = mocker.patch.object(server.mcp, "run")
    with pytest.raises(SystemExit):
        server.main()
    run.assert_not_called()


# ---------------------------------------------------------------------------
# AC1 — Package version 0.7.2 lockstep (__init__.py, pyproject.toml, uv.lock)
# ---------------------------------------------------------------------------


def test_package_runtime_version_is_0_7_2():
    assert apple_container_mcp.__version__ == "0.7.2"
    assert importlib.metadata.version("applecontainermcp") == "0.7.2"


def test_packaging_manifests_version_0_7_2_lockstep():
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    lockfile = tomllib.loads((REPO_ROOT / "uv.lock").read_text(encoding="utf-8"))

    assert pyproject["project"]["version"] == "0.7.2"
    locked_versions = [pkg.get("version") for pkg in lockfile["package"] if pkg.get("name") == "applecontainermcp"]
    assert locked_versions == ["0.7.2"]


# ---------------------------------------------------------------------------
# AC2 — README.md, CHANGELOG.md ([0.7.2]), and docs/TDD.md (1.7.1 audit)
# ---------------------------------------------------------------------------


def test_readme_documents_apple_container_1_7_1():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert "1.7.1 is recommended and locally tested" in readme
    assert "1.6.1 is recommended" not in readme
    assert "no plugin system" not in readme.lower()

    for required_term in (
        "cpuUtilization",
        "cluster",
        "--all",
        "[dns]",
        "config.toml",
        "Time Machine",
        "BuildKit",
        ":authority",
        "4.3.1",
        "0.54.0",
        "bundled CLI plugins",
    ):
        assert required_term in readme


def test_changelog_0_7_2_release_notes_and_0_7_0_date():
    changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert "## [0.7.2] - 2026-11-08" in changelog
    assert "## [0.7.0] - 2026-10-23" in changelog
    assert "## [0.7.0] - Unreleased" not in changelog

    release_072 = changelog.split("## [0.7.2] - 2026-11-08", 1)[1].split("\n## [", 1)[0]
    for required_term in (
        "1.7.1",
        "cpuUtilization",
        "cluster",
        "--all",
        "[dns]",
        "config.toml",
        "Time Machine",
        "BuildKit",
        ":authority",
        "4.3.1",
        "0.54.0",
        "d2c",
        "plugin",
    ):
        assert required_term in release_072


def test_tdd_documents_1_7_1_audit_and_recommended_version():
    tdd = (REPO_ROOT / "docs" / "TDD.md").read_text(encoding="utf-8")

    assert "1.7.1 audit" in tdd
    assert "1.7.1 recommended" in tdd
    assert "1.6.1 recommended" not in tdd
    assert "recommended 1.2" not in tdd

    audit_171 = tdd.split("1.7.1 audit", 1)[1].split("\n## ", 1)[0]
    for required_term in (
        "cpuUtilization",
        "cluster",
        "--all",
        "[dns]",
        "config.toml",
        "Time Machine",
        "BuildKit",
        ":authority",
        "4.3.1",
        "0.54.0",
        "d2c",
        "plugin",
    ):
        assert required_term in audit_171


# ---------------------------------------------------------------------------
# AC3 — 1.7.1 update design specification with zero TBD/TODO placeholders
# ---------------------------------------------------------------------------


def test_1_7_1_design_spec_complete_with_zero_placeholders():
    spec_path = REPO_ROOT / "docs" / "superpowers" / "specs" / "2026-11-08-apple-container-1.7.1-update-design.md"
    assert spec_path.is_file(), f"Missing 1.7.1 design spec: {spec_path}"

    spec_text = spec_path.read_text(encoding="utf-8")
    assert re.search(r"\b(?:TBD|TODO)\b", spec_text, re.IGNORECASE) is None

    for required_term in (
        "1.7.1",
        "0.7.2",
        "cpuUtilization",
        "cluster",
        "[dns]",
        "config.toml",
        "Time Machine",
        "BuildKit",
        ":authority",
        "4.3.1",
        "0.54.0",
        "d2c",
        "check_environment",
    ):
        assert required_term in spec_text


# ---------------------------------------------------------------------------
# AC4 — 1.7.1 live CLI & CI validation record with real host outputs
# ---------------------------------------------------------------------------


def test_1_7_1_validation_plan_records_live_cli_and_ci_outputs():
    plan_path = REPO_ROOT / "docs" / "superpowers" / "plans" / "2026-11-08-apple-container-1.7.1-validation.md"
    assert plan_path.is_file(), f"Missing 1.7.1 validation record: {plan_path}"

    plan_text = plan_path.read_text(encoding="utf-8")
    assert re.search(r"\b(?:TBD|TODO)\b", plan_text, re.IGNORECASE) is None

    for required_term in (
        "container CLI version 1.7.1",
        "container-plugins",
        "build",
        "builder",
        "cluster",
        "check_environment",
        "d2c",
        "not supported by Apple Container",
        "ruff",
        "mypy",
        "pytest",
        "uv lock --check",
    ):
        assert required_term in plan_text
    assert ("smoke_test.py" in plan_text) or ("system status" in plan_text)
