FROM python:3.11-slim AS base

RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ===== DEVELOPMENT STAGE =====
FROM base AS development

# Copy requirements file - FIX: Copy the entire requirements directory
COPY requirements /app/requirements

# Install dev requirements
RUN pip install --no-cache-dir -r requirements/dev.txt

COPY . /app

EXPOSE 8080

CMD ["python", "src/app/main.py"]

# ===== PRODUCTION STAGE =====
FROM base AS production

# Copy requirements file - FIX: Copy the entire requirements directory
COPY requirements /app/requirements

# Install prod requirements
RUN pip install --no-cache-dir -r requirements/prod.txt

COPY src /app/src
COPY static /app/static
COPY templates /app/templates

# Create consistent user
RUN useradd -m -u 1000 agtsdbx && chown -R agtsdbx:agtsdbx /app
USER agtsdbx

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

EXPOSE 8080

ENV PYTHONUNBUFFERED=1
ENV PYTHONOPTIMIZE=2
CMD ["python", "-O", "src/app/main.py"]
