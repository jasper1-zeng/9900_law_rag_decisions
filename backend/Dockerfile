FROM python:3.10-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install system dependencies for pgvector (if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies with specific versions for compatibility
COPY requirements.txt install_langchain.sh /app/

# First uninstall any conflicting packages
RUN pip uninstall -y sentence-transformers huggingface-hub transformers

# Install dependencies with specific compatible versions
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir huggingface_hub==0.7.0 && \
    pip install --no-cache-dir transformers==4.18.0 && \
    pip install --no-cache-dir sentence-transformers==2.0.0 && \
    pip install --no-cache-dir anthropic && \
    chmod +x install_langchain.sh && \
    ./install_langchain.sh

# Copy project files
COPY . /app/

# Create a .env file if it doesn't exist
RUN if [ ! -f .env ]; then cp .env.example .env || echo "No .env.example found"; fi

# Create a non-root user and switch to it
RUN adduser --disabled-password --gecos "" appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health/ || exit 1

# Command to run the application
CMD ["python", "run.py"]
