"""
Configuration models for MCP servers

Each class is a pydantic-settings model: instantiating it reads its fields
from environment variables with the class's prefix, for example
``BaseServerConfig()`` reads ``MCP_TRANSPORT``, ``MCP_PORT``, ... Pass
``_env_prefix="APP_"`` to read a different prefix, or keyword arguments to
set values directly.

Loading a .env file is left to the application (see
``create_main_with_modes``), so importing this module has no side effects.
"""

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseCacheConfig(BaseSettings):
    """
    Base configuration for file-based caching

    Environment variables: MCP_CACHE_PATH, MCP_CACHE_EXPIRY_DAYS
    """
    model_config = SettingsConfigDict(env_prefix="MCP_CACHE_", extra="ignore")

    path: Path = Field(
        default_factory=lambda: Path.home() / ".cache",
        description="Base directory for cache files"
    )
    expiry_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Number of days before cached data expires"
    )


class RedisCacheConfig(BaseSettings):
    """
    Redis cache configuration

    Environment variables: MCP_REDIS_HOST, MCP_REDIS_PORT, MCP_REDIS_DB,
    MCP_REDIS_PASSWORD, MCP_REDIS_NAMESPACE, MCP_REDIS_TTL, MCP_REDIS_TIMEOUT
    """
    model_config = SettingsConfigDict(env_prefix="MCP_REDIS_", extra="ignore")

    host: str = Field(
        default="localhost",
        description="Redis server hostname or IP address"
    )
    port: int = Field(
        default=6379,
        ge=1,
        le=65535,
        description="Redis server port"
    )
    db: int = Field(
        default=0,
        ge=0,
        le=15,
        description="Redis database index (0-15)"
    )
    password: str | None = Field(
        default=None,
        description="Redis password (optional)"
    )
    namespace: str = Field(
        default="mcp-cache",
        description="Default collection that keys are stored under"
    )
    ttl: int = Field(
        default=28800,  # 8 hours in seconds
        ge=60,          # Minimum 1 minute
        description="Default TTL for cached values in seconds"
    )
    timeout: float = Field(
        default=10.0,
        gt=0,
        description="Timeout in seconds for each Redis operation"
    )


class BaseServerConfig(BaseSettings):
    """
    Base server configuration

    Selects the transport and controls how the server listens for connections
    when using HTTP transport. The environment variables (MCP_TRANSPORT,
    MCP_HOST, MCP_PORT, MCP_AUTH_ENABLED) are the ones the standard CLI sets.
    """
    model_config = SettingsConfigDict(env_prefix="MCP_", extra="ignore")

    host: str = Field(
        default="0.0.0.0",
        description="Bind address (0.0.0.0 = all interfaces)"
    )
    port: int = Field(
        default=3000,
        ge=1,
        le=65535,
        description="Port number for HTTP server"
    )
    transport: Literal["stdio", "http"] = Field(
        default="stdio",
        description="Transport mode: 'stdio' for direct MCP, 'http' for web server"
    )
    auth_enabled: bool = Field(
        default=True,
        description="Whether authentication is enabled (when transport=http)"
    )

    @field_validator("transport", mode="before")
    @classmethod
    def _lowercase_transport(cls, value: object) -> object:
        return value.lower() if isinstance(value, str) else value
