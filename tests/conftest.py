import itertools

import pytest

from apple_container_mcp.tools import images as _images_mod


@pytest.fixture(autouse=True)
def _reset_build_state():
    """Clear shared build state between tests to prevent cross-test pollution."""
    with _images_mod._builds_lock:
        _images_mod.active_builds.clear()
    _images_mod._build_id_counter = itertools.count()
    yield
    # Clean up after the test as well, in case a background thread wrote state.
    with _images_mod._builds_lock:
        _images_mod.active_builds.clear()
