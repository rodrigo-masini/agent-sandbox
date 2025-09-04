FROM php:8.2-cli-alpine AS base

RUN apk add --no-cache \
    bash \
    git \
    curl \
    zip \
    unzip \
    docker-cli \
    sqlite \
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
    libc-dev

RUN docker-php-ext-install \
    pdo \
    pdo_mysql \
    pdo_pgsql \
    pcntl \
    posix \
    sockets \
    opcache

RUN pecl install redis && docker-php-ext-enable redis

COPY --from=composer:latest /usr/bin/composer /usr/bin/composer

WORKDIR /app

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

FROM base AS production

COPY . /app

RUN composer install --no-dev --no-scripts --no-autoloader --prefer-dist

RUN composer dump-autoload --optimize --classmap-authoritative

RUN mkdir -p /app/storage/logs /app/storage/cache /app/WORKDIR \
    && chmod -R 755 /app/storage \
    && chmod 700 /app/WORKDIR

RUN rm -rf /app/tests /app/.git /app/.github /app/docker

RUN adduser -D -u 1000 pandora
USER agtsdbx

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["php", "-d", "display_errors=0", "-d", "error_reporting=0", "-S", "0.0.0.0:8000", "-t", "public"]
