# GenOps Framework - Docker Configuration
# =======================================
#
# Multi-stage Docker build for GenOps framework with optimization for
# research reproducibility and production deployment.
#

# Base stage with system dependencies
FROM python:3.9-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    GENOPS_ENV=docker \
    GENOPS_DATABASE_URL=sqlite:///app/data/genops.db

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    sqlite3 \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create application user
RUN groupadd -r genops && useradd -r -g genops genops

# Set working directory
WORKDIR /app

# Copy Python requirements
COPY requirements.txt requirements-dev.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Development stage
FROM base as development

# Install development dependencies
RUN pip install --no-cache-dir -r requirements-dev.txt

# Copy source code
COPY . .

# Create necessary directories
RUN mkdir -p data config logs && \
    chown -R genops:genops /app

# Switch to non-root user
USER genops

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "from genops.persistence import get_data_store; get_data_store().health_check()" || exit 1

# Default command
CMD ["python", "-m", "genops.experiments", "validate-paper"]

# Production stage
FROM base as production

# Install only production dependencies
RUN pip install --no-cache-dir --only-binary=all \
    numpy \
    scipy \
    pandas \
    scikit-learn \
    && pip install --no-cache-dir -r requirements.txt

# Copy source code (excluding development files)
COPY genops/ ./genops/
COPY scripts/ ./scripts/
COPY config/default.yaml ./config/
COPY data/paper_dataset.json ./data/

# Create necessary directories
RUN mkdir -p data config logs && \
    chown -R genops:genops /app

# Pre-compile Python bytecode
RUN python -m compileall genops/

# Pre-initialize database
RUN python -c "from genops.persistence import DataStore; ds = DataStore(); print('Database initialized')"

# Switch to non-root user
USER genops

# Expose port for web interface (if implemented)
EXPOSE 8000

# Health check with production timeouts
HEALTHCHECK --interval=60s --timeout=30s --start-period=300s --retries=3 \
    CMD python -c "from genops.persistence import get_data_store, get_observability_manager; \
                   db_health = get_data_store().health_check(); \
                   obs_health = get_observability_manager().health_check(); \
                   exit(0 if db_health.is_healthy() and obs_health.is_healthy() else 1)" || exit 1

# Default command for production
CMD ["python", "-m", "genops.experiments", "run-paper-study"]

# Research validation stage
FROM production as research

# Install additional research dependencies
RUN pip install --no-cache-dir \
    jupyter \
    matplotlib \
    seaborn \
    plotly \
    notebook

# Copy research notebooks and scripts
COPY notebooks/ ./notebooks/
COPY research/ ./research/

# Create research directories
RUN mkdir -p results plots && \
    chown -R genops:genops /app/results /app/plots

# Expose Jupyter port
EXPOSE 8888

# Research validation command
CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]

# Minimal runtime stage for cloud deployment
FROM python:3.9-alpine as minimal

# Install minimal dependencies
RUN apk add --no-cache sqlite && \
    pip install --no-cache-dir \
    dataclasses-json \
    pydantic \
    sqlite3

# Copy only essential runtime files
COPY genops/models.py genops/persistence.py genops/experiments.py ./genops/
COPY config/default.yaml ./config/

# Create runtime user
RUN addgroup -g 1000 genops && \
    adduser -D -u 1000 -G genops genops

# Set permissions
RUN mkdir -p /data && chown genops:genops /data
USER genops

# Minimal health check
HEALTHCHECK --interval=120s --timeout=10s --retries=2 \
    CMD python -c "import sqlite3; sqlite3.connect('/data/genops.db').close()" || exit 1

WORKDIR /data
CMD ["python", "-c", "print('GenOps minimal runtime ready')"]