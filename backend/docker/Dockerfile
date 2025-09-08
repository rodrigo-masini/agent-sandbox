FROM php:8.2-cli-alpine AS base

# Install system dependencies and PHP extensions
RUN apk add --no-cache\
 bash\
 git\
 curl\
 zip\
 unzip\
 docker-cli\
 sqlite\
 sqlite-dev\
 postgresql-dev\
 postgresql-client\
 mysql-client\
 nodejs\
 npm\
 python3\
 py3-pip\
 gcc\
 g++\
 make\
 autoconf\
 libc-dev\
 linux-headers\
 libzip-dev\
 icu-dev\
 oniguruma-dev\
 libxml2-dev\
 freetype-dev\
 libjpeg-turbo-dev\
 libpng-dev\
 libwebp-dev\
 zlib-dev

# Configure and install PHP extensions
# IMPORTANT: is built-in for PHP 8.x, don't install it
RUN docker-php-ext-configure gd\
 --with-freetype\
 --with-jpeg\
 --with-webp\
 && docker-php-ext-install -j$(nproc)\
 pdo\
 pdo_mysql\
 pdo_pgsql\
 pdo_sqlite\
 pcntl\
 posix\
 sockets\
 opcache\
 zip\
 intl\
 bcmath\
 exif\
 gd\
 mbstring\
 xml

# Install Redis extension
RUN pecl install redis-5.3.7 && docker-php-ext-enable redis

# Install Composer
COPY --from=composer:2.7 /usr/bin/composer /usr/bin/composer

# Configure PHP
RUN {\
 echo 'memory_limit=512M';\
 echo 'max_execution_time=300';\
 echo 'upload_max_filesize=100M';\
 echo 'post_max_size=100M';\
 echo 'variables_order=EGPCS';\
 } > /usr/local/etc/php/conf.d/app.ini

WORKDIR /app

# ===== DEVELOPMENT STAGE =====
FROM base AS development

# Install dev tools
RUN apk add --no-cache vim htop strace tcpdump inotify-tools

# Create the entrypoint script inline
RUN cat > /docker-entrypoint.sh << 'ENTRYPOINT_SCRIPT' && chmod +x /docker-entrypoint.sh
#!/bin/sh
set -e

echo "🚀 Starting backend initialization..."

# Ensure directories exist with proper permissions
mkdir -p /app/storage/logs /app/storage/cache /app/storage/sessions /app/storage/framework /app/WORKDIR
chmod -R 777 /app/storage
chmod 777 /app/WORKDIR
touch /app/storage/logs/app.log
chmod 666 /app/storage/logs/app.log

# Install composer dependencies if vendor doesn't exist or composer. is newer
if [ ! -f /app/vendor/autoload.php ] || [ /app/composer. -nt /app/vendor/autoload.php ]; then
 echo "📦 Installing/updating composer dependencies..."
 cd /app
 
 # If composer.lock exists, install from it; otherwise update
 if [ -f /app/composer.lock ]; then
 composer install\
 --no-interaction\
 --no-progress\
 --prefer-dist\
 --optimize-autoloader\
 --no-scripts || {
 echo "⚠️ Composer install failed, trying update..."
 composer update\
 --no-interaction\
 --no-progress\
 --prefer-dist\
 --optimize-autoloader\
 --no-scripts
 }
 else
 composer update\
 --no-interaction\
 --no-progress\
 --prefer-dist\
 --optimize-autoloader\
 --no-scripts
 fi
 
 # Generate optimized autoloader
 composer dump-autoload --optimize --no-interaction
fi

# Wait for services if configured
if [ -n "$DATABASE_URL" ]; then
 echo "⏳ Waiting for database..."
 sleep 5
fi

if [ -n "$REDIS_HOST" ]; then
 echo "⏳ Waiting for Redis..."
 sleep 3
fi

echo "✅ Initialization complete, starting PHP server..."

# Start PHP server with exec to handle signals properly
exec php -S 0.0.0.0:8000 -t public
ENTRYPOINT_SCRIPT

# Copy composer files first (for layer caching)
COPY composer. /app/
COPY composer.lock* /app/

# Pre-install dependencies during build (will be updated at runtime if needed)
RUN composer install\
 --no-interaction\
 --no-progress\
 --prefer-dist\
 --optimize-autoloader\
 --no-scripts\
 --no-autoloader\
 2>/dev/null ||\
 composer update\
 --no-interaction\
 --no-progress\
 --prefer-dist\
 --optimize-autoloader\
 --no-scripts\
 --no-autoloader

# Copy application code
COPY . /app

# Generate autoloader after copying all files
RUN composer dump-autoload --optimize --no-interaction 2>/dev/null || true

# Ensure all directories exist and have proper permissions
RUN mkdir -p /app/storage/logs /app/storage/cache /app/storage/sessions /app/storage/framework /app/WORKDIR\
 && chmod -R 777 /app/storage\
 && chmod 777 /app/WORKDIR\
 && touch /app/storage/logs/app.log\
 && chmod 666 /app/storage/logs/app.log

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
HEALTHCHECK --interval=10s --timeout=10s --start-period=60s --retries=10\
 CMD curl -f http://localhost:8000/health || exit 1

# ===== PRODUCTION STAGE =====
FROM base AS production

COPY composer. composer.lock* /app/

RUN composer install\
 --no-dev\
 --no-interaction\
 --no-progress\
 --prefer-dist\
 --optimize-autoloader

COPY . /app

RUN composer dump-autoload --optimize --classmap-authoritative --no-dev

RUN mkdir -p /app/storage/logs /app/storage/cache /app/storage/sessions /app/WORKDIR\
 && chmod -R 755 /app/storage\
 && chmod 700 /app/WORKDIR

RUN rm -rf /app/tests /app/.git /app/.github /app/docker /app/.env.example

RUN adduser -D -u 1000 -s /bin/sh agtsdbx &&\
 chown -R agtsdbx:agtsdbx /app

USER agtsdbx

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=5\
 CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["php", "-d", "display_errors=0", "-d", "error_reporting=0", "-S", "0.0.0.0:8000", "-t", "public"]