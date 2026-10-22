"""
Data models for supported languages feature
"""

from typing import List
from pydantic import BaseModel, Field


class LanguageInfo(BaseModel):
    """Information about a supported language"""
    code: str = Field(description="ISO language code (e.g., 'es', 'fr')")
    name: str = Field(description="Human-readable language name (e.g., 'Spanish', 'French')")


class SupportedLanguagesResponse(BaseModel):
    """Response model for supported languages"""
    count: int = Field(description="Number of supported languages")
    languages: List[LanguageInfo] = Field(description="List of supported languages")
