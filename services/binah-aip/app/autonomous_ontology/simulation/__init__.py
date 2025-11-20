"""
Impact Simulation System (Phase 3)

This module implements the impact simulation and testing environment for
proposed ontology changes before they are deployed to production.
"""

from .sandbox_manager import SandboxManager
from .query_replay_engine import QueryReplayEngine
from .impact_analyzer import ImpactAnalyzer

__all__ = ["SandboxManager", "QueryReplayEngine", "ImpactAnalyzer"]
