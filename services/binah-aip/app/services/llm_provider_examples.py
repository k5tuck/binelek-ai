"""
LLM Provider Usage Examples

This module demonstrates how to use the LLM provider abstraction
with different providers (OpenAI, Anthropic, Ollama)
"""

import asyncio
import logging
from app.services.llm_provider_factory import LLMProviderFactory
from app.services.llm_service import LLMService
from app.services.llm_provider import LLMRequest

logger = logging.getLogger(__name__)


async def example_openai():
    """Example: Using OpenAI provider"""
    print("\n=== OpenAI Provider Example ===")

    try:
        # Method 1: Create provider directly
        provider = LLMProviderFactory.create_provider(
            provider="openai",
            api_key="your-api-key-here",  # Can also use settings
            default_model="gpt-4-turbo-preview"
        )

        # Check health
        is_healthy = await provider.health_check()
        print(f"OpenAI health: {is_healthy}")

        # List available models
        models = await provider.list_models()
        print(f"Available models: {models[:3]}...")  # Show first 3

        # Generate response
        request = LLMRequest(
            prompt="Explain quantum computing in simple terms",
            system_prompt="You are a helpful assistant explaining complex topics simply",
            temperature=0.7,
            max_tokens=200
        )

        response = await provider.generate_response(request)
        print(f"Response: {response.content[:100]}...")
        print(f"Tokens used: {response.tokens_used}")

    except Exception as e:
        print(f"Error: {e}")


async def example_anthropic():
    """Example: Using Anthropic provider"""
    print("\n=== Anthropic Provider Example ===")

    try:
        # Using LLMService wrapper
        llm_service = LLMService()

        # Generate response
        response = await llm_service.generate(
            prompt="What are the key considerations for real estate investment?",
            system_prompt="You are an expert real estate consultant",
            temperature=0.5,
            max_tokens=300
        )

        print(f"Response: {response.content[:150]}...")
        print(f"Provider: {response.provider}")
        print(f"Processing time: {response.processing_time_ms}ms")

    except Exception as e:
        print(f"Error: {e}")


async def example_streaming():
    """Example: Streaming response"""
    print("\n=== Streaming Response Example ===")

    try:
        provider = LLMProviderFactory.get_provider("anthropic")

        request = LLMRequest(
            prompt="List 5 tips for successful property management",
            system_prompt="You are a property management expert",
            max_tokens=300
        )

        print("Streaming response:")
        async for chunk in provider.generate_streaming_response(request):
            print(chunk, end="", flush=True)
        print()  # New line

    except Exception as e:
        print(f"Error: {e}")


async def example_ollama():
    """Example: Using local Ollama provider"""
    print("\n=== Ollama Provider Example ===")

    try:
        provider = LLMProviderFactory.create_provider(
            provider="ollama",
            base_url="http://localhost:11434",
            default_model="llama2"
        )

        # Check health
        is_healthy = await provider.health_check()
        print(f"Ollama health: {is_healthy}")

        if not is_healthy:
            print("Ollama is not running. Start it with: ollama serve")
            return

        # List models
        models = await provider.list_models()
        print(f"Available models: {models}")

        # Generate response
        response = await provider.generate_response(
            LLMRequest(
                prompt="What is machine learning?",
                temperature=0.7,
                max_tokens=150
            )
        )

        print(f"Response: {response.content}")

    except Exception as e:
        print(f"Error: {e}")


async def example_provider_switching():
    """Example: Switching between providers"""
    print("\n=== Provider Switching Example ===")

    try:
        llm_service = LLMService()
        prompt = "Summarize the benefits of cloud computing"

        # Use default provider
        print(f"Using provider: {llm_service.provider.provider_name}")
        response1 = await llm_service.generate(prompt, max_tokens=100)
        print(f"Response length: {len(response1.content)} chars")

        # Switch to different provider
        try:
            llm_service.switch_provider("openai")
            print(f"Switched to: {llm_service.provider.provider_name}")
            # Note: This will fail if OpenAI API key is not configured
        except ValueError as e:
            print(f"Cannot switch: {e}")

    except Exception as e:
        print(f"Error: {e}")


async def example_multi_tenant():
    """Example: Multi-tenant tracking"""
    print("\n=== Multi-Tenant Example ===")

    try:
        provider = LLMProviderFactory.get_provider()

        request = LLMRequest(
            prompt="Analyze this property for investment potential",
            tenant_id="tenant_abc123",
            user_id="user_xyz789",
            system_prompt="Provide professional real estate analysis",
            metadata={
                "property_type": "residential",
                "location": "Austin, TX",
                "purpose": "investment_analysis"
            }
        )

        response = await provider.generate_response(request)
        print(f"Generated for tenant: {request.tenant_id}")
        print(f"User: {request.user_id}")
        print(f"Response: {response.content[:150]}...")

    except Exception as e:
        print(f"Error: {e}")


async def main():
    """Run all examples"""
    print("LLM Provider Examples")
    print("=" * 50)

    # Note: These examples are for demonstration.
    # Most will fail without proper API keys or running services.

    # Uncomment to run specific examples:

    # await example_openai()
    # await example_anthropic()
    # await example_streaming()
    # await example_ollama()
    # await example_provider_switching()
    # await example_multi_tenant()

    print("\nExamples are available but require proper configuration.")
    print("See docstrings for usage details.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
