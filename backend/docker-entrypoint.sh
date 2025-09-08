#!/bin/sh
set -e

echo "Starting backend initialization..."

# Ensure directories exist with proper permissions
mkdir -p /app/storage/logs /app/storage/cache /app/storage/sessions /app/WORKDIR
chmod -R 777 /app/storage
chmod 777 /app/WORKDIR

# Wait for database if configured
if [ -n "$DATABASE_URL" ]; then
    echo "Waiting for database..."
    for i in $(seq 1 30); do
        if pg_isready -h "${DATABASE_HOST:-postgres}" -p "${DATABASE_PORT:-5432}" 2>/dev/null; then
            echo "Database is ready"
            break
        fi
        echo "Waiting for database... attempt $i/30"
        sleep 2
    done
fi

# Wait for Redis if configured
if [ -n "$REDIS_HOST" ]; then
    echo "Waiting for Redis..."
    for i in $(seq 1 30); do
        if redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT:-6379}" ping 2>/dev/null | grep -q PONG; then
            echo "Redis is ready"
            break
        fi
        echo "Waiting for Redis... attempt $i/30"
        sleep 2
    done
fi

# Install/update composer dependencies if vendor is missing or incomplete
if [ ! -f /app/vendor/autoload.php ]; then
    echo "Installing composer dependencies..."
    if [ -f /app/composer.lock ]; then
        composer install --no-interaction --no-progress --prefer-dist --optimize-autoloader --no-scripts
    else
        composer update --no-interaction --no-progress --prefer-dist --optimize-autoloader --no-scripts
    fi
    composer dump-autoload --optimize
fi

# Ensure log file exists and is writable
touch /app/storage/logs/app.log
chmod 666 /app/storage/logs/app.log

echo "Starting PHP server on 0.0.0.0:8000..."
exec php -S 0.0.0.0:8000 -t public