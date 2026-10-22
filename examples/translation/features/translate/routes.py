"""
REST API routes for translation feature
"""

import logging
from fastapi import APIRouter, HTTPException

from mcp_translation.translation_service import TranslationService
from mcp_translation.features.translate.models import TranslateRequest, TranslateResponse
from mcp_translation.shared.models import ErrorResponse

logger = logging.getLogger(__name__)


def create_router(translation_service: TranslationService) -> APIRouter:
    """
    Create router for translation REST endpoints

    Args:
        translation_service: Translation service instance

    Returns:
        Configured APIRouter
    """
    router = APIRouter(prefix="/translate", tags=["Translation"])

    @router.post(
        "",
        response_model=TranslateResponse,
        responses={
            400: {"model": ErrorResponse},
            500: {"model": ErrorResponse}
        }
    )
    async def translate_endpoint(request: TranslateRequest):
        """
        Translate text to target language

        Args:
            request: Translation request with text and language codes

        Returns:
            Translation result

        Raises:
            HTTPException: 400 for validation errors, 500 for service errors
        """
        try:
            result = await translation_service.translate(
                text=request.text,
                target_language=request.target_language,
                source_language=request.source_language
            )
            return result
        except ValueError as e:
            logger.warning(f"Validation error: {e}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Translation error: {e}")
            raise HTTPException(status_code=500, detail="Translation failed")

    return router
