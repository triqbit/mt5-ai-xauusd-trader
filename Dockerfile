# ============================================================
# MT5 AI/ML Trading Bot - Enterprise Edition
# Dockerfile (Python 3.11 slim, multi-stage build)
# Supporting linux/amd64 and linux/arm64
# ============================================================

# --- Stage 1: builder ------------------------------------------
FROM python:3.12-slim AS builder

ARG TARGETARCH
WORKDIR /app

# System dependencies for building TA-Lib and Python packages
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
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
RUN if [ "$TARGETARCH" = "arm64" ]; then \
        # ARM64 (Apple Silicon / AWS Graviton): PyPI provides valid CPU wheels
        sed -i '/--extra-index-url/d' requirements-docker.txt && \
        sed -i 's/+cpu//g' requirements-docker.txt; \
    else \
        # AMD64: Explicitly use the CPU-optimized wheels from PyTorch's dedicated index
        sed -i 's/torch==2.3.1/torch==2.3.1+cpu/g' requirements-docker.txt && \
        sed -i 's/torchvision==0.18.1/torchvision==0.18.1+cpu/g' requirements-docker.txt; \
    fi

# Initialize virtual environment for isolation
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements-docker.txt

# --- Stage 2: runtime ------------------------------------------
FROM python:3.12-slim AS runtime

WORKDIR /app

# Runtime system dependencies
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy TA-Lib shared libraries and headers from builder
COPY --from=builder /usr/lib/libta_lib* /usr/lib/
COPY --from=builder /usr/include/ta-lib /usr/include/ta-lib
RUN ldconfig

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application source and assets
COPY src/ ./src/
COPY migrations/ ./migrations/
COPY main.py .
COPY alembic.ini .

# Setup non-root user for production security
RUN useradd -m -u 1000 trader

# Create log directory and ensure correct ownership
RUN mkdir -p /app/logs && \
    chown -R trader:trader /app && \
    chmod 755 /app/logs

USER trader

# Expose ports for Prometheus (8000) and Dash (8050)
EXPOSE 8000 8050

# Health check to ensure the application environment is sane
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import src.core.config; print('healthy')" || exit 1

# Default execution entrypoint
ENTRYPOINT ["python", "main.py"]
CMD ["--mode", "demo", "--algo", "ensemble"]
