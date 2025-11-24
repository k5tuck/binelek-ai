"""
Configuration for binah-llm-extractor service.

This service extracts structured entities from unstructured text using LLMs.
"""

from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Service Configuration
    SERVICE_NAME: str = "binah-llm-extractor"
    SERVICE_VERSION: str = "1.0.0"
    PORT: int = 8110
    LOG_LEVEL: str = "INFO"

    # LLM Configuration
    LLM_PROVIDER: Literal["openai", "anthropic", "ollama"] = "openai"
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "gpt-4"  # or "claude-3-5-sonnet-20241022" or "llama3"
    LLM_TEMPERATURE: float = 0.1  # Lower for consistency

    # Kafka Configuration
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_GROUP_ID: str = "llm-entity-extractor"
    KAFKA_TOPIC_PATTERN: str = "extraction.raw.*"
    KAFKA_AUTO_OFFSET_RESET: str = "earliest"
    KAFKA_ENABLE_AUTO_COMMIT: bool = True

    # Service URLs
    ONTOLOGY_SERVICE_URL: str = "http://binah-ontology:8091"
    DISCOVERY_SERVICE_URL: str = "http://binah-discovery:8106"

    # Confidence Thresholds (aligned with binah-discovery)
    AUTO_APPLY_THRESHOLD: float = 0.90
    MANUAL_REVIEW_THRESHOLD: float = 0.75

    # Processing Configuration
    BATCH_SIZE: int = 10
    MAX_RETRIES: int = 3
    REQUEST_TIMEOUT: int = 30  # seconds

    # Feature Flags
    ENABLE_BATCH_PROCESSING: bool = True
    ENABLE_RELATIONSHIP_EXTRACTION: bool = True
    SEND_TO_REVIEW_QUEUE: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
