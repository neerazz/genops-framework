"""
GenOps: A Governance-First Architecture for AI in CI/CD Pipelines

This framework demonstrates the four pillars of GenOps:
1. Context-Aware Ingestion (RAG)
2. Probabilistic Planning with Guardrails
3. Staged Canary Rollouts
4. Runtime Governance

Author: Neeraj Kumar Singh Beshane
Conference: Conf42 DevOps 2026
"""

__version__ = "1.0.0"
__author__ = "Neeraj Kumar Singh Beshane"

from .context_ingestion import ContextIngestion
from .risk_scoring import RiskScorer
from .canary_rollout import CanaryRollout
from .governance import GovernanceEngine
from .pipeline import GenOpsPipeline
from .simulator import DeploymentSimulator, run_study_simulation

__all__ = [
    "ContextIngestion",
    "RiskScorer",
    "CanaryRollout",
    "GovernanceEngine",
    "GenOpsPipeline",
    "DeploymentSimulator",
    "run_study_simulation",
]
