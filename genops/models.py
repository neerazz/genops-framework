"""
Data models for GenOps framework.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List, Any
import uuid


class ServiceTier(Enum):
    """Service criticality tiers for risk assessment."""
    CRITICAL = 1      # Core revenue-generating services
    HIGH = 2          # Important business services
    MEDIUM = 3        # Supporting services
    LOW = 4           # Internal/dev services


class DeploymentStatus(Enum):
    """Status of a deployment through the pipeline."""
    PENDING = "pending"
    CONTEXT_GATHERED = "context_gathered"
    RISK_ASSESSED = "risk_assessed"
    CANARY_STARTED = "canary_started"
    CANARY_STAGE_1 = "canary_1%"
    CANARY_STAGE_2 = "canary_5%"
    CANARY_STAGE_3 = "canary_25%"
    CANARY_STAGE_4 = "canary_50%"
    CANARY_COMPLETE = "canary_100%"
    ROLLED_BACK = "rolled_back"
    COMPLETED = "completed"
    FAILED = "failed"


class RiskLevel(Enum):
    """Risk levels for deployment decisions."""
    LOW = "low"           # Auto-approve
    MEDIUM = "medium"     # Auto-approve with monitoring
    HIGH = "high"         # Requires human review
    CRITICAL = "critical" # Block until manual approval


class AutonomyLevel(Enum):
    """AI autonomy levels based on phase adoption."""
    SHADOW = "shadow"           # AI observes only, no execution
    ASSISTED = "assisted"       # AI executes low-risk with bounds
    GOVERNED = "governed"       # AI has expanded autonomy with gates
    LEARNING = "learning"       # Full autonomy with feedback loop


@dataclass
class Service:
    """Represents a microservice in the system."""
    id: str
    name: str
    tier: ServiceTier
    dependencies: List[str] = field(default_factory=list)
    owner_team: str = "platform"
    error_budget_remaining: float = 1.0  # 0.0 to 1.0
    recent_failure_rate: float = 0.0     # 0.0 to 1.0
    avg_deployment_time_min: float = 10.0
    last_incident_days_ago: int = 30
    deployment_frequency_daily: float = 5.0
    avg_latency_ms: float = 50.0
    availability_99d: float = 0.999

    def health_score(self) -> float:
        """Calculate service health score (0-1, higher is better)."""
        budget_factor = self.error_budget_remaining
        failure_factor = 1.0 - self.recent_failure_rate
        availability_factor = self.availability_99d
        return (budget_factor + failure_factor + availability_factor) / 3.0


@dataclass
class DeploymentContext:
    """Context gathered for a deployment decision."""
    change_size_lines: int
    files_changed: int
    has_db_migration: bool
    has_config_change: bool
    is_hotfix: bool
    time_of_day_hour: int  # 0-23
    day_of_week: int       # 0=Monday, 6=Sunday
    similar_past_failures: int = 0
    similar_past_successes: int = 0
    rag_confidence: float = 0.0  # RAG retrieval confidence


@dataclass
class RiskAssessment:
    """Result of risk scoring for a deployment."""
    deployment_id: str
    risk_score: float        # 0.0 to 1.0
    risk_level: RiskLevel
    confidence: float        # AI confidence in assessment
    factors: Dict[str, float] = field(default_factory=dict)
    recommendation: str = ""
    requires_human_review: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deployment_id": self.deployment_id,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level.value,
            "confidence": self.confidence,
            "factors": self.factors,
            "recommendation": self.recommendation,
            "requires_human_review": self.requires_human_review,
        }


@dataclass
class CanaryMetrics:
    """Metrics collected during canary stage."""
    stage: str
    traffic_percentage: float
    duration_seconds: int
    error_rate: float
    latency_p50_ms: float
    latency_p99_ms: float
    success_rate: float
    slo_violations: int = 0


@dataclass
class Deployment:
    """Represents a deployment through the GenOps pipeline."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    service_id: str = ""
    version: str = ""
    status: DeploymentStatus = DeploymentStatus.PENDING
    context: Optional[DeploymentContext] = None
    risk_assessment: Optional[RiskAssessment] = None
    canary_metrics: List[CanaryMetrics] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    rollback_reason: Optional[str] = None
    audit_trail: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def duration_minutes(self) -> float:
        """Calculate deployment duration in minutes."""
        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds() / 60.0

    def add_audit_event(self, event_type: str, details: Dict[str, Any]):
        """Add event to immutable audit trail."""
        self.audit_trail.append({
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "details": details,
            "deployment_status": self.status.value,
        })


@dataclass
class GovernancePolicy:
    """Policy rules for governance enforcement."""
    name: str
    description: str
    condition: str  # Python expression as string
    action: str     # "block", "warn", "require_approval"
    severity: str   # "critical", "high", "medium", "low"


@dataclass
class StudyResults:
    """Aggregate results matching the paper's metrics."""
    total_deployments: int = 0
    successful_deployments: int = 0
    failed_deployments: int = 0
    rolled_back_deployments: int = 0
    canary_caught_issues: int = 0
    safety_violations: int = 0
    total_cycle_time_minutes: float = 0.0

    @property
    def success_rate(self) -> float:
        if self.total_deployments == 0:
            return 0.0
        return self.successful_deployments / self.total_deployments

    @property
    def rollback_rate(self) -> float:
        if self.total_deployments == 0:
            return 0.0
        return self.rolled_back_deployments / self.total_deployments

    @property
    def failure_rate(self) -> float:
        if self.total_deployments == 0:
            return 0.0
        return self.failed_deployments / self.total_deployments

    @property
    def median_cycle_time(self) -> float:
        if self.total_deployments == 0:
            return 0.0
        return self.total_cycle_time_minutes / self.total_deployments

    @property
    def canary_catch_rate(self) -> float:
        """Percentage of issues caught by canary before full rollout."""
        total_issues = self.rolled_back_deployments + self.failed_deployments
        if total_issues == 0:
            return 0.0
        return self.canary_caught_issues / total_issues if total_issues > 0 else 0.0
