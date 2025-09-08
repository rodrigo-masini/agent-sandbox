#!/bin/bash
# Robust composer.lock generator for CI/CD

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

echo "🔧 Generating composer.lock for CI/CD..."

cd "$BACKEND_DIR"

# Check if composer.json exists
if [ ! -f composer.json ]; then
    echo "❌ Error: composer.json not found in $BACKEND_DIR"
    exit 1
fi

# Generate composer.lock using Docker to ensure consistency
echo "📦 Using Docker to generate composer.lock..."

# Use the same PHP version as in Dockerfile
docker run --rm \
    -v "$BACKEND_DIR":/app \
    -w /app \
    --user "$(id -u):$(id -g)" \
    composer:2.7 \
    update \
    --no-interaction \
    --no-progress \
    --prefer-dist \
    --prefer-stable \
    --ignore-platform-reqs \
    --no-scripts \
    --no-autoloader \
    --with-all-dependencies

if [ -f composer.lock ]; then
    echo "✅ composer.lock generated successfully"
    echo "📊 Package count: $(grep -c '"name":' composer.lock || echo 0)"
    
    # Validate the lock file
    docker run --rm \
        -v "$BACKEND_DIR":/app \
        -w /app \
        composer:2.7 \
        validate --no-check-all --no-check-publish
    
    echo "✅ composer.lock validated successfully"
else
    echo "❌ Failed to generate composer.lock"
    exit 1
fi