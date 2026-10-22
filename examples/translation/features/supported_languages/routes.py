"""
REST API routes for supported languages feature
"""

import logging
from fastapi import APIRouter, HTTPException

from mcp_translation.translation_service import TranslationService
from mcp_translation.features.supported_languages.models import SupportedLanguagesResponse
from mcp_translation.shared.models import ErrorResponse

logger = logging.getLogger(__name__)


def create_router(translation_service: TranslationService) -> APIRouter:
    """
    Create router for supported languages REST endpoints

    Args:
        translation_service: Translation service instance

    Returns:
        Configured APIRouter
    """
    router = APIRouter(prefix="/languages", tags=["Languages"])

    @router.get(
        "",
        response_model=SupportedLanguagesResponse,
        responses={
            500: {"model": ErrorResponse}
        }
    )
    async def languages_endpoint():
        """
        Get list of supported languages

        Returns:
            List of supported languages with codes and names

        Raises:
            HTTPException: 500 for service errors
        """
        try:
            languages = await translation_service.get_supported_languages()
            return {
                "count": len(languages),
                "languages": languages
            }
        except Exception as e:
            logger.error(f"Error getting languages: {e}")
            raise HTTPException(status_code=500, detail="Failed to get languages")

    return router
