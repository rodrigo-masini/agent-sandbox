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
mkdir -p deployment/kubernetes
mkdir -p deployment/terraform
mkdir -p deployment/ansible

# Set permissions
chmod -R 755 backend/storage
chmod 700 backend/WORKDIR

# Copy environment file
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your Fabric credentials"
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