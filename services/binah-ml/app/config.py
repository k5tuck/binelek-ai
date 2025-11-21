"""Configuration settings for Binah ML service"""

from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8102
    environment: Literal["development", "staging", "production"] = "development"

    # MLFlow
    mlflow_tracking_uri: str = "http://localhost:5000"
    mlflow_experiment_name: str = "binelek-ml"
    mlflow_artifact_root: str = "./mlruns"

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = ""

    # PostgreSQL - Dedicated binah_ml database
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "binah_ml"
    postgres_user: str = "binah"
    postgres_password: str = ""

    # JWT Authentication
    jwt_secret: str = "your-super-secret-key-change-this-in-production-at-least-32-characters-long"
    jwt_issuer: str = "Binah.Auth"
    jwt_audience: str = "Binah.Platform"
    jwt_algorithm: str = "HS256"

    # Training
    auto_retrain: bool = False
    retrain_schedule: str = "0 2 * * *"  # Cron expression

    # Model Registry
    model_registry_path: str = "./models"

    # Tenant Isolation
    enable_tenant_isolation: bool = True

    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
