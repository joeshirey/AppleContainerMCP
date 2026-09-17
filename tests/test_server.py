import pytest

from apple_container_mcp import server


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
