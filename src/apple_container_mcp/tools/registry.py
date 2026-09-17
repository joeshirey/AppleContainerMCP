"""Registry authentication tools."""

import subprocess
from typing import Dict, Any

from . import mcp, _run_container_cmd, ContainerCLIError, _validate_scheme


@mcp.tool()
def registry_login(server: str, username: str, password: str, scheme: str | None = None) -> Dict[str, Any]:
    """
    Log in to a container registry so that pull/push operations can authenticate.
    Example: registry_login("registry.example.com", "myuser", "mypassword")
    scheme may explicitly select http or https; CLI 1.4.1 defaults to https.
    Note: credentials are passed via stdin to avoid exposing them in process arguments.
    """
    error = _validate_scheme(scheme)
    if error:
        return {"status": "error", "message": error}
    full_cmd = ["container", "registry", "login", "--username", username, "--password-stdin", server]
    if scheme is not None:
        full_cmd.extend(["--scheme", scheme])
    try:
        process = subprocess.run(
            full_cmd,
            input=password,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if process.returncode != 0:
            return {"status": "error", "message": f"Failed to log in to '{server}'.", "details": process.stderr.strip()}
        return {"status": "ok", "message": f"Successfully logged in to '{server}'."}
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": f"Login to '{server}' timed out."}
    except FileNotFoundError:
        return {"status": "error", "message": "The 'container' CLI was not found on PATH."}


@mcp.tool()
def registry_logout(server: str) -> Dict[str, Any]:
    """
    Log out from a container registry, removing stored credentials.
    Example: registry_logout("registry.example.com")
    """
    try:
        _run_container_cmd(["registry", "logout", server])
        return {"status": "ok", "message": f"Successfully logged out from '{server}'."}
    except ContainerCLIError as e:
        return {"status": "error", "message": f"Failed to log out from '{server}'.", "details": e.stderr}
