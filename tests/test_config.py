from pathlib import Path

import pytest
from pydantic import ValidationError

from mcp_service_kit import BaseCacheConfig, BaseServerConfig, RedisCacheConfig


def test_server_config_defaults():
    config = BaseServerConfig()
    assert config.host == "0.0.0.0"
    assert config.port == 3000
    assert config.transport == "stdio"
    assert config.auth_enabled is True


def test_server_config_from_env(monkeypatch):
    monkeypatch.setenv("MCP_HOST", "127.0.0.1")
    monkeypatch.setenv("MCP_PORT", "8080")
    monkeypatch.setenv("MCP_TRANSPORT", "HTTP")
    monkeypatch.setenv("MCP_AUTH_ENABLED", "false")
    config = BaseServerConfig()
    assert config.host == "127.0.0.1"
    assert config.port == 8080
    assert config.transport == "http"
    assert config.auth_enabled is False


def test_server_config_custom_prefix(monkeypatch):
    monkeypatch.setenv("APP_PORT", "9000")
    assert BaseServerConfig(_env_prefix="APP_").port == 9000


def test_server_config_rejects_unknown_transport():
    with pytest.raises(ValidationError):
        BaseServerConfig(transport="rest")


def test_redis_config_defaults():
    config = RedisCacheConfig()
    assert config.host == "localhost"
    assert config.namespace == "mcp-cache"


def test_redis_config_from_env(monkeypatch):
    monkeypatch.setenv("MCP_REDIS_HOST", "cache.internal")
    monkeypatch.setenv("MCP_REDIS_PORT", "6380")
    monkeypatch.setenv("MCP_REDIS_DB", "2")
    monkeypatch.setenv("MCP_REDIS_PASSWORD", "secret")
    monkeypatch.setenv("MCP_REDIS_NAMESPACE", "ns")
    monkeypatch.setenv("MCP_REDIS_TTL", "120")
    monkeypatch.setenv("MCP_REDIS_TIMEOUT", "0.5")
    config = RedisCacheConfig()
    assert (config.host, config.port, config.db) == ("cache.internal", 6380, 2)
    assert config.password == "secret"
    assert config.namespace == "ns"
    assert config.ttl == 120
    assert config.timeout == 0.5


def test_cache_config_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("MCP_CACHE_PATH", str(tmp_path))
    monkeypatch.setenv("MCP_CACHE_EXPIRY_DAYS", "7")
    config = BaseCacheConfig()
    assert config.path == Path(tmp_path)
    assert config.expiry_days == 7
