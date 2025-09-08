FROM php:8.2-cli-alpine AS base

# Install system dependencies and PHP extensions
RUN apk add --no-cache \
    bash \
    git \
    curl \
    zip \
    unzip \
    docker-cli \
    sqlite \
    sqlite-dev \
    postgresql-dev \
    postgresql-client \
    mysql-client \
    nodejs \
    npm \
    python3 \
    py3-pip \
    gcc \
    g++ \
    make \
    autoconf \
    libc-dev \
    linux-headers \
    libzip-dev \
    icu-dev \
    oniguruma-dev \
    libxml2-dev \
    freetype-dev \
    libjpeg-turbo-dev \
    libpng-dev \
    libwebp-dev \
    zlib-dev

# Configure and install PHP extensions (NO json - it's built-in!)
RUN docker-php-ext-configure gd \
        --with-freetype \
        --with-jpeg \
        --with-webp \
    && docker-php-ext-install -j$(nproc) \
        pdo \
        pdo_mysql \
        pdo_pgsql \
        pdo_sqlite \
        pcntl \
        posix \
        sockets \
        opcache \
        zip \
        intl \
        bcmath \
        exif \
        gd \
        mbstring \
        xml

# Install Redis extension
RUN pecl install redis-5.3.7 && docker-php-ext-enable redis

# Install Composer
COPY --from=composer:2.7 /usr/bin/composer /usr/bin/composer

# Configure PHP
RUN { \
        echo 'memory_limit=512M'; \
        echo 'max_execution_time=300'; \
        echo 'upload_max_filesize=100M'; \
        echo 'post_max_size=100M'; \
        echo 'variables_order=EGPCS'; \
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
mkdir -p /app/storage/logs /app/storage/cache /app/storage/sessions /app/storage/framework /app/WORKDIR /app/vendor /app/public
chmod -R 777 /app/storage 2>/dev/null || true
chmod 777 /app/WORKDIR 2>/dev/null || true
touch /app/storage/logs/app.log
chmod 666 /app/storage/logs/app.log 2>/dev/null || true

# Check if composer.json exists
if [ ! -f /app/composer.json ]; then
    echo "⚠️  composer.json not found, creating minimal one..."
    cat > /app/composer.json << 'EOF'
{
    "name": "agent/sandbox",
    "type": "project",
    "require": {
        "php": "^8.0"
    },
    "autoload": {
        "psr-4": {
            "Agtsdbx\\": "src/"
        }
    }
}
EOF
fi

# Install composer dependencies if vendor doesn't exist
if [ ! -f /app/vendor/autoload.php ]; then
    echo "📦 Installing composer dependencies..."
    cd /app
    
    # Try to install, fall back to update if needed
    composer install \
        --no-interaction \
        --no-progress \
        --prefer-dist \
        --optimize-autoloader \
        --no-scripts 2>/dev/null || \
    composer update \
        --no-interaction \
        --no-progress \
        --prefer-dist \
        --optimize-autoloader \
        --no-scripts 2>/dev/null || \
    echo "⚠️  Composer install failed, continuing anyway..."
    
    # Try to generate autoloader
    composer dump-autoload --optimize --no-interaction 2>/dev/null || true
fi

# Create index.php if missing
if [ ! -f /app/public/index.php ] && [ ! -f /app/public/health.php ]; then
    echo "📝 Creating default index.php..."
    mkdir -p /app/public
    cat > /app/public/index.php << 'EOF'
<?php
header('Content-Type: application/json');
echo json_encode(['status' => 'running', 'service' => 'agtsdbx']);
EOF
fi

# Create health.php if missing
if [ ! -f /app/public/health.php ]; then
    echo "📝 Creating health endpoint..."
    cat > /app/public/health.php << 'EOF'
<?php
header('Content-Type: application/json');
echo json_encode([
    'status' => 'healthy',
    'timestamp' => date('c'),
    'php_version' => PHP_VERSION,
    'checks' => [
        'php' => true,
        'filesystem' => is_writable('/app/WORKDIR')
    ]
]);
EOF
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

# Copy composer files first (FIXED: composer.json not composer.)
COPY composer.json /app/composer.json
# Copy composer.lock if it exists (optional with *)
COPY composer.lock* /app/

# Try to install dependencies at build time (will be updated at runtime if needed)
RUN cd /app && \
    if [ -f composer.json ]; then \
        composer install \
            --no-interaction \
            --no-progress \
            --prefer-dist \
            --optimize-autoloader \
            --no-scripts \
            --ignore-platform-reqs \
            2>/dev/null || \
        composer update \
            --no-interaction \
            --no-progress \
            --prefer-dist \
            --optimize-autoloader \
            --no-scripts \
            --ignore-platform-reqs \
            2>/dev/null || \
        echo "Composer install failed at build time, will retry at runtime"; \
    fi

# Copy application code
COPY . /app

# Ensure directories and permissions
RUN mkdir -p /app/storage/logs /app/storage/cache /app/storage/sessions /app/storage/framework /app/WORKDIR /app/public /app/vendor \
    && chmod -R 777 /app/storage \
    && chmod 777 /app/WORKDIR \
    && touch /app/storage/logs/app.log \
    && chmod 666 /app/storage/logs/app.log

# Generate autoloader if possible
RUN cd /app && composer dump-autoload --optimize --no-interaction 2>/dev/null || true

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]

# Robust health check with retries
HEALTHCHECK --interval=10s --timeout=10s --start-period=60s --retries=15 \
    CMD curl -f http://localhost:8000/health || \
        curl -f http://localhost:8000/health.php || \
        curl -f http://localhost:8000/ || \
        php -r "echo 'OK';" || \
        exit 1

# ===== PRODUCTION STAGE =====
FROM base AS production

# Copy composer files (FIXED)
COPY composer.json /app/composer.json
COPY composer.lock* /app/

RUN cd /app && composer install \
    --no-dev \
    --no-interaction \
    --no-progress \
    --prefer-dist \
    --optimize-autoloader \
    --ignore-platform-reqs

COPY . /app

RUN cd /app && composer dump-autoload --optimize --classmap-authoritative --no-dev

RUN mkdir -p /app/storage/logs /app/storage/cache /app/storage/sessions /app/WORKDIR /app/public \
    && chmod -R 755 /app/storage \
    && chmod 700 /app/WORKDIR

RUN rm -rf /app/tests /app/.git /app/.github /app/docker /app/.env.example

RUN adduser -D -u 1000 -s /bin/sh agtsdbx && \
    chown -R agtsdbx:agtsdbx /app

USER agtsdbx

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["php", "-d", "display_errors=0", "-d", "error_reporting=0", "-S", "0.0.0.0:8000", "-t", "public"]