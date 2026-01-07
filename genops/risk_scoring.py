"""
Pillar 2: Probabilistic Planning with Guardrails

This module implements risk scoring that maps AI confidence to business
decision thresholds, ensuring AI decisions stay within acceptable bounds.

Key capabilities:
- Multi-factor risk scoring
- Service-tier aware thresholds
- Automated decision boundaries
- Escalation rules for high-risk changes
"""

from typing import Dict, Any, Tuple
from dataclasses import dataclass

from .models import (
    Service, DeploymentContext, RiskAssessment, RiskLevel,
    ServiceTier, AutonomyLevel
)


@dataclass
class RiskWeights:
    """Configurable weights for risk factors."""
    service_tier: float = 0.25
    service_health: float = 0.15
    historical_failure_rate: float = 0.20
    blast_radius: float = 0.15
    change_complexity: float = 0.15
    timing_risk: float = 0.10

    def total(self) -> float:
        return (self.service_tier + self.service_health +
                self.historical_failure_rate + self.blast_radius +
                self.change_complexity + self.timing_risk)


class RiskScorer:
    """
    Pillar 2: Probabilistic Planning with Guardrails

    Calculates risk scores based on multiple factors and maps them to
    autonomy levels and human gate requirements.

    Paper Reference:
    - Risk score = weighted combination of 5 factors
    - Thresholds map to autonomy levels
    - Error budgets constrain AI decisions
    """

    # Risk thresholds for each autonomy level
    RISK_THRESHOLDS = {
        AutonomyLevel.SHADOW: (0.0, 1.0),      # All deployments
        AutonomyLevel.ASSISTED: (0.0, 0.3),    # Low risk only
        AutonomyLevel.GOVERNED: (0.0, 0.6),    # Low-medium risk
        AutonomyLevel.LEARNING: (0.0, 0.8),    # Up to high-medium
    }

    # Decision thresholds
    AUTO_APPROVE_THRESHOLD = 0.3
    ENHANCED_MONITORING_THRESHOLD = 0.5
    HUMAN_REVIEW_THRESHOLD = 0.7
    BLOCK_THRESHOLD = 0.9

    def __init__(
        self,
        weights: RiskWeights = None,
        autonomy_level: AutonomyLevel = AutonomyLevel.GOVERNED
    ):
        self.weights = weights or RiskWeights()
        self.autonomy_level = autonomy_level

        # Normalize weights to sum to 1.0
        total = self.weights.total()
        if total != 1.0:
            self.weights.service_tier /= total
            self.weights.service_health /= total
            self.weights.historical_failure_rate /= total
            self.weights.blast_radius /= total
            self.weights.change_complexity /= total
            self.weights.timing_risk /= total

    def _calculate_tier_risk(self, service: Service) -> float:
        """Calculate risk based on service tier criticality."""
        tier_risks = {
            ServiceTier.CRITICAL: 0.9,
            ServiceTier.HIGH: 0.7,
            ServiceTier.MEDIUM: 0.4,
            ServiceTier.LOW: 0.2,
        }
        return tier_risks.get(service.tier, 0.5)

    def _calculate_health_risk(self, service: Service) -> float:
        """Calculate risk based on service health (inverse of health score)."""
        return 1.0 - service.health_score()

    def _calculate_historical_risk(self, context: DeploymentContext) -> float:
        """Calculate risk based on historical deployment patterns."""
        total = context.similar_past_successes + context.similar_past_failures
        if total == 0:
            return 0.5  # Unknown = medium risk

        failure_rate = context.similar_past_failures / total
        return min(failure_rate * 1.5, 1.0)  # Amplify failure signal

    def _calculate_blast_radius(
        self,
        service: Service,
        context: DeploymentContext
    ) -> float:
        """Calculate potential impact radius of a failed deployment."""
        risk = 0.0

        # More dependencies = higher blast radius
        num_deps = len(service.dependencies)
        if num_deps > 10:
            risk += 0.4
        elif num_deps > 5:
            risk += 0.2
        elif num_deps > 0:
            risk += 0.1

        # DB migrations affect data integrity
        if context.has_db_migration:
            risk += 0.3

        # Config changes can cascade
        if context.has_config_change:
            risk += 0.2

        return min(risk, 1.0)

    def _calculate_complexity_risk(self, context: DeploymentContext) -> float:
        """Calculate risk based on change complexity."""
        risk = 0.0

        # Change size
        if context.change_size_lines > 1000:
            risk += 0.4
        elif context.change_size_lines > 500:
            risk += 0.25
        elif context.change_size_lines > 200:
            risk += 0.1

        # Files changed
        if context.files_changed > 50:
            risk += 0.3
        elif context.files_changed > 20:
            risk += 0.15

        # Hotfixes are rushed, higher risk
        if context.is_hotfix:
            risk += 0.2

        return min(risk, 1.0)

    def _calculate_timing_risk(self, context: DeploymentContext) -> float:
        """Calculate risk based on deployment timing."""
        risk = 0.0

        # Off-hours deployments
        if context.time_of_day_hour >= 22 or context.time_of_day_hour <= 6:
            risk += 0.4

        # Friday/weekend deployments
        if context.day_of_week == 4:  # Friday
            risk += 0.3
        elif context.day_of_week >= 5:  # Weekend
            risk += 0.5

        return min(risk, 1.0)

    def calculate_risk_score(
        self,
        service: Service,
        context: DeploymentContext,
        deployment_id: str
    ) -> RiskAssessment:
        """
        Calculate comprehensive risk score for a deployment.

        Returns RiskAssessment with score, level, and detailed factors.
        """
        # Calculate individual factor scores
        factors = {
            "service_tier": self._calculate_tier_risk(service),
            "service_health": self._calculate_health_risk(service),
            "historical_failure": self._calculate_historical_risk(context),
            "blast_radius": self._calculate_blast_radius(service, context),
            "change_complexity": self._calculate_complexity_risk(context),
            "timing": self._calculate_timing_risk(context),
        }

        # Calculate weighted risk score
        risk_score = (
            factors["service_tier"] * self.weights.service_tier +
            factors["service_health"] * self.weights.service_health +
            factors["historical_failure"] * self.weights.historical_failure_rate +
            factors["blast_radius"] * self.weights.blast_radius +
            factors["change_complexity"] * self.weights.change_complexity +
            factors["timing"] * self.weights.timing_risk
        )

        # Determine risk level
        if risk_score >= self.BLOCK_THRESHOLD:
            risk_level = RiskLevel.CRITICAL
        elif risk_score >= self.HUMAN_REVIEW_THRESHOLD:
            risk_level = RiskLevel.HIGH
        elif risk_score >= self.ENHANCED_MONITORING_THRESHOLD:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        # Determine if human review required
        requires_human = risk_score >= self.HUMAN_REVIEW_THRESHOLD

        # Check autonomy level constraints
        min_risk, max_risk = self.RISK_THRESHOLDS[self.autonomy_level]
        if risk_score > max_risk:
            requires_human = True

        # Calculate confidence based on RAG context quality
        confidence = context.rag_confidence

        # Generate recommendation
        recommendation = self._generate_recommendation(
            risk_score, risk_level, factors, requires_human
        )

        return RiskAssessment(
            deployment_id=deployment_id,
            risk_score=risk_score,
            risk_level=risk_level,
            confidence=confidence,
            factors=factors,
            recommendation=recommendation,
            requires_human_review=requires_human
        )

    def _generate_recommendation(
        self,
        risk_score: float,
        risk_level: RiskLevel,
        factors: Dict[str, float],
        requires_human: bool
    ) -> str:
        """Generate actionable recommendation."""
        # Find top risk factors
        sorted_factors = sorted(factors.items(), key=lambda x: -x[1])
        top_risks = [f for f, score in sorted_factors[:2] if score > 0.5]

        if risk_level == RiskLevel.CRITICAL:
            return f"BLOCK: Risk score {risk_score:.2f} exceeds threshold. Top factors: {', '.join(top_risks) or 'multiple'}. Manual approval required."

        if risk_level == RiskLevel.HIGH:
            return f"ESCALATE: Risk score {risk_score:.2f}. Requires human review before proceeding. Top factors: {', '.join(top_risks) or 'cumulative'}."

        if risk_level == RiskLevel.MEDIUM:
            return f"PROCEED WITH CAUTION: Risk score {risk_score:.2f}. Enhanced monitoring recommended during canary."

        return f"AUTO-APPROVE: Risk score {risk_score:.2f}. Proceeding with standard canary rollout."

    def check_error_budget(self, service: Service) -> Tuple[bool, str]:
        """
        Check if deployment should be allowed based on error budget.

        Returns (allowed, reason)
        """
        if service.error_budget_remaining <= 0:
            return False, f"ERROR_BUDGET_EXHAUSTED: Service {service.name} has no remaining error budget"

        if service.error_budget_remaining < 0.1:
            return True, f"WARNING: Low error budget ({service.error_budget_remaining:.1%}). Consider delaying non-critical changes."

        return True, "OK: Sufficient error budget available"

    def get_autonomy_decision(
        self,
        risk_assessment: RiskAssessment,
        service: Service
    ) -> Dict[str, Any]:
        """
        Make autonomous decision based on risk assessment and autonomy level.
        """
        decision = {
            "allowed": True,
            "autonomy_level": self.autonomy_level.value,
            "action": "proceed",
            "canary_stages": ["1%", "5%", "25%", "50%", "100%"],
            "monitoring_level": "standard",
            "human_gate_required": False,
            "reason": ""
        }

        # Check error budget first
        budget_ok, budget_reason = self.check_error_budget(service)
        if not budget_ok:
            decision["allowed"] = False
            decision["action"] = "block"
            decision["reason"] = budget_reason
            return decision

        # Apply autonomy level constraints
        if risk_assessment.requires_human_review:
            decision["human_gate_required"] = True
            decision["action"] = "await_approval"
            decision["reason"] = "Risk exceeds autonomous decision threshold"

        # Adjust canary stages based on risk
        if risk_assessment.risk_level == RiskLevel.HIGH:
            decision["canary_stages"] = ["1%", "2%", "5%", "10%", "25%", "50%", "100%"]
            decision["monitoring_level"] = "intensive"
        elif risk_assessment.risk_level == RiskLevel.MEDIUM:
            decision["canary_stages"] = ["1%", "5%", "15%", "30%", "50%", "100%"]
            decision["monitoring_level"] = "enhanced"

        return decision
