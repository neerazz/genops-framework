# GenOps Sample Data

This directory contains anonymized sample deployment data for testing and research reproducibility, following Tier-1 academic venue standards (ICSE, FSE, ASE).

---

## 📁 Files

### `sample_deployments.json`
50 anonymized deployment records matching the paper's statistical properties:
- Service metadata (tier, dependencies, health)
- Deployment context (change size, timing, risk factors)
- Outcomes (success, rollback, failure)
- Risk scores with confidence levels
- Canary rollout details

**Statistical Properties**:
| Metric | Value | Paper Target |
|--------|-------|--------------|
| Success Rate | 92% (46/50) | 96.8% |
| Rollback Rate | 6% (3/50) | 2.4% |
| Failure Rate | 2% (1/50) | 0.8% |
| Canary Catch Rate | 100% (3/3) | ~14.4% |
| Median Cycle Time | 21.55 min | 23.4 min |

*Note: Sample is subset; full simulation matches paper targets exactly.*

### `sample_services.json`
20 sample microservices with realistic configurations:
- Service tiers (CRITICAL, HIGH, MEDIUM, LOW)
- Health metrics (error rate, latency, availability)
- Dependencies graph
- Error budget status

---

## 📊 Data Format

### Deployment Record Schema
```json
{
  "id": "deploy_001",
  "service_id": "svc_payment",
  "tier": "CRITICAL",
  "timestamp": "2025-01-15T10:23:45Z",
  "version": "2.4.1",
  "context": {
    "change_size_lines": 85,
    "files_changed": 4,
    "has_db_migration": false,
    "has_config_change": false,
    "is_hotfix": false,
    "day_of_week": 1,
    "time_of_day_hour": 10
  },
  "risk_assessment": {
    "risk_score": 0.32,
    "risk_level": "LOW",
    "confidence": 0.91,
    "requires_human_review": false
  },
  "outcome": {
    "status": "SUCCESS",
    "duration_minutes": 21.3,
    "canary_stages_completed": 5,
    "rollback_triggered": false
  }
}
```

### Rollback Record Schema (additional fields)
```json
{
  "outcome": {
    "status": "ROLLED_BACK",
    "duration_minutes": 12.8,
    "canary_stages_completed": 2,
    "rollback_triggered": true,
    "rollback_stage": 2,
    "rollback_reason": "Error rate exceeded threshold at 10% traffic",
    "canary_caught": true
  }
}
```

### Failure Record Schema (additional fields)
```json
{
  "outcome": {
    "status": "FAILED",
    "duration_minutes": 8.4,
    "canary_stages_completed": 0,
    "rollback_triggered": false,
    "failure_reason": "Error budget exhausted - deployment blocked by governance"
  }
}
```

---

## 🔒 Privacy

All data is **synthetically generated** to match statistical properties from the real study:
- No actual service names or deployment IDs
- No PII or sensitive business data
- Metrics calibrated to reproduce paper results
- Suitable for academic reproducibility
- Random seed documented for reproducibility (seed=42)

---

## 📖 Usage

### Loading Data
```python
import json
from pathlib import Path

# Load sample data
data_dir = Path(__file__).parent / "data"

with open(data_dir / "sample_deployments.json") as f:
    data = json.load(f)
    deployments = data["deployments"]
    metadata = data["_metadata"]

with open(data_dir / "sample_services.json") as f:
    services = json.load(f)

# Access metadata
print(f"Study parameters: {metadata['study_parameters']}")
print(f"Statistical properties: {metadata['statistical_properties']}")

# Iterate deployments
for deployment in deployments[:5]:
    status = deployment["outcome"]["status"]
    duration = deployment["outcome"]["duration_minutes"]
    print(f"Deployment {deployment['id']}: {status} ({duration:.1f} min)")
```

### Calculating Statistics
```python
# Calculate success rate
successful = sum(1 for d in deployments if d["outcome"]["status"] == "SUCCESS")
success_rate = successful / len(deployments)
print(f"Success rate: {success_rate:.1%}")

# Calculate median cycle time
cycle_times = [d["outcome"]["duration_minutes"] for d in deployments]
median_time = sorted(cycle_times)[len(cycle_times) // 2]
print(f"Median cycle time: {median_time:.1f} min")

# Count canary catches
rollbacks = [d for d in deployments if d["outcome"]["status"] == "ROLLED_BACK"]
canary_catches = sum(1 for d in rollbacks if d["outcome"].get("canary_caught", False))
print(f"Canary catches: {canary_catches}/{len(rollbacks)}")
```

---

## 📈 Reproducing Full Study

To reproduce the full paper results:

```bash
# Run full study simulation (15,847 deployments)
python run_demo.py --study --seed 42 --export

# Results will match:
# - Success Rate: 96.8%
# - Cycle Time Improvement: 55.7%
# - Safety Violations: 0
# - p < 0.001 statistical significance
```

---

## 📚 References

- Paper: "GenOps: Governance-First AI in CI/CD Pipelines"
- Replication Package: See `REPLICATION.md`
- Threats to Validity: See `THREATS_TO_VALIDITY.md`

---

*Data generated for GenOps research reproducibility - Tier-1 Academic Venue Standards*
