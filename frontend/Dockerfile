FROM python:3.11-slim AS base

RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

FROM base AS development

COPY requirements/dev.txt /app/requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

EXPOSE 8080

CMD ["python", "src/app/main.py"]

FROM base AS production

COPY requirements/prod.txt /app/requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

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
