FROM php:8.2-cli-alpine AS base

# Install system dependencies INCLUDING PostgreSQL dev libraries
RUN apk add --no-cache \
    bash \
    git \
    curl \
    zip \
    unzip \
    docker-cli \
    sqlite \
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
    linux-headers

# Install PHP extensions
RUN docker-php-ext-install \
    pdo \
    pdo_mysql \
    pdo_pgsql \
    pcntl \
    posix \
    sockets \
    opcache

# Install Redis extension
RUN pecl install redis && docker-php-ext-enable redis

# Install Composer
COPY --from=composer:latest /usr/bin/composer /usr/bin/composer

WORKDIR /app

# ===== DEVELOPMENT STAGE =====
FROM base AS development

RUN apk add --no-cache \
    vim \
    htop \
    strace \
    tcpdump

COPY . /app

RUN composer install --no-scripts --no-autoloader

RUN composer dump-autoload --optimize

RUN mkdir -p /app/storage/logs /app/storage/cache /app/WORKDIR \
    && chmod -R 755 /app/storage /app/WORKDIR

EXPOSE 8000

CMD ["php", "-S", "0.0.0.0:8000", "-t", "public"]

# ===== PRODUCTION STAGE =====
FROM base AS production

COPY . /app

RUN composer install --no-dev --no-scripts --no-autoloader --prefer-dist

RUN composer dump-autoload --optimize --classmap-authoritative

RUN mkdir -p /app/storage/logs /app/storage/cache /app/WORKDIR \
    && chmod -R 755 /app/storage \
    && chmod 700 /app/WORKDIR

RUN rm -rf /app/tests /app/.git /app/.github /app/docker

# Create consistent user
RUN adduser -D -u 1000 agtsdbx
USER agtsdbx

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["php", "-d", "display_errors=0", "-d", "error_reporting=0", "-S", "0.0.0.0:8000", "-t", "public"]
