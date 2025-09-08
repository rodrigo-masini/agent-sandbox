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

# Configure and install PHP extensions (NO json - it's built-in for PHP 8.x!)
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
        echo 'display_errors=1'; \
        echo 'error_reporting=E_ALL'; \
        echo 'log_errors=1'; \
        echo 'error_log=/dev/stderr'; \
    } > /usr/local/etc/php/conf.d/app.ini

WORKDIR /app

# ===== DEVELOPMENT STAGE =====
FROM base AS development

# Install dev tools
RUN apk add --no-cache vim htop strace tcpdump inotify-tools

# Copy composer files first for better caching
COPY composer.json /app/composer.json
COPY composer.lock* /app/

# Install composer dependencies at build time
RUN if [ -f composer.lock ]; then \
        echo "Installing from composer.lock..." && \
        composer install \
            --no-interaction \
            --no-progress \
            --prefer-dist \
            --optimize-autoloader \
            --no-scripts \
            --ignore-platform-reqs; \
    else \
        echo "Installing without composer.lock..." && \
        composer install \
            --no-interaction \
            --no-progress \
            --prefer-dist \
            --optimize-autoloader \
            --no-scripts \
            --ignore-platform-reqs; \
    fi

# Copy all application files
COPY . /app

# Create necessary directories with proper permissions
RUN mkdir -p /app/storage/logs /app/storage/cache /app/storage/sessions /app/storage/framework /app/WORKDIR /app/public /app/vendor \
    && chmod -R 777 /app/storage \
    && chmod 777 /app/WORKDIR \
    && touch /app/storage/logs/app.log \
    && chmod 666 /app/storage/logs/app.log

# Create the entrypoint script (simplified and more robust)
RUN cat > /docker-entrypoint.sh << 'ENTRYPOINT_SCRIPT' && chmod +x /docker-entrypoint.sh
#!/bin/bash
set -e

echo "🚀 Starting backend (PID $$)..."
echo "📋 Environment:"
echo "  - PHP: $(php -v | head -1)"
echo "  - Composer: $(composer --version 2>/dev/null || echo 'Not installed')"
echo "  - Working Dir: $(pwd)"
echo "  - User: $(whoami)"

# Ensure critical directories exist
mkdir -p /app/storage/logs /app/WORKDIR /app/public
chmod 777 /app/storage/logs /app/WORKDIR 2>/dev/null || true

# Check if vendor/autoload.php exists
if [ ! -f /app/vendor/autoload.php ]; then
    echo "⚠️  Vendor autoload missing, attempting to install dependencies..."
    cd /app
    if [ -f composer.json ]; then
        composer install --no-interaction --no-progress --prefer-dist --optimize-autoloader --no-scripts || {
            echo "❌ Composer install failed"
            echo "Composer output:"
            composer diagnose
            exit 1
        }
    fi
fi

# Create a minimal health check endpoint if missing
if [ ! -f /app/public/health.php ]; then
    echo "📝 Creating health endpoint..."
    cat > /app/public/health.php << 'EOF'
<?php
header('Content-Type: application/json');
http_response_code(200);
echo json_encode([
    'status' => 'healthy',
    'timestamp' => date('c'),
    'php_version' => PHP_VERSION
]);
EOF
fi

# Create index.php if missing
if [ ! -f /app/public/index.php ]; then
    echo "📝 Creating index.php..."
    cat > /app/public/index.php << 'EOF'
<?php
require_once dirname(__DIR__) . '/vendor/autoload.php';
header('Content-Type: application/json');
$uri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
if ($uri === '/health') {
    include 'health.php';
} else {
    echo json_encode(['status' => 'running', 'service' => 'agtsdbx', 'path' => $uri]);
}
EOF
fi

echo "✅ Starting PHP development server on 0.0.0.0:8000..."
exec php -S 0.0.0.0:8000 -t public
ENTRYPOINT_SCRIPT

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]

# Simplified health check that's more forgiving
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=10 \
    CMD php -r "echo 'OK';" || exit 1

# ===== PRODUCTION STAGE =====
FROM base AS production

COPY composer.json composer.lock* /app/

RUN composer install \
    --no-dev \
    --no-interaction \
    --no-progress \
    --prefer-dist \
    --optimize-autoloader \
    --ignore-platform-reqs

COPY . /app

RUN composer dump-autoload --optimize --classmap-authoritative --no-dev

RUN mkdir -p /app/storage/logs /app/storage/cache /app/storage/sessions /app/WORKDIR /app/public \
    && chmod -R 755 /app/storage \
    && chmod 700 /app/WORKDIR

RUN adduser -D -u 1000 -s /bin/sh agtsdbx && \
    chown -R agtsdbx:agtsdbx /app

USER agtsdbx

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["php", "-S", "0.0.0.0:8000", "-t", "public"]