# ============================================================
# MT5 AI/ML Trading Bot - Enterprise Edition
# Dockerfile (Python 3.11 slim, multi-stage build)
# ============================================================

# --- Stage 1: builder ------------------------------------------
FROM python:3.11-slim AS builder

# Required for multi-arch build logic
ARG TARGETARCH

WORKDIR /app

# System deps for TA-Lib and compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ make \
    libpq-dev \
    wget ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Build TA-Lib from source (GitHub releases mirror)
RUN wget -q https://github.com/ta-lib/ta-lib/releases/download/v0.6.4/ta-lib-0.6.4-src.tar.gz && \
    tar xf ta-lib-0.6.4-src.tar.gz && \
    cd ta-lib-0.6.4 && ./configure --prefix=/usr && make -j$(nproc) && make install && \
    cd .. && rm -rf ta-lib-0.6.4 ta-lib-0.6.4-src.tar.gz

# Python dependencies
COPY requirements-docker.txt .

# Architecture-specific PyTorch handling:
# amd64 uses torch+cpu from the extra index
# arm64 uses standard torch from PyPI (which are CPU-only on ARM anyway)
RUN if [ "$TARGETARCH" = "arm64" ]; then \
        sed -i 's/+cpu//g' requirements-docker.txt && \
        sed -i '/--extra-index-url/d' requirements-docker.txt; \
    fi

# Install dependencies into /install prefix
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements-docker.txt

# --- Stage 2: runtime ------------------------------------------
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy TA-Lib shared libraries from builder
COPY --from=builder /usr/lib/libta_lib* /usr/lib/
COPY --from=builder /usr/include/ta-lib /usr/include/ta-lib

# Copy installed Python packages from builder prefix
COPY --from=builder /install /usr/local

# Ensure shared libraries are recognized
RUN ldconfig

# Create necessary directories and non-root user
RUN mkdir -p logs data && \
    useradd -m -u 1000 trader && \
    chown -R trader:trader /app

# Copy application source
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
