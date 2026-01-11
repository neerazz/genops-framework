# Contributing to GenOps Framework

Thank you for your interest in contributing to GenOps! This document provides guidelines for contributing to the project.

## 🏗️ Development Setup

1. **Clone the repository**
   ```bash
   git clone git@github.com:neerazz/genops-framework.git
   cd genops-framework
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install development dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Run tests to verify setup**
   ```bash
   pytest tests/ -v
   ```

## 📋 Code Standards

### Style Guide
- Follow PEP 8 for Python code style
- Use type hints for all function signatures
- Document all public functions with docstrings
- Maximum line length: 100 characters

### Commit Messages
Use conventional commits format:
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `test:` Test additions/modifications
- `refactor:` Code refactoring

### Testing Requirements
- All new features must include tests
- All tests must pass before merging
- Target test coverage: >80%

## 🧪 Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_pillars.py -v

# Run with coverage
pytest --cov=genops --cov-report=html

# Run the demo for manual verification
python run_demo.py --quick
```

## 📁 Project Structure

```
genops/
├── models.py             # Data models and validation
├── context_ingestion.py  # Pillar 1: RAG-style context
├── risk_scoring.py       # Pillar 2: Risk assessment
├── canary_rollout.py     # Pillar 3: Staged rollouts
├── governance.py         # Pillar 4: Audit & policies
├── pipeline.py           # Main orchestrator
└── simulator.py          # Deployment simulation
```

## 🔄 Pull Request Process

1. **Fork** the repository
2. **Create** a feature branch from `main`
3. **Make** your changes with appropriate tests
4. **Run** the full test suite
5. **Submit** a pull request with a clear description

### PR Checklist
- [ ] Tests pass locally (`pytest tests/ -v`)
- [ ] Demo runs successfully (`python run_demo.py --quick`)
- [ ] Code follows style guidelines
- [ ] Documentation updated if needed
- [ ] Commits follow conventional format

## 📖 Documentation

When adding new features:
- Update `README.md` if adding user-facing features
- Update `REPRODUCIBILITY.md` if changing validation steps
- Add inline comments for complex logic
- Include usage examples in docstrings

## 🆘 Need Help?

- Open an issue for bugs or feature requests
- Tag issues with appropriate labels
- Join discussions in existing issues

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

*Thank you for contributing to safer AI-powered deployments!*
