# ============================================================
# MT5 AI/ML Trading Bot - Enterprise Edition
# Dockerfile (Python 3.11 slim, multi-stage build)
# ============================================================

# --- Stage 1: builder ------------------------------------------
FROM python:3.11-slim AS builder

# Re-declare ARG TARGETARCH in this stage for multi-arch logic
ARG TARGETARCH

WORKDIR /app

# System deps for TA-Lib and PostgreSQL driver
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ make \
    libpq-dev \
    wget ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Build TA-Lib from source
# SourceForge is unreliable, using GitHub mirror
RUN wget -q https://github.com/ta-lib/ta-lib/releases/download/v0.6.4/ta-lib-0.6.4-src.tar.gz && \
    tar xf ta-lib-0.6.4-src.tar.gz && \
    cd ta-lib-0.6.4 && ./configure --prefix=/usr && make -j$(nproc) && make install && \
    cd .. && rm -rf ta-lib-0.6.4 ta-lib-0.6.4-src.tar.gz

# Create virtual environment to isolate dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Python dependencies
COPY requirements-docker.txt .

# Handle architecture-specific PyTorch installation
# For amd64, use +cpu wheels from custom index.
# For arm64, use standard wheels from PyPI (default wheels are CPU-only on Linux).
RUN pip install --no-cache-dir --upgrade pip && \
    if [ "$TARGETARCH" = "arm64" ]; then \
        sed -i 's/+cpu//g' requirements-docker.txt && \
        sed -i '/--extra-index-url/d' requirements-docker.txt; \
    fi && \
    pip install --no-cache-dir -r requirements-docker.txt

# --- Stage 2: runtime ------------------------------------------
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install runtime system deps (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy TA-Lib shared libraries from builder
COPY --from=builder /usr/lib/libta_lib* /usr/lib/
COPY --from=builder /usr/include/ta-lib /usr/include/ta-lib

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH"
ENV LD_LIBRARY_PATH="/usr/lib:$LD_LIBRARY_PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy application source and configuration
COPY src/ ./src/
COPY main.py .
COPY migrations/ ./migrations/
COPY alembic.ini .

# Create logs directory and set permissions for the non-root user
RUN mkdir -p /app/logs && chmod 777 /app/logs

# Non-root user for security
RUN useradd -m -u 1000 trader && \
    chown -R trader:trader /app
USER trader

# Expose Prometheus metrics and dashboard ports
EXPOSE 8000 8050

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import src.core.config; print('healthy')" || exit 1

# Default: run in demo mode
ENTRYPOINT ["python", "main.py"]
CMD ["--mode", "demo", "--algo", "ensemble"]
