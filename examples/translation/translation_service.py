"""
Translation service - Business logic layer

This demonstrates how to implement your core business logic
separately from MCP/REST concerns.
"""

import hashlib
import logging
from typing import Any, Dict, List

from key_value.aio.protocols import AsyncKeyValue

from .config import TranslationAPIConfig

logger = logging.getLogger(__name__)


class TranslationService:
    """
    Handles translation operations

    This is your business logic layer - it knows nothing about
    MCP or REST APIs, just pure translation functionality.
    """

    def __init__(self, api_config: TranslationAPIConfig, cache: AsyncKeyValue):
        """
        Initialize translation service

        Args:
            api_config: Translation API configuration
            cache: Key-value store for caching translations
        """
        self.api_config = api_config
        self.cache = cache

        logger.info(f"Initialized TranslationService with API: {api_config.api_url}")
        logger.info(f"Supported languages: {', '.join(api_config.supported_languages)}")

    async def translate(
        self,
        text: str,
        target_language: str,
        source_language: str = "auto"
    ) -> Dict[str, Any]:
        """
        Translate text to target language

        Args:
            text: Text to translate
            target_language: Target language code (e.g., 'es', 'fr')
            source_language: Source language code (default: 'auto' for auto-detect)

        Returns:
            Dictionary with translation result

        Raises:
            ValueError: If language codes are invalid
        """
        # Validate inputs
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        if target_language not in self.api_config.supported_languages:
            raise ValueError(
                f"Unsupported target language: {target_language}. "
                f"Supported: {', '.join(self.api_config.supported_languages)}"
            )

        text = text.strip()
        logger.info(f"Translating text to {target_language}: {text[:50]}...")

        # Check cache first
        cache_key = hashlib.sha256(
            f"{source_language}:{target_language}:{text}".encode()
        ).hexdigest()
        cached_result = await self.cache.get(cache_key, collection="translations")

        if cached_result:
            logger.info("Using cached translation")
            return cached_result

        # In a real implementation, you would call the actual translation API here
        # For this demo, we'll just return a mock translation
        result = {
            "original_text": text,
            "translated_text": f"[{target_language.upper()}] {text}",  # Mock translation
            "source_language": source_language,
            "target_language": target_language,
            "confidence": 0.95,  # Mock confidence score
            "detected_language": source_language if source_language != "auto" else "en",
            "service": "demo"
        }

        # Cache the result for 24 hours
        await self.cache.put(cache_key, result, collection="translations", ttl=86400)

        logger.info(f"Translation completed: {target_language}")
        return result

    async def get_supported_languages(self) -> List[Dict[str, str]]:
        """
        Get list of supported languages

        Returns:
            List of language dictionaries with code and name
        """
        # In a real implementation, this might call the API to get updated language list
        # For demo purposes, we'll return a static list
        language_names = {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ja": "Japanese",
            "zh": "Chinese",
            "ko": "Korean",
            "ru": "Russian"
        }

        return [
            {"code": code, "name": language_names.get(code, code)}
            for code in self.api_config.supported_languages
        ]

    async def detect_language(self, text: str) -> Dict[str, Any]:
        """
        Detect the language of given text

        Args:
            text: Text to analyze

        Returns:
            Dictionary with detected language and confidence
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        logger.info(f"Detecting language for: {text[:50]}...")

        # Mock language detection
        # In real implementation, call detection API
        return {
            "text": text,
            "detected_language": "en",  # Mock detection
            "language_name": "English",
            "confidence": 0.98,
            "is_reliable": True
        }
