"""
Configuration management for Translation MCP Server

Shows how to extend core configuration classes for your service.
"""

import os
from typing import Optional, List
from pydantic import BaseModel, Field

from core.config import (
    AuthentikConfig,
    BaseServerConfig,
    RedisCacheConfig,
    load_dotenv
)

# Ensure environment variables are loaded
load_dotenv()


class TranslationAPIConfig(BaseModel):
    """
    Configuration for translation API

    This shows how to add service-specific configuration
    """
    api_key: str = Field(
        default="demo-key",
        description="Translation API key"
    )
    api_url: str = Field(
        default="https://translation.googleapis.com/language/translate/v2",
        description="Translation API endpoint"
    )
    default_source_lang: str = Field(
        default="auto",
        description="Default source language (auto-detect)"
    )
    supported_languages: List[str] = Field(
        default=["en", "es", "fr", "de", "it", "pt", "ja", "zh", "ko", "ru"],
        description="List of supported language codes"
    )

    @classmethod
    def from_env(cls) -> "TranslationAPIConfig":
        """Load translation API config from environment variables"""
        api_key = os.getenv("TRANSLATION_API_KEY", "demo-key")
        api_url = os.getenv("TRANSLATION_API_URL", cls.model_fields["api_url"].default)
        default_source = os.getenv("TRANSLATION_DEFAULT_SOURCE", "auto")

        # Parse supported languages from comma-separated string
        supported_str = os.getenv("TRANSLATION_SUPPORTED_LANGUAGES", "")
        supported = [lang.strip() for lang in supported_str.split(",")] if supported_str else cls.model_fields["supported_languages"].default

        return cls(
            api_key=api_key,
            api_url=api_url,
            default_source_lang=default_source,
            supported_languages=supported
        )


class ServerConfig(BaseServerConfig):
    """
    Server configuration for Translation MCP

    Extends BaseServerConfig with translation-specific settings
    """
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="List of allowed origins for CORS"
    )

    @classmethod
    def from_env(cls) -> "ServerConfig":
        """Load server configuration from environment variables"""
        config = super().from_env(env_prefix="MCP_")

        # Parse CORS origins
        cors_str = os.getenv("MCP_CORS_ORIGINS", "http://localhost:3000,http://localhost:8080")
        config.cors_origins = [origin.strip() for origin in cors_str.split(",")]

        return config


class AppConfig(BaseModel):
    """
    Complete application configuration

    Aggregates all configuration sections into a single object.
    """
    server: ServerConfig
    redis_cache: RedisCacheConfig
    translation_api: TranslationAPIConfig
    authentik: Optional[AuthentikConfig] = None

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Load complete configuration from environment variables"""
        server = ServerConfig.from_env()
        redis_cache = RedisCacheConfig.from_env(env_prefix="MCP_")
        translation_api = TranslationAPIConfig.from_env()

        # Only load Authentik config if using HTTP transport with auth enabled
        authentik = None
        if server.transport == "http" and server.auth_enabled:
            authentik = AuthentikConfig.from_env_optional()

        return cls(
            server=server,
            redis_cache=redis_cache,
            translation_api=translation_api,
            authentik=authentik
        )


# Global configuration instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get global application configuration"""
    global _config
    if _config is None:
        _config = AppConfig.from_env()
    return _config


def load_config() -> AppConfig:
    """Load application configuration from environment"""
    global _config
    _config = AppConfig.from_env()
    return _config
