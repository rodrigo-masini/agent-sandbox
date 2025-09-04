# Magic Agent Sandbox

## Overview

Magic Agent Sandbox is an *almost* production-ready integration between MAGIC Fabric AI platform and a powerful backend execution server. This system enables AI-powered system management through natural language.

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11
- PHP 8.0+
- Fabric API credentials (API Key, Org ID, Project ID)

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/agent-sandbox.git
cd agent-sandbox

# Copy environment configuration
cp .env.example .env

# Edit .env with your Tela/Fabric credentials
# REQUIRED: Set these values
# FABRIC_API_KEY=your_api_key_here
# FABRIC_ORG_ID=your_org_id_here  
# FABRIC_PROJECT_ID=your_project_id_here

# Install dependencies
make install

# Start development environment
make dev

# Access the application
# Frontend: http://localhost:8080
# Backend API: http://localhost:8000
```

## Setup Scripts

### File: scripts/setup.sh
```bash
#!/bin/bash
set -e

echo "🚀 Magic Agent Sandbox Setup Script"
echo "=================================="

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "❌ Docker required but not installed."; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "❌ Docker Compose required but not installed."; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 required but not installed."; exit 1; }

# Create directories
echo "📁 Creating directories..."
mkdir -p backend/storage/logs
mkdir -p backend/storage/cache
mkdir -p backend/WORKDIR
mkdir -p frontend/static
mkdir -p frontend/templates
mkdir -p monitoring/prometheus
mkdir -p monitoring/grafana/dashboards

# Set permissions
chmod -R 755 backend/storage
chmod 700 backend/WORKDIR

# Copy environment file
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your Tela/Fabric credentials"
fi

# Install backend dependencies
echo "📦 Installing backend dependencies..."
cd backend
if [ -f composer.json ]; then
    docker run --rm -v $(pwd):/app composer install
fi
cd ..

# Install frontend dependencies  
echo "📦 Installing frontend dependencies..."
cd frontend
pip3 install -r requirements/base.txt
cd ..

# Generate secrets
echo "🔐 Generating secrets..."
if grep -q "your-secret-key-here" .env; then
    SECRET_KEY=$(openssl rand -hex 32)
    sed -i.bak "s/your-secret-key-here-generate-with-openssl-rand-hex-32/$SECRET_KEY/g" .env
    JWT_SECRET=$(openssl rand -hex 32)
    sed -i.bak "s/your-jwt-secret-here/$JWT_SECRET/g" .env
fi

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env and add your Fabric credentials"
echo "2. Run 'make dev' to start development environment"
echo "3. Access http://localhost:8080"
```

### File: scripts/deploy.sh
```bash
#!/bin/bash
set -e

echo "🚀 Deploying Magic Agent Sandbox to Production"
echo "============================================="

# Load environment
source .env

# Build production images
echo "🔨 Building production images..."
docker-compose -f docker-compose.prod.yml build

# Run database migrations
echo "📊 Running database migrations..."
docker-compose -f docker-compose.prod.yml run --rm php artisan migrate

# Start services
echo "🎯 Starting production services..."
docker-compose -f docker-compose.prod.yml up -d

# Health check
echo "❤️  Running health checks..."
sleep 10
curl -f http://localhost/health || { echo "❌ Health check failed"; exit 1; }

echo "✅ Deployment complete!"
echo "Application is running at http://localhost"
```

### File: scripts/backup.sh
```bash
#!/bin/bash
set -e

BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "📦 Creating backup in $BACKUP_DIR..."

# Backup database
if [ "$DATABASE_URL" != "" ]; then
    echo "Backing up database..."
    docker exec pandora-db-prod pg_dump -U pandora pandora > "$BACKUP_DIR/database.sql"
fi

# Backup WORKDIR
echo "Backing up WORKDIR..."
tar -czf "$BACKUP_DIR/workdir.tar.gz" backend/WORKDIR/

# Backup storage
echo "Backing up storage..."
tar -czf "$BACKUP_DIR/storage.tar.gz" backend/storage/

# Backup configurations
echo "Backing up configurations..."
cp .env "$BACKUP_DIR/.env"
cp docker-compose.prod.yml "$BACKUP_DIR/docker-compose.prod.yml"

echo "✅ Backup complete! Location: $BACKUP_DIR"
```

## Project Structure

```
pandora-enterprise/
├── backend/                # PHP Backend Server
│   ├── src/               
│   │   ├── Core/          # Core application components
│   │   ├── Controllers/   # Request handlers
│   │   ├── Services/      # Business logic
│   │   └── Storage/       # Storage management
│   ├── config/            # Configuration files
│   ├── public/            # Public entry points
│   ├── storage/           # Logs, cache, sessions
│   └── WORKDIR/           # Sandboxed execution directory
│
├── frontend/              # Python/NiceGUI Frontend
│   ├── src/              
│   │   ├── app/          # Main application
│   │   ├── clients/      # API clients
│   │   ├── tools/        # Tool implementations
│   │   ├── ui/           # UI components
│   │   └── core/         # Core utilities
│   ├── static/           # Static assets
│   └── templates/        # HTML templates
│
├── monitoring/           # Monitoring stack
│   ├── prometheus/       # Metrics collection
│   └── grafana/          # Dashboards
│
├── deployment/           # Deployment configurations
│   ├── kubernetes/       # K8s manifests
│   ├── terraform/        # Infrastructure as code
│   └── ansible/          # Configuration management
│
└── scripts/              # Utility scripts
```

## API Documentation

### Fabric Configuration

The system uses Fabric's OpenAI-compatible API with required headers:

```python
headers = {
    "Authorization": f"Bearer {FABRIC_API_KEY}",
    "OpenAI-Organization": FABRIC_ORG_ID,  # REQUIRED
    "OpenAI-Project": FABRIC_PROJECT_ID,    # REQUIRED
    "Content-Type": "application/json"
}
```

### Available Tools

The AI assistant has access to these tools:

#### Execution Tools
- `execute_shell_command`: Run shell commands
- `execute_script`: Execute script files
- `execute_parallel_commands`: Run multiple commands in parallel

#### File Tools
- `write_file`: Create or update files
- `read_file`: Read file contents
- `list_files`: List directory contents
- `delete_file`: Delete files
- `create_directory`: Create directories

#### System Tools
- `get_system_info`: Get system information
- `get_process_list`: List running processes
- `check_disk_usage`: Check disk space
- `check_network_connectivity`: Test network

#### Docker Tools (if enabled)
- `docker_run`: Run containers
- `docker_list`: List containers
- `docker_stop`: Stop containers
- `docker_remove`: Remove containers
- `docker_logs`: View container logs

#### Network Tools
- `http_request`: Make HTTP requests
- `download_file`: Download files from URLs
- `check_port`: Check port availability
- `dns_lookup`: Perform DNS lookups

#### Database Tools
- `execute_sql`: Execute SQL queries
- `backup_database`: Create database backups

## Security Features

- **Authentication**: JWT tokens and API keys
- **Authorization**: Role-based access control
- **Rate Limiting**: Configurable per-user/IP limits
- **Command Sanitization**: Input validation and filtering
- **Sandboxing**: Firejail/Docker isolation
- **Path Restrictions**: Filesystem access controls
- **Network Filtering**: Domain/IP whitelisting
- **Audit Logging**: All operations logged

## Monitoring

Access monitoring dashboards:
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (default: admin/admin)

## Troubleshooting

### Common Issues

1. **Fabric connection failed**
   - Verify API credentials in .env
   - Check network connectivity
   - Ensure headers are included

2. **Command execution blocked**
   - Check security whitelist/blacklist
   - Verify user permissions
   - Review sandbox settings

3. **File operations failing**
   - Check path permissions
   - Verify allowed paths configuration
   - Ensure WORKDIR exists and is writable

### Logs

View logs with:
```bash
# All logs
make logs

# Backend logs
docker logs pandora-backend

# Frontend logs  
docker logs pandora-frontend
```

## Production Deployment

### Kubernetes

```bash
# Deploy to Kubernetes
kubectl apply -f deployment/kubernetes/

# Scale replicas
kubectl scale deployment pandora-backend --replicas=3

# View status
kubectl get pods -n pandora
```

### Docker Swarm

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.prod.yml pandora

# Scale service
docker service scale pandora_backend=3
```

## Development

### Running Tests

```bash
# Run all tests
make test

# Backend tests
cd backend && vendor/bin/phpunit

# Frontend tests
cd frontend && python -m pytest tests/

# Integration tests
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

### Code Quality

```bash
# PHP Static Analysis
cd backend && vendor/bin/phpstan analyse

# Python Linting
cd frontend && flake8 src/
cd frontend && mypy src/

# Format code
cd backend && vendor/bin/php-cs-fixer fix
cd frontend && black src/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

- Documentation: TBD
- Issues: TBD
- Email: TBD
  
## Important Notes

⚠️ **REQUIRED**: You MUST set the following in your .env file:
- `FABRIC_API_KEY`: Your Fabric API key
- `FABRIC_ORG_ID`: Your organization ID  
- `FABRIC_PROJECT_ID`: Your project ID

Without these, the AI integration will not function.

## Version History

- v1.0.0 - Initial release with full Tela/Fabric integration
- v0.2.0 - Beta release with core functionality
- v0.1.0 - Alpha release for testing
