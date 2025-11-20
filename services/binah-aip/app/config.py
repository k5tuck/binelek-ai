"""Configuration settings for Binah AIP service"""

from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8096
    environment: Literal["development", "staging", "production"] = "development"

    # LLM Provider Configuration
    llm_provider: Literal["openai", "anthropic", "ollama"] = "anthropic"

    # OpenAI Configuration
    openai_api_key: str | None = None
    openai_model: str = "gpt-4-turbo-preview"

    # Anthropic Configuration
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-3-sonnet-20240229"

    # Ollama Configuration
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama2"

    # Default Model (fallback)
    llm_model: str = "gpt-4-turbo-preview"
    embedding_model: str = "text-embedding-3-small"

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = ""

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "binelek_pipeline"
    postgres_user: str = "postgres"
    postgres_password: str = ""

    # Service URLs
    ontology_service_url: str = "http://localhost:8091"
    pipeline_service_url: str = "http://localhost:8094"
    context_service_url: str = "http://localhost:8095"

    # AI Configuration
    max_reasoning_steps: int = 5
    temperature: float = 0.7
    max_tokens: int = 4000

    # Tenant Isolation
    enable_tenant_isolation: bool = True

    # JWT Authentication
    jwt_secret: str = "your-super-secret-key-change-this-in-production-at-least-32-characters-long"
    jwt_issuer: str = "Binah.Auth"
    jwt_audience: str = "Binah.Platform"
    jwt_algorithm: str = "HS256"

    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
