#!/bin/bash
# This script generates composer.lock for each PHP version

set -e

echo "Generating composer.lock for PHP compatibility..."

# Try to use the lowest PHP version we support
docker run --rm \
    -v "$(pwd)":/app \
    -w /app \
    composer:2 \
    composer update --no-interaction --prefer-dist --prefer-stable

echo "composer.lock generated successfully"