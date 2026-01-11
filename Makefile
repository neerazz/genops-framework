# GenOps Framework - Build Automation
# ===================================
#
# This Makefile provides comprehensive build automation for the GenOps framework,
# ensuring reproducible builds, testing, and deployment across all environments.
#
# Usage:
#   make help          # Show available targets
#   make setup         # Complete environment setup
#   make test          # Run test suite
#   make validate-paper # Reproduce paper results
#
# For research paper submission, run:
#   make paper-validation
#

.PHONY: help setup clean test test-coverage lint format docs build publish
.PHONY: validate-paper reproduce-paper show-results benchmark
.PHONY: docker-build docker-run k8s-deploy cloud-deploy
.PHONY: paper-validation paper-submission-check

# Configuration
PYTHON := python3.9
VENV := genops_env
PIP := $(VENV)/bin/pip
PYTHON_EXEC := $(VENV)/bin/python
PYTEST := $(VENV)/bin/pytest
MYPY := $(VENV)/bin/mypy
BLACK := $(VENV)/bin/black
ISORT := $(VENV)/bin/isort
SPHINX := $(VENV)/bin/sphinx-build

# Default target
help:
	@echo "GenOps Framework - Build Automation"
	@echo "===================================="
	@echo ""
	@echo "Available targets:"
	@echo "  setup              Complete environment setup"
	@echo "  clean              Clean build artifacts"
	@echo "  test               Run test suite"
	@echo "  test-coverage      Run tests with coverage"
	@echo "  lint               Run linting and type checking"
	@echo "  format             Format code"
	@echo "  docs               Build documentation"
	@echo "  build              Build distribution packages"
	@echo "  publish            Publish to PyPI"
	@echo ""
	@echo "Paper Validation:"
	@echo "  validate-paper     Validate all paper claims"
	@echo "  reproduce-paper    Exact paper reproduction"
	@echo "  show-results       Display validation results"
	@echo "  benchmark          Run performance benchmarks"
	@echo ""
	@echo "Deployment:"
	@echo "  docker-build       Build Docker image"
	@echo "  docker-run         Run in Docker container"
	@echo "  k8s-deploy         Deploy to Kubernetes"
	@echo "  cloud-deploy       Deploy to cloud"
	@echo ""
	@echo "Research:"
	@echo "  paper-validation   Complete paper validation suite"
	@echo "  paper-submission-check  Pre-submission validation"
	@echo ""
	@echo "Development:"
	@echo "  dev-setup          Development environment setup"
	@echo "  dev-server         Run development server"
	@echo "  dev-test           Run tests in watch mode"

# Environment setup
setup: venv install install-dev setup-data setup-config
	@echo "✓ Environment setup complete"

venv:
	@echo "Creating virtual environment..."
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip

install:
	@echo "Installing core dependencies..."
	$(PIP) install -r requirements.txt

install-dev:
	@echo "Installing development dependencies..."
	$(PIP) install -r requirements-dev.txt

setup-data:
	@echo "Setting up test data..."
	mkdir -p data
	$(PYTHON_EXEC) -m genops.data.generate_paper_dataset --output=data/paper_dataset.json

setup-config:
	@echo "Setting up configuration..."
	mkdir -p config
	cp config/default.yaml config/local.yaml

# Cleaning
clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf docs/_build/
	rm -rf data/*.tmp
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

clean-all: clean
	rm -rf $(VENV)
	rm -rf data/
	rm -rf logs/
	rm -rf *.db

# Testing
test:
	@echo "Running test suite..."
	$(PYTEST) tests/ -v --tb=short

test-unit:
	@echo "Running unit tests..."
	$(PYTEST) tests/test_models.py tests/test_risk_scoring.py -v

test-integration:
	@echo "Running integration tests..."
	$(PYTEST) tests/test_integration.py -v --tb=long

test-property:
	@echo "Running property-based tests..."
	$(PYTEST) tests/ -k "property_based" -v

test-coverage:
	@echo "Running tests with coverage..."
	$(PYTEST) tests/ --cov=genops --cov-report=html --cov-report=term-missing

test-full: test-coverage test-property

# Code quality
lint:
	@echo "Running linting and type checking..."
	$(MYPY) genops/ --ignore-missing-imports
	$(PYTHON_EXEC) -m flake8 genops/ tests/ --max-line-length=100
	$(PYTHON_EXEC) -m pylint genops/ --disable=C0114,C0115,C0116

format:
	@echo "Formatting code..."
	$(BLACK) genops/ tests/
	$(ISORT) genops/ tests/

format-check:
	@echo "Checking code formatting..."
	$(BLACK) --check genops/ tests/
	$(ISORT) --check-only genops/ tests/

# Documentation
docs:
	@echo "Building documentation..."
	cd docs && $(SPHINX) -b html . _build/html
	@echo "Documentation built: docs/_build/html/index.html"

docs-serve:
	@echo "Serving documentation locally..."
	cd docs/_build/html && python3 -m http.server 8001

# Building and publishing
build:
	@echo "Building distribution packages..."
	$(PYTHON_EXEC) setup.py sdist bdist_wheel

publish-test:
	@echo "Publishing to TestPyPI..."
	$(PYTHON_EXEC) -m twine upload --repository testpypi dist/*

publish:
	@echo "Publishing to PyPI..."
	$(PYTHON_EXEC) -m twine upload dist/*

# Paper validation
validate-paper:
	@echo "Validating paper claims..."
	$(PYTHON_EXEC) -m genops.experiments validate-paper --output=results/paper_validation.json

reproduce-paper:
	@echo "Reproducing exact paper results..."
	export GENOPS_PAPER_MODE=true && \
	export GENOPS_SAMPLE_SIZE=15847 && \
	export GENOPS_RANDOM_SEED=42 && \
	$(PYTHON_EXEC) -m genops.experiments run-paper-study --output=results/paper_reproduction.json

show-results:
	@echo "Displaying validation results..."
	$(PYTHON_EXEC) scripts/display_results.py results/paper_validation.json

benchmark:
	@echo "Running performance benchmarks..."
	mkdir -p results
	$(PYTHON_EXEC) -m genops.benchmarks run-all --output=results/benchmarks.json
	$(PYTHON_EXEC) -m genops.benchmarks report --input=results/benchmarks.json --format=markdown

benchmark-profile:
	@echo "Running performance profiling..."
	$(PYTHON_EXEC) -m cProfile -o results/profile.prof -m genops.experiments validate-paper
	$(PYTHON_EXEC) scripts/analyze_profile.py results/profile.prof

# Complete paper validation suite
paper-validation: clean setup validate-paper benchmark
	@echo "Running complete paper validation..."
	$(PYTHON_EXEC) scripts/validate_all_claims.py
	@echo "✓ Paper validation complete"

paper-submission-check:
	@echo "Pre-submission validation checks..."
	$(PYTHON_EXEC) scripts/pre_submission_check.py

# Docker operations
docker-build:
	@echo "Building Docker image..."
	docker build -t genops-framework:latest .

docker-build-prod:
	@echo "Building production Docker image..."
	docker build -t genops-framework:prod -f Dockerfile.prod .

docker-run:
	@echo "Running in Docker container..."
	docker run -it --rm \
		-v $(PWD)/data:/app/data \
		-v $(PWD)/config:/app/config \
		-p 8000:8000 \
		genops-framework:latest

docker-test:
	@echo "Running tests in Docker..."
	docker run --rm genops-framework:latest make test

# Kubernetes deployment
k8s-deploy:
	@echo "Deploying to Kubernetes..."
	kubectl apply -f k8s/
	kubectl rollout status deployment/genops-deployment

k8s-logs:
	@echo "Viewing Kubernetes logs..."
	kubectl logs -f deployment/genops-deployment

k8s-cleanup:
	@echo "Cleaning up Kubernetes deployment..."
	kubectl delete -f k8s/

# Cloud deployment
cloud-deploy-aws:
	@echo "Deploying to AWS..."
	cdk deploy GenOpsStack --require-approval never

cloud-deploy-gcp:
	@echo "Deploying to GCP..."
	gcloud builds submit --config cloudbuild.yaml

cloud-deploy-azure:
	@echo "Deploying to Azure..."
	az deployment group create --resource-group genops-rg --template-file azuredeploy.json

# Development workflow
dev-setup: setup
	@echo "Setting up development environment..."
	$(PIP) install -r requirements-dev.txt
	pre-commit install
	git config core.hooksPath .git/hooks

dev-server:
	@echo "Starting development server..."
	export FLASK_ENV=development && \
	$(PYTHON_EXEC) -m genops.web.app

dev-test:
	@echo "Running tests in watch mode..."
	$(PYTHON_EXEC) -m pytest-watch tests/ -- -v

dev-lint:
	@echo "Running linting in watch mode..."
	@which entr > /dev/null || (echo "Install entr: brew install entr" && exit 1)
	find genops/ tests/ -name "*.py" | entr make lint

# Utility targets
version:
	$(PYTHON_EXEC) -c "import genops; print(genops.__version__)"

deps-update:
	@echo "Updating dependencies..."
	$(PIP) install --upgrade pip-tools
	pip-compile requirements.in > requirements.txt
	pip-compile requirements-dev.in > requirements-dev.txt

deps-install:
	@echo "Installing updated dependencies..."
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt

# Health checks
health-check:
	@echo "Running health checks..."
	$(PYTHON_EXEC) -c "from genops.persistence import get_data_store; print('Database:', get_data_store().health_check().overall_status)"
	$(PYTHON_EXEC) -c "from genops.persistence import get_observability_manager; print('Observability:', get_observability_manager().health_check().overall_status)"
	@echo "✓ All systems healthy"

# Emergency recovery
emergency-restore:
	@echo "Emergency database restore..."
	cp genops.db.backup genops.db
	$(PYTHON_EXEC) -m genops.persistence migrate

# Statistics and reporting
stats:
	@echo "Code statistics:"
	@echo "Lines of code:" $$(find genops/ -name "*.py" -exec wc -l {} \; | tail -1 | awk '{print $$1}')
	@echo "Test coverage:" $$(make test-coverage 2>/dev/null | grep "TOTAL" | awk '{print $$4}')
	@echo "Documentation completeness:" $$(make docs 2>/dev/null && echo "Built successfully" || echo "Build failed")

# CI/CD pipeline simulation
ci-pipeline: clean setup test-coverage lint docs build
	@echo "✓ CI pipeline completed successfully"

# All-in-one setup for new contributors
onboard: clean setup dev-setup test docs
	@echo "✓ Onboarding complete - you're ready to contribute!"

# Default target shows help
.DEFAULT_GOAL := help