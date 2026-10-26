import logging
from urllib.parse import urlsplit

import httpx2
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


def test_http_without_provider_refuses_to_start():
    with pytest.raises(ValueError, match="--no-auth"):
        make_server(transport="http").create_mcp_app()


def test_no_auth_logs_one_warning(caplog):
    make_server(transport="http", auth_enabled=False).create_mcp_app()
    warnings = [
        r for r in caplog.records
        if r.name == "mcp_service_kit.server" and r.levelno == logging.WARNING
    ]
    assert len(warnings) == 1
    assert "--no-auth" in warnings[0].getMessage()


def test_run_exits_on_missing_provider(caplog):
    with pytest.raises(SystemExit) as exc_info:
        make_server(transport="http").run()
    assert exc_info.value.code == 1
    assert "Configuration error" in caplog.text


def test_create_asgi_app():
    app = make_server(transport="http", auth_enabled=False).create_asgi_app()
    assert callable(app)


async def test_http_endpoint_is_served():
    server = make_server(transport="http", auth_enabled=False)
    app = server.create_asgi_app()
    path = urlsplit(server.http_endpoint_url()).path
    initialize = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "0"},
        },
    }
    async with app.router.lifespan_context(app):
        transport = httpx2.ASGITransport(app=app)
        async with httpx2.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                path,
                json=initialize,
                headers={"accept": "application/json, text/event-stream"},
            )
    assert response.status_code == 200


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
