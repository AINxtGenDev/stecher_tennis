FROM python:3.12-slim AS builder

WORKDIR /build

# Install system build deps needed for C extensions (bcrypt, greenlet)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY docker-requirements.txt .
RUN python -m venv /venv && \
    /venv/bin/pip install --no-cache-dir --upgrade pip && \
    /venv/bin/pip install --no-cache-dir -r docker-requirements.txt

# Stage 2: Runtime — clean image, no build tools
FROM python:3.12-slim AS runtime

# Non-root user (UID/GID 1000 is convention; avoids conflicts with host)
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid 1000 --no-create-home --shell /sbin/nologin appuser

WORKDIR /app

# Copy venv from builder
COPY --from=builder /venv /venv

# Copy application files
COPY --chown=appuser:appgroup app.py schema.sql initial_players.json ./
COPY --chown=appuser:appgroup templates/ templates/
COPY --chown=appuser:appgroup static/ static/
COPY --chown=appuser:appgroup entrypoint.sh ./

# Create data directory with correct permissions
RUN mkdir -p /app/data && chown appuser:appgroup /app/data

RUN chmod +x /app/entrypoint.sh

USER appuser

ENV PATH="/venv/bin:$PATH"
ENV DB_PATH=/app/data/tennis.db

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

ENTRYPOINT ["./entrypoint.sh"]
