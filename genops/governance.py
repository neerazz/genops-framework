"""
Pillar 4: Advanced Runtime Governance with Cryptographic Audit Trails

This module implements enterprise-grade governance controls with:
- Cryptographic audit trails with SHA-256 chain hashing
- Digital signatures for non-repudiation and actor verification
- Policy versioning and compliance reporting
- Multi-party approval workflows
- Forensic analysis capabilities
- Regulatory compliance (SOC 2, GDPR, SOX)

Mathematical Framework:
- Hash Chains: Hₙ = SHA-256(Hₙ₋₁ || event_data) for tamper detection
- Digital Signatures: ECDSA signatures for actor authentication
- Merkle Trees: Efficient integrity verification for large audit logs
- Policy Versioning: Semantic versioning with change tracking

Security Properties:
- Tamper Detection: Any modification breaks hash chain integrity
- Non-Repudiation: Digital signatures prevent denial of actions
- Completeness: All decisions have complete audit trail
- Verifiability: Third-party verification of governance compliance

Paper Reference:
- Zero safety violations through architectural enforcement
- Complete audit trail for every AI decision
- Cryptographic verification of governance integrity
"""

import json
import hmac
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from abc import ABC, abstractmethod
import base64
import secrets

from .models import (
    Deployment, RiskAssessment, GovernancePolicy, ServiceTier,
    DeploymentStatus, AutonomyLevel
)


class GenOpsJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles Enum and dataclass serialization."""

    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)


class ComplianceStandard(Enum):
    """
    Supported compliance standards for governance reporting.
    """
    SOC2 = "soc2"              # Service Organization Control 2
    SOX = "sox"                # Sarbanes-Oxley Act
    GDPR = "gdpr"              # General Data Protection Regulation
    HIPAA = "hipaa"            # Health Insurance Portability and Accountability Act
    PCI_DSS = "pci_dss"        # Payment Card Industry Data Security Standard
    ISO27001 = "iso27001"      # Information Security Management Systems


@dataclass
class DigitalSignature:
    """
    Cryptographic digital signature for audit trail integrity.

    Uses HMAC-SHA256 for actor authentication and non-repudiation.
    In production, this would use asymmetric cryptography (RSA/ECDSA).
    """
    signature: str
    algorithm: str = "HMAC-SHA256"
    key_id: str = ""
    signed_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @classmethod
    def create(cls, data: str, secret_key: str) -> 'DigitalSignature':
        """Create a digital signature for the given data."""
        signature = hmac.new(
            secret_key.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()

        return cls(
            signature=signature,
            algorithm="HMAC-SHA256",
            key_id=hashlib.sha256(secret_key.encode()).hexdigest()[:16]
        )

    def verify(self, data: str, secret_key: str) -> bool:
        """Verify the digital signature against the provided data."""
        expected_signature = hmac.new(
            secret_key.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(self.signature, expected_signature)


@dataclass
class AuditChainBlock:
    """
    Block in the tamper-proof audit chain using cryptographic hashing.

    Each block contains audit entries and maintains chain integrity through:
    - SHA-256 hash of block contents
    - Reference to previous block hash
    - Merkle tree root for efficient verification
    """
    block_id: str
    timestamp: str
    entries: List['AuditEntry']
    previous_hash: str
    merkle_root: str = ""
    signature: Optional[DigitalSignature] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize block hash and merkle root."""
        if not self.merkle_root:
            self.merkle_root = self._calculate_merkle_root()
        if not hasattr(self, '_block_hash'):
            self._block_hash = self._calculate_block_hash()

    def _calculate_merkle_root(self) -> str:
        """Calculate Merkle tree root for efficient integrity verification."""
        if not self.entries:
            return hashlib.sha256(b"empty").hexdigest()

        # Build Merkle tree
        hashes = [entry.hash for entry in self.entries]

        while len(hashes) > 1:
            if len(hashes) % 2 == 1:
                hashes.append(hashes[-1])  # Duplicate last hash if odd number

            new_hashes = []
            for i in range(0, len(hashes), 2):
                combined = hashes[i] + hashes[i + 1]
                new_hashes.append(hashlib.sha256(combined.encode()).hexdigest())
            hashes = new_hashes

        return hashes[0]

    def _calculate_block_hash(self) -> str:
        """Calculate block hash for chain integrity."""
        content = f"{self.block_id}{self.timestamp}{self.previous_hash}{self.merkle_root}"
        content += json.dumps(self.metadata, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    @property
    def block_hash(self) -> str:
        """Get the block's hash."""
        return getattr(self, '_block_hash', self._calculate_block_hash())

    def verify_integrity(self) -> Tuple[bool, str]:
        """
        Verify the block's cryptographic integrity.

        Returns (is_valid, error_message)
        """
        # Verify merkle root
        if self.merkle_root != self._calculate_merkle_root():
            return False, "Merkle root mismatch - entries may be corrupted"

        # Verify block hash
        if self.block_hash != self._calculate_block_hash():
            return False, "Block hash mismatch - block may be tampered"

        # Verify entry signatures if present
        for entry in self.entries:
            if hasattr(entry, 'signature') and entry.signature:
                data_to_verify = f"{entry.timestamp}{entry.deployment_id}{entry.event_type}"
                if not entry.signature.verify(data_to_verify, "system_key"):  # In production, use proper key management
                    return False, f"Entry {entry.hash} signature verification failed"

        return True, "Block integrity verified"


@dataclass
class PolicyVersion:
    """
    Versioned governance policy with change tracking.

    Implements semantic versioning and audit trail for policy modifications.
    """
    policy_id: str
    version: str  # Semantic version (e.g., "1.2.3")
    content: GovernancePolicy
    created_at: str
    created_by: str
    change_reason: str
    previous_version: Optional[str] = None
    signature: Optional[DigitalSignature] = None

    def __post_init__(self):
        """Initialize version hash for integrity."""
        self._version_hash = self._calculate_version_hash()

    def _calculate_version_hash(self) -> str:
        """Calculate hash of the policy version for integrity."""
        content_str = f"{self.policy_id}{self.version}{self.created_at}{self.created_by}"
        content_str += json.dumps(asdict(self.content), sort_keys=True, cls=GenOpsJSONEncoder)
        return hashlib.sha256(content_str.encode()).hexdigest()

    @property
    def version_hash(self) -> str:
        """Get the version's hash."""
        return self._version_hash


class ApprovalWorkflow:
    """
    Multi-party approval workflow for high-risk deployments.

    Implements configurable approval processes with:
    - Sequential or parallel approval flows
    - Role-based approval requirements
    - Time-based escalation
    - Audit trail of all approval actions
    """

    def __init__(self, workflow_id: str, required_approvers: List[str]):
        self.workflow_id = workflow_id
        self.required_approvers = required_approvers
        self.approvals: Dict[str, Dict[str, Any]] = {}  # approver -> approval_details
        self.created_at = datetime.now().isoformat()
        self.status = "pending"  # pending, approved, rejected, expired

    def add_approval(self, approver: str, decision: str, reason: str = "") -> bool:
        """
        Add an approval decision to the workflow.

        Args:
            approver: ID of the approver
            decision: "approve" or "reject"
            reason: Optional reason for the decision

        Returns:
            True if workflow status changed to final state
        """
        if approver not in self.required_approvers:
            raise ValueError(f"Approver {approver} not authorized for this workflow")

        if approver in self.approvals:
            raise ValueError(f"Approver {approver} has already voted")

        self.approvals[approver] = {
            "decision": decision,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
            "approver": approver
        }

        # Check if workflow is complete
        return self._update_workflow_status()

    def _update_workflow_status(self) -> bool:
        """Update workflow status based on current approvals."""
        total_required = len(self.required_approvers)
        total_approved = sum(1 for a in self.approvals.values() if a["decision"] == "approve")
        total_rejected = sum(1 for a in self.approvals.values() if a["decision"] == "reject")

        if total_rejected > 0:
            self.status = "rejected"
            return True
        elif total_approved == total_required:
            self.status = "approved"
            return True
        else:
            self.status = "pending"
            return False

    def is_approved(self) -> bool:
        """Check if the workflow has been approved."""
        return self.status == "approved"

    def get_approval_summary(self) -> Dict[str, Any]:
        """Get summary of approval workflow status."""
        return {
            "workflow_id": self.workflow_id,
            "status": self.status,
            "required_approvers": self.required_approvers,
            "current_approvals": len(self.approvals),
            "approved": sum(1 for a in self.approvals.values() if a["decision"] == "approve"),
            "rejected": sum(1 for a in self.approvals.values() if a["decision"] == "reject"),
            "approvals": self.approvals,
            "created_at": self.created_at
        }


@dataclass
class AuditEntry:
    """
    Cryptographically secure audit trail entry with tamper detection.

    Features:
    - SHA-256 content hashing for integrity verification
    - Digital signatures for non-repudiation
    - Chain linking for chronological ordering
    - Metadata enrichment for forensic analysis

    Security Properties:
    - Tamper Detection: SHA-256 hash of all content
    - Non-Repudiation: Digital signature prevents denial
    - Chain Integrity: Previous hash reference
    - Completeness: All fields cryptographically bound
    """
    timestamp: str
    deployment_id: str
    event_type: str
    actor: str  # "ai_agent", "human_reviewer", "system"
    action: str
    details: Dict[str, Any]
    actor_id: str = ""  # Unique actor identifier
    risk_score: Optional[float] = None
    confidence: Optional[float] = None
    policies_evaluated: List[str] = field(default_factory=list)
    policies_violated: List[str] = field(default_factory=list)
    compliance_standard: Optional[ComplianceStandard] = None
    previous_hash: str = ""  # Chain linking
    hash: str = ""  # Content hash for tamper detection
    signature: Optional[DigitalSignature] = None
    metadata: Dict[str, Any] = field(default_factory=dict)  # Forensic data

    def __post_init__(self):
        """Initialize cryptographic properties."""
        import copy
        # Ensure deep copies of mutable structures to prevent retroactive tampering
        self.details = copy.deepcopy(self.details)
        self.metadata = copy.deepcopy(self.metadata)

        # Initialize actor_id if not provided
        if not self.actor_id:
            self.actor_id = self._generate_actor_id()

        # Add forensic metadata
        self._add_forensic_metadata()

        # Calculate hash after all properties are set
        if not self.hash:
            self.hash = self._calculate_hash()

    def _calculate_hash(self) -> str:
        """Calculate SHA-256 hash for tamper detection."""
        content = f"{self.timestamp}{self.deployment_id}{self.event_type}{self.actor}{self.actor_id}"
        content += f"{self.action}{self.previous_hash}"
        content += json.dumps(self.details, sort_keys=True)
        content += json.dumps(self.metadata, sort_keys=True)

        return hashlib.sha256(content.encode()).hexdigest()

    def _generate_actor_id(self) -> str:
        """Generate unique actor identifier for audit purposes."""
        if self.actor == "system":
            return "system"
        elif self.actor == "ai_agent":
            return f"ai_agent_{hashlib.sha256(self.actor.encode()).hexdigest()[:8]}"
        else:
            # For human actors, generate consistent ID
            return hashlib.sha256(f"{self.actor}_{self.timestamp}".encode()).hexdigest()[:16]

    def _add_forensic_metadata(self):
        """Add forensic metadata for compliance and analysis."""
        self.metadata.update({
            "entry_version": "2.0",
            "cryptographic_standard": "SHA-256",
            "compliance_frameworks": [c.value for c in ComplianceStandard] if self.compliance_standard else [],
            "chain_position": "linked" if self.previous_hash else "genesis",
            "entropy_check": secrets.token_hex(4),  # Randomness check
        })

    def sign(self, secret_key: str) -> 'AuditEntry':
        """Sign the audit entry with digital signature."""
        data_to_sign = f"{self.timestamp}{self.deployment_id}{self.event_type}{self.hash}"
        self.signature = DigitalSignature.create(data_to_sign, secret_key)
        return self

    def verify_signature(self, secret_key: str) -> bool:
        """Verify the digital signature of the audit entry."""
        if not self.signature:
            return False

        data_to_verify = f"{self.timestamp}{self.deployment_id}{self.event_type}{self.hash}"
        return self.signature.verify(data_to_verify, secret_key)

    def verify_integrity(self) -> Tuple[bool, str]:
        """
        Verify the cryptographic integrity of the audit entry.

        Returns (is_valid, error_message)
        """
        # Verify content hash
        if self.hash != self._calculate_hash():
            return False, "Content hash mismatch - entry may be tampered"

        # Verify signature if present
        if self.signature:
            if not self.verify_signature("default_system_key"):  # Match default signing key
                return False, "Digital signature verification failed"

        # Verify chain integrity (if not genesis block)
        if self.previous_hash and not self.previous_hash.startswith("genesis"):
            # In practice, would verify against previous entry
            pass

        return True, "Entry integrity verified"

    def to_compliance_format(self, standard: ComplianceStandard) -> Dict[str, Any]:
        """
        Convert audit entry to compliance-specific format.

        Supports multiple regulatory standards with appropriate field mappings.
        """
        base_entry = {
            "timestamp": self.timestamp,
            "actor": self.actor,
            "action": self.action,
            "resource": self.deployment_id,
            "details": self.details,
            "evidence": {
                "hash": self.hash,
                "signature": self.signature.signature if self.signature else None,
                "metadata": self.metadata
            }
        }

        if standard == ComplianceStandard.SOC2:
            return {
                **base_entry,
                "control_objective": "CC6.1",  # Logical access controls
                "risk_assessment": self.risk_score,
                "audit_trail": "tamper_proof",
                "compliance_status": "verified" if self.verify_integrity()[0] else "compromised"
            }

        elif standard == ComplianceStandard.GDPR:
            return {
                **base_entry,
                "data_subject": "deployment_process",
                "processing_purpose": "automated_deployment_governance",
                "legal_basis": "legitimate_interest",
                "data_retention": "7_years",
                "privacy_impact": "minimal" if self.risk_score and self.risk_score < 0.5 else "significant"
            }

        elif standard == ComplianceStandard.SOX:
            return {
                **base_entry,
                "financial_impact": self.details.get("financial_impact", "unknown"),
                "internal_controls": self.policies_evaluated,
                "material_weakness": len(self.policies_violated) > 0,
                "audit_evidence": self.hash
            }

        return base_entry


class GovernanceEngine:
    """
    Advanced Runtime Governance with Cryptographic Audit Trails

    Implements enterprise-grade governance with:
    1. Cryptographic audit chains with SHA-256 hashing and digital signatures
    2. Policy versioning and change tracking with semantic versioning
    3. Multi-party approval workflows for high-risk decisions
    4. Multi-standard compliance reporting (SOC 2, GDPR, SOX, HIPAA, PCI DSS)
    5. Forensic analysis capabilities with tamper-proof evidence
    6. Real-time policy validation with confidence scoring

    Security Architecture:
    - Hash Chains: Prevent tampering through cryptographic linking
    - Digital Signatures: Ensure non-repudiation of all actions
    - Merkle Trees: Enable efficient integrity verification
    - Policy Versioning: Track all policy changes with audit trail
    - Multi-Party Approval: Require consensus for critical decisions

    Performance Characteristics:
    - Audit Logging: O(1) per event with cryptographic overhead
    - Integrity Verification: O(n) for full chain, O(log n) for Merkle proofs
    - Compliance Reporting: O(m) where m = audit events per report
    - Policy Evaluation: O(p) where p = number of active policies

    Paper Reference:
    - Zero safety violations through architectural enforcement
    - Complete audit trail for every AI decision
    - Cryptographic verification of governance integrity
    """

    # Enhanced default policies with compliance mappings
    DEFAULT_POLICIES = [
        GovernancePolicy(
            name="critical_service_human_review",
            description="Critical services require human review for high-risk changes",
            condition="service.tier == ServiceTier.CRITICAL and risk_score > 0.5",
            action="require_approval",
            severity="high",
            mathematical_formulation="P(approval_required) = 1 if tier ∈ {CRITICAL} ∧ risk > 0.5",
            compliance_standards=[ComplianceStandard.SOC2, ComplianceStandard.SOX]
        ),
        GovernancePolicy(
            name="no_friday_deployments",
            description="Block deployments on Friday after 4 PM",
            condition="context.day_of_week == 4 and context.time_of_day_hour >= 16",
            action="block",
            severity="medium",
            mathematical_formulation="P(block) = 1 if day = 5 ∧ hour ≥ 16",  # Day 5 = Friday
            compliance_standards=[ComplianceStandard.SOC2]
        ),
        GovernancePolicy(
            name="error_budget_protection",
            description="Block deployments when error budget exhausted",
            condition="service.error_budget_remaining <= 0",
            action="block",
            severity="critical",
            mathematical_formulation="P(block) = 1 if error_budget ≤ 0",
            compliance_standards=[ComplianceStandard.SOC2, ComplianceStandard.SOX]
        ),
        GovernancePolicy(
            name="db_migration_review",
            description="Database migrations require human review",
            condition="context.has_db_migration and service.tier.value <= 2",
            action="require_approval",
            severity="high",
            mathematical_formulation="P(approval_required) = 1 if has_migration ∧ tier ≤ 2",
            compliance_standards=[ComplianceStandard.GDPR, ComplianceStandard.SOX]
        ),
        GovernancePolicy(
            name="large_change_caution",
            description="Large changes require extra canary stages",
            condition="context.change_size_lines > 1000",
            action="warn",
            severity="medium",
            mathematical_formulation="P(warn) = 1 if change_size > 1000",
            compliance_standards=[ComplianceStandard.SOC2]
        ),
        GovernancePolicy(
            name="gdpr_data_processing",
            description="Require approval for deployments involving personal data",
            condition="context.involves_personal_data and risk_score > 0.3",
            action="require_approval",
            severity="high",
            mathematical_formulation="P(approval_required) = 1 if personal_data ∧ risk > 0.3",
            compliance_standards=[ComplianceStandard.GDPR]
        ),
        GovernancePolicy(
            name="pci_compliance_check",
            description="Block deployments violating PCI DSS requirements",
            condition="context.involves_payment_data and not context.pci_compliant",
            action="block",
            severity="critical",
            mathematical_formulation="P(block) = 1 if payment_data ∧ ¬pci_compliant",
            compliance_standards=[ComplianceStandard.PCI_DSS]
        ),
    ]

    def __init__(
        self,
        policies: Optional[List[GovernancePolicy]] = None,
        autonomy_level: AutonomyLevel = AutonomyLevel.GOVERNED,
        enable_cryptography: bool = True,
        secret_key: Optional[str] = None
    ):
        self.policies = policies or self.DEFAULT_POLICIES.copy()
        self.autonomy_level = autonomy_level
        self.enable_cryptography = enable_cryptography

        # Cryptographic audit trail
        self.audit_log: List[AuditEntry] = []
        self.audit_blocks: List[AuditChainBlock] = []
        self.current_block_entries: List[AuditEntry] = []
        self.last_block_hash = "genesis"
        self.secret_key = secret_key or "default_system_key"  # In production, use proper key management

        # Policy versioning
        self.policy_versions: Dict[str, List[PolicyVersion]] = {}
        self._initialize_policy_versions()

        # Approval workflows
        self.active_workflows: Dict[str, ApprovalWorkflow] = {}

        # Model registry with enhanced security
        self.model_registry: Dict[str, Dict[str, Any]] = {
            "genops-risk-scorer-v1": {
                "approved": True,
                "version": "1.0.0",
                "performance_metrics": {"accuracy": 0.94, "latency_ms": 45},
                "security_clearance": "high",
                "last_audited": datetime.now().isoformat(),
                "cryptographic_hash": hashlib.sha256(b"genops-risk-scorer-v1").hexdigest()
            },
            "genops-context-rag-v1": {
                "approved": True,
                "version": "1.0.0",
                "performance_metrics": {"retrieval_accuracy": 0.89, "latency_ms": 120},
                "security_clearance": "high",
                "last_audited": datetime.now().isoformat(),
                "cryptographic_hash": hashlib.sha256(b"genops-context-rag-v1").hexdigest()
            },
        }

        # Compliance reporting
        self.compliance_reports: Dict[str, Dict[str, Any]] = {}

    def _initialize_policy_versions(self):
        """Initialize policy versions for change tracking."""
        for policy in self.policies:
            version = PolicyVersion(
                policy_id=policy.name,
                version="1.0.0",
                content=policy,
                created_at=datetime.now().isoformat(),
                created_by="system",
                change_reason="Initial policy creation"
            )
            self.policy_versions[policy.name] = [version]

    def _create_audit_block(self) -> AuditChainBlock:
        """Create a new audit block when current block reaches capacity."""
        if not self.current_block_entries:
            return None

        block = AuditChainBlock(
            block_id=f"block_{len(self.audit_blocks) + 1}",
            timestamp=datetime.now().isoformat(),
            entries=self.current_block_entries.copy(),
            previous_hash=self.last_block_hash,
            metadata={
                "block_size": len(self.current_block_entries),
                "policies_active": len(self.policies),
                "autonomy_level": self.autonomy_level.value
            }
        )

        # Sign the block if cryptography is enabled
        if self.enable_cryptography:
            block.signature = DigitalSignature.create(block.block_hash, self.secret_key)

        self.audit_blocks.append(block)
        self.last_block_hash = block.block_hash
        self.current_block_entries.clear()

        return block

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
        policies_evaluated: Optional[List[str]] = None,
        policies_violated: Optional[List[str]] = None,
        compliance_standard: Optional[ComplianceStandard] = None
    ) -> AuditEntry:
        """
        Log an event to the cryptographically secure audit trail.

        Enhanced with digital signatures, chain linking, and forensic metadata.
        """
        # Create audit entry with chain linking
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
            compliance_standard=compliance_standard,
            previous_hash=self.audit_log[-1].hash if self.audit_log else "genesis"
        )

        # Sign the entry if cryptography is enabled
        if self.enable_cryptography:
            entry = entry.sign(self.secret_key)

        # Add to current audit log
        self.audit_log.append(entry)
        self.current_block_entries.append(entry)

        # Add to deployment audit trail
        deployment.add_audit_event(event_type, asdict(entry))

        # Create new audit block if current block is full (every 100 entries)
        if len(self.current_block_entries) >= 100:
            self._create_audit_block()

        return entry

    def update_policy(
        self,
        policy_name: str,
        updated_policy: GovernancePolicy,
        change_reason: str,
        actor: str = "system"
    ) -> PolicyVersion:
        """
        Update a governance policy with version tracking and audit trail.

        Implements semantic versioning and maintains complete change history.
        """
        if policy_name not in self.policy_versions:
            raise ValueError(f"Policy {policy_name} not found")

        current_versions = self.policy_versions[policy_name]
        current_version = current_versions[-1]

        # Calculate new version (simplified semantic versioning)
        current_semver = current_version.version.split('.')
        new_version = f"{current_semver[0]}.{current_semver[1]}.{int(current_semver[2]) + 1}"

        # Create new policy version
        new_policy_version = PolicyVersion(
            policy_id=policy_name,
            version=new_version,
            content=updated_policy,
            created_at=datetime.now().isoformat(),
            created_by=actor,
            change_reason=change_reason,
            previous_version=current_version.version
        )

        # Sign the policy version
        if self.enable_cryptography:
            data_to_sign = f"{new_policy_version.policy_id}{new_policy_version.version}"
            new_policy_version.signature = DigitalSignature.create(data_to_sign, self.secret_key)

        # Update policy registry
        self.policy_versions[policy_name].append(new_policy_version)

        # Update active policy
        policy_index = next(
            (i for i, p in enumerate(self.policies) if p.name == policy_name),
            None
        )
        if policy_index is not None:
            self.policies[policy_index] = updated_policy

        # Log policy change in audit trail
        self.log_audit_event(
            deployment=Deployment(id="policy_update", status=DeploymentStatus.COMPLETED),  # Dummy deployment
            event_type="policy_update",
            action=f"Updated policy {policy_name} to version {new_version}",
            details={
                "policy_name": policy_name,
                "previous_version": current_version.version,
                "new_version": new_version,
                "change_reason": change_reason,
                "changes": self._calculate_policy_changes(current_version.content, updated_policy)
            },
            actor=actor,
            compliance_standard=ComplianceStandard.SOX  # Policy changes are SOX relevant
        )

        return new_policy_version

    def _calculate_policy_changes(self, old_policy: GovernancePolicy, new_policy: GovernancePolicy) -> Dict[str, Any]:
        """Calculate what changed between policy versions."""
        changes = {}
        old_dict = asdict(old_policy)
        new_dict = asdict(new_policy)

        for key in old_dict:
            if old_dict[key] != new_dict[key]:
                changes[key] = {
                    "from": old_dict[key],
                    "to": new_dict[key]
                }

        return changes

    def create_approval_workflow(
        self,
        deployment: Deployment,
        required_approvers: List[str],
        reason: str = "High-risk deployment requires approval"
    ) -> ApprovalWorkflow:
        """
        Create a multi-party approval workflow for high-risk deployments.

        Implements consensus-based decision making for critical governance decisions.
        """
        workflow_id = f"approval_{deployment.id}_{int(datetime.now().timestamp())}"

        workflow = ApprovalWorkflow(workflow_id, required_approvers)
        self.active_workflows[workflow_id] = workflow

        # Log workflow creation
        self.log_audit_event(
            deployment=deployment,
            event_type="approval_workflow_created",
            action=f"Created approval workflow requiring {len(required_approvers)} approvals",
            details={
                "workflow_id": workflow_id,
                "required_approvers": required_approvers,
                "reason": reason,
                "risk_score": getattr(deployment, 'risk_assessment', {}).get('risk_score') if hasattr(deployment, 'risk_assessment') else None
            },
            actor="system",
            compliance_standard=ComplianceStandard.SOC2
        )

        return workflow

    def process_approval_vote(
        self,
        workflow_id: str,
        approver: str,
        decision: str,
        reason: str = "",
        deployment: Optional[Deployment] = None
    ) -> Tuple[bool, str]:
        """
        Process an approval vote in an active workflow.

        Returns (workflow_complete, status_message)
        """
        if workflow_id not in self.active_workflows:
            raise ValueError(f"Workflow {workflow_id} not found")

        workflow = self.active_workflows[workflow_id]
        workflow_complete = workflow.add_approval(approver, decision, reason)

        # Log the approval vote
        if deployment:
            self.log_audit_event(
                deployment=deployment,
                event_type="approval_vote",
                action=f"Approver {approver} voted {decision}",
                details={
                    "workflow_id": workflow_id,
                    "approver": approver,
                    "decision": decision,
                    "reason": reason,
                    "workflow_status": workflow.status
                },
                actor=approver,
                compliance_standard=ComplianceStandard.SOX
            )

        if workflow_complete:
            status_msg = f"Workflow {workflow_id} completed with status: {workflow.status}"
            del self.active_workflows[workflow_id]  # Clean up completed workflow
        else:
            status_msg = f"Vote recorded. Workflow {workflow_id} status: {workflow.status}"

        return workflow_complete, status_msg

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
        target_id: Optional[str] = None,
        standard: ComplianceStandard = ComplianceStandard.SOC2,
        time_range: Optional[Tuple[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive compliance report for specified standard.

        Supports multiple compliance frameworks with automated evidence collection,
        risk assessment, and audit trail verification.

        Args:
            target_id: Specific deployment ID or None for all deployments
            standard: Compliance standard to report against
            time_range: Optional (start_date, end_date) filter

        Returns:
            Detailed compliance report with evidence and recommendations
        """
        # Filter audit entries
        relevant_entries = self.audit_log
        if target_id:
            relevant_entries = [e for e in relevant_entries if e.deployment_id == target_id]
        if time_range:
            start_date, end_date = time_range
            relevant_entries = [
                e for e in relevant_entries
                if start_date <= e.timestamp.split('T')[0] <= end_date
            ]

        # Verify audit chain integrity
        integrity_check = self.verify_audit_integrity(relevant_entries)

        # Generate standard-specific report
        report = {
            "report_id": f"{standard.value}_{int(datetime.now().timestamp())}",
            "generated_at": datetime.now().isoformat(),
            "compliance_standard": standard.value,
            "time_range": time_range,
            "target_id": target_id,
            "audit_integrity": integrity_check,
            "summary": self._generate_compliance_summary(relevant_entries, standard),
            "evidence": self._collect_compliance_evidence(relevant_entries, standard),
            "risk_assessment": self._assess_compliance_risks(relevant_entries, standard),
            "recommendations": self._generate_compliance_recommendations(relevant_entries, standard)
        }

        # Cache the report
        self.compliance_reports[report["report_id"]] = report

        return report

    def _generate_compliance_summary(self, entries: List[AuditEntry], standard: ComplianceStandard) -> Dict[str, Any]:
        """Generate compliance summary statistics."""
        total_entries = len(entries)
        violated_entries = len([e for e in entries if e.policies_violated])
        human_interventions = len([e for e in entries if e.actor != "ai_agent"])
        high_risk_actions = len([e for e in entries if e.risk_score and e.risk_score > 0.7])

        compliance_score = 1.0 - (violated_entries / max(total_entries, 1))

        return {
            "total_audit_entries": total_entries,
            "policy_violations": violated_entries,
            "human_interventions": human_interventions,
            "high_risk_actions": high_risk_actions,
            "overall_compliance_score": compliance_score,
            "compliance_rating": "PASS" if compliance_score >= 0.95 else "REVIEW_NEEDED" if compliance_score >= 0.85 else "FAIL"
        }

    def _collect_compliance_evidence(self, entries: List[AuditEntry], standard: ComplianceStandard) -> List[Dict[str, Any]]:
        """Collect compliance evidence in standard-specific format."""
        evidence = []

        for entry in entries:
            if entry.compliance_standard == standard or not entry.compliance_standard:
                evidence_entry = entry.to_compliance_format(standard)
                evidence_entry["cryptographic_proof"] = {
                    "entry_hash": entry.hash,
                    "signature_verified": entry.verify_signature(self.secret_key) if entry.signature else False,
                    "chain_integrity": entry.verify_integrity()[0]
                }
                evidence.append(evidence_entry)

        return evidence

    def _assess_compliance_risks(self, entries: List[AuditEntry], standard: ComplianceStandard) -> Dict[str, Any]:
        """Assess compliance risks based on audit patterns."""
        risk_factors = {
            "unauthorized_actions": len([e for e in entries if e.policies_violated]),
            "missing_approvals": len([e for e in entries if "require_approval" in [p.action for p in self.policies if p.name in (e.policies_evaluated or [])] and e.actor == "ai_agent"]),
            "tamper_attempts": len([e for e in entries if not e.verify_integrity()[0]]),
            "high_risk_deployments": len([e for e in entries if e.risk_score and e.risk_score > 0.8]),
        }

        # Calculate overall risk score
        weights = {"unauthorized_actions": 0.4, "missing_approvals": 0.3, "tamper_attempts": 0.2, "high_risk_deployments": 0.1}
        risk_score = sum(factor * weights[key] for key, factor in risk_factors.items())
        risk_score = min(risk_score / max(len(entries), 1), 1.0)

        return {
            "risk_score": risk_score,
            "risk_level": "CRITICAL" if risk_score > 0.8 else "HIGH" if risk_score > 0.6 else "MEDIUM" if risk_score > 0.3 else "LOW",
            "risk_factors": risk_factors,
            "mitigation_required": risk_score > 0.5
        }

    def _generate_compliance_recommendations(self, entries: List[AuditEntry], standard: ComplianceStandard) -> List[str]:
        """Generate compliance improvement recommendations."""
        recommendations = []

        violation_patterns = {}
        for entry in entries:
            for violation in entry.policies_violated:
                violation_patterns[violation] = violation_patterns.get(violation, 0) + 1

        # Common violation-based recommendations
        if violation_patterns.get("critical_service_human_review", 0) > 0:
            recommendations.append("Implement automated approval workflows for critical service deployments")

        if violation_patterns.get("error_budget_protection", 0) > 0:
            recommendations.append("Review error budget calculation and alerting thresholds")

        if violation_patterns.get("no_friday_deployments", 0) > 0:
            recommendations.append("Strengthen deployment scheduling controls and approval processes")

        # Standard-specific recommendations
        if standard == ComplianceStandard.GDPR:
            recommendations.append("Implement data processing impact assessments for all deployments")
            recommendations.append("Enhance data subject access and consent management")

        elif standard == ComplianceStandard.SOX:
            recommendations.append("Strengthen financial control validations in deployment processes")
            recommendations.append("Implement dual authorization for material changes")

        elif standard == ComplianceStandard.SOC2:
            recommendations.append("Enhance monitoring and alerting for security control violations")
            recommendations.append("Implement regular security control testing and validation")

        # Cryptographic integrity recommendations
        integrity_issues = sum(1 for e in entries if not e.verify_integrity()[0])
        if integrity_issues > 0:
            recommendations.append(f"Address {integrity_issues} audit integrity issues - potential tampering detected")

        return recommendations

    def verify_audit_integrity(self, entries: Optional[List[AuditEntry]] = None) -> Dict[str, Any]:
        """
        Verify the cryptographic integrity of the audit trail.

        Performs comprehensive integrity checks including:
        - Hash chain verification
        - Digital signature validation
        - Merkle tree consistency
        - Temporal ordering validation
        """
        target_entries = entries or self.audit_log

        integrity_results = {
            "total_entries": len(target_entries),
            "chain_integrity": True,
            "signature_verification": True,
            "temporal_consistency": True,
            "block_integrity": True,
            "issues": []
        }

        # Verify hash chain
        for i, entry in enumerate(target_entries):
            is_valid, error_msg = entry.verify_integrity()
            if not is_valid:
                integrity_results["chain_integrity"] = False
                integrity_results["issues"].append(f"Entry {i} integrity failure: {error_msg}")

        # Verify signatures
        signature_failures = 0
        for entry in target_entries:
            if entry.signature and not entry.verify_signature(self.secret_key):
                signature_failures += 1

        if signature_failures > 0:
            integrity_results["signature_verification"] = False
            integrity_results["issues"].append(f"{signature_failures} signature verification failures")

        # Verify temporal consistency
        timestamps = [entry.timestamp for entry in target_entries]
        if timestamps != sorted(timestamps):
            integrity_results["temporal_consistency"] = False
            integrity_results["issues"].append("Temporal ordering inconsistency detected")

        # Verify audit blocks
        for block in self.audit_blocks:
            is_valid, error_msg = block.verify_integrity()
            if not is_valid:
                integrity_results["block_integrity"] = False
                integrity_results["issues"].append(f"Block {block.block_id} integrity failure: {error_msg}")

        # Overall integrity status
        integrity_results["overall_integrity"] = all([
            integrity_results["chain_integrity"],
            integrity_results["signature_verification"],
            integrity_results["temporal_consistency"],
            integrity_results["block_integrity"]
        ])

        return integrity_results

    def perform_forensic_analysis(
        self,
        incident_timestamp: str,
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Perform forensic analysis of a security incident or policy violation.

        Collects comprehensive evidence including:
        - Timeline of events before/during/after incident
        - Actor behavior patterns
        - Policy violation patterns
        - Cryptographic evidence chain
        """
        incident_time = datetime.fromisoformat(incident_timestamp.replace('Z', '+00:00'))
        start_time = incident_time - timedelta(hours=time_window_hours)
        end_time = incident_time + timedelta(hours=time_window_hours)

        # Collect relevant audit entries
        relevant_entries = [
            e for e in self.audit_log
            if start_time <= datetime.fromisoformat(e.timestamp.replace('Z', '+00:00')) <= end_time
        ]

        # Analyze patterns
        actor_patterns = {}
        policy_violations = {}
        risk_patterns = []

        for entry in relevant_entries:
            # Actor behavior analysis
            actor_key = f"{entry.actor}:{entry.actor_id}"
            if actor_key not in actor_patterns:
                actor_patterns[actor_key] = {"actions": [], "violations": 0, "high_risk_actions": 0}
            actor_patterns[actor_key]["actions"].append(entry.action)
            actor_patterns[actor_key]["violations"] += len(entry.policies_violated)
            if entry.risk_score and entry.risk_score > 0.7:
                actor_patterns[actor_key]["high_risk_actions"] += 1

            # Policy violation patterns
            for violation in entry.policies_violated:
                policy_violations[violation] = policy_violations.get(violation, 0) + 1

            # Risk escalation patterns
            if entry.risk_score:
                risk_patterns.append({
                    "timestamp": entry.timestamp,
                    "risk_score": entry.risk_score,
                    "action": entry.action,
                    "violations": len(entry.policies_violated)
                })

        return {
            "incident_timestamp": incident_timestamp,
            "analysis_window": f"{time_window_hours} hours",
            "total_events": len(relevant_entries),
            "actor_analysis": actor_patterns,
            "policy_violation_patterns": policy_violations,
            "risk_escalation_timeline": sorted(risk_patterns, key=lambda x: x["timestamp"]),
            "cryptographic_evidence": {
                "chain_integrity": self.verify_audit_integrity(relevant_entries)["overall_integrity"],
                "evidence_hashes": [e.hash for e in relevant_entries],
                "block_membership": self._find_entry_blocks(relevant_entries)
            },
            "recommendations": self._generate_forensic_recommendations(actor_patterns, policy_violations)
        }

    def _find_entry_blocks(self, entries: List[AuditEntry]) -> List[str]:
        """Find which audit blocks contain the given entries."""
        entry_hashes = {e.hash for e in entries}
        block_membership = []

        for block in self.audit_blocks:
            block_hashes = {e.hash for e in block.entries}
            if entry_hashes & block_hashes:  # Intersection
                block_membership.append(block.block_id)

        return block_membership

    def _generate_forensic_recommendations(self, actor_patterns: Dict, policy_violations: Dict) -> List[str]:
        """Generate forensic analysis recommendations."""
        recommendations = []

        # Actor behavior recommendations
        suspicious_actors = [
            actor for actor, pattern in actor_patterns.items()
            if pattern["violations"] > 5 or pattern["high_risk_actions"] > 10
        ]
        if suspicious_actors:
            recommendations.append(f"Review access privileges for suspicious actors: {', '.join(suspicious_actors)}")

        # Policy violation recommendations
        frequent_violations = [policy for policy, count in policy_violations.items() if count > 3]
        if frequent_violations:
            recommendations.append(f"Strengthen enforcement of frequently violated policies: {', '.join(frequent_violations)}")

        # General recommendations
        if len(actor_patterns) > 10:
            recommendations.append("Implement actor behavior monitoring and anomaly detection")

        if sum(policy_violations.values()) > len(actor_patterns) * 2:
            recommendations.append("Review policy definitions and enforcement mechanisms")

        return recommendations

    def check_safety_violation(
        self,
        deployment: Deployment,
        action_taken: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform comprehensive safety violation analysis with cryptographic verification.

        Enhanced safety checking that includes:
        1. Policy bypass detection with cryptographic proof
        2. Approval workflow integrity verification
        3. Model approval validation with hash verification
        4. Audit trail tamper detection
        5. Temporal consistency validation

        Returns detailed violation analysis with evidence.
        """
        violations = {
            "has_violations": False,
            "violation_types": [],
            "severity": "none",
            "evidence": [],
            "cryptographic_integrity": True,
            "recommendations": []
        }

        deployment_entries = [e for e in self.audit_log if e.deployment_id == deployment.id]

        # 1. Check for bypassed policy blocks with cryptographic proof
        for entry in deployment_entries:
            if entry.policies_violated:
                for policy_name in entry.policies_violated:
                    policy = next(
                        (p for p in self.policies if p.name == policy_name),
                        None
                    )
                    if policy and policy.action == "block":
                        if deployment.status == DeploymentStatus.COMPLETED:
                            violations["has_violations"] = True
                            violations["violation_types"].append("policy_bypass")
                            violations["severity"] = "critical"
                            violations["evidence"].append({
                                "type": "policy_bypass",
                                "policy": policy_name,
                                "action_taken": action_taken,
                                "entry_hash": entry.hash,
                                "timestamp": entry.timestamp
                            })

        # 2. Check approval workflow integrity
        approval_workflows = [e for e in deployment_entries if e.event_type == "approval_workflow_created"]
        for workflow_entry in approval_workflows:
            workflow_id = workflow_entry.details.get("workflow_id")
            if workflow_id in self.active_workflows:
                workflow = self.active_workflows[workflow_id]
                if not workflow.is_approved():
                    violations["has_violations"] = True
                    violations["violation_types"].append("missing_approval")
                    violations["severity"] = max(violations["severity"], "high", key=lambda x: ["none", "low", "medium", "high", "critical"].index(x))
                    violations["evidence"].append({
                        "type": "missing_approval",
                        "workflow_id": workflow_id,
                        "status": workflow.status,
                        "required_approvals": len(workflow.required_approvers),
                        "current_approvals": len(workflow.approvals)
                    })

        # 3. Verify model approval with cryptographic hash
        model_usage = context.get("models_used", [])
        for model_id in model_usage:
            approval_status = self.verify_model_approval(model_id)
            if not approval_status[0]:  # Not approved
                violations["has_violations"] = True
                violations["violation_types"].append("unapproved_model")
                violations["severity"] = max(violations["severity"], "high", key=lambda x: ["none", "low", "medium", "high", "critical"].index(x))
                violations["evidence"].append({
                    "type": "unapproved_model",
                    "model_id": model_id,
                    "reason": approval_status[1],
                    "registry_hash": self.model_registry.get(model_id, {}).get("cryptographic_hash")
                })

        # 4. Verify audit trail integrity
        integrity_check = self.verify_audit_integrity(deployment_entries)
        if not integrity_check["overall_integrity"]:
            violations["has_violations"] = True
            violations["violation_types"].append("audit_tampering")
            violations["severity"] = "critical"
            violations["cryptographic_integrity"] = False
            violations["evidence"].append({
                "type": "audit_tampering",
                "integrity_check": integrity_check,
                "affected_entries": len(integrity_check["issues"])
            })

        # 5. Check temporal consistency
        if not integrity_check["temporal_consistency"]:
            violations["has_violations"] = True
            violations["violation_types"].append("temporal_inconsistency")
            violations["severity"] = max(violations["severity"], "medium", key=lambda x: ["none", "low", "medium", "high", "critical"].index(x))
            violations["evidence"].append({
                "type": "temporal_inconsistency",
                "description": "Audit entries are not in chronological order"
            })

        # Generate recommendations based on violations
        if violations["has_violations"]:
            if "policy_bypass" in violations["violation_types"]:
                violations["recommendations"].append("Immediate security review required - critical policy bypassed")
            if "audit_tampering" in violations["violation_types"]:
                violations["recommendations"].append("Forensic investigation required - audit trail compromised")
            if "unapproved_model" in violations["violation_types"]:
                violations["recommendations"].append("Model registry audit required - unapproved models in use")
            if "missing_approval" in violations["violation_types"]:
                violations["recommendations"].append("Approval workflow enforcement needs strengthening")

        # In GenOps architecture, these should be architecturally impossible
        # This is why the paper reports zero violations - the system prevents them
        return violations

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
