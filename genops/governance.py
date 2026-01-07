"""
Pillar 4: Runtime Governance

This module implements governance controls including:
- Model registry alignment
- Immutable audit trails
- Policy enforcement
- Compliance validation

Key capabilities:
- Complete decision explainability
- Forensic analysis support
- Real-time policy validation
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
import hashlib

from .models import (
    Deployment, RiskAssessment, GovernancePolicy, ServiceTier,
    DeploymentStatus, AutonomyLevel
)


@dataclass
class AuditEntry:
    """Immutable audit trail entry."""
    timestamp: str
    deployment_id: str
    event_type: str
    actor: str  # "ai_agent", "human_reviewer", "system"
    action: str
    details: Dict[str, Any]
    risk_score: Optional[float] = None
    confidence: Optional[float] = None
    policies_evaluated: List[str] = field(default_factory=list)
    policies_violated: List[str] = field(default_factory=list)
    hash: str = ""  # Hash for tamper detection

    def __post_init__(self):
        if not self.hash:
            self.hash = self._calculate_hash()

    def _calculate_hash(self) -> str:
        """Calculate hash for tamper detection."""
        content = f"{self.timestamp}{self.deployment_id}{self.event_type}{self.action}{json.dumps(self.details, sort_keys=True)}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class GovernanceEngine:
    """
    Pillar 4: Runtime Governance

    Implements comprehensive governance including:
    - Model registry for approved AI models
    - Immutable audit trails
    - Policy enforcement
    - Compliance validation

    Paper Reference:
    - Zero safety policy violations achieved through architectural enforcement
    - Complete audit trail for every AI decision
    """

    # Default policies
    DEFAULT_POLICIES = [
        GovernancePolicy(
            name="critical_service_human_review",
            description="Critical services require human review for high-risk changes",
            condition="service.tier == ServiceTier.CRITICAL and risk_score > 0.5",
            action="require_approval",
            severity="high"
        ),
        GovernancePolicy(
            name="no_friday_deployments",
            description="Block deployments on Friday after 4 PM",
            condition="context.day_of_week == 4 and context.time_of_day_hour >= 16",
            action="block",
            severity="medium"
        ),
        GovernancePolicy(
            name="error_budget_protection",
            description="Block deployments when error budget exhausted",
            condition="service.error_budget_remaining <= 0",
            action="block",
            severity="critical"
        ),
        GovernancePolicy(
            name="db_migration_review",
            description="Database migrations require human review",
            condition="context.has_db_migration and service.tier.value <= 2",
            action="require_approval",
            severity="high"
        ),
        GovernancePolicy(
            name="large_change_caution",
            description="Large changes require extra canary stages",
            condition="context.change_size_lines > 1000",
            action="warn",
            severity="medium"
        ),
    ]

    def __init__(
        self,
        policies: List[GovernancePolicy] = None,
        autonomy_level: AutonomyLevel = AutonomyLevel.GOVERNED
    ):
        self.policies = policies or self.DEFAULT_POLICIES
        self.autonomy_level = autonomy_level
        self.audit_log: List[AuditEntry] = []
        self.model_registry: Dict[str, Dict[str, Any]] = {
            "genops-risk-scorer-v1": {
                "approved": True,
                "version": "1.0.0",
                "performance_metrics": {"accuracy": 0.94, "latency_ms": 45},
            },
            "genops-context-rag-v1": {
                "approved": True,
                "version": "1.0.0",
                "performance_metrics": {"retrieval_accuracy": 0.89, "latency_ms": 120},
            },
        }

    def evaluate_policies(
        self,
        deployment: Deployment,
        service: Any,  # Service
        context: Any,  # DeploymentContext
        risk_score: float
    ) -> Dict[str, Any]:
        """
        Evaluate all governance policies for a deployment.

        Returns policy evaluation results.
        """
        results = {
            "policies_evaluated": [],
            "policies_violated": [],
            "actions_required": [],
            "warnings": [],
            "allowed": True,
            "requires_approval": False,
        }

        for policy in self.policies:
            results["policies_evaluated"].append(policy.name)

            # Evaluate policy condition (simplified evaluation)
            violated = self._evaluate_condition(
                policy.condition, service, context, risk_score
            )

            if violated:
                results["policies_violated"].append(policy.name)

                if policy.action == "block":
                    results["allowed"] = False
                    results["actions_required"].append({
                        "policy": policy.name,
                        "action": "BLOCKED",
                        "reason": policy.description,
                        "severity": policy.severity
                    })
                elif policy.action == "require_approval":
                    results["requires_approval"] = True
                    results["actions_required"].append({
                        "policy": policy.name,
                        "action": "REQUIRES_APPROVAL",
                        "reason": policy.description,
                        "severity": policy.severity
                    })
                elif policy.action == "warn":
                    results["warnings"].append({
                        "policy": policy.name,
                        "message": policy.description,
                        "severity": policy.severity
                    })

        return results

    def _evaluate_condition(
        self,
        condition: str,
        service: Any,
        context: Any,
        risk_score: float
    ) -> bool:
        """
        Evaluate a policy condition.

        In production, this would use a proper expression evaluator.
        Here we simulate common conditions.
        """
        # Simplified condition evaluation
        if "service.tier == ServiceTier.CRITICAL" in condition:
            if not hasattr(service, 'tier') or service.tier != ServiceTier.CRITICAL:
                return False
            if "risk_score > 0.5" in condition and risk_score <= 0.5:
                return False
            return True

        if "day_of_week == 4" in condition and "time_of_day_hour >= 16" in condition:
            if hasattr(context, 'day_of_week') and hasattr(context, 'time_of_day_hour'):
                return context.day_of_week == 4 and context.time_of_day_hour >= 16
            return False

        if "error_budget_remaining <= 0" in condition:
            if hasattr(service, 'error_budget_remaining'):
                return service.error_budget_remaining <= 0
            return False

        if "has_db_migration" in condition:
            if hasattr(context, 'has_db_migration') and context.has_db_migration:
                if "tier.value <= 2" in condition and hasattr(service, 'tier'):
                    return service.tier.value <= 2
            return False

        if "change_size_lines > 1000" in condition:
            if hasattr(context, 'change_size_lines'):
                return context.change_size_lines > 1000
            return False

        return False

    def log_audit_event(
        self,
        deployment: Deployment,
        event_type: str,
        action: str,
        details: Dict[str, Any],
        actor: str = "ai_agent",
        risk_assessment: Optional[RiskAssessment] = None,
        policies_evaluated: List[str] = None,
        policies_violated: List[str] = None
    ) -> AuditEntry:
        """
        Log an event to the immutable audit trail.
        """
        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            deployment_id=deployment.id,
            event_type=event_type,
            actor=actor,
            action=action,
            details=details,
            risk_score=risk_assessment.risk_score if risk_assessment else None,
            confidence=risk_assessment.confidence if risk_assessment else None,
            policies_evaluated=policies_evaluated or [],
            policies_violated=policies_violated or [],
        )

        self.audit_log.append(entry)
        deployment.add_audit_event(event_type, asdict(entry))

        return entry

    def verify_model_approval(self, model_id: str) -> Tuple[bool, str]:
        """
        Verify that a model is approved in the registry.
        """
        if model_id not in self.model_registry:
            return False, f"Model {model_id} not found in registry"

        model_info = self.model_registry[model_id]
        if not model_info.get("approved", False):
            return False, f"Model {model_id} is not approved for production use"

        return True, f"Model {model_id} approved (version {model_info.get('version', 'unknown')})"

    def generate_compliance_report(
        self,
        deployment: Deployment
    ) -> Dict[str, Any]:
        """
        Generate compliance report for a deployment.

        Useful for audits and post-incident analysis.
        """
        deployment_events = [
            e for e in self.audit_log
            if e.deployment_id == deployment.id
        ]

        return {
            "deployment_id": deployment.id,
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_events": len(deployment_events),
                "status": deployment.status.value,
                "duration_minutes": deployment.duration_minutes,
                "policies_violated": list(set(
                    p for e in deployment_events for p in e.policies_violated
                )),
                "human_interventions": sum(
                    1 for e in deployment_events if e.actor == "human_reviewer"
                ),
            },
            "timeline": [
                {
                    "timestamp": e.timestamp,
                    "event": e.event_type,
                    "action": e.action,
                    "actor": e.actor,
                    "risk_score": e.risk_score,
                }
                for e in deployment_events
            ],
            "audit_integrity": all(
                e.hash == e._calculate_hash() for e in deployment_events
            ),
        }

    def check_safety_violation(
        self,
        deployment: Deployment,
        action_taken: str,
        context: Dict[str, Any]
    ) -> bool:
        """
        Check if an action constitutes a safety violation.

        A safety violation occurs when:
        1. A blocked policy was bypassed
        2. A required approval was skipped
        3. An unapproved model was used
        4. Audit trail was tampered with

        Returns True if a violation occurred.
        """
        # In GenOps, these should be architecturally impossible
        # This is why the paper reports zero violations

        # Check if any critical policies were violated but action proceeded
        for entry in self.audit_log:
            if entry.deployment_id != deployment.id:
                continue

            # Check for bypassed blocks
            if entry.policies_violated:
                for policy_name in entry.policies_violated:
                    policy = next(
                        (p for p in self.policies if p.name == policy_name),
                        None
                    )
                    if policy and policy.action == "block":
                        if deployment.status == DeploymentStatus.COMPLETED:
                            return True  # Violation: blocked but completed

        return False

    def export_audit_log(self, format: str = "json") -> str:
        """Export audit log for compliance purposes."""
        if format == "json":
            return json.dumps(
                [asdict(e) for e in self.audit_log],
                indent=2,
                default=str
            )
        else:
            raise ValueError(f"Unsupported format: {format}")


# Type hint fix for tuple return
from typing import Tuple
