# ============================================================
# MT5 AI/ML Trading Bot - Enterprise Edition
# Dockerfile (Multi-stage build, Multi-platform support)
# ============================================================

# --- Stage 1: builder ------------------------------------------
FROM --platform=$BUILDPLATFORM python:3.11-slim AS builder

ARG TARGETARCH
WORKDIR /app

# System deps for TA-Lib and building Python wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ make \
    libpq-dev \
    wget ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Build TA-Lib from source
RUN wget -q https://github.com/ta-lib/ta-lib/releases/download/v0.6.4/ta-lib-0.6.4-src.tar.gz && \
    tar xf ta-lib-0.6.4-src.tar.gz && \
    cd ta-lib-0.6.4 && ./configure --prefix=/usr && make -j$(nproc) && make install && \
    cd .. && rm -rf ta-lib-0.6.4 ta-lib-0.6.4-src.tar.gz

# Prepare installation directory
RUN mkdir /install

# Copy requirements
COPY requirements-docker.txt .

# Install Python dependencies with architecture-specific logic
# For amd64, we use the CPU-specific PyTorch wheels.
# For arm64, we strip the +cpu suffix and the extra-index-url to use standard wheels.
RUN pip install --upgrade pip && \
    if [ "$TARGETARCH" = "arm64" ]; then \
        sed -i '/--extra-index-url/d' requirements-docker.txt && \
        sed -i 's/+cpu//g' requirements-docker.txt; \
    fi && \
    pip install --no-cache-dir --prefix=/install -r requirements-docker.txt

# --- Stage 2: runtime ------------------------------------------
FROM python:3.11-slim AS runtime

# Install runtime system dependencies (e.g., for PostgreSQL if using psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy TA-Lib shared libraries from builder
COPY --from=builder /usr/lib/libta_lib* /usr/lib/
COPY --from=builder /usr/include/ta-lib /usr/include/ta-lib

# Copy installed Python packages
COPY --from=builder /install /usr/local

# Create necessary directories
RUN mkdir -p /app/logs /app/data && chmod 777 /app/logs /app/data

# Non-root user for security
RUN useradd -m -u 1000 trader && \
    chown -R trader:trader /app
USER trader

# Copy application source
COPY src/ ./src/
COPY main.py .

# Expose Prometheus metrics and dashboard ports
EXPOSE 8000 8050

# Health check (uses a simple import check)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import src.core.config; print('healthy')" || exit 1

# Default environment variables
ENV MODE=demo \
    ALGO=ensemble \
    PYTHONUNBUFFERED=1

# Entrypoint
ENTRYPOINT ["python", "main.py"]
CMD ["--mode", "demo", "--algo", "ensemble"]
