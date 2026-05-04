# ============================================================
# MT5 AI/ML Trading Bot - Enterprise Edition
# Dockerfile (Python 3.11 slim, multi-stage build)
# Supporting linux/amd64 and linux/arm64
# ============================================================

# --- Stage 1: builder ------------------------------------------
FROM python:3.14-slim AS builder

ARG TARGETARCH
WORKDIR /app

# System dependencies for building TA-Lib and Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ make \
    libpq-dev \
    wget ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Build TA-Lib from source
RUN wget -q https://github.com/ta-lib/ta-lib/releases/download/v0.6.4/ta-lib-0.6.4-src.tar.gz && \
    tar xf ta-lib-0.6.4-src.tar.gz && \
    cd ta-lib-0.6.4 && ./configure --prefix=/usr && make -j$(nproc) && make install

# Prepare requirements
COPY requirements-docker.txt .

# Architecture-specific adjustments for PyTorch
# amd64: uses extra-index-url for CPU wheels
# arm64: uses standard PyPI wheels (no +cpu suffix)
RUN if [ "$TARGETARCH" = "arm64" ]; then \
        sed -i '/--extra-index-url/d' requirements-docker.txt && \
        sed -i 's/+cpu//g' requirements-docker.txt; \
    fi

# Install Python dependencies into a separate prefix for easy copying
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements-docker.txt

# --- Stage 2: runtime ------------------------------------------
FROM python:3.14-slim AS runtime

WORKDIR /app

# Runtime system dependencies (libpq5 for PostgreSQL support)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy TA-Lib shared libraries and headers from builder
COPY --from=builder /usr/lib/libta_lib* /usr/lib/
COPY --from=builder /usr/include/ta-lib /usr/include/ta-lib

# Copy compiled Python packages from builder
COPY --from=builder /install /usr/local

# Copy application source and assets
COPY src/ ./src/
COPY migrations/ ./migrations/
COPY main.py .
COPY alembic.ini .

# Create log directory with proper permissions
RUN mkdir -p /app/logs && chmod 777 /app/logs

# Setup non-root user for production security
RUN useradd -m -u 1000 trader && \
    chown -R trader:trader /app
USER trader

# Expose ports for Prometheus (8000) and Dash (8050)
EXPOSE 8000 8050

# Health check to ensure the application environment is sane
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import src.core.config; print('healthy')" || exit 1

# Default execution entrypoint
ENTRYPOINT ["python", "main.py"]
CMD ["--mode", "demo", "--algo", "ensemble"]
