"""
Configuration management for Translation MCP Server

Shows how to combine mcp-service-kit configuration classes with your own.
Each section reads its own environment variables when instantiated.
"""

from typing import Annotated

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from mcp_service_kit import BaseServerConfig, RedisCacheConfig


class TranslationAPIConfig(BaseSettings):
    """
    Configuration for translation API

    This shows how to add service-specific configuration. Environment
    variables: TRANSLATION_API_KEY, TRANSLATION_API_URL,
    TRANSLATION_DEFAULT_SOURCE_LANG, TRANSLATION_SUPPORTED_LANGUAGES
    (comma-separated).
    """
    model_config = SettingsConfigDict(env_prefix="TRANSLATION_", extra="ignore")

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
    supported_languages: Annotated[list[str], NoDecode] = Field(
        default=["en", "es", "fr", "de", "it", "pt", "ja", "zh", "ko", "ru"],
        description="List of supported language codes"
    )

    @field_validator("supported_languages", mode="before")
    @classmethod
    def _split_languages(cls, value: object) -> object:
        if isinstance(value, str):
            return [lang.strip() for lang in value.split(",") if lang.strip()]
        return value


class AppConfig(BaseModel):
    """
    Complete application configuration

    Aggregates all configuration sections into a single object. The server
    section is passed to the server; the rest go to the service.
    """
    server: BaseServerConfig = Field(default_factory=BaseServerConfig)
    redis_cache: RedisCacheConfig = Field(default_factory=RedisCacheConfig)
    translation_api: TranslationAPIConfig = Field(default_factory=TranslationAPIConfig)
