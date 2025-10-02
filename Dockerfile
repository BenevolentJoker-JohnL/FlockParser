# FlockParser - Production Docker Image
# Multi-stage build for optimized image size

FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    poppler-utils \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements
WORKDIR /app
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

LABEL maintainer="benevolentjoker@gmail.com"
LABEL description="FlockParser - Distributed Document RAG System with GPU-aware routing"
LABEL version="1.0.0"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-eng \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user for security
RUN useradd -m -u 1000 flockparser && \
    mkdir -p /app /data /logs && \
    chown -R flockparser:flockparser /app /data /logs

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=flockparser:flockparser . .

# Switch to non-root user
USER flockparser

# Create necessary directories
RUN mkdir -p converted_files chroma_db knowledge_base logs

# Expose ports
EXPOSE 8000 8501

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LOG_LEVEL=INFO

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Default command (can be overridden)
CMD ["python", "-m", "uvicorn", "flock_ai_api:app", "--host", "0.0.0.0", "--port", "8000"]
