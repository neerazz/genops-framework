"""
Unit tests for GenOps models with property-based testing.

Tests mathematical correctness, data validation, and statistical properties
of all core model classes using hypothesis for property-based testing.
"""

import pytest
import hypothesis
from hypothesis import given, strategies as st, settings, HealthCheck
import statistics
import math
from dataclasses import asdict

from genops.models import (
    Service, ServiceTier, DeploymentContext, RiskAssessment, RiskLevel,
    SLOConfig, CanaryMetrics, StatisticalControlLimits,
    DataValidator, ValidationError, validate_range, validate_type,
    validate_positive, validate_non_empty
)


class TestServiceModel:
    """Test Service model correctness and validation."""

    def test_service_health_calculation(self):
        """Test service health score calculation with boundary conditions."""
        # Perfect health
        service = Service(
            id="test", name="test", tier=ServiceTier.HIGH,
            error_budget_remaining=1.0,
            recent_failure_rate=0.0,
            availability_99d=1.0
        )
        assert service.health_score() == pytest.approx(1.0)

        # Poor health
        service = Service(
            id="test", name="test", tier=ServiceTier.HIGH,
            error_budget_remaining=0.0,
            recent_failure_rate=0.1,
            availability_99d=0.9
        )
        health = service.health_score()
        assert 0.0 <= health <= 1.0
        health = service.health_score()
        assert 0.0 <= health <= 1.0
        assert health < 0.6  # Should be low (0.54 calculated)

    @given(
        budget=st.floats(0.0, 1.0),
        failure_rate=st.floats(0.0, 1.0),
        availability=st.floats(0.0, 1.0)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_service_health_property_based(self, budget, failure_rate, availability):
        """Property-based test for service health calculation."""
        service = Service(
            id="test", name="test", tier=ServiceTier.MEDIUM,
            error_budget_remaining=budget,
            recent_failure_rate=failure_rate,
            availability_99d=availability
        )

        health = service.health_score()

        # Health should always be in [0,1]
        assert 0.0 <= health <= 1.0

        # Health should be monotonic in good factors
        service_better = Service(
            id="test", name="test", tier=ServiceTier.MEDIUM,
            error_budget_remaining=min(1.0, budget + 0.1),
            recent_failure_rate=max(0.0, failure_rate - 0.1),
            availability_99d=min(1.0, availability + 0.1)
        )
        assert service_better.health_score() >= health

    def test_service_validation(self):
        """Test service data validation."""
        # Valid service
        service = Service(id="test", name="test", tier=ServiceTier.HIGH)
        # Should not raise exception

        # Invalid error budget
        with pytest.raises(ValidationError):
            Service(
                id="test", name="test", tier=ServiceTier.HIGH,
                error_budget_remaining=1.5
            )

        # Invalid failure rate
        with pytest.raises(ValidationError):
            Service(
                id="test", name="test", tier=ServiceTier.HIGH,
                recent_failure_rate=-0.1
            )

    def test_service_risk_profile(self):
        """Test service risk profile generation."""
        critical_service = Service(
            id="critical", name="critical", tier=ServiceTier.CRITICAL,
            error_budget_remaining=0.5, recent_failure_rate=0.02
        )

        low_service = Service(
            id="low", name="low", tier=ServiceTier.LOW,
            error_budget_remaining=0.9, recent_failure_rate=0.001
        )

        critical_risk = critical_service.risk_profile()
        low_risk = low_service.risk_profile()

        # Critical service should have higher criticality risk
        assert critical_risk["criticality_risk"] > low_risk["criticality_risk"]

        # Low service should have lower composite risk
        assert critical_risk["composite_risk"] > low_risk["composite_risk"]


class TestRiskAssessmentModel:
    """Test RiskAssessment model statistical properties."""

    def test_risk_level_mapping(self):
        """Test risk level mapping from risk scores."""
        # Low risk
        assessment = RiskAssessment(
            deployment_id="test",
            risk_score=0.2,
            confidence=0.9
        )
        assert assessment.risk_level == RiskLevel.LOW

        # Medium risk
        assessment = RiskAssessment(
            deployment_id="test",
            risk_score=0.5,
            confidence=0.9
        )
        assert assessment.risk_level == RiskLevel.MEDIUM

        # High risk
        assessment = RiskAssessment(
            deployment_id="test",
            risk_score=0.8,
            confidence=0.9
        )
        assert assessment.risk_level == RiskLevel.HIGH

    def test_confidence_interval_calculation(self):
        """Test confidence interval mathematical correctness."""
        assessment = RiskAssessment(
            deployment_id="test",
            risk_score=0.5,
            confidence=0.8,
            uncertainty=0.1
        )

        lower, upper = assessment.confidence_interval()

        # Bounds should be valid
        assert 0.0 <= lower <= upper <= 1.0

        # Should contain the point estimate
        assert lower <= assessment.risk_score <= upper

        # Width should be reasonable (2σ margin -> 4σ width. For 0.1, width=0.4)
        width = upper - lower
        assert 0.35 <= width <= 0.45  # Approximate 4σ bounds

    @given(
        risk_score=st.floats(0.0, 1.0),
        confidence=st.floats(0.5, 1.0),
        uncertainty=st.floats(0.01, 0.5)
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_risk_assessment_properties(self, risk_score, confidence, uncertainty):
        """Property-based test for risk assessment properties."""
        assessment = RiskAssessment(
            deployment_id="test",
            risk_score=risk_score,
            confidence=confidence,
            uncertainty=uncertainty
        )

        # Basic properties
        assert 0.0 <= assessment.risk_score <= 1.0
        assert 0.0 <= assessment.confidence <= 1.0
        assert 0.0 <= assessment.uncertainty <= 1.0

        # Confidence interval properties
        lower, upper = assessment.confidence_interval()
        assert 0.0 <= lower <= upper <= 1.0
        assert lower <= assessment.risk_score <= upper

        # Risk factors should be valid
        for factor_value in assessment.factors.values():
            assert 0.0 <= factor_value <= 1.0

    def test_risk_probability_distribution(self):
        """Test risk probability distribution calculation."""
        assessment = RiskAssessment(
            deployment_id="test",
            risk_score=0.5,
            confidence=0.8
        )

        distribution = assessment.risk_probability_distribution()

        # Should have all risk levels
        assert set(distribution.keys()) == {"LOW", "MEDIUM", "HIGH"}

        # Probabilities should sum to 1
        total_prob = sum(distribution.values())
        assert abs(total_prob - 1.0) < 1e-6

        # All probabilities should be non-negative
        for prob in distribution.values():
            assert prob >= 0.0


class TestSLOConfigModel:
    """Test SLO configuration validation and compliance checking."""

    def test_slo_validation(self):
        """Test SLO configuration validation."""
        # Valid configuration
        slo = SLOConfig()
        # Should not raise exception

        # Invalid error rate threshold
        with pytest.raises(ValidationError):
            SLOConfig(error_rate_threshold=-0.1)

        # Invalid latency (P99 < P50)
        with pytest.raises(ValidationError):
            SLOConfig(
                latency_p50_threshold_ms=100.0,
                latency_p99_threshold_ms=50.0
            )

    def test_slo_compliance_checking(self):
        """Test SLO compliance evaluation."""
        slo = SLOConfig(
            error_rate_threshold=0.02,
            latency_p50_threshold_ms=150.0,
            latency_p99_threshold_ms=600.0,
            success_rate_threshold=0.98,
            max_slo_violations=1
        )

        # Compliant metrics
        compliant_metrics = CanaryMetrics(
            stage="test",
            traffic_percentage=0.5,
            duration_seconds=300,
            error_rate=0.01,
            latency_p50_ms=100.0,
            latency_p99_ms=300.0,
            success_rate=0.99,
            slo_violations=0
        )
        assert slo.is_violated(compliant_metrics) == False

        # Non-compliant metrics (high error rate)
        non_compliant_metrics = CanaryMetrics(
            stage="test",
            traffic_percentage=0.5,
            duration_seconds=300,
            error_rate=0.05,  # Above 0.02 threshold
            latency_p50_ms=100.0,
            latency_p99_ms=300.0,
            success_rate=0.99,
            slo_violations=1
        )
        # Calculation: 1 violation (error 0.05 > 0.02) >= 1 (max) -> True
        assert slo.is_violated(non_compliant_metrics) == True


class TestStatisticalControlLimits:
    """Test statistical process control implementation."""

    def test_control_limits_calculation(self):
        """Test control limits calculation from sample data."""
        # Generate normal data
        data = [0.05 + 0.01 * (i - 50) / 10 for i in range(100)]  # Mean=0.05, std=0.01

        mean = statistics.mean(data)
        std = statistics.stdev(data)

        limits = StatisticalControlLimits(mean=mean, std=std)

        # Check control limit calculations
        assert limits.upper_1sigma == pytest.approx(mean + 1 * std, abs=1e-10)
        assert limits.upper_2sigma == pytest.approx(mean + 2 * std, abs=1e-10)
        assert limits.upper_3sigma == pytest.approx(mean + 3 * std, abs=1e-10)
        assert limits.lower_1sigma == pytest.approx(mean - 1 * std, abs=1e-10)

    def test_western_electric_rules(self):
        """Test SPC rule violation detection."""
        control = StatisticalControlLimits(mean=0.05, std=0.01)

        # Rule 1: Point beyond 3σ (limit is 0.08)
        # Using 0.09 to ensure > 0.08. Must have len >= 8.
        violations = [0.04] * 7 + [0.09]
        
        violation, rule = control.check_western_electric_rules(violations)
        if not violation:
            print(f"\nDEBUG: upper_3sigma={control.upper_3sigma}, last_point={violations[-1]}")
        assert violation, f"Rule 1 failed: upper_3sigma={control.upper_3sigma}, last_point={violations[-1]}"
        assert "Rule 1" in rule

        # Rule 2 violation: 9 points on one side
        trend_data = [0.06] * 9  # 9 points above mean
        violation, rule = control.check_western_electric_rules(trend_data)
        assert violation
        assert "Rule 2" in rule


class TestDataValidation:
    """Test data validation utilities."""

    def test_service_health_validation(self):
        """Test service health validation logic."""
        # Valid service
        valid_service = Service(id="test", name="test", tier=ServiceTier.HIGH)
        is_valid, errors = DataValidator.validate_service_health(valid_service)
        assert is_valid
        assert len(errors) == 0

        # Invalid service (range violation)
        with pytest.raises(ValidationError):
            Service(
                id="test", name="test", tier=ServiceTier.HIGH,
                error_budget_remaining=1.5,  # Invalid > 1.0
                recent_failure_rate=0.1,
                availability_99d=0.95
            )

    def test_risk_assessment_validation(self):
        """Test risk assessment validation."""
        # Valid assessment
        valid_assessment = RiskAssessment(
            deployment_id="test",
            risk_score=0.5,
            confidence=0.8
        )
        is_valid, errors = DataValidator.validate_risk_assessment(valid_assessment)
        assert is_valid

        # Invalid assessment (risk score out of bounds)
        with pytest.raises(ValidationError):
            RiskAssessment(
                deployment_id="test",
                risk_score=1.5,  # Invalid
                confidence=0.8
            )

    def test_slo_config_validation(self):
        """Test SLO configuration validation."""
        # Valid config
        valid_config = SLOConfig()
        is_valid, errors = DataValidator.validate_slo_config(valid_config)
        assert is_valid

        # Invalid config (P99 < P50)
        with pytest.raises(ValidationError):
            SLOConfig(
                latency_p50_threshold_ms=200.0,
                latency_p99_threshold_ms=150.0  # Invalid
            )


class TestValidationDecorators:
    """Test runtime validation decorators."""

    def test_validate_range_decorator(self):
        """Test range validation decorator."""
        @validate_range(min_val=0.0, max_val=1.0)
        def set_probability(self, prob: float):
            return prob

        # Valid value
        result = set_probability(None, 0.5)
        assert result == 0.5

        # Invalid value
        with pytest.raises(ValidationError):
            set_probability(None, 1.5)

    def test_validate_type_decorator(self):
        """Test type validation decorator."""
        @validate_type(str)
        def process_name(self, name: str):
            return name.upper()

        # Valid type
        result = process_name(None, "test")
        assert result == "TEST"

        # Invalid type
        with pytest.raises(ValidationError):
            process_name(None, 123)

    def test_validate_positive_decorator(self):
        """Test positive value validation decorator."""
        @validate_positive()
        def set_timeout(self, timeout: float):
            return timeout

        # Valid positive value
        result = set_timeout(None, 5.0)
        assert result == 5.0

        # Invalid negative value
        with pytest.raises(ValidationError):
            set_timeout(None, -1.0)

    def test_validate_non_empty_decorator(self):
        """Test non-empty validation decorator."""
        @validate_non_empty()
        def process_list(self, items: list):
            return len(items)

        # Valid non-empty list
        result = process_list(None, [1, 2, 3])
        assert result == 3

        # Invalid empty list
        with pytest.raises(ValidationError):
            process_list(None, [])


class TestModelIntegration:
    """Test integration between model components."""

    def test_service_context_integration(self):
        """Test service and deployment context integration."""
        service = Service(
            id="web_api", name="Web API", tier=ServiceTier.HIGH,
            error_budget_remaining=0.8,
            recent_failure_rate=0.02,
            availability_99d=0.995
        )

        context = DeploymentContext(
            change_size_lines=1500,
            files_changed=15,
            has_db_migration=False,
            has_config_change=True,
            is_hotfix=False,
            time_of_day_hour=14,
            day_of_week=2
        )

        # Test integration properties
        assert service.health_score() > 0.7  # Should be healthy
        assert context.blast_radius_estimate() > 0  # Should have blast radius

        # Test cross-references
        # Service ID reference removed from DeploymentContext model

    def test_end_to_end_model_flow(self):
        """Test complete model workflow from service to risk assessment."""
        # Create service
        service = Service(
            id="api", name="API Service", tier=ServiceTier.CRITICAL,
            error_budget_remaining=0.9,
            recent_failure_rate=0.01,
            availability_99d=0.999
        )

        # Create context
        # Create context
        context = DeploymentContext(
            change_size_lines=2000,
            files_changed=20,
            has_db_migration=True,
            has_config_change=False,
            is_hotfix=False,
            time_of_day_hour=10,
            day_of_week=1
        )

        # Create risk assessment
        assessment = RiskAssessment(
            deployment_id="deploy_001",
            risk_score=0.7,
            risk_level=RiskLevel.HIGH,
            confidence=0.85,
            factors={
                "service_criticality": service.tier.risk_multiplier,
                "service_health": service.health_score(),
                "change_complexity": min(1.0, context.change_size_lines / 5000),
                "blast_radius": context.blast_radius_estimate()
            }
        )

        # Validate integration
        assert assessment.risk_level == RiskLevel.HIGH
        assert assessment.deployment_id == "deploy_001"
        assert assessment.confidence > 0.8
        assert "change_complexity" in assessment.factors

        # Validate risk factors are reasonable
        for factor_value in assessment.factors.values():
            assert 0.0 <= factor_value <= 1.0

        # Validate confidence interval
        lower, upper = assessment.confidence_interval()
        assert lower <= assessment.risk_score <= upper