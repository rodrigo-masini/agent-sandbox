# Detect Docker Compose command
DOCKER_COMPOSE := $(shell which docker-compose 2>/dev/null || echo "docker compose")

.PHONY: help install dev prod test clean

help:
	@echo "Magic Agent Sandbox - Available Commands:"
	@echo "  make install    - Install dependencies"
	@echo "  make dev        - Start development environment"
	@echo "  make prod       - Start production environment"
	@echo "  make test       - Run tests"
	@echo "  make clean      - Clean up containers and volumes"
	@echo "  make logs       - Show logs"
	@echo "  make shell      - Open shell in backend container"
	@echo "  make migrate    - Run database migrations"
	@echo "  make backup     - Backup data"
	@echo "  make restore    - Restore data"

install:
	@echo "Installing dependencies..."
	@if [ -f backend/composer.json ]; then cd backend && composer install; fi
	@if [ -f frontend/requirements/dev.txt ]; then cd frontend && pip install -r requirements/dev.txt; fi
	@echo "Creating .env file if not exists..."
	@if [ ! -f .env ]; then cp .env.example .env; fi
	@echo "Installation complete!"

dev:
	@echo "Starting development environment..."
	$(DOCKER_COMPOSE) up -d
	@echo "Development environment started!"
	@echo "Frontend: http://localhost:8080"
	@echo "Backend: http://localhost:8000"

prod:
	@echo "Starting production environment..."
	$(DOCKER_COMPOSE) -f docker-compose.prod.yml up -d
	@echo "Production environment started!"

test:
	@echo "Running tests..."
	@if [ -f backend/vendor/bin/phpunit ]; then (cd backend && vendor/bin/phpunit); fi
	@if [ -d frontend/tests ]; then (cd frontend && python3 -m pytest tests/); fi

clean:
	@echo "Cleaning up..."
	$(DOCKER_COMPOSE) down -v
	rm -rf backend/vendor frontend/__pycache__
	@echo "Cleanup complete!"

logs:
	$(DOCKER_COMPOSE) logs -f

shell:
	docker exec -it agtsdbx-backend-dev bash

migrate:
	@echo "Running database migrations..."
	docker exec agtsdbx-backend-dev php artisan migrate

backup:
	@echo "Creating backup..."
	mkdir -p backups
	docker exec agtsdbx-db-dev pg_dump -U agtsdbx agtsdbx > backups/agtsdbx_$(shell date +%Y%m%d_%H%M%S).sql
	tar -czf backups/workdir_$(shell date +%Y%m%d_%H%M%S).tar.gz -C backend WORKDIR/
	@echo "Backup complete!"

restore:
	@echo "Restoring from backup..."
	@read -p "Enter backup file name: " backup; \
	docker exec -i agtsdbx-db-dev psql -U agtsdbx agtsdbx < backups/$$backup
	@echo "Restore complete!"
