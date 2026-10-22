"""
Translation MCP Server

This demonstrates how to create a complete MCP server by extending
BaseMCPServer from the mcp-weather core infrastructure.
"""

import logging
import sys
from typing import List, Optional, Any

from fastapi import FastAPI, APIRouter, HTTPException
from core.server import BaseMCPServer
from core.auth_mcp import create_auth_provider
from core.cache import RedisCacheClient

from mcp_translation.config import AppConfig, get_config
from mcp_translation.translation_service import TranslationService
from mcp_translation.service import TranslationMCPService

logger = logging.getLogger(__name__)


class TranslationMCPServer(BaseMCPServer):
    """
    Translation MCP Server implementation

    Extends BaseMCPServer to provide translation functionality via MCP protocol.
    This shows how to implement all required abstract methods.
    """

    @property
    def service_title(self) -> str:
        """Title shown in API documentation"""
        return "Translation MCP Server"

    @property
    def service_description(self) -> str:
        """Description shown in API documentation"""
        return (
            "Provides text translation capabilities via Model Context Protocol (MCP). "
            "Supports multiple languages with automatic detection and caching. "
            "Built using mcp-weather core infrastructure."
        )

    @property
    def service_version(self) -> str:
        """Service version"""
        return "1.0.0"

    @property
    def allowed_cors_origins(self) -> List[str]:
        """CORS origins for web clients"""
        return self.config.server.cors_origins

    def create_auth_provider(self) -> Optional[Any]:
        """
        Create authentication provider for this server

        Returns None to disable auth, or create an Authentik provider
        """
        if not self.config.authentik:
            logger.info("Authentication is disabled (no Authentik config)")
            return None

        logger.info("Creating Authentik authentication provider")
        return create_auth_provider("translation")

    def create_router(self) -> APIRouter:
        """
        Create REST API router with endpoints

        Uses feature-based organization - each feature has its own routes.py
        This demonstrates automatic feature route discovery and composition.
        """
        import importlib
        import pkgutil
        from pathlib import Path

        # Create main router
        router = APIRouter()

        # Access the translation service through the MCP service wrapper
        translation_service = self.service.translation_service

        # Add base routes (health, info)
        @router.get("/health")
        async def health():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "service": "translation",
                "version": self.service_version
            }

        @router.get("/info")
        async def info():
            """Service information endpoint"""
            return {
                "title": self.service_title,
                "description": self.service_description,
                "version": self.service_version,
                "supported_languages": await translation_service.get_supported_languages()
            }

        # Discover and include feature routes
        features_package = "mcp_translation.features"
        features_path = Path(__file__).parent / "features"

        if features_path.exists():
            for _, feature_name, is_pkg in pkgutil.iter_modules([str(features_path)]):
                if not is_pkg:
                    continue

                try:
                    # Import the routes module from the feature
                    routes_module_name = f"{features_package}.{feature_name}.routes"
                    routes_module = importlib.import_module(routes_module_name)

                    # Check if the module has a create_router function
                    if hasattr(routes_module, "create_router"):
                        # Create and include the feature router
                        feature_router = routes_module.create_router(translation_service)
                        router.include_router(feature_router)
                        logger.info(f"✓ Included routes from feature: {feature_name}")

                except ModuleNotFoundError:
                    # Feature doesn't have routes.py, skip it
                    logger.debug(f"Feature '{feature_name}' has no routes.py, skipping")
                except Exception as e:
                    logger.error(f"Error including routes from feature '{feature_name}': {e}")

        return router

    def register_exception_handlers(self, app: FastAPI) -> None:
        """
        Register custom exception handlers

        This demonstrates how to add service-specific error handling.
        """
        from fastapi import Request
        from fastapi.responses import JSONResponse

        @app.exception_handler(ValueError)
        async def value_error_handler(request: Request, exc: ValueError):
            """Handle validation errors"""
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Validation Error",
                    "detail": str(exc)
                }
            )

        @app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            """Handle unexpected errors"""
            logger.error(f"Unhandled exception: {exc}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "detail": "An unexpected error occurred"
                }
            )


def main():
    """
    Main entry point for the Translation MCP Server (manual implementation)
    """
    try:
        # Set log level to INFO
        logging.getLogger().setLevel(logging.INFO)

        logger.info("Starting Translation MCP Server...")
        logger.info("Loading configuration...")
        config = get_config()

        # Create Redis cache client
        logger.info("Initializing Redis cache...")
        cache_client = RedisCacheClient(config.redis_cache)

        # Create translation service (business logic)
        logger.info("Initializing translation service...")
        translation_service = TranslationService(
            api_config=config.translation_api,
            cache_client=cache_client
        )

        # Create MCP service wrapper
        logger.info("Creating MCP service wrapper...")
        mcp_service = TranslationMCPService(translation_service)

        # Create and run server
        logger.info("Creating server...")
        server = TranslationMCPServer(config, mcp_service)

        logger.info("Starting server...")
        server.run()

    except KeyboardInterrupt:
        logger.info("\nShutdown requested by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


def create_translation_service(config: AppConfig) -> TranslationMCPService:
    """Factory function for creating the translation service"""
    # Create Redis cache client
    cache_client = RedisCacheClient(config.redis_cache)
    
    # Create translation service (business logic)
    translation_service = TranslationService(
        api_config=config.translation_api,
        cache_client=cache_client
    )
    
    # Create MCP service wrapper
    return TranslationMCPService(translation_service)


# 🆕 NEW: Alternative main with CLI mode support
from core.server import create_main_with_modes

main_with_modes = create_main_with_modes(
    TranslationMCPServer,
    create_translation_service,
    get_config,
    "translation-server",
    "Translation MCP Server - Provides text translation via MCP protocol"
)


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # You can choose between two approaches:
    
    # Option 1: Manual main (current approach) 
    # main()
    
    # Option 2: 🆕 NEW - Automatic CLI with --mode support
    main_with_modes()
