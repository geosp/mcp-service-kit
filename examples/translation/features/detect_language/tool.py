"""
MCP Tool: Detect Language

Provides the detect_language tool for AI assistants.
"""

import logging
from typing import Dict, Any

from fastmcp import FastMCP

from mcp_translation.translation_service import TranslationService
from mcp_translation.features.detect_language.models import DetectLanguageRequest

logger = logging.getLogger(__name__)


def register_tool(mcp: FastMCP, translation_service: TranslationService) -> None:
    """
    Register the detect_language tool with the MCP server

    Args:
        mcp: FastMCP server instance
        translation_service: TranslationService instance
    """
    @mcp.tool()
    async def detect_language(text: str) -> Dict[str, Any]:
        """
        Detect the language of given text

        This tool helps AI assistants identify the language of user-provided text.
        Useful for understanding multilingual input or helping users identify unknown languages.

        Use this tool when users ask:
        - "What language is this: [text]?"
        - "Detect the language of this text"
        - "Is this Spanish or Portuguese?"
        - "What language am I speaking?"

        Features:
        - Automatic language detection
        - Confidence scores
        - Reliability indicators
        - Support for 10+ languages

        Args:
            text (str): Text to analyze
                Examples: "Bonjour", "こんにちは", "Hola mundo"

        Returns:
            dict: Language detection result containing:
                - text: The input text
                - detected_language: Detected language code
                - language_name: Human-readable language name
                - confidence: Detection confidence (0-1)
                - is_reliable: Boolean indicating detection reliability

        Raises:
            ValueError: If text is empty

        Example Usage (in AI conversation):
            User: "What language is 'Bonjour le monde'?"

            AI calls: detect_language("Bonjour le monde")

            AI responds: "This text is in French (detected with 98% confidence)"
        """
        try:
            logger.info(f"MCP tool called: detect_language(text='{text[:30]}...')")

            # Create and validate request
            request = DetectLanguageRequest(text=text)

            # Call translation service
            result = await translation_service.detect_language(request.text)

            logger.info(f"Language detected: {result['detected_language']}")
            return result

        except ValueError as e:
            logger.warning(f"Language detection validation error: {e}")
            raise
        except Exception as e:
            logger.error(f"Language detection error: {e}")
            raise
