# Epic 6: Backend Deployment & Home Assistant Connection - Project Plan

**Document ID:** EPIC-6-DEPLOYMENT-2026
**Epic Title:** Backend Deployment & Home Assistant Connection (Docker + Compose)
**Status:** Planned
**Target Completion:** 2026-05-26
**Estimated Duration:** 2 weeks (~80 hours)
**Last Updated:** 2026-03-24
**Deployment Strategy:** Docker + Docker Compose for complete system orchestration

---

## Executive Summary

Epic 6 establishes production-ready backend deployment infrastructure with Docker containerization and robust Home Assistant integration. This epic transforms the development Chatterbox system into a production-grade deployable service using Docker and Docker Compose for complete system orchestration. The deployment strategy enables single-command deployment of the entire Chatterbox backend, database, and supporting services. The focus is creating a stable, maintainable deployment that can scale across multiple devices while maintaining high reliability and observability.

---

## Goals & Success Criteria

### Primary Goals
1. Containerize backend using Docker with multi-stage builds
2. Create docker-compose environment for full system deployment
3. Establish stable Wyoming protocol connection to Home Assistant
4. Implement comprehensive logging and monitoring integration
5. Create deployment automation and rollback procedures
6. Enable scalable multi-device deployment
7. Establish production-grade operational procedures

### Success Criteria
- [ ] Docker image builds reliably with <5 min build time
- [ ] docker-compose brings entire system up in single command
- [ ] Wyoming protocol connection stable for >24 hours
- [ ] All system events logged with structured format
- [ ] Log aggregation working with 99% log delivery
- [ ] Deployment takes <15 minutes for new instance
- [ ] Rollback procedure works without data loss
- [ ] System automatically recovers from common failures
- [ ] Performance within SLA (latency, throughput)
- [ ] Monitoring/alerting operational for production

---

## Dependencies & Prerequisites

### Hard Dependencies
- **Epic 4 (LLM Integration):** Backend system functional
- **Epic 5 (Persistence):** Database integration complete
- **Epic 2 (Observability):** Monitoring infrastructure designed

### Prerequisites
- Docker and Docker Compose installed on deployment host
- Home Assistant instance running and accessible
- Network connectivity between deployment host and HA
- Sufficient disk space for logs and database (10+ GB recommended)
- MQTT broker available (local or remote)
- Secrets management system available

### Blockers to Identify
- Home Assistant API stability
- Network connectivity issues
- Resource constraints on deployment hardware
- Certificate/TLS requirements

---

## Detailed Task Breakdown

### Task 6.1: Dockerfile Creation & Optimization
**Objective:** Create production-grade Dockerfile with multi-stage builds
**Estimated Hours:** 8
**Acceptance Criteria:**
- [ ] Multi-stage Dockerfile reduces image size <500MB
- [ ] Python dependencies frozen with exact versions
- [ ] Security: non-root user, minimal base image
- [ ] Build process reproducible and automated
- [ ] Image scanned for vulnerabilities
- [ ] Health check mechanism built in

**Implementation Details:**

**Multi-Stage Dockerfile:**

```dockerfile
# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Build wheels
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 chatterbox

# Copy wheels from builder
COPY --from=builder /build/wheels /wheels

# Install wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt

# Copy application code
COPY --chown=chatterbox:chatterbox . .

# Switch to non-root user
USER chatterbox

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Expose ports
EXPOSE 8000

# Run application
CMD ["python", "-m", "chatterbox.main"]
```

**Image Optimization:**
- Use slim base image (not full Python image)
- Multi-stage to avoid build tools in final image
- Remove package manager caches
- Minimal final image size

**Testing Plan:**
- Build succeeds and produces working container
- Image size <500MB
- Security scan passes
- Health check works

---

### Task 6.2: Docker Compose Configuration
**Objective:** Create docker-compose for full stack deployment
**Estimated Hours:** 10
**Depends On:** Task 6.1
**Acceptance Criteria:**
- [ ] Brings up backend, DB, MQTT broker
- [ ] Volume mounts for persistence
- [ ] Environment configuration via .env
- [ ] Network isolation between services
- [ ] Port mappings clear and documented
- [ ] Health checks for all services
- [ ] Logs directed to stdout for aggregation

**Implementation Details:**

**docker-compose.yml:**

```yaml
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: chatterbox-postgres
    environment:
      POSTGRES_USER: chatterbox
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: chatterbox
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init_db.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U chatterbox"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - chatterbox

  # Redis Cache (optional)
  redis:
    image: redis:7-alpine
    container_name: chatterbox-redis
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - chatterbox

  # MQTT Broker
  mosquitto:
    image: eclipse-mosquitto:2-alpine
    container_name: chatterbox-mosquitto
    ports:
      - "1883:1883"
      - "9001:9001"
    volumes:
      - ./mosquitto.conf:/mosquitto/config/mosquitto.conf
      - mosquitto_data:/mosquitto/data
      - mosquitto_logs:/mosquitto/log
    healthcheck:
      test: ["CMD", "mosquitto_sub", "-h", "localhost", "-t", "$SYS/broker/clients/connected"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - chatterbox

  # Chatterbox Backend
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: chatterbox-backend
    environment:
      DATABASE_URL: postgresql://chatterbox:${DB_PASSWORD}@postgres:5432/chatterbox
      REDIS_URL: redis://redis:6379/0
      MQTT_HOST: mosquitto
      MQTT_PORT: 1883
      HOME_ASSISTANT_URL: ${HA_URL}
      HOME_ASSISTANT_TOKEN: ${HA_TOKEN}
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      mosquitto:
        condition: service_healthy
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - chatterbox
    restart: unless-stopped

volumes:
  postgres_data:
  mosquitto_data:
  mosquitto_logs:

networks:
  chatterbox:
    driver: bridge
```

**Environment Variables (.env.example):**

```bash
# Database
DB_PASSWORD=secure_password_here

# Home Assistant
HA_URL=http://homeassistant:8123
HA_TOKEN=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...

# Logging
LOG_LEVEL=INFO

# Application
APP_ENV=production
```

**Testing Plan:**
- Compose up brings all services online
- All services pass health checks
- Services communicate correctly
- Volume persistence works
- Env variable substitution works

---

### Task 6.3: Logging & Log Aggregation Configuration
**Objective:** Configure structured logging across all services
**Estimated Hours:** 10
**Depends On:** Task 6.2
**Acceptance Criteria:**
- [ ] All services output structured JSON logs
- [ ] Log level configurable per service
- [ ] Logs aggregated to single log file
- [ ] Log rotation configured
- [ ] Sensitive data redacted from logs
- [ ] Timestamp in ISO 8601 format
- [ ] Log searching capability
- [ ] Integration with monitoring system

**Implementation Details:**

**Python Logging Configuration:**

```python
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """Format logs as JSON for structured logging"""

    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields if present
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "conversation_id"):
            log_data["conversation_id"] = record.conversation_id
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms

        # Redact sensitive data
        if "password" in record.getMessage().lower():
            log_data["message"] = "***REDACTED***"

        return json.dumps(log_data)


def setup_logging(log_level=logging.INFO):
    """Configure logging for entire application"""

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Console handler (stdout for Docker)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter())

    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        "/app/logs/chatterbox.log",
        maxBytes=100_000_000,  # 100 MB
        backupCount=10
    )
    file_handler.setFormatter(JSONFormatter())

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Set specific loggers
    logging.getLogger("chatterbox").setLevel(log_level)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)

    return root_logger
```

**Log Aggregation Script:**

```bash
#!/bin/bash
# aggregate_logs.sh - Combine logs from all services

TIMESTAMP=$(date -u +"%Y-%m-%d")
AGGREGATE_FILE="/app/logs/aggregate_${TIMESTAMP}.log"

# Collect logs from all containers
docker compose logs --no-color --timestamps > "${AGGREGATE_FILE}"

# Compress old logs
find /app/logs -name "aggregate_*.log" -mtime +30 -exec gzip {} \;

echo "Logs aggregated to ${AGGREGATE_FILE}"
```

**Testing Plan:**
- Verify JSON log format
- Test log rotation at boundaries
- Verify sensitive data redaction
- Test with high volume logging
- Validate searchability of logs

---

### Task 6.4: Wyoming Protocol Service Integration
**Objective:** Establish reliable Wyoming protocol connection to HA
**Estimated Hours:** 12
**Depends On:** Task 6.2
**Acceptance Criteria:**
- [ ] Wyoming protocol service runs as separate process
- [ ] Connection to HA established and stable
- [ ] Handles HA disconnections gracefully
- [ ] Reconnection automatic with exponential backoff
- [ ] Service discovery or explicit configuration
- [ ] Logged for monitoring
- [ ] Latency tracking (<1s for round trip)

**Implementation Details:**

**Wyoming Service Manager:**

```python
import asyncio
from typing import Callable, Optional
import logging

class WyomingServiceManager:
    """Manages Wyoming protocol connection to Home Assistant"""

    def __init__(self, ha_url: str, port: int = 10700):
        self.ha_url = ha_url
        self.port = port
        self.logger = logging.getLogger(__name__)
        self.connected = False
        self.connection_attempts = 0
        self.max_retries = 5
        self.base_backoff = 1  # seconds

    async def connect(self):
        """Establish connection to Wyoming service"""
        while self.connection_attempts < self.max_retries:
            try:
                reader, writer = await asyncio.open_connection(
                    self.ha_url, self.port
                )
                self.connected = True
                self.connection_attempts = 0
                self.logger.info(
                    f"Connected to Wyoming at {self.ha_url}:{self.port}"
                )
                return reader, writer

            except ConnectionError as e:
                self.connection_attempts += 1
                backoff = self.base_backoff * (2 ** self.connection_attempts)
                self.logger.warning(
                    f"Connection attempt {self.connection_attempts} failed. "
                    f"Retrying in {backoff}s: {e}"
                )
                await asyncio.sleep(backoff)

        raise ConnectionError(f"Failed to connect to Wyoming after {self.max_retries} attempts")

    async def send_audio(self, audio_data: bytes) -> str:
        """Send audio to Wyoming and get response"""
        if not self.connected:
            raise RuntimeError("Not connected to Wyoming")

        try:
            reader, writer = await self.connect()

            # Send audio in chunks
            writer.write(audio_data)
            await writer.drain()

            # Read response
            response = await reader.read(4096)
            return response.decode()

        except Exception as e:
            self.connected = False
            self.logger.error(f"Error sending audio: {e}")
            raise

    async def health_check(self):
        """Periodic health check of connection"""
        while True:
            try:
                if not self.connected:
                    await self.connect()
                # Connection test by sending empty message
                # (Wyoming protocol specific)
            except Exception as e:
                self.logger.error(f"Health check failed: {e}")
                self.connected = False

            await asyncio.sleep(60)  # Check every minute
```

**Service Registration:**

```python
# Registration with Home Assistant
async def register_with_home_assistant(ha_client, service_info):
    """Register Chatterbox service in Home Assistant"""

    device_registry = await ha_client.async_get_device_registry()

    service = {
        "domain": "wyoming",
        "service": "register_satellite",
        "data": {
            "name": "Chatterbox Backend",
            "host": service_info["host"],
            "port": service_info["port"],
            "protocol": "wyoming"
        }
    }

    await ha_client.call_service(**service)
    logger.info("Registered with Home Assistant")
```

**Testing Plan:**
- Connection to Wyoming succeeds
- Connection survives HA restart
- Reconnection works with exponential backoff
- Latency tracking accurate
- Handles network failures gracefully

---

### Task 6.5: Health Checks & Self-Healing
**Objective:** Implement automatic detection and recovery from failures
**Estimated Hours:** 8
**Depends On:** Task 6.4
**Acceptance Criteria:**
- [ ] Service health monitored continuously
- [ ] Automatic restart on failure
- [ ] Dependency health checked (DB, HA, MQTT)
- [ ] Graceful shutdown on terminal failure
- [ ] Health status reported to monitoring
- [ ] Recovery time <2 minutes

**Implementation Details:**

**Health Check Service:**

```python
import asyncio
from datetime import datetime
from typing import Dict

class HealthChecker:
    """Monitor health of all dependencies"""

    def __init__(self, config):
        self.config = config
        self.health_status = {
            "database": {"healthy": False, "last_check": None},
            "wyoming": {"healthy": False, "last_check": None},
            "mqtt": {"healthy": False, "last_check": None},
            "api": {"healthy": False, "last_check": None},
        }

    async def check_database(self) -> bool:
        """Check database connectivity"""
        try:
            async with get_db() as db:
                result = await db.execute("SELECT 1")
                return result.fetchone() is not None
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    async def check_wyoming(self) -> bool:
        """Check Wyoming service connection"""
        try:
            # Attempt connection and test message
            reader, writer = await asyncio.open_connection(
                self.config.WYOMING_HOST,
                self.config.WYOMING_PORT,
                timeout=5
            )
            writer.close()
            return True
        except Exception as e:
            logger.error(f"Wyoming health check failed: {e}")
            return False

    async def check_mqtt(self) -> bool:
        """Check MQTT broker connection"""
        try:
            async with aiomqtt.connect(self.config.MQTT_HOST) as client:
                # Send test publish
                await client.publish("$SYS/check", b"test")
                return True
        except Exception as e:
            logger.error(f"MQTT health check failed: {e}")
            return False

    async def run_checks(self):
        """Run all health checks periodically"""
        while True:
            self.health_status["database"]["healthy"] = await self.check_database()
            self.health_status["database"]["last_check"] = datetime.utcnow()

            self.health_status["wyoming"]["healthy"] = await self.check_wyoming()
            self.health_status["wyoming"]["last_check"] = datetime.utcnow()

            self.health_status["mqtt"]["healthy"] = await self.check_mqtt()
            self.health_status["mqtt"]["last_check"] = datetime.utcnow()

            # Determine overall health
            critical = [
                self.health_status["database"]["healthy"],
                self.health_status["wyoming"]["healthy"],
            ]

            if not all(critical):
                logger.critical("Critical service down")
                # Trigger alerting/restart

            await asyncio.sleep(30)  # Check every 30 seconds

    def get_status(self) -> Dict:
        """Return current health status"""
        return self.health_status
```

**API Health Endpoint:**

```python
@app.get("/health")
async def health_check(health_checker: HealthChecker = Depends()):
    status = health_checker.get_status()
    is_healthy = all(
        s["healthy"] for s in status.values() if s["critical"]
    )
    return {
        "status": "healthy" if is_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "components": status
    }
```

**Testing Plan:**
- Each service failure detected within 30 seconds
- Recovery from DB disconnection
- Recovery from Wyoming disconnection
- Cascading failure handling
- Health endpoint accuracy

---

### Task 6.6: Environment Configuration Management
**Objective:** Manage configuration across dev/staging/production
**Estimated Hours:** 6
**Depends On:** Task 6.2
**Acceptance Criteria:**
- [ ] Configuration from environment variables
- [ ] Secrets stored securely (not in code)
- [ ] Configuration validation at startup
- [ ] Different profiles for dev/staging/prod
- [ ] .env file support with overrides
- [ ] Documentation of all configuration options

**Implementation Details:**

**Configuration Module:**

```python
from pydantic import BaseSettings, validator
from typing import Optional

class Settings(BaseSettings):
    """Application configuration"""

    # Database
    database_url: str
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Wyoming
    wyoming_host: str
    wyoming_port: int = 10700

    # MQTT
    mqtt_host: str
    mqtt_port: int = 1883
    mqtt_username: Optional[str] = None
    mqtt_password: Optional[str] = None

    # Home Assistant
    home_assistant_url: str
    home_assistant_token: str

    # Application
    app_env: str = "development"  # development, staging, production
    log_level: str = "INFO"
    debug: bool = False

    # Monitoring
    sentry_dsn: Optional[str] = None

    @validator("database_url")
    def validate_database_url(cls, v):
        if not v.startswith(("postgresql://", "sqlite:///")):
            raise ValueError("Invalid database URL")
        return v

    @validator("wyoming_host")
    def validate_wyoming_host(cls, v):
        if not v:
            raise ValueError("Wyoming host required")
        return v

    class Config:
        env_file = ".env"
        case_sensitive = False

# Load settings
settings = Settings()

# Validate required settings
def validate_settings():
    """Ensure all critical settings present"""
    required = [
        "database_url",
        "wyoming_host",
        "home_assistant_url",
        "home_assistant_token"
    ]
    for setting in required:
        if not getattr(settings, setting):
            raise ValueError(f"Missing required setting: {setting}")
```

**Configuration Profiles:**

```yaml
# config/development.yaml
database_url: sqlite:///./dev.db
log_level: DEBUG
debug: true

# config/staging.yaml
database_url: postgresql://user:pass@staging-db/chatterbox
log_level: INFO
debug: false

# config/production.yaml
database_url: postgresql://user:pass@prod-db/chatterbox
log_level: WARNING
debug: false
```

**Testing Plan:**
- Validate required settings present
- Test environment variable override
- Test configuration validation
- Test different profiles

---

### Task 6.7: Deployment Documentation & Runbooks
**Objective:** Create comprehensive deployment guides
**Estimated Hours:** 8
**Depends On:** All deployment tasks
**Acceptance Criteria:**
- [ ] Quick start guide for basic deployment
- [ ] Detailed setup guide for production
- [ ] Configuration reference documentation
- [ ] Troubleshooting common issues
- [ ] Rollback procedures documented
- [ ] Scaling guidelines
- [ ] Operations runbooks

**Implementation Details:**

**Documentation Structure:**

1. **Quick Start Guide**
   - Prerequisites
   - Clone and configure
   - docker-compose up
   - Verify health

2. **Production Setup**
   - Hardware requirements
   - Network configuration
   - Security hardening
   - Backup strategy
   - Monitoring setup

3. **Configuration Guide**
   - All environment variables
   - Home Assistant setup
   - MQTT configuration
   - Database setup

4. **Troubleshooting**
   - Common errors and solutions
   - Log analysis
   - Service restart procedures
   - Debug mode activation

5. **Operations**
   - Daily checks
   - Backup procedures
   - Update procedures
   - Recovery procedures

**Testing Plan:**
- New user follows quick start successfully
- Production setup guide tested end-to-end
- All troubleshooting scenarios documented

---

### Task 6.8: Monitoring & Alerting Integration
**Objective:** Integrate with monitoring system for production alerts
**Estimated Hours:** 8
**Depends On:** Tasks 6.3, 6.5
**Acceptance Criteria:**
- [ ] Metrics exported for Prometheus
- [ ] Key alerts defined and tested
- [ ] Alert escalation configured
- [ ] Performance baselines established
- [ ] Dashboard created
- [ ] Integration with existing monitoring

**Implementation Details:**

**Prometheus Metrics:**

```python
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
request_count = Counter(
    'chatterbox_requests_total',
    'Total requests',
    ['method', 'endpoint']
)

request_duration = Histogram(
    'chatterbox_request_duration_seconds',
    'Request duration',
    ['method', 'endpoint']
)

active_conversations = Gauge(
    'chatterbox_active_conversations',
    'Number of active conversations'
)

wyoming_connection_status = Gauge(
    'chatterbox_wyoming_connected',
    'Wyoming connection status (1=connected)'
)

database_pool_size = Gauge(
    'chatterbox_db_pool_size',
    'Database connection pool size'
)

# Metrics endpoint
@app.get("/metrics")
async def metrics():
    return Response(
        generate_latest(),
        media_type="text/plain; charset=utf-8"
    )
```

**Alert Rules (Prometheus):**

```yaml
groups:
- name: chatterbox
  rules:
  - alert: WyomingDisconnected
    expr: chatterbox_wyoming_connected == 0
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "Wyoming service disconnected"

  - alert: HighLatency
    expr: chatterbox_request_duration_seconds > 5
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High request latency detected"

  - alert: DatabasePoolExhausted
    expr: chatterbox_db_pool_size == 0
    labels:
      severity: critical
    annotations:
      summary: "Database connection pool exhausted"
```

**Testing Plan:**
- Metrics collected and exported
- Alerts fire at appropriate thresholds
- Dashboard displays correct data
- Escalation procedures work

---

### Task 6.9: Security Hardening & Secrets Management
**Objective:** Secure deployment for production environment
**Estimated Hours:** 8
**Depends On:** Task 6.2
**Acceptance Criteria:**
- [ ] Secrets not in code or logs
- [ ] TLS/SSL for external connections
- [ ] Network policies restrict access
- [ ] Database password rotation procedure
- [ ] API key management
- [ ] Security scan of dependencies
- [ ] Authentication for all endpoints

**Implementation Details:**

**Secrets Management (using HashiCorp Vault):**

```python
import hvac

class SecretManager:
    def __init__(self, vault_addr: str, vault_token: str):
        self.client = hvac.Client(url=vault_addr, token=vault_token)

    def get_secret(self, path: str) -> dict:
        """Retrieve secret from Vault"""
        response = self.client.secrets.kv.read_secret_version(path=path)
        return response['data']['data']

    def get_database_password(self) -> str:
        """Get database password"""
        secrets = self.get_secret('chatterbox/database')
        return secrets['password']

    def get_ha_token(self) -> str:
        """Get Home Assistant token"""
        secrets = self.get_secret('chatterbox/home_assistant')
        return secrets['token']
```

**TLS Configuration:**

```python
# Require HTTPS in production
if settings.app_env == "production":
    from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
    app.add_middleware(HTTPSRedirectMiddleware)

    # CORS for specific origins only
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.home_assistant_url],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
```

**Testing Plan:**
- Secrets not exposed in logs
- TLS connections work correctly
- Network policies enforced
- Security scan passes

---

### Task 6.10: Scaling & Multi-Instance Deployment
**Objective:** Enable deployment across multiple devices
**Estimated Hours:** 8
**Depends On:** Tasks 6.2, 6.4
**Acceptance Criteria:**
- [ ] Multiple backend instances supported
- [ ] Shared database with coordination
- [ ] Load balancing configured
- [ ] Device discovery working
- [ ] Context sharing between instances
- [ ] No conflicts in multi-instance setup

**Implementation Details:**

**Load Balancer Configuration (nginx):**

```nginx
upstream chatterbox_backend {
    least_conn;
    server backend1:8000;
    server backend2:8000;
    server backend3:8000;
}

server {
    listen 80;
    server_name chatterbox.local;

    location / {
        proxy_pass http://chatterbox_backend;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header Host $host;
    }

    location /health {
        access_log off;
        proxy_pass http://chatterbox_backend/health;
    }
}
```

**Multi-Instance Coordination (using Redis):**

```python
class InstanceCoordinator:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.instance_id = str(uuid4())

    async def register_instance(self):
        """Register this instance in cluster"""
        await self.redis.setex(
            f"instance:{self.instance_id}",
            ttl=60,
            value=json.dumps({
                "started": datetime.utcnow().isoformat(),
                "version": VERSION,
                "host": self.host
            })
        )

    async def get_active_instances(self) -> List[str]:
        """Get list of active instances"""
        keys = await self.redis.keys("instance:*")
        return [k.decode().split(":")[-1] for k in keys]

    async def coordinate_on_message(self, message_id: str):
        """Ensure only one instance processes message"""
        lock = await self.redis.set(
            f"lock:{message_id}",
            self.instance_id,
            nx=True,
            ex=30
        )
        return lock == 1  # True if got lock
```

**Testing Plan:**
- Multiple instances start successfully
- Load balanced correctly
- No duplicate processing
- Failover works correctly

---

### Task 6.11: Backup & Recovery Procedures
**Objective:** Ensure data safety with backup and recovery
**Estimated Hours:** 6
**Depends On:** Task 6.2
**Acceptance Criteria:**
- [ ] Automated daily backups
- [ ] Backup verification
- [ ] Recovery procedure tested
- [ ] Recovery time <1 hour
- [ ] Off-site backup copy
- [ ] Backup retention policy

**Implementation Details:**

**Backup Script:**

```bash
#!/bin/bash
# backup_database.sh

BACKUP_DIR="/backups"
DB_NAME="chatterbox"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/chatterbox_${TIMESTAMP}.sql.gz"

# Create backup
docker exec chatterbox-postgres pg_dump -U chatterbox chatterbox | \
    gzip > "${BACKUP_FILE}"

# Verify backup
if ! gunzip -t "${BACKUP_FILE}"; then
    echo "Backup verification failed!"
    rm "${BACKUP_FILE}"
    exit 1
fi

# Keep only 30 days of backups
find "${BACKUP_DIR}" -name "chatterbox_*.sql.gz" -mtime +30 -delete

# Upload to S3 (or other off-site storage)
aws s3 cp "${BACKUP_FILE}" s3://backups/chatterbox/

echo "Backup completed: ${BACKUP_FILE}"
```

**Cron Job:**

```bash
# /etc/cron.d/chatterbox-backup
# Daily backup at 2 AM
0 2 * * * root /app/scripts/backup_database.sh
```

**Recovery Procedure:**

```bash
#!/bin/bash
# recover_database.sh <backup_file>

BACKUP_FILE=$1

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "Backup file not found: ${BACKUP_FILE}"
    exit 1
fi

# Stop application
docker compose down

# Create new database
docker compose up -d postgres
sleep 10

# Restore from backup
gunzip -c "${BACKUP_FILE}" | \
    docker exec -i chatterbox-postgres \
    psql -U chatterbox -d chatterbox

# Restart application
docker compose up -d

echo "Recovery complete from ${BACKUP_FILE}"
```

**Testing Plan:**
- Backups created daily
- Backup file integrity verified
- Recovery successful and complete
- Recovery doesn't lose data

---

### Task 6.12: Integration Testing & Production Validation
**Objective:** Comprehensive testing before production deployment
**Estimated Hours:** 10
**Depends On:** All deployment tasks
**Acceptance Criteria:**
- [ ] All services integrated and working
- [ ] End-to-end conversation flow tested
- [ ] Performance meets SLA
- [ ] Reliability tested (24-hour stability)
- [ ] Failover scenarios tested
- [ ] Monitoring and alerting verified
- [ ] Documentation complete and verified

**Implementation Details:**

**Integration Test Suite:**

```python
@pytest.mark.integration
class TestIntegration:

    @pytest.mark.asyncio
    async def test_full_conversation_flow(self):
        """Test complete conversation: record → LLM → response"""
        # Start service
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Create conversation
            resp = await client.post("/conversations", json={"title": "Test"})
            assert resp.status_code == 201
            conversation_id = resp.json()["id"]

            # Send user message
            resp = await client.post(
                f"/conversations/{conversation_id}/messages",
                json={"content": "What is 2+2?"}
            )
            assert resp.status_code == 200

            # Verify LLM response
            assert "4" in resp.json()["response"]

    @pytest.mark.asyncio
    async def test_wyoming_integration(self):
        """Test Wyoming protocol connection and message flow"""
        # Verify connection established
        assert wyoming_manager.connected

        # Send test audio
        result = await wyoming_manager.send_audio(test_audio_data)
        assert result is not None

    @pytest.mark.asyncio
    async def test_persistence_across_restart(self):
        """Test conversation persists across service restart"""
        # Create and store conversation
        conv_id = await create_test_conversation()
        await add_message(conv_id, "Test message")

        # Restart service
        await restart_service()

        # Verify message still there
        messages = await get_messages(conv_id)
        assert len(messages) > 0

    @pytest.mark.asyncio
    async def test_health_checks(self):
        """Verify all health checks pass"""
        resp = await client.get("/health")
        assert resp.status_code == 200
        health = resp.json()
        assert health["status"] == "healthy"
        assert health["components"]["database"]["healthy"]
        assert health["components"]["wyoming"]["healthy"]
```

**Performance Test:**

```python
@pytest.mark.performance
async def test_latency_sla():
    """Verify latency under load meets SLA (<5s for simple query)"""
    client = AsyncClient(app=app)

    response_times = []
    for _ in range(100):
        start = time.time()
        await client.post(
            "/conversations/123/messages",
            json={"content": "Test"}
        )
        response_times.append(time.time() - start)

    average = sum(response_times) / len(response_times)
    p95 = sorted(response_times)[95]

    assert average < 2.0, f"Average latency {average}s exceeds SLA"
    assert p95 < 5.0, f"P95 latency {p95}s exceeds SLA"
```

**Testing Plan:**
- Execute full integration test suite
- Run 24-hour stability test
- Load test with expected throughput
- Verify all monitoring and alerts
- Test failover scenarios
- Validate documentation accuracy

---

### Task 6.13: Post-Deployment Verification & Documentation
**Objective:** Verify production deployment and finalize documentation
**Estimated Hours:** 6
**Depends On:** Task 6.12
**Acceptance Criteria:**
- [ ] All services running in production
- [ ] Health checks passing
- [ ] Monitoring and alerting active
- [ ] Backups running automatically
- [ ] Logs being aggregated
- [ ] Team trained on operations
- [ ] Runbooks accessible

**Implementation Details:**

**Deployment Checklist:**

```markdown
## Deployment Verification Checklist

### Pre-Deployment
- [ ] Code reviewed and merged
- [ ] Tests passing (unit, integration, performance)
- [ ] Secrets configured in vault
- [ ] Database migrations created
- [ ] Backups configured and tested
- [ ] Monitoring setup tested
- [ ] Communication plan in place

### Deployment Day
- [ ] Backup of current system
- [ ] Services brought up in docker-compose
- [ ] Health checks passing
- [ ] Initial data load complete
- [ ] All endpoints responding
- [ ] Wyoming connection established

### Post-Deployment (24 hours)
- [ ] No errors in logs
- [ ] Performance metrics within SLA
- [ ] All alerts firing correctly
- [ ] Database performing well
- [ ] Users reporting no issues
- [ ] Backup executed successfully
```

**Testing Plan:**
- All items in checklist verified
- Production environment stable
- Team ready for operations

---

## Technical Implementation Details

### Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│           Home Assistant                             │
│  ┌──────────────────────────────────────────────┐   │
│  │ Wyoming Protocol Service                     │   │
│  │ (STT, TTS, Satellites)                      │   │
│  └──────────────────────────────────────────────┘   │
│                      │                               │
└──────────────────────┼───────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
   (TCP/IP)                       (MQTT)
        │                             │
        │     ┌─────────────────────┐ │
        │     │ Load Balancer/Proxy │ │
        │     └──────────┬──────────┘ │
        │                │            │
        │   ┌────────────┼─────────────┤
        │   │            │            │
        │   ▼            ▼            ▼
    ┌───────────┐ ┌───────────┐ ┌───────────┐
    │ Backend 1 │ │ Backend 2 │ │ Backend 3 │
    │ (Docker)  │ │ (Docker)  │ │ (Docker)  │
    └────┬──────┘ └────┬──────┘ └────┬──────┘
         │             │             │
         └─────────────┼─────────────┘
                       │
         ┌─────────────┴─────────────────┐
         │                               │
         ▼                               ▼
    ┌──────────────┐          ┌──────────────────┐
    │ PostgreSQL   │          │ MQTT Broker      │
    │ Database     │          │ (Mosquitto)      │
    │              │          │                  │
    └──────────────┘          └──────────────────┘
         │
         │
    ┌────▼──────────┐
    │ Backup System │
    │ (Daily to S3) │
    └───────────────┘

External Services:
    ├── Monitoring/Prometheus
    ├── Log Aggregation
    ├── Alert System
    └── S3 for Backups
```

### Service Communication

```
Device Audio → Wyoming → Load Balancer → Backend Instances
                                              ↓
                                        Database
                                              ↓
                                        LLM Processing
                                              ↓
                                        TTS Generation
                                              ↓
Response Audio ← Wyoming ← Load Balancer ← Backend
```

---

## Testing Plan

### Unit Tests
- Configuration validation
- Logging format verification
- Health check logic
- Metrics collection

### Integration Tests
- Full conversation flow with all services
- Wyoming protocol communication
- Database persistence
- MQTT message delivery

### System Tests
- 24-hour stability
- Load testing (100+ concurrent users)
- Failover scenarios
- Recovery procedures

### Acceptance Tests
- Deployment takes <15 minutes
- All health checks pass
- Performance meets SLA
- Monitoring/alerting functional

---

## Estimated Timeline

**Week 1 (40 hours):**
- Task 6.1: Dockerfile (8 hrs)
- Task 6.2: Docker Compose (10 hrs)
- Task 6.3: Logging (10 hrs)
- Task 6.4: Wyoming Integration (12 hrs - continuation)

**Week 2 (40 hours):**
- Task 6.4: Wyoming Integration (continued from 4 hrs)
- Task 6.5: Health Checks (8 hrs)
- Task 6.6: Configuration (6 hrs)
- Task 6.7: Documentation (8 hrs)
- Task 6.8: Monitoring (8 hrs)
- Tasks 6.9-6.13: Security, Scaling, Backup, Testing, Verification (26 hrs total)

**Total: ~80 hours (~2 weeks at 40 hrs/week)**

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-----------|--------|-----------|
| Wyoming connection instability | Medium | High | Robust reconnection logic; health checks; fallback |
| Performance degradation at scale | Medium | High | Load test early; optimize queries; caching |
| Data loss during migration | Low | Critical | Backup first; test on copy; rollback ready |
| Security vulnerabilities | Medium | High | Security scan; code review; secrets management |
| Configuration complexity | Medium | Medium | Clear documentation; configuration validation |
| Multi-instance coordination issues | Low | Medium | Redis-based coordination; locking mechanisms |
| Backup/recovery untested | Low | Critical | Test recovery procedures regularly |
| Monitoring alert fatigue | Medium | Low | Tune alert thresholds carefully; combine rules |

---

## Acceptance Criteria (Epic-Level)

### Functional
- [ ] Backend deployed and running in Docker
- [ ] Connection to HA stable and maintained
- [ ] All services integrated and working
- [ ] Full conversation flow end-to-end
- [ ] Persistence working across restarts
- [ ] Multi-instance deployment possible

### Performance
- [ ] Conversation latency <5 seconds
- [ ] Audio processing <500ms
- [ ] Database queries <200ms
- [ ] System handles expected load
- [ ] Memory footprint <500MB per instance

### Reliability
- [ ] 99% uptime target
- [ ] Automatic failure recovery
- [ ] Health checks <30 second detection time
- [ ] Data backed up daily
- [ ] Recovery time <1 hour

### Operational
- [ ] Monitoring and alerting working
- [ ] Logs aggregated and searchable
- [ ] Runbooks documented
- [ ] Deployment fully automated
- [ ] Team trained on operations

---

## Link to Master Plan

**Master Plan Reference:** [master-plan.md](master-plan.md)

This epic enables production-ready deployment as outlined in Phase 3-4 of the master plan. It transforms the development system into an operationally-ready service that can be deployed to production and scaled across multiple devices.

**Dependencies Met by Previous Epics:**
- Epic 1: Foundation framework established
- Epic 4: LLM system operational
- Epic 5: Persistence layer ready

**Enables Next Epics:**
- Epic 7: Recording & PCM streaming requires stable backend
- Epic 8+: Advanced features depend on reliable backend
- Epic 11: Production monitoring/observability
- Epic 12: Documentation and maintenance

---

## Approval & Sign-Off

**Epic Owner:** [To be assigned]
**DevOps Lead:** [To be assigned]
**Security Lead:** [To be assigned]

**Approved By:**
- [ ] Epic Owner
- [ ] DevOps Lead
- [ ] Security Lead

**Approved Date:** _______________

---

**Document Owner:** Chatterbox Project Team
**Created:** 2026-03-24
**Last Updated:** 2026-03-24
**Next Review:** 2026-05-26 (Epic 4+5 completion)
