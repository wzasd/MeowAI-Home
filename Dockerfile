# MeowAI Home - Production Dockerfile
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e "."

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Create non-root user
RUN groupadd -r meowai && useradd -r -g meowai meowai

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ ./src/
COPY skills/ ./skills/
COPY packs/ ./packs/
COPY cat-config.json .

# Create data directory
RUN mkdir -p /app/data && chown -R meowai:meowai /app

# Switch to non-root user
USER meowai

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/monitoring/health/live || exit 1

# Expose ports
EXPOSE 8000 5173

# Environment
ENV MEOWAI_ENV=production
ENV MEOWAI_DB_PATH=/app/data/meowai.db
ENV PYTHONUNBUFFERED=1

# Start command
CMD ["python", "-m", "uvicorn", "src.web.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
