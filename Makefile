
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
	cd backend && composer install
	cd frontend && pip install -r requirements/dev.txt
	@echo "Creating .env file if not exists..."
	@if [ ! -f .env ]; then cp .env.example .env; fi
	@echo "Installation complete!"

dev:
	@echo "Starting development environment..."
	docker-compose up -d
	@echo "Development environment started!"
	@echo "Frontend: http://localhost:8080"
	@echo "Backend: http://localhost:8000"

prod:
	@echo "Starting production environment..."
	docker-compose -f docker-compose.prod.yml up -d
	@echo "Production environment started!"

test:
	@echo "Running tests..."
	cd backend && vendor/bin/phpunit
	cd frontend && python -m pytest tests/

clean:
	@echo "Cleaning up..."
	docker-compose down -v
	rm -rf backend/vendor frontend/__pycache__
	@echo "Cleanup complete!"

logs:
	docker-compose logs -f

shell:
	docker exec -it pandora-backend-dev bash

migrate:
	@echo "Running database migrations..."
	docker exec pandora-backend-dev php artisan migrate

backup:
	@echo "Creating backup..."
	mkdir -p backups
	docker exec pandora-db-dev pg_dump -U pandora pandora > backups/pandora_$(shell date +%Y%m%d_%H%M%S).sql
	tar -czf backups/workdir_$(shell date +%Y%m%d_%H%M%S).tar.gz -C backend WORKDIR/
	@echo "Backup complete!"

restore:
	@echo "Restoring from backup..."
	@read -p "Enter backup file name: " backup; \
	docker exec -i pandora-db-dev psql -U pandora pandora < backups/$$backup
	@echo "Restore complete!"
