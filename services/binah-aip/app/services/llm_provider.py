"""LLM Provider Interface and Models"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class LLMRequest(BaseModel):
    """Standard LLM request model"""
    prompt: str = Field(..., description="The prompt/input to send to the LLM")
    model: Optional[str] = Field(None, description="Model to use (overrides default)")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Temperature for sampling")
    max_tokens: Optional[int] = Field(None, gt=0, description="Maximum tokens in response")
    system_prompt: Optional[str] = Field(None, description="System message/context")
    tenant_id: Optional[str] = Field(None, description="Tenant ID for multi-tenancy")
    user_id: Optional[str] = Field(None, description="User ID for tracking")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class LLMResponse(BaseModel):
    """Standard LLM response model"""
    content: str = Field(..., description="The LLM response content")
    model: str = Field(..., description="Model used for generation")
    tokens_used: int = Field(default=0, description="Total tokens used")
    input_tokens: int = Field(default=0, description="Input tokens")
    output_tokens: int = Field(default=0, description="Output tokens")
    finish_reason: str = Field(default="stop", description="Reason for completion")
    processing_time_ms: float = Field(default=0, description="Processing time in milliseconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    provider: str = Field(..., description="LLM provider used")
    request_id: Optional[str] = Field(None, description="Request tracking ID")


class ILLMProvider(ABC):
    """Interface for LLM providers"""

    @abstractmethod
    async def generate_response(
        self,
        request: LLMRequest
    ) -> LLMResponse:
        """
        Generate a response from the LLM

        Args:
            request: LLMRequest with prompt and configuration

        Returns:
            LLMResponse with the generated content and metadata
        """
        pass

    @abstractmethod
    async def generate_streaming_response(
        self,
        request: LLMRequest
    ) -> AsyncIterator[str]:
        """
        Generate a streaming response from the LLM

        Args:
            request: LLMRequest with prompt and configuration

        Yields:
            Chunks of the generated response
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the LLM provider is available and healthy

        Returns:
            True if healthy, False otherwise
        """
        pass

    @abstractmethod
    async def list_models(self) -> list[str]:
        """
        List available models from the provider

        Returns:
            List of available model names
        """
        pass
