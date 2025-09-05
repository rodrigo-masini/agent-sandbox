FROM python:3.11-slim AS base

RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ===== DEVELOPMENT STAGE =====
FROM base AS development

# Copy requirements directory first
COPY requirements /app/requirements

# Install dev requirements
RUN pip install --no-cache-dir -r requirements/dev.txt

# Copy all application files
COPY . /app

# Set Python path to ensure imports work
ENV PYTHONPATH=/app

EXPOSE 8080

# Use module execution to avoid import issues
CMD ["python", "-m", "src.app.main"]

# ===== PRODUCTION STAGE =====
FROM base AS production

# Copy requirements directory first  
COPY requirements /app/requirements

# Install prod requirements
RUN pip install --no-cache-dir -r requirements/prod.txt

# Copy only necessary directories for production
COPY src /app/src
COPY static /app/static
COPY templates /app/templates

# Set Python path
ENV PYTHONPATH=/app

# Create consistent user
RUN useradd -m -u 1000 agtsdbx && chown -R agtsdbx:agtsdbx /app
USER agtsdbx

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

EXPOSE 8080

ENV PYTHONUNBUFFERED=1
ENV PYTHONOPTIMIZE=2
CMD ["python", "-O", "-m", "src.app.main"]