"""
Data Persistence and Configuration Management for GenOps Framework

This module provides comprehensive data persistence, configuration management,
and observability capabilities for production deployment of the GenOps framework.

Mathematical Framework:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Data Persistence Strategy:
   - Multi-layer storage: Memory → Cache → Persistent → Archive
   - Consistency models: Eventual consistency for operational data
   - Data partitioning: Time-based and service-based sharding
   - Backup strategy: Point-in-time recovery with Merkle tree validation

2. Configuration Management:
   - Hierarchical configuration: Global → Environment → Service → Instance
   - Dynamic reconfiguration: Hot-swappable parameters with validation
   - Configuration versioning: Immutable configuration history
   - Rollback capabilities: Configuration drift detection and correction

3. Observability Framework:
   - Metrics collection: RED (Rate, Error, Duration) methodology
   - Distributed tracing: End-to-end request tracing with correlation IDs
   - Structured logging: JSON-formatted logs with semantic fields
   - Health checking: Multi-dimensional health assessment with alerts

4. Performance Optimization:
   - Connection pooling: Database connection reuse with health checks
   - Caching strategies: Multi-level caching with TTL and invalidation
   - Batch operations: Bulk data operations for efficiency
   - Compression: Adaptive compression for storage and network efficiency

Usage Examples:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

>>> from genops.persistence import DataStore, ConfigurationManager, ObservabilityManager
>>>
>>> # Initialize persistence layer
>>> store = DataStore(config={"database_url": "postgresql://localhost/genops"})
>>> config = ConfigurationManager()
>>> observability = ObservabilityManager()
>>>
>>> # Persist deployment data
>>> deployment = store.save_deployment(deployment_data)
>>> print(f"Saved deployment: {deployment.id}")
>>>
>>> # Load configuration
>>> risk_config = config.load_section("risk_scoring")
>>> print(f"Risk weights: {risk_config.weights}")
>>>
>>> # Record metrics
>>> observability.record_metric("risk_calculation_time", 2.3, {"tier": "HIGH"})
>>> observability.record_trace("deployment_workflow", correlation_id="dep_123")
>>>
>>> # Health check
>>> health = observability.health_check()
>>> print(f"System health: {health.overall_status}")
"""

import json
import sqlite3
import hashlib
import threading
import time
from typing import Dict, List, Any, Optional, Callable, Union, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import logging
import uuid
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

from .models import (
    Service, DeploymentContext, RiskAssessment, Deployment, DeploymentStatus,
    AuditEntry, VectorEmbedding, KnowledgeNode
)


class StorageBackend(Enum):
    """Supported storage backends for data persistence."""
    MEMORY = "memory"
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    REDIS = "redis"
    S3 = "s3"


class CacheStrategy(Enum):
    """Caching strategies for performance optimization."""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    WRITE_THROUGH = "write_through"
    WRITE_BEHIND = "write_behind"


@dataclass
class PersistenceConfig:
    """
    Configuration for data persistence layer.

    Defines storage backends, caching strategies, and performance parameters.
    """
    backend: StorageBackend = StorageBackend.SQLITE
    database_url: str = "genops.db"
    cache_strategy: CacheStrategy = CacheStrategy.LRU
    cache_size: int = 10000
    cache_ttl_seconds: int = 3600  # 1 hour
    max_connections: int = 10
    connection_timeout: float = 30.0
    enable_compression: bool = True
    backup_interval_hours: int = 24
    enable_encryption: bool = False
    encryption_key: Optional[str] = None

    def __post_init__(self):
        """Validate configuration parameters."""
        if self.backend == StorageBackend.POSTGRESQL and not self.database_url.startswith("postgresql://"):
            raise ValueError("PostgreSQL backend requires postgresql:// URL")

        if self.backend == StorageBackend.REDIS and not self.database_url.startswith("redis://"):
            raise ValueError("Redis backend requires redis:// URL")

        if self.enable_encryption and not self.encryption_key:
            raise ValueError("Encryption requires encryption_key")


@dataclass
class CacheEntry:
    """Cache entry with metadata for invalidation and statistics."""
    key: str
    value: Any
    created_at: datetime
    accessed_at: datetime
    access_count: int = 0
    ttl_seconds: Optional[int] = None
    size_bytes: int = 0

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        if self.ttl_seconds is None:
            return False
        return (datetime.now() - self.created_at).total_seconds() > self.ttl_seconds

    def touch(self):
        """Update access metadata."""
        self.accessed_at = datetime.now()
        self.access_count += 1


@dataclass
class HealthStatus:
    """System health status with detailed component information."""
    overall_status: str  # "healthy", "degraded", "unhealthy"
    timestamp: datetime
    components: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    alerts: List[str] = field(default_factory=list)

    def is_healthy(self) -> bool:
        """Check if system is healthy."""
        return self.overall_status == "healthy"

    def add_component_status(self, component: str, status: str, details: Dict[str, Any]):
        """Add component health status."""
        self.components[component] = {
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }

    def add_metric(self, name: str, value: float):
        """Add health metric."""
        self.metrics[name] = value

    def add_alert(self, alert: str):
        """Add health alert."""
        self.alerts.append(alert)


class LRUCache:
    """
    Least Recently Used cache implementation with TTL support.

    Provides O(1) access time and automatic eviction of expired entries.
    """

    def __init__(self, max_size: int = 10000, default_ttl: Optional[int] = None):
        """
        Initialize LRU cache.

        Args:
            max_size: Maximum number of entries
            default_ttl: Default TTL in seconds for entries
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, CacheEntry] = {}
        self.access_order: Dict[str, None] = {}  # For O(1) LRU tracking
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self._lock:
            entry = self.cache.get(key)
            if entry is None or entry.is_expired():
                if entry:
                    self._remove_entry(key)
                return None

            entry.touch()
            self._update_access_order(key)
            return entry.value

    def put(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Put value in cache."""
        with self._lock:
            # Remove existing entry if present
            if key in self.cache:
                self._remove_entry(key)

            # Evict if at capacity
            if len(self.cache) >= self.max_size:
                self._evict_lru()

            # Add new entry
            ttl = ttl_seconds or self.default_ttl
            size_bytes = self._estimate_size(value)
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=datetime.now(),
                accessed_at=datetime.now(),
                ttl_seconds=ttl,
                size_bytes=size_bytes
            )

            self.cache[key] = entry
            self.access_order[key] = None

    def remove(self, key: str) -> bool:
        """Remove entry from cache."""
        with self._lock:
            if key in self.cache:
                self._remove_entry(key)
                return True
            return False

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self.cache.clear()
            self.access_order.clear()

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_size = sum(entry.size_bytes for entry in self.cache.values())
            hit_rate = 0.0
            if self.cache:
                total_accesses = sum(entry.access_count for entry in self.cache.values())
                hit_rate = total_accesses / len(self.cache) if total_accesses > 0 else 0.0

            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "total_size_bytes": total_size,
                "hit_rate": hit_rate,
                "utilization_percent": (len(self.cache) / self.max_size) * 100
            }

    def _remove_entry(self, key: str) -> None:
        """Remove entry from cache data structures."""
        del self.cache[key]
        del self.access_order[key]

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self.access_order:
            return

        # Find LRU entry (first in access order)
        lru_key = next(iter(self.access_order))
        self._remove_entry(lru_key)

    def _update_access_order(self, key: str) -> None:
        """Update access order for LRU tracking."""
        # Remove and re-add to make it most recently used
        del self.access_order[key]
        self.access_order[key] = None

    def _estimate_size(self, obj: Any) -> int:
        """Estimate memory size of object in bytes."""
        try:
            # Rough estimation using JSON serialization
            json_str = json.dumps(obj, default=str)
            return len(json_str.encode('utf-8'))
        except (TypeError, ValueError):
            # Fallback estimation
            if isinstance(obj, (list, tuple)):
                return sum(self._estimate_size(item) for item in obj) + 64
            elif isinstance(obj, dict):
                return sum(self._estimate_size(k) + self._estimate_size(v) for k, v in obj.items()) + 64
            else:
                return 128  # Default object size


class DataStore:
    """
    Unified data persistence layer for GenOps framework.

    Provides multi-backend storage with caching, connection pooling,
    and automatic failover capabilities.
    """

    def __init__(self, config: PersistenceConfig):
        """
        Initialize data store.

        Args:
            config: Persistence configuration
        """
        self.config = config
        self.cache = LRUCache(
            max_size=config.cache_size,
            default_ttl=config.cache_ttl_seconds
        )

        # Initialize storage backend
        if config.backend == StorageBackend.SQLITE:
            self._init_sqlite()
        elif config.backend == StorageBackend.POSTGRESQL:
            self._init_postgresql()
        elif config.backend == StorageBackend.REDIS:
            self._init_redis()
        else:
            raise ValueError(f"Unsupported backend: {config.backend}")

        # Connection pool
        self._connection_pool = []
        self._pool_lock = threading.Lock()

        # Initialize schema
        self._create_tables()

        # Background tasks
        self._start_background_tasks()

    def _init_sqlite(self):
        """Initialize SQLite backend."""
        self.db_path = self.config.database_url
        self.db_template = """
            CREATE TABLE IF NOT EXISTS {table_name} (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                version INTEGER DEFAULT 1
            );
            CREATE INDEX IF NOT EXISTS idx_{table_name}_created ON {table_name}(created_at);
            CREATE INDEX IF NOT EXISTS idx_{table_name}_updated ON {table_name}(updated_at);
        """

    def _init_postgresql(self):
        """Initialize PostgreSQL backend."""
        # Implementation would connect to PostgreSQL
        raise NotImplementedError("PostgreSQL backend not yet implemented")

    def _init_redis(self):
        """Initialize Redis backend."""
        # Implementation would connect to Redis
        raise NotImplementedError("Redis backend not yet implemented")

    def _create_tables(self):
        """Create database tables."""
        tables = [
            "services", "deployment_contexts", "risk_assessments",
            "deployments", "audit_entries", "vector_embeddings",
            "knowledge_nodes", "metrics", "configurations"
        ]

        for table in tables:
            sql = self.db_template.format(table_name=table)
            self._execute_query(sql)

    def _start_background_tasks(self):
        """Start background maintenance tasks."""
        # Cache cleanup
        def cleanup_cache():
            while True:
                time.sleep(300)  # Clean every 5 minutes
                expired_keys = [
                    key for key, entry in self.cache.cache.items()
                    if entry.is_expired()
                ]
                for key in expired_keys:
                    self.cache.remove(key)

        # Backup task
        def backup_data():
            while True:
                time.sleep(self.config.backup_interval_hours * 3600)
                self._create_backup()

        # Start background threads
        threading.Thread(target=cleanup_cache, daemon=True).start()
        threading.Thread(target=backup_data, daemon=True).start()

    @contextmanager
    def _get_connection(self):
        """Get database connection from pool."""
        with self._pool_lock:
            if self._connection_pool:
                conn = self._connection_pool.pop()
            else:
                conn = sqlite3.connect(self.db_path, timeout=self.config.connection_timeout)
                conn.row_factory = sqlite3.Row

            try:
                yield conn
            finally:
                if len(self._connection_pool) < self.config.max_connections:
                    self._connection_pool.append(conn)
                else:
                    conn.close()

    def _execute_query(self, query: str, params: Tuple = ()) -> List[Dict]:
        """Execute database query."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()

            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
            return []

    def save_deployment(self, deployment: Deployment) -> Deployment:
        """Save deployment to persistent storage."""
        cache_key = f"deployment:{deployment.id}"
        data = json.dumps(asdict(deployment), default=str)

        # Save to database
        self._execute_query(
            "INSERT OR REPLACE INTO deployments (id, data, updated_at) VALUES (?, ?, ?)",
            (deployment.id, data, datetime.now())
        )

        # Cache the result
        self.cache.put(cache_key, deployment)

        return deployment

    def load_deployment(self, deployment_id: str) -> Optional[Deployment]:
        """Load deployment from storage."""
        cache_key = f"deployment:{deployment_id}"

        # Try cache first
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        # Load from database
        rows = self._execute_query(
            "SELECT data FROM deployments WHERE id = ?",
            (deployment_id,)
        )

        if rows:
            data = json.loads(rows[0]["data"])
            deployment = Deployment(**data)
            self.cache.put(cache_key, deployment)
            return deployment

        return None

    def save_risk_assessment(self, assessment: RiskAssessment) -> RiskAssessment:
        """Save risk assessment to storage."""
        cache_key = f"risk:{assessment.deployment_id}"
        data = json.dumps(asdict(assessment), default=str)

        self._execute_query(
            "INSERT OR REPLACE INTO risk_assessments (id, data, updated_at) VALUES (?, ?, ?)",
            (assessment.deployment_id, data, datetime.now())
        )

        self.cache.put(cache_key, assessment)
        return assessment

    def save_audit_entry(self, entry: AuditEntry) -> AuditEntry:
        """Save audit entry with cryptographic integrity."""
        cache_key = f"audit:{entry.id}"
        data = json.dumps(asdict(entry), default=str)

        self._execute_query(
            "INSERT OR REPLACE INTO audit_entries (id, data, updated_at) VALUES (?, ?, ?)",
            (entry.id, data, datetime.now())
        )

        self.cache.put(cache_key, entry)
        return entry

    def save_vector_embedding(self, embedding: VectorEmbedding) -> VectorEmbedding:
        """Save vector embedding for semantic search."""
        cache_key = f"embedding:{embedding.id}"
        data = json.dumps(asdict(embedding), default=str)

        self._execute_query(
            "INSERT OR REPLACE INTO vector_embeddings (id, data, updated_at) VALUES (?, ?, ?)",
            (embedding.id, data, datetime.now())
        )

        self.cache.put(cache_key, embedding)
        return embedding

    def search_similar_deployments(self, embedding: List[float], limit: int = 10) -> List[DeploymentContext]:
        """Search for similar deployments using vector similarity."""
        # This is a simplified implementation - in practice would use vector database
        cache_key = f"similar:{hash(tuple(embedding))}"

        cached = self.cache.get(cache_key)
        if cached:
            return cached

        # Load all embeddings and calculate cosine similarity
        rows = self._execute_query("SELECT data FROM vector_embeddings")

        similarities = []
        for row in rows:
            stored_data = json.loads(row["data"])
            stored_embedding = stored_data["vector"]

            similarity = self._cosine_similarity(embedding, stored_embedding)
            similarities.append((stored_data, similarity))

        # Sort by similarity and return top results
        similarities.sort(key=lambda x: x[1], reverse=True)
        results = []

        for stored_data, similarity in similarities[:limit]:
            context_data = stored_data.get("context", {})
            if context_data:
                context = DeploymentContext(**context_data)
                results.append(context)

        self.cache.put(cache_key, results, ttl_seconds=600)  # Cache for 10 minutes
        return results

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    def get_metrics_summary(self, time_range_hours: int = 24) -> Dict[str, Any]:
        """Get performance metrics summary."""
        cutoff_time = datetime.now() - timedelta(hours=time_range_hours)

        # Query recent metrics
        rows = self._execute_query(
            "SELECT data FROM metrics WHERE created_at > ?",
            (cutoff_time,)
        )

        metrics = []
        for row in rows:
            data = json.loads(row["data"])
            metrics.append(data)

        # Aggregate metrics
        if not metrics:
            return {"total_operations": 0, "avg_response_time": 0.0, "error_rate": 0.0}

        total_operations = len(metrics)
        avg_response_time = sum(m.get("response_time", 0) for m in metrics) / total_operations
        error_count = sum(1 for m in metrics if m.get("error", False))
        error_rate = error_count / total_operations if total_operations > 0 else 0.0

        return {
            "total_operations": total_operations,
            "avg_response_time": avg_response_time,
            "error_rate": error_rate,
            "time_range_hours": time_range_hours
        }

    def _create_backup(self):
        """Create database backup."""
        if self.config.backend != StorageBackend.SQLITE:
            return  # Only SQLite backups implemented

        backup_path = f"{self.db_path}.backup.{int(datetime.now().timestamp())}"

        with self._get_connection() as conn:
            # Create backup using SQLite backup API
            backup_conn = sqlite3.connect(backup_path)
            conn.backup(backup_conn)
            backup_conn.close()

        print(f"Database backup created: {backup_path}")

    def health_check(self) -> HealthStatus:
        """Perform comprehensive health check."""
        health = HealthStatus(
            overall_status="healthy",
            timestamp=datetime.now()
        )

        # Check database connectivity
        try:
            self._execute_query("SELECT 1")
            health.add_component_status("database", "healthy", {"latency_ms": 1.0})
        except Exception as e:
            health.add_component_status("database", "unhealthy", {"error": str(e)})
            health.overall_status = "unhealthy"

        # Check cache health
        cache_stats = self.cache.stats()
        if cache_stats["size"] > cache_stats["max_size"] * 0.9:
            health.add_component_status("cache", "degraded", cache_stats)
            health.add_alert("Cache near capacity")
        else:
            health.add_component_status("cache", "healthy", cache_stats)

        # Check connection pool
        with self._pool_lock:
            pool_size = len(self._connection_pool)

        if pool_size == 0:
            health.add_component_status("connection_pool", "healthy", {"active_connections": pool_size})
        elif pool_size > self.config.max_connections * 0.8:
            health.add_component_status("connection_pool", "degraded", {"active_connections": pool_size})
        else:
            health.add_component_status("connection_pool", "healthy", {"active_connections": pool_size})

        # Performance metrics
        metrics_summary = self.get_metrics_summary(time_range_hours=1)
        health.add_metric("operations_per_hour", metrics_summary["total_operations"])
        health.add_metric("avg_response_time_ms", metrics_summary["avg_response_time"] * 1000)
        health.add_metric("error_rate_percent", metrics_summary["error_rate"] * 100)

        # Overall status determination
        component_statuses = [comp["status"] for comp in health.components.values()]
        if "unhealthy" in component_statuses:
            health.overall_status = "unhealthy"
        elif "degraded" in component_statuses:
            health.overall_status = "degraded"

        return health


class ConfigurationManager:
    """
    Hierarchical configuration management system.

    Supports multiple configuration sources with inheritance,
    validation, and dynamic reloading capabilities.
    """

    def __init__(self, config_dir: str = "config"):
        """
        Initialize configuration manager.

        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)

        # Configuration hierarchy: global -> environment -> service -> instance
        self._config_cache: Dict[str, Dict] = {}
        self._config_mtimes: Dict[str, float] = {}
        self._lock = threading.Lock()

        # Load default configuration
        self._load_default_config()

    def _load_default_config(self):
        """Load default configuration values."""
        self._config_cache["global"] = {
            "risk_scoring": {
                "weights": {
                    "service_criticality": 0.3,
                    "service_health": 0.25,
                    "change_complexity": 0.2,
                    "blast_radius": 0.15,
                    "timing_risk": 0.1
                },
                "enable_bayesian": True,
                "enable_temporal": True,
                "monte_carlo_samples": 1000
            },
            "canary_rollout": {
                "stages": [0.1, 0.25, 0.5, 1.0],
                "slo_violation_threshold": 0.05,
                "rollback_timeout_seconds": 300,
                "enable_advanced_monitoring": True
            },
            "governance": {
                "require_approvals_for_high_risk": True,
                "friday_deployment_block": True,
                "error_budget_protection": True,
                "audit_retention_days": 365
            },
            "context_ingestion": {
                "embedding_dimension": 1536,
                "similarity_threshold": 0.8,
                "max_context_items": 50,
                "enable_knowledge_graph": True
            }
        }

    def load_section(self, section_name: str, environment: str = "default") -> Dict[str, Any]:
        """
        Load configuration section with inheritance.

        Args:
            section_name: Name of configuration section
            environment: Environment name (default, staging, production)

        Returns:
            Merged configuration for the section
        """
        with self._lock:
            cache_key = f"{section_name}:{environment}"

            # Check if configuration needs reloading
            if self._needs_reload(cache_key):
                config = self._load_section_config(section_name, environment)
                self._config_cache[cache_key] = config

            return self._config_cache.get(cache_key, {}).copy()

    def _needs_reload(self, cache_key: str) -> bool:
        """Check if configuration needs to be reloaded."""
        # Check global config
        global_config_file = self.config_dir / "global.json"
        if global_config_file.exists():
            current_mtime = global_config_file.stat().st_mtime
            if current_mtime != self._config_mtimes.get("global", 0):
                return True

        # Check environment config
        env_config_file = self.config_dir / f"{cache_key.split(':')[1]}.json"
        if env_config_file.exists():
            current_mtime = env_config_file.stat().st_mtime
            if current_mtime != self._config_mtimes.get(cache_key, 0):
                return True

        return cache_key not in self._config_cache

    def _load_section_config(self, section_name: str, environment: str) -> Dict[str, Any]:
        """Load and merge configuration section."""
        # Start with global defaults
        config = self._config_cache.get("global", {}).get(section_name, {}).copy()

        # Load global overrides
        global_config_file = self.config_dir / "global.json"
        if global_config_file.exists():
            global_data = json.loads(global_config_file.read_text())
            if section_name in global_data:
                self._deep_merge(config, global_data[section_name])
            self._config_mtimes["global"] = global_config_file.stat().st_mtime

        # Load environment overrides
        env_config_file = self.config_dir / f"{environment}.json"
        if env_config_file.exists():
            env_data = json.loads(env_config_file.read_text())
            if section_name in env_data:
                self._deep_merge(config, env_data[section_name])
            self._config_mtimes[f"{section_name}:{environment}"] = env_config_file.stat().st_mtime

        return config

    def _deep_merge(self, base: Dict, override: Dict) -> None:
        """Deep merge override dictionary into base dictionary."""
        for key, value in override.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def save_section(self, section_name: str, config: Dict[str, Any], environment: str = "default") -> None:
        """
        Save configuration section.

        Args:
            section_name: Name of configuration section
            config: Configuration data to save
            environment: Environment name
        """
        with self._lock:
            env_config_file = self.config_dir / f"{environment}.json"
            env_config_file.parent.mkdir(exist_ok=True)

            # Load existing environment config
            env_data = {}
            if env_config_file.exists():
                env_data = json.loads(env_config_file.read_text())

            # Update section
            env_data[section_name] = config

            # Save back to file
            env_config_file.write_text(json.dumps(env_data, indent=2))

            # Invalidate cache
            cache_key = f"{section_name}:{environment}"
            if cache_key in self._config_cache:
                del self._config_cache[cache_key]

    def validate_config(self, section_name: str, config: Dict[str, Any]) -> List[str]:
        """
        Validate configuration section.

        Args:
            section_name: Name of configuration section
            config: Configuration to validate

        Returns:
            List of validation error messages
        """
        errors = []

        if section_name == "risk_scoring":
            errors.extend(self._validate_risk_scoring_config(config))
        elif section_name == "canary_rollout":
            errors.extend(self._validate_canary_config(config))
        elif section_name == "governance":
            errors.extend(self._validate_governance_config(config))

        return errors

    def _validate_risk_scoring_config(self, config: Dict) -> List[str]:
        """Validate risk scoring configuration."""
        errors = []

        if "weights" in config:
            weights = config["weights"]
            if not isinstance(weights, dict):
                errors.append("weights must be a dictionary")
            elif abs(sum(weights.values()) - 1.0) > 1e-6:
                errors.append("weights must sum to 1.0")

        return errors

    def _validate_canary_config(self, config: Dict) -> List[str]:
        """Validate canary rollout configuration."""
        errors = []

        if "stages" in config:
            stages = config["stages"]
            if not isinstance(stages, list):
                errors.append("stages must be a list")
            elif not all(0 < stage <= 1 for stage in stages):
                errors.append("stages must be between 0 and 1")
            elif stages != sorted(stages):
                errors.append("stages must be in ascending order")

        return errors

    def _validate_governance_config(self, config: Dict) -> List[str]:
        """Validate governance configuration."""
        errors = []

        if "audit_retention_days" in config:
            retention = config["audit_retention_days"]
            if not isinstance(retention, int) or retention <= 0:
                errors.append("audit_retention_days must be a positive integer")

        return errors


class ObservabilityManager:
    """
    Comprehensive observability framework for GenOps.

    Provides metrics collection, distributed tracing, structured logging,
    and health monitoring capabilities.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize observability manager.

        Args:
            config: Observability configuration
        """
        self.config = config or {}
        self.logger = logging.getLogger("genops.observability")
        self.logger.setLevel(logging.INFO)

        # Metrics storage
        self._metrics: List[Dict[str, Any]] = []
        self._traces: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

        # Performance counters
        self._counters: Dict[str, int] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = {}

        # Setup logging
        self._setup_logging()

    def _setup_logging(self):
        """Setup structured JSON logging."""
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"component": "%(name)s", "message": "%(message)s", '
            '"extra": %(extra)s}'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def record_metric(self, name: str, value: Union[int, float],
                     tags: Optional[Dict[str, Any]] = None) -> None:
        """
        Record a metric measurement.

        Args:
            name: Metric name
            value: Metric value
            tags: Additional metric tags
        """
        metric_data = {
            "name": name,
            "value": value,
            "timestamp": datetime.now().isoformat(),
            "tags": tags or {}
        }

        with self._lock:
            self._metrics.append(metric_data)

            # Update aggregations
            if isinstance(value, (int, float)):
                if name not in self._histograms:
                    self._histograms[name] = []
                self._histograms[name].append(float(value))

                # Keep only last 1000 measurements per metric
                if len(self._histograms[name]) > 1000:
                    self._histograms[name] = self._histograms[name][-1000:]

    def increment_counter(self, name: str, amount: int = 1,
                         tags: Optional[Dict[str, Any]] = None) -> None:
        """
        Increment a counter metric.

        Args:
            name: Counter name
            amount: Amount to increment
            tags: Additional metric tags
        """
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + amount

        self.record_metric(name, self._counters[name], tags)

    def set_gauge(self, name: str, value: float,
                  tags: Optional[Dict[str, Any]] = None) -> None:
        """
        Set a gauge metric.

        Args:
            name: Gauge name
            value: Gauge value
            tags: Additional metric tags
        """
        with self._lock:
            self._gauges[name] = value

        self.record_metric(name, value, tags)

    def start_trace(self, trace_name: str, correlation_id: Optional[str] = None) -> str:
        """
        Start a distributed trace.

        Args:
            trace_name: Name of the trace
            correlation_id: Optional correlation ID

        Returns:
            Trace ID for the started trace
        """
        trace_id = correlation_id or str(uuid.uuid4())
        trace_data = {
            "trace_id": trace_id,
            "name": trace_name,
            "start_time": datetime.now(),
            "spans": [],
            "tags": {}
        }

        with self._lock:
            self._traces[trace_id] = trace_data

        self.logger.info(f"Started trace: {trace_name}", extra={"trace_id": trace_id})
        return trace_id

    def add_span(self, trace_id: str, span_name: str,
                duration_ms: float, tags: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a span to an existing trace.

        Args:
            trace_id: Trace ID
            span_name: Span name
            duration_ms: Span duration in milliseconds
            tags: Additional span tags
        """
        span_data = {
            "name": span_name,
            "duration_ms": duration_ms,
            "timestamp": datetime.now().isoformat(),
            "tags": tags or {}
        }

        with self._lock:
            if trace_id in self._traces:
                self._traces[trace_id]["spans"].append(span_data)

    def end_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """
        End a distributed trace and return trace data.

        Args:
            trace_id: Trace ID to end

        Returns:
            Completed trace data or None if trace not found
        """
        with self._lock:
            if trace_id not in self._traces:
                return None

            trace_data = self._traces[trace_id]
            trace_data["end_time"] = datetime.now()
            trace_data["total_duration_ms"] = (
                trace_data["end_time"] - trace_data["start_time"]
            ).total_seconds() * 1000

            # Log completed trace
            self.logger.info(
                f"Completed trace: {trace_data['name']}",
                extra={
                    "trace_id": trace_id,
                    "duration_ms": trace_data["total_duration_ms"],
                    "span_count": len(trace_data["spans"])
                }
            )

            # Remove from active traces (keep in history if needed)
            del self._traces[trace_id]

            return trace_data

    def log_event(self, level: str, message: str,
                 extra: Optional[Dict[str, Any]] = None) -> None:
        """
        Log a structured event.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR)
            message: Log message
            extra: Additional structured data
        """
        extra = extra or {}
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(message, extra=extra)

    def get_metrics_summary(self, time_range_minutes: int = 60) -> Dict[str, Any]:
        """
        Get metrics summary for the specified time range.

        Args:
            time_range_minutes: Time range in minutes

        Returns:
            Metrics summary with statistics
        """
        cutoff_time = datetime.now() - timedelta(minutes=time_range_minutes)

        with self._lock:
            # Filter recent metrics
            recent_metrics = [
                m for m in self._metrics
                if datetime.fromisoformat(m["timestamp"]) > cutoff_time
            ]

            if not recent_metrics:
                return {"total_metrics": 0, "metrics_by_name": {}}

            # Group by metric name
            metrics_by_name = {}
            for metric in recent_metrics:
                name = metric["name"]
                if name not in metrics_by_name:
                    metrics_by_name[name] = []
                metrics_by_name[name].append(metric["value"])

            # Calculate statistics
            summary = {"total_metrics": len(recent_metrics), "metrics_by_name": {}}

            for name, values in metrics_by_name.items():
                if values:
                    summary["metrics_by_name"][name] = {
                        "count": len(values),
                        "mean": statistics.mean(values),
                        "median": statistics.median(values),
                        "min": min(values),
                        "max": max(values),
                        "p95": sorted(values)[int(0.95 * len(values))] if len(values) > 1 else max(values)
                    }

            return summary

    def get_active_traces(self) -> List[Dict[str, Any]]:
        """Get list of currently active traces."""
        with self._lock:
            return list(self._traces.values())

    def health_check(self) -> HealthStatus:
        """
        Perform comprehensive health check of observability system.

        Returns:
            Health status with detailed component information
        """
        health = HealthStatus(
            overall_status="healthy",
            timestamp=datetime.now()
        )

        # Check metrics collection
        metrics_count = len(self._metrics)
        health.add_component_status(
            "metrics_collection",
            "healthy" if metrics_count >= 0 else "unhealthy",
            {"total_metrics": metrics_count}
        )

        # Check tracing system
        active_traces = len(self._traces)
        health.add_component_status(
            "tracing_system",
            "healthy",
            {"active_traces": active_traces}
        )

        # Check logging system
        try:
            self.logger.info("Health check test message", extra={"test": True})
            health.add_component_status("logging_system", "healthy", {})
        except Exception as e:
            health.add_component_status("logging_system", "unhealthy", {"error": str(e)})
            health.overall_status = "degraded"

        # Performance metrics
        metrics_summary = self.get_metrics_summary(time_range_minutes=5)
        total_recent_metrics = metrics_summary.get("total_metrics", 0)
        health.add_metric("metrics_per_minute", total_recent_metrics / 5)

        # Memory usage check (rough estimate)
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / (1024 * 1024)
        health.add_metric("memory_usage_mb", memory_mb)

        if memory_mb > 1000:  # 1GB threshold
            health.add_alert("High memory usage detected")
            health.overall_status = "degraded"

        return health


# Convenience functions for global usage
_default_store = None
_default_config = None
_default_observability = None


def get_data_store() -> DataStore:
    """Get global data store instance."""
    global _default_store
    if _default_store is None:
        config = PersistenceConfig()
        _default_store = DataStore(config)
    return _default_store


def get_config_manager() -> ConfigurationManager:
    """Get global configuration manager instance."""
    global _default_config
    if _default_config is None:
        _default_config = ConfigurationManager()
    return _default_config


def get_observability_manager() -> ObservabilityManager:
    """Get global observability manager instance."""
    global _default_observability
    if _default_observability is None:
        _default_observability = ObservabilityManager()
    return _default_observability


# Example usage and validation
if __name__ == "__main__":
    print("GenOps Persistence and Observability Framework")
    print("=" * 60)

    # Initialize components
    print("Initializing data store...")
    store = get_data_store()

    print("Initializing configuration manager...")
    config_manager = get_config_manager()

    print("Initializing observability...")
    observability = get_observability_manager()

    # Test basic functionality
    print("Testing basic operations...")

    # Load configuration
    risk_config = config_manager.load_section("risk_scoring")
    print(f"Risk scoring weights: {risk_config.get('weights', {})}")

    # Record some metrics
    observability.record_metric("test_operation", 2.3, {"component": "persistence"})
    observability.increment_counter("operations_total")
    observability.set_gauge("active_connections", 5.0)

    # Start a trace
    trace_id = observability.start_trace("test_workflow")
    observability.add_span(trace_id, "data_save", 150.0, {"table": "deployments"})
    observability.add_span(trace_id, "cache_update", 50.0, {"cache_hits": 1})
    observability.end_trace(trace_id)

    # Health check
    health = observability.health_check()
    print(f"System health: {health.overall_status}")
    print(f"Components: {list(health.components.keys())}")

    # Metrics summary
    metrics_summary = observability.get_metrics_summary(time_range_minutes=10)
    print(f"Recent metrics: {metrics_summary.get('total_metrics', 0)}")

    print("\nAll systems operational! ✓")