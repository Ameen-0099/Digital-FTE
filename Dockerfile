# NexusFlow Customer Success Digital FTE - Production Dockerfile
# =============================================================
# Multi-stage build for production-ready container
# Includes FastAPI API + Agent Worker + all dependencies

# =============================================================================
# STAGE 1: Builder
# =============================================================================
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# =============================================================================
# STAGE 2: Production
# =============================================================================
FROM python:3.11-slim as production

# Labels
LABEL maintainer="Digital FTE Team"
LABEL version="1.0.0"
LABEL description="NexusFlow Customer Success Digital FTE"

# Create non-root user for security
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=appuser:appgroup production/ ./production/
COPY --chown=appuser:appgroup src/ ./src/
COPY --chown=appuser:appgroup context/ ./context/

# Create necessary directories
RUN mkdir -p /app/logs /app/data/conversations && \
    chown -R appuser:appgroup /app/logs /app/data

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Default command (can be overridden in Kubernetes)
CMD ["uvicorn", "production.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# =============================================================================
# BUILD INSTRUCTIONS
# =============================================================================
# Build the image:
#   docker build -t nexusflow-digital-fte:1.0.0 .
#
# Run locally:
#   docker run -p 8000:8000 --env-file .env nexusflow-digital-fte:1.0.0
#
# Run worker only:
#   docker run --env-file .env nexusflow-digital-fte:1.0.0 python -m production.workers.message_processor
#
# Push to registry:
#   docker tag nexusflow-digital-fte:1.0.0 registry.example.com/nexusflow-digital-fte:1.0.0
#   docker push registry.example.com/nexusflow-digital-fte:1.0.0
