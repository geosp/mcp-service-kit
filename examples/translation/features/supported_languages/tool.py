"""
MCP Tool: Get Supported Languages

Provides the get_supported_languages tool for AI assistants.
"""

import logging
from typing import Dict, Any

from fastmcp import FastMCP

from mcp_translation.translation_service import TranslationService

logger = logging.getLogger(__name__)


def register_tool(mcp: FastMCP, translation_service: TranslationService) -> None:
    """
    Register the get_supported_languages tool with the MCP server

    Args:
        mcp: FastMCP server instance
        translation_service: TranslationService instance
    """
    @mcp.tool()
    async def get_supported_languages() -> Dict[str, Any]:
        """
        Get list of supported languages for translation

        This tool provides information about available translation languages.
        Helps users understand which languages are supported.

        Use this tool when users ask:
        - "What languages can you translate?"
        - "Do you support Japanese translation?"
        - "List all available languages"
        - "Can you translate to Korean?"

        Returns:
            dict: Supported languages information containing:
                - count: Number of supported languages
                - languages: List of language objects with:
                    - code: ISO language code (e.g., 'es', 'fr')
                    - name: Human-readable name (e.g., 'Spanish', 'French')

        Example Usage (in AI conversation):
            User: "What languages can you translate to?"

            AI calls: get_supported_languages()

            AI responds: "I can translate to 10 languages including Spanish, French,
                         German, Italian, Portuguese, Japanese, Chinese, Korean, and Russian."
        """
        try:
            logger.info("MCP tool called: get_supported_languages()")

            languages = await translation_service.get_supported_languages()

            result = {
                "count": len(languages),
                "languages": languages
            }

            logger.info(f"Returned {len(languages)} supported languages")
            return result

        except Exception as e:
            logger.error(f"Error getting supported languages: {e}")
            raise
