import itertools

import pytest

from apple_container_mcp import tools


@pytest.fixture(autouse=True)
def _reset_build_state():
    """Clear shared build state between tests to prevent cross-test pollution."""
    with tools._builds_lock:
        tools.active_builds.clear()
    tools._build_id_counter = itertools.count()
    yield
    # Clean up after the test as well, in case a background thread wrote state.
    with tools._builds_lock:
        tools.active_builds.clear()
