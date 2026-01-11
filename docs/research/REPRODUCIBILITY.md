# GenOps Framework - Reproducibility Guide

*Version 2.0.0 - Research Paper Implementation*

This document provides comprehensive instructions for reproducing the GenOps framework results, setting up development environments, and deploying the system in production. All procedures are designed to ensure scientific reproducibility and production reliability.

## Table of Contents

1. [Quick Start](#quick-start)
2. [System Requirements](#system-requirements)
3. [Environment Setup](#environment-setup)
4. [Data Setup](#data-setup)
5. [Running Experiments](#running-experiments)
6. [Reproducing Paper Results](#reproducing-paper-results)
7. [Development Setup](#development-setup)
8. [Production Deployment](#production-deployment)
9. [Troubleshooting](#troubleshooting)
10. [Contributing](#contributing)

## Quick Start

```bash
# Clone the repository
git clone git@github.com:neerazz/genops-framework.git
cd genops-framework

# Setup environment
make setup

# Run paper validation
make validate-paper

# View results
make show-results
```

## System Requirements

### Hardware Requirements

| Component | Minimum | Recommended | Paper Validation |
|-----------|---------|-------------|------------------|
| CPU | 4 cores | 8+ cores | 16 cores (AMD Ryzen 9) |
| RAM | 8GB | 16GB | 32GB DDR4 |
| Storage | 50GB SSD | 100GB SSD | 500GB NVMe SSD |
| Network | 10Mbps | 100Mbps | 1Gbps |

### Software Requirements

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.9+ | Core runtime |
| SQLite | 3.35+ | Default database |
| Docker | 20.10+ | Containerization |
| Make | 4.3+ | Build automation |
| Git | 2.30+ | Version control |

### Supported Platforms

- **Linux**: Ubuntu 20.04+, CentOS 8+, RHEL 8+
- **macOS**: 11.0+ (Intel/Apple Silicon)
- **Windows**: 10+ (WSL2 recommended)
- **Containers**: Docker, Podman, Kubernetes

## Environment Setup

### Automated Setup (Recommended)

```bash
# Using Make (Linux/macOS)
make setup

# Using PowerShell (Windows)
.\\scripts\\setup.ps1

# Using Docker
docker build -t genops-framework .
docker run -it genops-framework
```

### Manual Setup

#### 1. Python Environment

```bash
# Create virtual environment
python -m venv genops_env
source genops_env/bin/activate  # Linux/macOS
# genops_env\\Scripts\\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

#### 2. System Dependencies

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y build-essential python3-dev sqlite3

# macOS
brew install sqlite python@3.9

# CentOS/RHEL
sudo yum install -y gcc python39-devel sqlite
```

#### 3. Configuration

```bash
# Copy default configuration
cp config/default.yaml config/local.yaml

# Edit configuration for your environment
vim config/local.yaml
```

### Environment Variables

```bash
# Required
export GENOPS_ENV=development
export GENOPS_DATABASE_URL=sqlite:///genops.db

# Optional
export GENOPS_LOG_LEVEL=INFO
export GENOPS_CACHE_SIZE=10000
export GENOPS_MAX_WORKERS=4
```

## Data Setup

### Synthetic Data Generation

The framework includes comprehensive synthetic data generators for reproducible testing:

```bash
# Generate paper-scale dataset (15,847 deployments)
python -m genops.data.generate_paper_dataset

# Generate custom dataset
python -c "
from genops.data import DataGenerator
generator = DataGenerator()
data = generator.generate_deployments(n=1000, seed=42)
generator.save_to_disk(data, 'custom_dataset.json')
"
```

### Real Data Import

```python
from genops.data import DataImporter

# Import from CSV
importer = DataImporter()
deployments = importer.from_csv('historical_deployments.csv')
importer.save_to_database(deployments)

# Import from JSON
deployments = importer.from_json('deployments.json')
importer.validate_and_import(deployments)
```

### Database Schema Setup

```bash
# Initialize database
python -m genops.persistence init-db

# Run migrations
python -m genops.persistence migrate

# Seed with test data
python -m genops.persistence seed --dataset=paper
```

## Running Experiments

### Paper Validation Experiments

```bash
# Run complete paper validation (15,847 deployments)
python -m genops.experiments validate-paper

# Run specific experiment
python -m genops.experiments run --config=experiments/risk_scoring.json

# Run with custom parameters
python -m genops.experiments run \
    --sample-size=10000 \
    --statistical-power=0.95 \
    --random-seed=42
```

### Custom Experiments

```python
from genops.experiments import ExperimentRunner, StudyConfiguration

# Configure custom study
config = StudyConfiguration(
    name="custom_study",
    hypothesis="Custom hypothesis",
    sample_size=5000,
    random_seed=123
)

# Run experiment
runner = ExperimentRunner(config)
results = runner.run_full_study()

# Analyze results
print(f"Success Rate: {results.success_rate:.3f}")
print(f"Claims Validated: {sum(results.claims_validated.values())}/6")
```

### Performance Benchmarking

```bash
# Run performance benchmarks
python -m genops.benchmarks run-all

# Run specific benchmark
python -m genops.benchmarks risk-calculation --iterations=10000

# Generate performance report
python -m genops.benchmarks report --format=markdown
```

## Reproducing Paper Results

### Exact Replication

```bash
# Set exact paper parameters
export GENOPS_PAPER_MODE=true
export GENOPS_SAMPLE_SIZE=15847
export GENOPS_RANDOM_SEED=42
export GENOPS_STATISTICAL_POWER=0.95

# Run paper validation
make reproduce-paper

# Verify results match paper claims
python scripts/verify_paper_claims.py
```

### Expected Results

| Metric | Paper Claim | Validation Range | Status |
|--------|-------------|------------------|---------|
| Safety Violations | 0 | [0, 0] | ✅ |
| Success Rate | 96.8% | [96.0%, 97.5%] | ✅ |
| Cycle Time Improvement | 55.7% | [52.0%, 59.0%] | ✅ |
| Canary Catch Rate | 14.4% | [12.0%, 17.0%] | ✅ |
| Risk Calc Latency (P95) | <5ms | [<4.5ms, <5.5ms] | ✅ |

### Statistical Validation

```python
from genops.experiments import StatisticalValidator

# Load experimental results
results = load_results('paper_validation_run.json')

# Validate all claims
validator = StatisticalValidator()
validation = validator.validate_claims(results)

print("Paper Claims Validation:")
for claim, valid in validation.items():
    status = "VALIDATED" if valid else "FAILED"
    print(f"  {claim}: {status}")
```

## Development Setup

### Local Development

```bash
# Clone and setup
git clone git@github.com:neerazz/genops-framework.git
cd genops-framework

# Install in development mode
pip install -e .

# Run tests
make test

# Run linting
make lint

# Generate documentation
make docs
```

### IDE Setup

#### VS Code
```json
{
    "python.defaultInterpreterPath": "./genops_env/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black",
    "editor.formatOnSave": true
}
```

#### PyCharm
- Set Python interpreter to virtual environment
- Enable pytest as test runner
- Configure black as code formatter
- Enable mypy type checking

### Testing

```bash
# Run all tests
make test

# Run with coverage
make test-coverage

# Run specific test module
pytest tests/test_models.py -v

# Run property-based tests
pytest tests/test_models.py::TestServiceModel::test_service_health_property_based -v
```

## Production Deployment

### Docker Deployment

```bash
# Build production image
docker build -t genops-framework:latest -f Dockerfile.prod .

# Run with production config
docker run -d \
    --name genops-prod \
    -p 8000:8000 \
    -v /data/genops:/app/data \
    -e GENOPS_ENV=production \
    -e GENOPS_DATABASE_URL=postgresql://prod-db:5432/genops \
    genops-framework:latest
```

### Kubernetes Deployment

```bash
# Deploy to Kubernetes
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -l app=genops

# View logs
kubectl logs -f deployment/genops-deployment
```

### AWS Deployment

```bash
# Using AWS CDK
cdk deploy GenOpsStack

# Or using CloudFormation
aws cloudformation deploy \
    --template-file cloudformation/genops.yaml \
    --stack-name genops-prod
```

### Configuration Management

```yaml
# config/production.yaml
database:
  url: postgresql://prod-db:5432/genops
  pool_size: 20
  ssl_mode: require

cache:
  strategy: redis
  url: redis://prod-cache:6379
  ttl_seconds: 3600

monitoring:
  enabled: true
  metrics_endpoint: /metrics
  health_endpoint: /health

security:
  enable_audit: true
  encryption_key: ${ENCRYPTION_KEY}
  jwt_secret: ${JWT_SECRET}
```

## Troubleshooting

### Common Issues

#### Import Errors
```bash
# Reinstall dependencies
pip uninstall genops-framework
pip install -r requirements.txt
pip install -e .
```

#### Database Connection Issues
```bash
# Check database connectivity
python -c "from genops.persistence import DataStore; ds = DataStore(); ds.health_check()"

# Reset database
rm genops.db
python -m genops.persistence init-db
```

#### Performance Issues
```bash
# Run performance diagnostics
python -m genops.benchmarks diagnostics

# Check system resources
python -c "import psutil; print(f'CPU: {psutil.cpu_percent()}%, RAM: {psutil.virtual_memory().percent}%')"
```

#### Memory Issues
```bash
# Enable memory profiling
export GENOPS_MEMORY_PROFILE=true

# Run with memory limits
python -m genops.experiments run --memory-limit=2GB
```

### Debug Mode

```bash
# Enable debug logging
export GENOPS_LOG_LEVEL=DEBUG

# Run with debug flags
python -m genops.experiments run --debug --verbose

# Profile execution
python -c "
import cProfile
from genops.experiments import ExperimentRunner
runner = ExperimentRunner()
cProfile.run('runner.run_full_study()', 'profile.prof')
"
```

### Getting Help

- **Documentation**: https://genops-framework.readthedocs.io/
- **Issues**: https://github.com/neerazz/genops-framework/issues
- **Discussions**: https://github.com/neerazz/genops-framework/discussions
- **Email**: research@genops-framework.org

## Contributing

### Development Workflow

```bash
# Create feature branch
git checkout -b feature/new-capability

# Run tests and linting
make test
make lint

# Update documentation
make docs

# Submit pull request
git push origin feature/new-capability
```

### Code Standards

- **Type Hints**: All functions must have complete type annotations
- **Docstrings**: Use Google-style docstrings with mathematical formulations
- **Testing**: Minimum 95% code coverage, property-based tests for core logic
- **Performance**: All changes must maintain or improve performance benchmarks
- **Documentation**: Update docs for any user-facing changes

### Research Contributions

For research paper contributions:

1. **Reproduce existing results** before making changes
2. **Add statistical validation** for new claims
3. **Update performance benchmarks** if algorithms change
4. **Document all parameters** and their validation
5. **Provide reproducibility scripts** for new experiments

### Release Process

```bash
# Update version
vim genops/__init__.py

# Run full test suite
make test-full

# Build documentation
make docs

# Create release
git tag v2.1.0
git push origin v2.1.0

# Publish to PyPI
make publish
```

## License and Citation

This framework is released under the MIT License. If you use GenOps in your research, please cite:

```bibtex
@software{genops2024,
  title={{GenOps}: Governance-First AI for CI/CD Pipelines},
  author={{GenOps Team}},
  url={https://github.com/neerazz/genops-framework},
  version={2.0.0},
  year={2024}
}
```

## Acknowledgments

- **Research Advisors**: For methodological guidance
- **Open Source Community**: For libraries and tools
- **Beta Testers**: For validation and feedback
- **Academic Reviewers**: For paper feedback and suggestions

---

*This document is automatically generated and version-controlled with the codebase to ensure accuracy and reproducibility.*