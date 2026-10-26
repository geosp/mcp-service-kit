"""
Translation MCP Server

This demonstrates how to create a complete MCP server by extending
BaseMCPServer from mcp-service-kit.

Run it with:
    python -m examples.translation.server --mode stdio
    python -m examples.translation.server --mode http --port 3000 --no-auth
"""

import logging

from mcp_service_kit import BaseMCPServer, create_main_with_modes
from mcp_service_kit.cache import create_redis_store

from .config import AppConfig
from .service import TranslationMCPService
from .translation_service import TranslationService

logger = logging.getLogger(__name__)


class TranslationMCPServer(BaseMCPServer):
    """
    Translation MCP Server implementation

    Extends BaseMCPServer to provide translation functionality via MCP protocol.
    Only the service metadata is required; override create_auth_provider()
    to protect the HTTP transport.
    """

    @property
    def service_title(self) -> str:
        """Human-readable server title"""
        return "Translation MCP Server"

    @property
    def service_description(self) -> str:
        """Server description"""
        return (
            "Provides text translation capabilities via Model Context Protocol (MCP). "
            "Supports multiple languages with automatic detection and caching. "
            "Built using mcp-service-kit."
        )

    @property
    def service_version(self) -> str:
        """Service version"""
        return "1.0.0"


def create_translation_service(config: AppConfig) -> TranslationMCPService:
    """Factory function for creating the translation service"""
    # Create Redis-backed cache (falls back to no caching if Redis is down)
    cache = create_redis_store(config.redis_cache)

    # Create translation service (business logic)
    translation_service = TranslationService(
        api_config=config.translation_api,
        cache=cache
    )

    # Create MCP service wrapper
    return TranslationMCPService(translation_service)


main = create_main_with_modes(
    TranslationMCPServer,
    create_translation_service,
    AppConfig,
    "translation-server",
    "Translation MCP Server - Provides text translation via MCP protocol"
)


if __name__ == "__main__":
    main()
