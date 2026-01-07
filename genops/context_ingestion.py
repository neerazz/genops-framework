"""
Pillar 1: Context-Aware Ingestion

This module implements RAG (Retrieval-Augmented Generation) over operational
history to ground AI decisions in organization-specific context.

Key capabilities:
- Retrieves similar past deployments
- Analyzes historical success/failure patterns
- Provides context for risk assessment
"""

import random
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

from .models import Service, DeploymentContext, ServiceTier


@dataclass
class HistoricalDeployment:
    """A past deployment record for RAG retrieval."""
    deployment_id: str
    service_id: str
    timestamp: datetime
    success: bool
    change_size_lines: int
    had_db_migration: bool
    had_config_change: bool
    failure_reason: Optional[str] = None
    rollback_stage: Optional[str] = None  # Which canary stage caused rollback


class ContextIngestion:
    """
    Pillar 1: Context-Aware Ingestion

    Simulates RAG over build history and deployment metadata to provide
    AI with organization-specific operational context.

    Paper Reference:
    - Embeddings: text-embedding-3-large (1536 dims)
    - Vector store: Pinecone
    - Retrieval: top-k=10, cosine similarity threshold >0.75
    - LLM: GPT-4o (128K context)
    """

    def __init__(self, similarity_threshold: float = 0.75, top_k: int = 10):
        self.similarity_threshold = similarity_threshold
        self.top_k = top_k
        self.deployment_history: List[HistoricalDeployment] = []
        self.runbook_knowledge: Dict[str, str] = {}
        self.incident_history: List[Dict[str, Any]] = []

        # Generate synthetic historical data
        self._generate_historical_data()

    def _generate_historical_data(self, num_records: int = 5000):
        """Generate realistic historical deployment data."""
        services = [
            "auth-service", "payment-gateway", "user-api", "notification-svc",
            "search-engine", "inventory-mgmt", "order-processor", "analytics",
            "cdn-proxy", "config-service", "logging-agent", "metrics-collector"
        ]

        base_time = datetime.now() - timedelta(days=240)  # 8 months of history

        for i in range(num_records):
            service = random.choice(services)
            timestamp = base_time + timedelta(
                days=random.randint(0, 240),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )

            # Simulate realistic success patterns
            change_size = random.randint(5, 2000)
            has_migration = random.random() < 0.15
            has_config = random.random() < 0.25

            # Higher risk factors reduce success probability
            base_success_rate = 0.94  # Baseline from paper
            if has_migration:
                base_success_rate -= 0.08
            if has_config:
                base_success_rate -= 0.03
            if change_size > 500:
                base_success_rate -= 0.05
            if change_size > 1000:
                base_success_rate -= 0.05

            success = random.random() < base_success_rate

            failure_reason = None
            rollback_stage = None
            if not success:
                failure_reason = random.choice([
                    "latency_spike",
                    "error_rate_exceeded",
                    "memory_exhaustion",
                    "dependency_timeout",
                    "config_mismatch",
                    "db_connection_pool_exhausted"
                ])
                rollback_stage = random.choice([
                    "canary_1%", "canary_5%", "canary_25%", "canary_50%", "production"
                ])

            self.deployment_history.append(HistoricalDeployment(
                deployment_id=f"dep-{i:06d}",
                service_id=service,
                timestamp=timestamp,
                success=success,
                change_size_lines=change_size,
                had_db_migration=has_migration,
                had_config_change=has_config,
                failure_reason=failure_reason,
                rollback_stage=rollback_stage
            ))

    def retrieve_similar_deployments(
        self,
        service: Service,
        context: DeploymentContext
    ) -> Tuple[List[HistoricalDeployment], float]:
        """
        Retrieve similar past deployments using simulated vector similarity.

        Returns:
            Tuple of (similar deployments, confidence score)
        """
        relevant = []

        for hist in self.deployment_history:
            # Simulate similarity scoring based on matching characteristics
            similarity = 0.0

            # Service match is most important
            if hist.service_id == service.name:
                similarity += 0.4

            # Similar change characteristics
            size_diff = abs(hist.change_size_lines - context.change_size_lines)
            if size_diff < 100:
                similarity += 0.2
            elif size_diff < 500:
                similarity += 0.1

            # Same risk factors
            if hist.had_db_migration == context.has_db_migration:
                similarity += 0.15
            if hist.had_config_change == context.has_config_change:
                similarity += 0.15

            # Recent is more relevant (recency bias)
            days_ago = (datetime.now() - hist.timestamp).days
            if days_ago < 30:
                similarity += 0.1

            if similarity >= self.similarity_threshold:
                relevant.append((hist, similarity))

        # Sort by similarity and take top-k
        relevant.sort(key=lambda x: x[1], reverse=True)
        top_matches = [r[0] for r in relevant[:self.top_k]]

        # Calculate confidence based on match quality
        if not relevant:
            confidence = 0.3  # Low confidence when no matches
        else:
            avg_similarity = sum(r[1] for r in relevant[:self.top_k]) / min(len(relevant), self.top_k)
            confidence = min(avg_similarity + 0.2, 0.98)  # Cap at 98%

        return top_matches, confidence

    def analyze_historical_patterns(
        self,
        similar_deployments: List[HistoricalDeployment]
    ) -> Dict[str, Any]:
        """
        Analyze patterns in similar historical deployments.

        Returns insights for risk assessment.
        """
        if not similar_deployments:
            return {
                "success_rate": 0.5,  # Uncertain
                "common_failure_reasons": [],
                "risky_patterns": [],
                "safe_patterns": [],
                "sample_size": 0
            }

        successes = sum(1 for d in similar_deployments if d.success)
        failures = len(similar_deployments) - successes

        # Analyze failure patterns
        failure_reasons = {}
        rollback_stages = {}

        for dep in similar_deployments:
            if dep.failure_reason:
                failure_reasons[dep.failure_reason] = failure_reasons.get(dep.failure_reason, 0) + 1
            if dep.rollback_stage:
                rollback_stages[dep.rollback_stage] = rollback_stages.get(dep.rollback_stage, 0) + 1

        # Identify risky patterns
        risky_patterns = []
        safe_patterns = []

        migrations_success = sum(1 for d in similar_deployments if d.had_db_migration and d.success)
        migrations_total = sum(1 for d in similar_deployments if d.had_db_migration)
        if migrations_total > 0:
            migration_rate = migrations_success / migrations_total
            if migration_rate < 0.85:
                risky_patterns.append(f"DB migrations: {migration_rate:.0%} success rate")
            else:
                safe_patterns.append(f"DB migrations: {migration_rate:.0%} success rate")

        large_changes_success = sum(1 for d in similar_deployments if d.change_size_lines > 500 and d.success)
        large_changes_total = sum(1 for d in similar_deployments if d.change_size_lines > 500)
        if large_changes_total > 0:
            large_rate = large_changes_success / large_changes_total
            if large_rate < 0.90:
                risky_patterns.append(f"Large changes (>500 lines): {large_rate:.0%} success rate")

        return {
            "success_rate": successes / len(similar_deployments),
            "common_failure_reasons": sorted(failure_reasons.items(), key=lambda x: -x[1])[:3],
            "rollback_stage_distribution": rollback_stages,
            "risky_patterns": risky_patterns,
            "safe_patterns": safe_patterns,
            "sample_size": len(similar_deployments)
        }

    def gather_context(self, service: Service, context: DeploymentContext) -> Dict[str, Any]:
        """
        Main entry point: Gather all context for a deployment.

        This simulates RAG over:
        - Build history
        - Deployment logs
        - Infrastructure metadata
        - Incident history
        """
        # Retrieve similar deployments
        similar, confidence = self.retrieve_similar_deployments(service, context)

        # Analyze patterns
        patterns = self.analyze_historical_patterns(similar)

        # Update context with findings
        context.similar_past_failures = sum(1 for d in similar if not d.success)
        context.similar_past_successes = sum(1 for d in similar if d.success)
        context.rag_confidence = confidence

        return {
            "similar_deployments_count": len(similar),
            "historical_success_rate": patterns["success_rate"],
            "common_failure_reasons": patterns["common_failure_reasons"],
            "risky_patterns": patterns["risky_patterns"],
            "safe_patterns": patterns["safe_patterns"],
            "rag_confidence": confidence,
            "recommendation": self._generate_recommendation(patterns, context)
        }

    def _generate_recommendation(
        self,
        patterns: Dict[str, Any],
        context: DeploymentContext
    ) -> str:
        """Generate AI recommendation based on context."""
        warnings = []

        if patterns["success_rate"] < 0.85:
            warnings.append("historical success rate below 85%")

        if context.has_db_migration and patterns["risky_patterns"]:
            warnings.append("DB migration detected with risky patterns")

        if context.time_of_day_hour >= 22 or context.time_of_day_hour <= 5:
            warnings.append("deployment during off-hours")

        if context.day_of_week >= 4:  # Friday-Sunday
            warnings.append("deployment on weekend/end-of-week")

        if not warnings:
            return "PROCEED: Historical patterns indicate low risk"
        elif len(warnings) == 1:
            return f"CAUTION: {warnings[0]}"
        else:
            return f"HIGH ATTENTION: Multiple risk factors - {', '.join(warnings)}"
