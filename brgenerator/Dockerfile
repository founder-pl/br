# BR Documentation Generator
# Multi-stage build for smaller image

FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY src/ src/

# Install package
RUN pip install --no-cache-dir build && \
    python -m build --wheel && \
    pip install --no-cache-dir dist/*.whl

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies for WeasyPrint
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/br-doc /usr/local/bin/br-doc

# Create directories
RUN mkdir -p /app/input /app/output /app/templates

# Copy default templates
COPY config/ /app/config/

# Environment defaults
ENV LLM_DEFAULT_PROVIDER=openrouter \
    OPENROUTER_MODEL=nvidia/nemotron-3-nano-30b-a3b:free \
    OLLAMA_BASE_URL=http://host.docker.internal:11434 \
    VALIDATION_LEVELS=structure,content,legal,financial \
    VALIDATION_MAX_ITERATIONS=3 \
    PDF_TEMPLATE=professional

# Volumes
VOLUME ["/app/input", "/app/output"]

# Entry point
ENTRYPOINT ["br-doc"]
CMD ["--help"]
