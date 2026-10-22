"""
Shared models for translation MCP server

Contains base models and error types used across features.
"""

from typing import Optional
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response model"""
    error: str = Field(description="Error type")
    detail: str = Field(description="Error details")
    code: Optional[str] = Field(default=None, description="Error code")


class BaseTranslationRequest(BaseModel):
    """Base request model for translation operations"""
    pass


class BaseTranslationResponse(BaseModel):
    """Base response model for translation operations"""
    pass
