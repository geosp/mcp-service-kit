"""
Data models for language detection feature
"""

from pydantic import BaseModel, Field


class DetectLanguageRequest(BaseModel):
    """Request model for language detection"""
    text: str = Field(description="Text to analyze", min_length=1, max_length=5000)


class DetectLanguageResponse(BaseModel):
    """Response model for language detection"""
    text: str = Field(description="Input text")
    detected_language: str = Field(description="Detected language code")
    language_name: str = Field(description="Human-readable language name")
    confidence: float = Field(
        description="Detection confidence score (0-1)",
        ge=0,
        le=1
    )
    is_reliable: bool = Field(description="Whether detection is considered reliable")
