"""
MCP Tool: Translate Text

Provides the translate_text tool for AI assistants.
"""

import logging
from typing import Dict, Any

from fastmcp import FastMCP

from mcp_translation.translation_service import TranslationService
from mcp_translation.features.translate.models import TranslateRequest, TranslateResponse

logger = logging.getLogger(__name__)


def register_tool(mcp: FastMCP, translation_service: TranslationService) -> None:
    """
    Register the translate_text tool with the MCP server

    Args:
        mcp: FastMCP server instance
        translation_service: TranslationService instance for translations
    """
    @mcp.tool()
    async def translate_text(text: str, target_language: str, source_language: str = "auto") -> Dict[str, Any]:
        """
        Translate text from one language to another

        This tool enables AI assistants to translate text for users.
        It supports automatic language detection and caches translations for performance.

        Use this tool when users ask questions like:
        - "Translate 'Hello' to Spanish"
        - "How do you say 'Good morning' in French?"
        - "What's the German word for 'computer'?"
        - "Translate this paragraph to Japanese: [text]"

        Features:
        - Automatic source language detection
        - Translation caching (24-hour TTL)
        - Support for 10+ languages
        - Confidence scores for translations

        Args:
            text (str): The text to translate
                Examples: "Hello world", "How are you?", "Good morning"

            target_language (str): Target language code
                Examples: "es" (Spanish), "fr" (French), "de" (German), "ja" (Japanese)
                Supported: en, es, fr, de, it, pt, ja, zh, ko, ru

            source_language (str, optional): Source language code
                Default: "auto" (automatic detection)
                Examples: "en", "es", "fr", or "auto"

        Returns:
            dict: Translation result containing:
                - original_text: The input text
                - translated_text: The translated text
                - source_language: Source language code
                - target_language: Target language code
                - detected_language: Detected source language (if auto-detect used)
                - confidence: Translation confidence score (0-1)
                - service: Translation service used

        Raises:
            ValueError: If text is empty or language codes are invalid

        Example Usage (in AI conversation):
            User: "Translate 'Hello world' to Spanish"

            AI calls: translate_text("Hello world", "es")

            AI responds: "The Spanish translation of 'Hello world' is 'Hola mundo'"

        Notes:
            - Translations are cached for 24 hours to improve performance
            - Language detection is automatic if source_language is 'auto'
            - Confidence scores indicate translation reliability
        """
        try:
            logger.info(f"MCP tool called: translate_text(text='{text[:30]}...', target='{target_language}')")

            # Create and validate request
            request = TranslateRequest(
                text=text,
                target_language=target_language,
                source_language=source_language
            )

            # Call translation service
            result = await translation_service.translate(
                text=request.text,
                target_language=request.target_language,
                source_language=request.source_language
            )

            logger.info(f"Translation completed: {target_language}")
            return result

        except ValueError as e:
            logger.warning(f"Translation validation error: {e}")
            raise
        except Exception as e:
            logger.error(f"Translation error: {e}")
            raise
