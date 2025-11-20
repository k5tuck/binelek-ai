# LLM Provider Abstraction

## Overview

The LLM Provider abstraction provides a unified interface for working with multiple Large Language Model (LLM) providers:

- **OpenAI** - GPT-4, GPT-3.5, etc.
- **Anthropic** - Claude 3 (Opus, Sonnet, Haiku), Claude 2, etc.
- **Ollama** - Local LLM models (Llama 2, Mistral, etc.)

This abstraction allows you to:
1. Switch between providers without changing application code
2. Support multiple providers simultaneously
3. Implement provider-agnostic business logic
4. Handle provider-specific features through a common interface

## Architecture

### Components

```
ILLMProvider (Interface)
  ├── OpenAIProvider
  ├── AnthropicProvider
  └── OllamaProvider

LLMProviderFactory
  └── Creates provider instances

LLMService
  └── High-level interface for common operations

LLMRequest / LLMResponse
  └── Standardized data models
```

### File Structure

```
app/services/
├── llm_provider.py              # Interface + data models
├── llm_provider_factory.py      # Factory pattern
├── llm_service.py               # High-level service
├── llm_provider_examples.py     # Usage examples
└── providers/
    ├── __init__.py
    ├── openai_provider.py       # OpenAI implementation
    ├── anthropic_provider.py    # Anthropic implementation
    └── ollama_provider.py       # Ollama implementation
```

## Quick Start

### 1. Configuration

Set environment variables in `.env`:

```bash
# Select active provider
LLM_PROVIDER=anthropic

# OpenAI Configuration
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-turbo-preview

# Anthropic Configuration
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-sonnet-20240229

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
```

### 2. Basic Usage

```python
from app.services.llm_service import LLMService

# Create service (uses configured provider)
llm_service = LLMService()

# Generate response
response = await llm_service.generate(
    prompt="What is real estate valuation?",
    system_prompt="You are a real estate expert",
    max_tokens=500
)

print(response.content)
```

### 3. Streaming Response

```python
async for chunk in llm_service.generate_stream(
    prompt="Explain property investment strategies",
    max_tokens=1000
):
    print(chunk, end="", flush=True)
```

### 4. Switch Providers at Runtime

```python
# Switch to OpenAI
llm_service.switch_provider("openai")

# Generate with OpenAI
response = await llm_service.generate("Your prompt here")

# Switch back to Anthropic
llm_service.switch_provider("anthropic")
```

## Detailed Usage

### Using ILLMProvider Interface

```python
from app.services.llm_provider_factory import LLMProviderFactory
from app.services.llm_provider import LLMRequest

# Create provider
provider = LLMProviderFactory.get_provider("anthropic")

# Check health
is_healthy = await provider.health_check()

# List models
models = await provider.list_models()

# Generate response
request = LLMRequest(
    prompt="Your question here",
    system_prompt="System instructions",
    temperature=0.7,
    max_tokens=1000,
    tenant_id="tenant_abc",
    user_id="user_xyz"
)

response = await provider.generate_response(request)
```

### Creating Custom Provider

To add support for another LLM service:

```python
from app.services.llm_provider import ILLMProvider, LLMRequest, LLMResponse
from typing import AsyncIterator

class CustomProvider(ILLMProvider):
    def __init__(self, api_key: str, default_model: str = "model-name"):
        self.api_key = api_key
        self.default_model = default_model
        self.provider_name = "custom"

    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        # Implementation here
        pass

    async def generate_streaming_response(
        self, request: LLMRequest
    ) -> AsyncIterator[str]:
        # Streaming implementation
        pass

    async def health_check(self) -> bool:
        # Health check logic
        pass

    async def list_models(self) -> list[str]:
        # Return available models
        pass
```

## Provider-Specific Details

### OpenAI Provider

**Supported Models:**
- gpt-4-turbo-preview
- gpt-4-vision-preview
- gpt-3.5-turbo
- gpt-3.5-turbo-16k

**Features:**
- Full streaming support
- Token counting via API
- Vision capabilities (images)
- Function calling

**Configuration:**
```python
provider = LLMProviderFactory.create_provider(
    provider="openai",
    api_key="sk-...",
    default_model="gpt-4-turbo-preview"
)
```

### Anthropic Provider

**Supported Models:**
- claude-3-opus-20240229
- claude-3-sonnet-20240229
- claude-3-haiku-20240307
- claude-2.1
- claude-instant-1.2

**Features:**
- Streaming via context manager
- Stop sequences
- System prompts
- Extended thinking (Claude 3)

**Configuration:**
```python
provider = LLMProviderFactory.create_provider(
    provider="anthropic",
    api_key="sk-ant-...",
    default_model="claude-3-sonnet-20240229"
)
```

### Ollama Provider

**Supported Models:**
- llama2
- mistral
- neural-chat
- starling-lm
- And any model available in your Ollama installation

**Features:**
- Local execution (no API costs)
- Streaming support
- Custom models
- Fast response times

**Configuration:**
```python
# Start Ollama first:
# ollama serve

provider = LLMProviderFactory.create_provider(
    provider="ollama",
    base_url="http://localhost:11434",
    default_model="llama2"
)

# Pull a model before using:
# ollama pull llama2
# ollama pull mistral
```

## Request/Response Models

### LLMRequest

```python
class LLMRequest(BaseModel):
    prompt: str                              # Required: The input prompt
    model: Optional[str] = None              # Override default model
    temperature: Optional[float] = None      # 0.0-2.0, default 0.7
    max_tokens: Optional[int] = None         # Max response length
    system_prompt: Optional[str] = None      # System context
    tenant_id: Optional[str] = None          # For multi-tenancy
    user_id: Optional[str] = None            # User tracking
    metadata: dict[str, Any] = {}            # Additional data
```

### LLMResponse

```python
class LLMResponse(BaseModel):
    content: str                             # The generated response
    model: str                               # Model used
    tokens_used: int                         # Total tokens
    input_tokens: int                        # Input token count
    output_tokens: int                       # Output token count
    finish_reason: str                       # Why completion stopped
    processing_time_ms: float                # Execution time
    timestamp: datetime                      # When generated
    provider: str                            # Which provider
    request_id: Optional[str]                # For tracking
```

## Multi-Tenancy

The provider supports tenant isolation:

```python
request = LLMRequest(
    prompt="Your prompt",
    tenant_id="tenant_abc123",
    user_id="user_xyz789",
    metadata={
        "domain": "real_estate",
        "operation": "property_analysis"
    }
)

response = await provider.generate_response(request)
# Response.content is isolated to the tenant
```

## Error Handling

```python
from anthropic import APIError

try:
    response = await llm_service.generate("Your prompt")
except APIError as e:
    print(f"API Error: {e}")
except ValueError as e:
    print(f"Configuration Error: {e}")
except Exception as e:
    print(f"Unexpected Error: {e}")
```

## Performance Tips

### Token Management
- Estimate tokens before requests: `len(prompt.split()) * 1.3`
- Use smaller models for high-volume scenarios
- Cache responses for repeated queries

### Streaming for Long Responses
```python
# Good for long outputs
async for chunk in llm_service.generate_stream(
    prompt="Write a detailed analysis...",
    max_tokens=4000
):
    # Process chunk immediately
    pass
```

### Health Checks
```python
# Verify provider availability before use
is_healthy = await llm_service.health_check()
if not is_healthy:
    print("Provider unavailable, falling back...")
```

## Testing

```python
import pytest

@pytest.mark.asyncio
async def test_openai_provider():
    provider = LLMProviderFactory.create_provider("openai")
    request = LLMRequest(prompt="Test prompt", max_tokens=10)
    response = await provider.generate_response(request)
    assert response.content
    assert response.provider == "openai"

@pytest.mark.asyncio
async def test_provider_switching():
    service = LLMService()
    original = service.provider.provider_name

    service.switch_provider("anthropic")
    assert service.provider.provider_name == "anthropic"

    service.switch_provider(original)
```

## Troubleshooting

### No Module Named 'openai'
```bash
pip install openai
```

### API Key Not Found
```bash
# Set in .env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### Ollama Connection Refused
```bash
# Start Ollama server
ollama serve

# In another terminal, pull a model
ollama pull llama2
```

### Rate Limiting
- Implement backoff: Use Tenacity library
- Queue requests: Use async queues
- Cache results: Redis or in-memory cache

## Integration with Agents

```python
# In your agent class
from app.services.llm_service import LLMService

class PropertyAnalysisAgent:
    def __init__(self):
        self.llm_service = LLMService()

    async def analyze_property(self, property_data):
        response = await self.llm_service.generate(
            prompt=f"Analyze: {property_data}",
            system_prompt="You are a real estate expert",
            max_tokens=1000
        )
        return response.content
```

## Configuration Management

### Environment-Based Selection

```bash
# Development - Use local Ollama
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434

# Production - Use Anthropic
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

### Runtime Provider Factory

```python
# Factory auto-detects from settings
provider = LLMProviderFactory.get_provider()

# Or explicitly specify
provider = LLMProviderFactory.create_provider("anthropic")
```

## Best Practices

1. **Always use LLMService for application code**
   - More convenient than raw provider interface
   - Consistent API across providers

2. **Implement health checks**
   - Before critical operations
   - In startup/readiness checks

3. **Handle streaming for long responses**
   - Better UX for large outputs
   - Reduced latency perception

4. **Log provider selection**
   - Easier debugging
   - Performance monitoring

5. **Test with multiple providers**
   - Different behavior patterns
   - Provider-specific edge cases

6. **Cache results when appropriate**
   - Reduce API costs
   - Improve response times

## Examples

See `llm_provider_examples.py` for:
- Basic usage with each provider
- Streaming responses
- Provider switching
- Multi-tenant tracking
- Error handling

## Related Documentation

- OpenAI API: https://platform.openai.com/docs
- Anthropic API: https://docs.anthropic.com
- Ollama: https://ollama.ai

---

**Last Updated:** 2025-11-15
**Version:** 1.0.0
