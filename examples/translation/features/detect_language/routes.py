"""
REST API routes for language detection feature
"""

import logging
from fastapi import APIRouter, HTTPException

from mcp_translation.translation_service import TranslationService
from mcp_translation.features.detect_language.models import (
    DetectLanguageRequest,
    DetectLanguageResponse
)
from mcp_translation.shared.models import ErrorResponse

logger = logging.getLogger(__name__)


def create_router(translation_service: TranslationService) -> APIRouter:
    """
    Create router for language detection REST endpoints

    Args:
        translation_service: Translation service instance

    Returns:
        Configured APIRouter
    """
    router = APIRouter(prefix="/detect", tags=["Language Detection"])

    @router.post(
        "",
        response_model=DetectLanguageResponse,
        responses={
            400: {"model": ErrorResponse},
            500: {"model": ErrorResponse}
        }
    )
    async def detect_language_endpoint(request: DetectLanguageRequest):
        """
        Detect the language of provided text

        Args:
            request: Language detection request with text

        Returns:
            Detection result with language code and confidence

        Raises:
            HTTPException: 400 for validation errors, 500 for service errors
        """
        try:
            result = await translation_service.detect_language(request.text)
            return result
        except ValueError as e:
            logger.warning(f"Validation error: {e}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Language detection error: {e}")
            raise HTTPException(status_code=500, detail="Language detection failed")

    return router
