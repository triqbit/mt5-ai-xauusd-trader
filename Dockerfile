# ============================================================
# MT5 AI/ML Trading Bot - Enterprise Edition
# Dockerfile (Python 3.11 slim, multi-stage build)
# Supporting linux/amd64 and linux/arm64
# ============================================================

# --- Stage 1: builder ------------------------------------------
FROM python:3.11-slim AS builder

ARG TARGETARCH
WORKDIR /app

# System deps for TA-Lib and building Python packages
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

# Python dependencies
COPY requirements-docker.txt .

# Handle architecture-specific torch installation
RUN pip install --upgrade pip && \
    if [ "$TARGETARCH" = "arm64" ]; then \
        sed -i '/--extra-index-url/d' requirements-docker.txt && \
        sed -i 's/+cpu//g' requirements-docker.txt; \
    fi && \
    pip install --no-cache-dir --prefix=/install -r requirements-docker.txt

# --- Stage 2: runtime ------------------------------------------
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy TA-Lib shared libraries and headers from builder
COPY --from=builder /usr/lib/libta_lib* /usr/lib/
COPY --from=builder /usr/include/ta-lib /usr/include/ta-lib

# Copy installed Python packages
COPY --from=builder /install /usr/local

# Copy application source
COPY src/ ./src/
COPY main.py .
COPY alembic.ini .
COPY migrations/ ./migrations/

# Non-root user for security
RUN useradd -m -u 1000 trader && \
    mkdir -p /app/logs && \
    chown -R trader:trader /app/logs
USER trader

# Expose Prometheus metrics and dashboard ports
EXPOSE 8000 8050

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import src.core.config; print('healthy')" || exit 1

# Default: run in demo mode
ENTRYPOINT ["python", "main.py"]
CMD ["--mode", "demo", "--algo", "ensemble"]
