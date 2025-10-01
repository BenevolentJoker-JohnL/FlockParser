FROM python:3.10-slim

LABEL maintainer="benevolentjoker@gmail.com"
LABEL description="FlockParser - Distributed Document RAG System"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-eng \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p converted_files knowledge_base chroma_db_cli

# Expose ports
EXPOSE 8000 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/')" || exit 1

# Default command (can be overridden in docker-compose)
CMD ["python", "flockparsecli.py"]
