import pytest
from fastmcp import Client
from fastmcp.server.auth import JWTVerifier

from mcp_service_kit import BaseServerConfig

from .conftest import DummyServer, DummyService


def make_server(server_class=DummyServer, **config):
    return server_class(BaseServerConfig(**config), DummyService())


async def test_create_mcp_app_registers_tools():
    mcp = make_server().create_mcp_app()
    async with Client(mcp) as client:
        tools = await client.list_tools()
        assert [t.name for t in tools] == ["add"]
        result = await client.call_tool("add", {"a": 2, "b": 3})
        assert result.data == 5


class AuthServer(DummyServer):
    calls = 0

    def create_auth_provider(self):
        type(self).calls += 1
        self.provider = JWTVerifier(
            jwks_uri="https://auth.example.com/.well-known/jwks.json",
            issuer="https://auth.example.com",
            audience="mcp",
        )
        return self.provider


@pytest.mark.parametrize(
    ("transport", "auth_enabled", "expect_auth"),
    [
        ("http", True, True),
        ("http", False, False),
        ("stdio", True, False),
        ("stdio", False, False),
    ],
)
def test_auth_hook_only_for_http_with_auth(transport, auth_enabled, expect_auth):
    AuthServer.calls = 0
    server = make_server(AuthServer, transport=transport, auth_enabled=auth_enabled)
    mcp = server.create_mcp_app()
    assert AuthServer.calls == (1 if expect_auth else 0)
    if expect_auth:
        assert mcp.auth is server.provider
    else:
        assert mcp.auth is None


def test_http_without_provider_warns(caplog):
    make_server(transport="http").create_mcp_app()
    assert "without authentication" in caplog.text


def test_create_asgi_app():
    app = make_server(transport="http").create_asgi_app()
    assert callable(app)


class ConfiguredServer(DummyServer):
    instructions = "Use add for arithmetic."

    def create_middleware(self):
        from fastmcp.server.middleware.timing import TimingMiddleware

        return [TimingMiddleware()]


async def test_metadata_and_middleware_reach_fastmcp():
    mcp = make_server(ConfiguredServer).create_mcp_app()
    assert mcp.version == "0.0.0"
    assert mcp.instructions == "Use add for arithmetic."
    assert any(type(m).__name__ == "TimingMiddleware" for m in mcp.middleware)
    async with Client(mcp) as client:
        assert client.instructions == "Use add for arithmetic."
        assert client.server_info.version == "0.0.0"
