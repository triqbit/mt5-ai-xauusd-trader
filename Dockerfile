# ============================================================
# MT5 AI/ML Trading Bot - Enterprise Edition
# Dockerfile (Python 3.11 slim, multi-stage build)
# Multi-arch support: linux/amd64, linux/arm64
# ============================================================

# --- Stage 1: builder ------------------------------------------
FROM python:3.11-slim AS builder

ARG TARGETARCH
WORKDIR /app

# System deps for TA-Lib, PostgreSQL driver, and build tools
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

# Prepare Python environment
COPY requirements-docker.txt .

# Handle architecture-specific PyTorch requirements
# amd64 uses +cpu wheels from PyTorch index; arm64 uses standard PyPI wheels
RUN if [ "$TARGETARCH" = "arm64" ]; then \
        sed -i '/--extra-index-url/d' requirements-docker.txt && \
        sed -i 's/+cpu//g' requirements-docker.txt; \
    fi

# Install dependencies into a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements-docker.txt

# --- Stage 2: runtime ------------------------------------------
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install runtime system dependencies (libpq for psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy TA-Lib shared libraries from builder
COPY --from=builder /usr/lib/libta_lib* /usr/lib/

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH"
ENV LD_LIBRARY_PATH="/usr/lib:${LD_LIBRARY_PATH:-}"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Non-root user for security
RUN useradd -m -u 1000 trader && \
    mkdir -p /app/logs /app/data && \
    chown -R trader:trader /app

# Copy application source with correct ownership
COPY --chown=trader:trader src/ ./src/
COPY --chown=trader:trader main.py .

USER trader

# Expose Prometheus metrics and dashboard ports
EXPOSE 8000 8050

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import src.core.config; print('healthy')" || exit 1

# Default: run in demo mode
ENTRYPOINT ["python", "main.py"]
CMD ["--mode", "demo", "--algo", "ensemble"]
