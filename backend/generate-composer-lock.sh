#!/bin/bash
# Generate composer.lock file for consistent dependencies

cd "$(dirname "$0")"

if [ ! -f composer.lock ]; then
    echo "Generating composer.lock..."
    docker run --rm \
        -v "$(pwd)":/app \
        -w /app \
        composer:2 \
        composer update --no-interaction --prefer-dist --prefer-stable
    echo "composer.lock generated successfully"
else
    echo "composer.lock already exists"
fi