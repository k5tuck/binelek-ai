"""Ollama LLM Provider Implementation"""

from typing import AsyncIterator, Optional
import logging
import time
import httpx
import json
from app.services.llm_provider import ILLMProvider, LLMRequest, LLMResponse

logger = logging.getLogger(__name__)


class OllamaProvider(ILLMProvider):
    """Ollama LLM Provider for local LLM models"""

    def __init__(self, base_url: str = "http://localhost:11434", default_model: str = "llama2"):
        """
        Initialize Ollama provider

        Args:
            base_url: Base URL for Ollama API
            default_model: Default model to use if not specified
        """
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.provider_name = "ollama"
        self.client = httpx.AsyncClient(timeout=300.0)  # Long timeout for local models

    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """
        Generate a response from Ollama

        Args:
            request: LLMRequest with prompt and configuration

        Returns:
            LLMResponse with the generated content
        """
        try:
            start_time = time.time()
            model = request.model or self.default_model
            temperature = request.temperature if request.temperature is not None else 0.7

            # Build prompt with system context if provided
            full_prompt = request.prompt
            if request.system_prompt:
                full_prompt = f"{request.system_prompt}\n\n{request.prompt}"

            # Call Ollama API
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": full_prompt,
                    "stream": False,
                    "temperature": temperature,
                },
            )

            if response.status_code != 200:
                logger.error(f"Ollama API error: {response.status_code} {response.text}")
                raise RuntimeError(f"Ollama API returned {response.status_code}")

            result = response.json()
            content = result.get("response", "")

            processing_time = (time.time() - start_time) * 1000

            return LLMResponse(
                content=content,
                model=model,
                tokens_used=0,  # Ollama doesn't return token counts
                input_tokens=0,
                output_tokens=0,
                finish_reason="stop",
                processing_time_ms=processing_time,
                provider=self.provider_name,
            )

        except httpx.RequestError as e:
            logger.error(f"Ollama connection error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error generating Ollama response: {e}")
            raise

    async def generate_streaming_response(
        self, request: LLMRequest
    ) -> AsyncIterator[str]:
        """
        Generate a streaming response from Ollama

        Args:
            request: LLMRequest with prompt and configuration

        Yields:
            Chunks of the generated response
        """
        try:
            model = request.model or self.default_model
            temperature = request.temperature if request.temperature is not None else 0.7

            # Build prompt with system context if provided
            full_prompt = request.prompt
            if request.system_prompt:
                full_prompt = f"{request.system_prompt}\n\n{request.prompt}"

            # Stream from Ollama
            async with self.client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": full_prompt,
                    "stream": True,
                    "temperature": temperature,
                },
            ) as response:
                if response.status_code != 200:
                    logger.error(f"Ollama streaming API error: {response.status_code}")
                    raise RuntimeError(f"Ollama API returned {response.status_code}")

                async for line in response.aiter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            if "response" in chunk:
                                yield chunk["response"]
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to decode Ollama response line: {line}")
                            continue

        except httpx.RequestError as e:
            logger.error(f"Ollama streaming connection error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in Ollama streaming response: {e}")
            raise

    async def health_check(self) -> bool:
        """
        Check if Ollama is running and accessible

        Returns:
            True if Ollama is accessible, False otherwise
        """
        try:
            response = await self.client.get(f"{self.base_url}/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False

    async def list_models(self) -> list[str]:
        """
        List available models in Ollama

        Returns:
            List of available model names
        """
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            if response.status_code != 200:
                logger.error(f"Failed to list Ollama models: {response.status_code}")
                return []

            data = response.json()
            models = data.get("models", [])
            return [model.get("name", "") for model in models if model.get("name")]
        except Exception as e:
            logger.error(f"Error listing Ollama models: {e}")
            return []

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
