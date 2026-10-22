"""
Data models for translation feature
"""

from typing import Optional
from pydantic import BaseModel, Field


class TranslateRequest(BaseModel):
    """Request model for translation"""
    text: str = Field(description="Text to translate", min_length=1, max_length=5000)
    target_language: str = Field(description="Target language code (e.g., 'es', 'fr')")
    source_language: str = Field(
        default="auto",
        description="Source language code or 'auto' for detection"
    )


class TranslateResponse(BaseModel):
    """Response model for translation"""
    original_text: str = Field(description="Original input text")
    translated_text: str = Field(description="Translated text")
    source_language: str = Field(description="Source language code")
    target_language: str = Field(description="Target language code")
    detected_language: Optional[str] = Field(
        default=None,
        description="Detected language (if auto-detect was used)"
    )
    confidence: float = Field(
        default=1.0,
        description="Translation confidence score (0-1)",
        ge=0,
        le=1
    )
    service: str = Field(default="demo", description="Translation service used")
