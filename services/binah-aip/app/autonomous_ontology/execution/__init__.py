"""
Automated Execution Engine (Phase 5)

This module implements automated execution of approved ontology changes
with zero-downtime deployment.
"""

from .yaml_editor import YAMLEditor
from .migration_generator import MigrationGenerator
from .deployment_orchestrator import DeploymentOrchestrator

__all__ = ["YAMLEditor", "MigrationGenerator", "DeploymentOrchestrator"]
