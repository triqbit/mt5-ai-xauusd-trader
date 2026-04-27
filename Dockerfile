# ============================================================
# MT5 AI/ML Trading Bot - Enterprise Edition
# Dockerfile (Python 3.11 slim, multi-stage build)
# Multi-platform support: linux/amd64, linux/arm64
# ============================================================

# --- Stage 1: builder ------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /app

# System deps for TA-Lib and building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ make \
    libpq-dev \
    wget ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Build TA-Lib from source
# Using v0.6.4 which is stable and compatible with modern NumPy
RUN wget -q https://github.com/ta-lib/ta-lib/releases/download/v0.6.4/ta-lib-0.6.4-src.tar.gz && \
    tar xf ta-lib-0.6.4-src.tar.gz && \
    cd ta-lib-0.6.4 && ./configure --prefix=/usr && make -j$(nproc) && make install && \
    cd .. && rm -rf ta-lib-0.6.4 ta-lib-0.6.4-src.tar.gz

# Create virtual environment to isolate dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements-docker.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements-docker.txt

# --- Stage 2: runtime ------------------------------------------
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install runtime system dependencies
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
ENV LD_LIBRARY_PATH="/usr/lib"
ENV PYTHONUNBUFFERED=1

# Ensure TA-Lib is found by the system
RUN ldconfig

# Copy application source
COPY src/ ./src/
COPY main.py .

# Create logs directory and set permissions
RUN mkdir -p logs && chmod 777 logs

# Non-root user for security (UID 1000 is standard)
RUN useradd -m -u 1000 trader && chown -R trader:trader /app
USER trader

# Expose Prometheus metrics and dashboard ports
EXPOSE 8000 8050

# Health check (uses the app's config validation as a basic check)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "from src.core.config import get_config; get_config()" || exit 1

# Default execution
ENTRYPOINT ["python", "main.py"]
CMD ["--mode", "demo", "--algo", "ensemble"]
