"""
Unit Tests for GenOps Four Pillars

Tests each pillar independently:
- Pillar 1: Context-Aware Ingestion
- Pillar 2: Risk Scoring
- Pillar 3: Canary Rollout
- Pillar 4: Runtime Governance
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from genops.models import (
    Service, ServiceTier, DeploymentContext, Deployment,
    RiskLevel, AutonomyLevel, DeploymentStatus
)
from genops.context_ingestion import ContextIngestion
from genops.risk_scoring import RiskScorer, RiskWeights
from genops.canary_rollout import CanaryRollout, SLOConfig, CanaryOutcome
from genops.governance import GovernanceEngine, GovernancePolicy


class TestContextIngestion:
    """Tests for Pillar 1: Context-Aware Ingestion"""

    @pytest.fixture
    def context_engine(self):
        return ContextIngestion(similarity_threshold=0.75, top_k=10)

    @pytest.fixture
    def sample_service(self):
        return Service(
            id="svc-auth",
            name="auth-service",
            tier=ServiceTier.CRITICAL,
            dependencies=["db-primary", "cache-redis"],
            deployment_frequency_daily=5.0,
            recent_failure_rate=0.02,
            error_budget_remaining=0.85,
            avg_latency_ms=45.0,
            availability_99d=0.999,
        )

    @pytest.fixture
    def sample_context(self):
        return DeploymentContext(
            change_size_lines=150,
            files_changed=10,
            has_db_migration=False,
            has_config_change=True,
            is_hotfix=False,
            time_of_day_hour=14,
            day_of_week=2,
            similar_past_failures=0,
            similar_past_successes=0,
            rag_confidence=0.0,
        )

    def test_historical_data_generation(self, context_engine):
        """Test that historical data is generated with realistic patterns."""
        assert len(context_engine.deployment_history) == 5000

        # Check success rate is reasonable (around 90%)
        successes = sum(1 for d in context_engine.deployment_history if d.success)
        success_rate = successes / len(context_engine.deployment_history)
        assert 0.80 < success_rate < 0.98

    def test_similar_deployment_retrieval(self, context_engine, sample_service, sample_context):
        """Test RAG-style retrieval of similar deployments."""
        similar, confidence = context_engine.retrieve_similar_deployments(
            sample_service, sample_context
        )

        # Should return up to top_k results
        assert len(similar) <= 10
        assert 0.0 <= confidence <= 1.0

    def test_context_gathering(self, context_engine, sample_service, sample_context):
        """Test full context gathering workflow."""
        context = context_engine.gather_context(sample_service, sample_context)

        assert "similar_deployments_count" in context
        assert "historical_success_rate" in context
        assert "rag_confidence" in context
        assert "recommendation" in context

    def test_pattern_analysis(self, context_engine):
        """Test historical pattern analysis."""
        # Get some deployments
        sample_deps = context_engine.deployment_history[:20]
        patterns = context_engine.analyze_historical_patterns(sample_deps)

        assert "success_rate" in patterns
        assert "common_failure_reasons" in patterns
        assert 0.0 <= patterns["success_rate"] <= 1.0


class TestRiskScoring:
    """Tests for Pillar 2: Probabilistic Planning with Guardrails"""

    @pytest.fixture
    def risk_scorer(self):
        return RiskScorer(autonomy_level=AutonomyLevel.GOVERNED)

    @pytest.fixture
    def critical_service(self):
        return Service(
            id="svc-payment",
            name="payment-gateway",
            tier=ServiceTier.CRITICAL,
            dependencies=["auth-service", "db-primary"],
            deployment_frequency_daily=3.0,
            recent_failure_rate=0.01,
            error_budget_remaining=0.5,
            avg_latency_ms=50.0,
            availability_99d=0.9999,
        )

    @pytest.fixture
    def low_risk_context(self):
        return DeploymentContext(
            change_size_lines=50,
            files_changed=5,
            has_db_migration=False,
            has_config_change=False,
            is_hotfix=False,
            time_of_day_hour=10,
            day_of_week=1,  # Tuesday
            similar_past_failures=1,
            similar_past_successes=10,
            rag_confidence=0.85,
        )

    @pytest.fixture
    def high_risk_context(self):
        return DeploymentContext(
            change_size_lines=1500,
            files_changed=60,
            has_db_migration=True,
            has_config_change=True,
            is_hotfix=True,
            time_of_day_hour=23,  # Late night
            day_of_week=4,  # Friday
            similar_past_failures=5,
            similar_past_successes=5,
            rag_confidence=0.6,
        )

    def test_low_risk_deployment(self, risk_scorer, critical_service, low_risk_context):
        """Test that low-risk deployments get appropriate scores."""
        assessment = risk_scorer.calculate_risk_score(
            critical_service, low_risk_context, "dep-001"
        )

        # Critical service increases risk, but context is low-risk
        assert assessment.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]
        assert assessment.risk_score < 0.7

    def test_high_risk_deployment(self, risk_scorer, critical_service, high_risk_context):
        """Test that high-risk deployments are properly flagged."""
        assessment = risk_scorer.calculate_risk_score(
            critical_service, high_risk_context, "dep-002"
        )

        # Risk score should be elevated (>0.5) and require human review
        assert assessment.risk_score > 0.5
        assert assessment.risk_level in [RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        assert assessment.requires_human_review is True

    def test_error_budget_check(self, risk_scorer, critical_service):
        """Test error budget enforcement."""
        # Service with budget
        allowed, reason = risk_scorer.check_error_budget(critical_service)
        assert allowed is True

        # Service without budget
        critical_service.error_budget_remaining = 0.0
        allowed, reason = risk_scorer.check_error_budget(critical_service)
        assert allowed is False
        assert "ERROR_BUDGET_EXHAUSTED" in reason

    def test_risk_weights_normalization(self):
        """Test that risk weights are properly normalized."""
        custom_weights = RiskWeights(
            service_tier=0.5,
            service_health=0.5,
            historical_failure_rate=0.5,
            blast_radius=0.5,
            change_complexity=0.5,
            timing_risk=0.5,
        )
        scorer = RiskScorer(weights=custom_weights)

        # Weights should be normalized to sum to 1.0
        total = (scorer.weights.service_tier + scorer.weights.service_health +
                 scorer.weights.historical_failure_rate + scorer.weights.blast_radius +
                 scorer.weights.change_complexity + scorer.weights.timing_risk)
        assert abs(total - 1.0) < 0.001


class TestCanaryRollout:
    """Tests for Pillar 3: Staged Canary Rollouts"""

    @pytest.fixture
    def canary(self):
        return CanaryRollout(SLOConfig(
            error_rate_threshold=0.01,
            latency_p50_threshold_ms=100.0,
            latency_p99_threshold_ms=500.0,
            success_rate_threshold=0.99,
        ))

    @pytest.fixture
    def healthy_service(self):
        return Service(
            id="svc-healthy",
            name="healthy-service",
            tier=ServiceTier.MEDIUM,
            dependencies=[],
            deployment_frequency_daily=5.0,
            recent_failure_rate=0.005,
            error_budget_remaining=0.9,
            avg_latency_ms=30.0,
            availability_99d=0.999,
        )

    def test_default_stages(self, canary):
        """Test default canary stage configuration."""
        from genops.models import RiskLevel

        stages = canary.get_stages(RiskLevel.LOW)
        assert len(stages) == 5
        assert stages[0].traffic_percentage == 0.01  # 1%
        assert stages[-1].traffic_percentage == 1.0  # 100%

    def test_high_risk_stages(self, canary):
        """Test that high-risk deployments get more canary stages."""
        from genops.models import RiskLevel

        stages = canary.get_stages(RiskLevel.HIGH)
        assert len(stages) == 7  # More granular stages
        assert stages[0].traffic_percentage == 0.01
        assert stages[1].traffic_percentage == 0.02  # Extra early stage

    def test_slo_compliance_check(self, canary):
        """Test SLO compliance checking."""
        from genops.models import CanaryMetrics

        # Good metrics
        good_metrics = CanaryMetrics(
            stage="5%",
            traffic_percentage=0.05,
            duration_seconds=300,
            error_rate=0.005,
            latency_p50_ms=50.0,
            latency_p99_ms=200.0,
            success_rate=0.995,
            slo_violations=0,
        )
        compliant, violations = canary.check_slo_compliance(good_metrics)
        assert compliant is True
        assert len(violations) == 0

        # Bad metrics
        bad_metrics = CanaryMetrics(
            stage="5%",
            traffic_percentage=0.05,
            duration_seconds=300,
            error_rate=0.05,  # 5% error rate - bad
            latency_p50_ms=150.0,  # High latency
            latency_p99_ms=800.0,  # Very high p99
            success_rate=0.95,  # Below threshold
            slo_violations=4,
        )
        compliant, violations = canary.check_slo_compliance(bad_metrics)
        assert compliant is False
        assert len(violations) >= 1

    def test_rollback_reset(self, canary):
        """Test canary state reset."""
        canary.rollback_triggered = True
        canary.rollback_reason = "Test reason"

        canary.reset()

        assert canary.rollback_triggered is False
        assert canary.rollback_reason is None


class TestGovernance:
    """Tests for Pillar 4: Runtime Governance"""

    @pytest.fixture
    def governance(self):
        return GovernanceEngine(autonomy_level=AutonomyLevel.GOVERNED)

    @pytest.fixture
    def deployment(self):
        return Deployment(
            service_id="svc-test",
            version="1.0.0",
            status=DeploymentStatus.PENDING,
        )

    @pytest.fixture
    def critical_service(self):
        return Service(
            id="svc-critical",
            name="critical-service",
            tier=ServiceTier.CRITICAL,
            dependencies=["db"],
            deployment_frequency_daily=3.0,
            recent_failure_rate=0.02,
            error_budget_remaining=0.5,
            avg_latency_ms=50.0,
            availability_99d=0.999,
        )

    def test_policy_evaluation(self, governance, deployment, critical_service):
        """Test governance policy evaluation."""
        context = DeploymentContext(
            change_size_lines=100,
            files_changed=5,
            has_db_migration=False,
            has_config_change=False,
            is_hotfix=False,
            time_of_day_hour=14,
            day_of_week=2,
            similar_past_failures=0,
            similar_past_successes=5,
            rag_confidence=0.9,
        )

        result = governance.evaluate_policies(
            deployment, critical_service, context, risk_score=0.6
        )

        assert "policies_evaluated" in result
        assert "allowed" in result
        assert len(result["policies_evaluated"]) > 0

    def test_audit_logging(self, governance, deployment):
        """Test immutable audit trail."""
        entry = governance.log_audit_event(
            deployment,
            event_type="test_event",
            action="test_action",
            details={"test": "data"},
        )

        assert entry.deployment_id == deployment.id
        assert entry.event_type == "test_event"
        assert entry.hash != ""  # Hash should be calculated

        # Verify hash integrity
        assert entry.hash == entry._calculate_hash()

    def test_model_registry(self, governance):
        """Test model registry approval checking."""
        # Approved model
        approved, reason = governance.verify_model_approval("genops-risk-scorer-v1")
        assert approved is True

        # Unknown model
        approved, reason = governance.verify_model_approval("unknown-model")
        assert approved is False

    def test_compliance_report_generation(self, governance, deployment):
        """Test compliance report generation."""
        # Log some events
        governance.log_audit_event(
            deployment, "event1", "action1", {"key": "value1"}
        )
        governance.log_audit_event(
            deployment, "event2", "action2", {"key": "value2"}
        )

        report = governance.generate_compliance_report(deployment)

        assert report["deployment_id"] == deployment.id
        assert report["summary"]["total_events"] >= 2
        assert "timeline" in report
        assert report["audit_integrity"] is True

    def test_safety_violation_detection(self, governance, deployment):
        """Test that safety violations are properly detected."""
        # In normal operation, there should be no violations
        violation = governance.check_safety_violation(deployment, "deploy", {})
        assert violation is False

    def test_friday_deployment_blocking(self, governance, deployment, critical_service):
        """Test that Friday evening deployments are blocked."""
        friday_evening_context = DeploymentContext(
            change_size_lines=100,
            files_changed=5,
            has_db_migration=False,
            has_config_change=False,
            is_hotfix=False,
            time_of_day_hour=17,  # 5 PM
            day_of_week=4,  # Friday
            similar_past_failures=0,
            similar_past_successes=5,
            rag_confidence=0.9,
        )

        result = governance.evaluate_policies(
            deployment, critical_service, friday_evening_context, risk_score=0.3
        )

        # Should be blocked by no_friday_deployments policy
        assert result["allowed"] is False or "no_friday_deployments" in result["policies_violated"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
