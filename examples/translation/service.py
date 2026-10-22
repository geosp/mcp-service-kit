"""
MCP Service wrapper for translation functionality

This demonstrates automatic feature discovery and registration pattern.
"""

import logging
import importlib
import pkgutil
from pathlib import Path

from core.server import BaseService
from fastmcp import FastMCP

from mcp_translation.translation_service import TranslationService

logger = logging.getLogger(__name__)


class TranslationMCPService(BaseService):
    """
    MCP Service wrapper for translation functionality

    Uses automatic feature discovery to register MCP tools.
    Each feature module in features/ can have a tool.py with a register_tool() function.
    """

    def __init__(self, translation_service: TranslationService):
        """
        Initialize MCP service

        Args:
            translation_service: Business logic service for translations
        """
        self.translation_service = translation_service
        logger.info("TranslationMCPService created")

    def initialize(self) -> None:
        """Initialize the service (called during startup)"""
        logger.info("TranslationMCPService initialized")

    def get_service_name(self) -> str:
        """Get the name of this service"""
        return "translation"

    def register_mcp_tools(self, mcp: FastMCP) -> None:
        """
        Register MCP tools for this service using automatic feature discovery

        Discovers and registers tools from all feature modules that have a tool.py
        with a register_tool() function.
        """
        logger.info("Discovering and registering MCP tools from features...")

        # Get the features package path
        features_package = "mcp_translation.features"
        features_path = Path(__file__).parent / "features"

        if not features_path.exists():
            logger.warning(f"Features directory not found: {features_path}")
            return

        # Discover all feature modules
        feature_count = 0
        for _, feature_name, is_pkg in pkgutil.iter_modules([str(features_path)]):
            if not is_pkg:
                continue  # Skip non-package modules

            try:
                # Import the tool module from the feature
                tool_module_name = f"{features_package}.{feature_name}.tool"
                tool_module = importlib.import_module(tool_module_name)

                # Check if the module has a register_tool function
                if hasattr(tool_module, "register_tool"):
                    # Register the tool, passing the translation service
                    tool_module.register_tool(mcp, self.translation_service)
                    feature_count += 1
                    logger.info(f"✓ Registered tools from feature: {feature_name}")
                else:
                    logger.warning(f"Feature '{feature_name}' has no register_tool() function")

            except ModuleNotFoundError:
                # Feature doesn't have a tool.py, skip it
                logger.debug(f"Feature '{feature_name}' has no tool.py, skipping")
            except Exception as e:
                logger.error(f"Error registering tools from feature '{feature_name}': {e}")

        logger.info(f"Registered MCP tools from {feature_count} features")

    def cleanup(self) -> None:
        """Clean up service resources (called during shutdown)"""
        logger.info("TranslationMCPService cleanup")
