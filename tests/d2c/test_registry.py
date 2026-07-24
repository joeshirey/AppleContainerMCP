import pytest
from d2c.registry import translate


def test_ps_translates_to_list() -> None:
    args, note = translate(["ps"])
    assert args == ["container", "list"]
    assert note is None


def test_ps_with_dash_a_passthrough() -> None:
    args, note = translate(["ps", "-a"])
    assert args == ["container", "list", "-a"]


def test_images_translates_to_image_list() -> None:
    args, note = translate(["images"])
    assert args == ["container", "image", "list"]


def test_rmi_translates_and_has_note() -> None:
    args, note = translate(["rmi", "nginx"])
    assert args == ["container", "image", "remove", "nginx"]
    assert note is not None
    assert len(note) > 0


def test_pull_translates_to_image_pull() -> None:
    args, note = translate(["pull", "nginx"])
    assert args == ["container", "image", "pull", "nginx"]


def test_push_translates_to_image_push() -> None:
    args, note = translate(["push", "myrepo/myimage"])
    assert args == ["container", "image", "push", "myrepo/myimage"]


def test_tag_translates_to_image_tag() -> None:
    args, note = translate(["tag", "src", "dst"])
    assert args == ["container", "image", "tag", "src", "dst"]


def test_rm_translates_to_delete() -> None:
    args, note = translate(["rm", "mycontainer"])
    assert args == ["container", "delete", "mycontainer"]


def test_login_translates_to_registry_login() -> None:
    args, note = translate(["login", "registry.example.com"])
    assert args == ["container", "registry", "login", "registry.example.com"]


def test_logout_translates_to_registry_logout() -> None:
    args, note = translate(["logout"])
    assert args == ["container", "registry", "logout"]


def test_info_translates_to_system_status() -> None:
    args, note = translate(["info"])
    assert args == ["container", "system", "status"]


def test_version_translates_to_system_version() -> None:
    args, note = translate(["version"])
    assert args == ["container", "system", "version"]


def test_load_translates_to_image_load() -> None:
    args, note = translate(["load"])
    assert args == ["container", "image", "load"]


def test_save_translates_to_image_save() -> None:
    args, note = translate(["save", "myimage"])
    assert args == ["container", "image", "save", "myimage"]


def test_network_subcommand_passthrough() -> None:
    args, note = translate(["network", "ls"])
    assert args == ["container", "network", "ls"]


def test_volume_subcommand_passthrough() -> None:
    args, note = translate(["volume", "create", "myvol"])
    assert args == ["container", "volume", "create", "myvol"]


def test_system_subcommand_passthrough() -> None:
    args, note = translate(["system", "df"])
    assert args == ["container", "system", "df"]


def test_image_subcommand_passthrough() -> None:
    args, note = translate(["image", "ls"])
    assert args == ["container", "image", "ls"]


def test_builder_subcommand_passthrough() -> None:
    args, note = translate(["builder", "start"])
    assert args == ["container", "builder", "start"]


def test_docker_container_namespace_stripped() -> None:
    args, note = translate(["container", "run", "nginx"])
    assert args == ["container", "run", "nginx"]


def test_docker_container_ps_alias() -> None:
    args, note = translate(["container", "ps"])
    assert args == ["container", "list"]


def test_unknown_command_raises_key_error() -> None:
    with pytest.raises(KeyError):
        translate(["nonexistent"])


def test_empty_args_raises_key_error() -> None:
    with pytest.raises(KeyError):
        translate([])
