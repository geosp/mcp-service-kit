import pytest
from fastmcp import FastMCP

from mcp_service_kit import BaseMCPServer, BaseService

ENV_VARS = [
    "MCP_TRANSPORT", "MCP_HOST", "MCP_PORT", "MCP_AUTH_ENABLED", "LOG_LEVEL",
    "MCP_REDIS_HOST", "MCP_REDIS_PORT", "MCP_REDIS_DB", "MCP_REDIS_PASSWORD",
    "MCP_REDIS_NAMESPACE", "MCP_REDIS_TTL", "MCP_REDIS_TIMEOUT",
    "MCP_CACHE_PATH", "MCP_CACHE_EXPIRY_DAYS", "APP_PORT",
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Start every test without the variables the kit reads or writes."""
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)


class DummyService(BaseService):
    def initialize(self) -> None:
        pass

    def get_service_name(self) -> str:
        return "dummy"

    def register_mcp_tools(self, mcp: FastMCP) -> None:
        @mcp.tool()
        def add(a: int, b: int) -> int:
            """Add two numbers"""
            return a + b


class DummyServer(BaseMCPServer):
    service_title = "Dummy"
    service_description = "Dummy server for tests"
    service_version = "0.0.0"
