#!/bin/bash
# Robust setup script for Agent Sandbox

set -e
trap 'echo "❌ Setup failed at line $LINENO"' ERR

echo "🚀 Magic Agent Sandbox - Robust Setup"
echo "====================================="

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}✅ $1${NC}"; }
log_warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# Check prerequisites
check_prerequisites() {
    echo "🔍 Checking prerequisites..."
    
    local missing=()
    
    command -v docker >/dev/null 2>&1 || missing+=("docker")
    command -v git >/dev/null 2>&1 || missing+=("git")
    
    # Check for docker-compose or docker compose
    if ! command -v docker-compose >/dev/null 2>&1 && ! docker compose version >/dev/null 2>&1; then
        missing+=("docker-compose")
    fi
    
    if [ ${#missing[@]} -gt 0 ]; then
        log_error "Missing required tools: ${missing[*]}"
        echo "Please install the missing tools and try again."
        exit 1
    fi
    
    log_info "All prerequisites met"
}

# Fix backend Dockerfile
fix_dockerfile() {
    echo "🔧 Fixing backend Dockerfile..."
    
    local dockerfile="$BACKEND_DIR/docker/Dockerfile"
    
    if [ -f "$dockerfile" ]; then
        # Remove json from docker-php-ext-install if present
        if grep -q "docker-php-ext-install.*json" "$dockerfile"; then
            log_warn "Removing 'json' extension from Dockerfile (built-in for PHP 8.x)"
            sed -i.bak 's/json//' "$dockerfile"
            sed -i 's/  */ /g' "$dockerfile"  # Remove extra spaces
            sed -i 's/ \\$/\\/' "$dockerfile"  # Fix trailing backslashes
            log_info "Dockerfile fixed"
        else
            log_info "Dockerfile already correct"
        fi
    else
        log_error "Dockerfile not found at $dockerfile"
        exit 1
    fi
}

# Generate composer.lock
generate_composer_lock() {
    echo "📦 Generating composer.lock..."
    
    cd "$BACKEND_DIR"
    
    if [ -f composer.lock ]; then
        log_info "composer.lock already exists"
        return
    fi
    
    # Use Docker to generate composer.lock
    docker run --rm \
        -v "$BACKEND_DIR":/app \
        -w /app \
        composer:2.7 \
        update \
        --no-interaction \
        --no-progress \
        --prefer-dist \
        --prefer-stable \
        --ignore-platform-reqs \
        --no-scripts \
        --no-autoloader
    
    if [ -f composer.lock ]; then
        log_info "composer.lock generated successfully"
    else
        log_error "Failed to generate composer.lock"
        exit 1
    fi
}

# Setup Python modules
setup_python_modules() {
    echo "🐍 Setting up Python modules..."
    
    local modules=(
        "src"
        "src/app"
        "src/core" 
        "src/clients"
        "src/tools"
        "src/ui"
        "src/ui/components"
        "src/ui/layouts"
    )
    
    for module in "${modules[@]}"; do
        local module_path="$FRONTEND_DIR/$module"
        mkdir -p "$module_path"
        
        if [ ! -f "$module_path/__init__.py" ]; then
            touch "$module_path/__init__.py"
            echo "# Module: $module" > "$module_path/__init__.py"
        fi
    done
    
    log_info "Python modules configured"
}

# Create directory structure
create_directories() {
    echo "📁 Creating directory structure..."
    
    local dirs=(
        "$BACKEND_DIR/storage/logs"
        "$BACKEND_DIR/storage/cache"
        "$BACKEND_DIR/storage/sessions"
        "$BACKEND_DIR/storage/framework"
        "$BACKEND_DIR/WORKDIR"
        "$BACKEND_DIR/public"
        "$BACKEND_DIR/config"
        "$BACKEND_DIR/src"
        "$BACKEND_DIR/tests"
        "$FRONTEND_DIR/static/css"
        "$FRONTEND_DIR/static/js"
        "$FRONTEND_DIR/templates"
        "$FRONTEND_DIR/tests"
        "$PROJECT_ROOT/monitoring/prometheus"
        "$PROJECT_ROOT/monitoring/grafana/dashboards"
    )
    
    for dir in "${dirs[@]}"; do
        mkdir -p "$dir"
    done
    
    # Set permissions
    chmod -R 755 "$BACKEND_DIR/storage" 2>/dev/null || true
    chmod 755 "$BACKEND_DIR/WORKDIR" 2>/dev/null || true
    
    log_info "Directory structure created"
}

# Setup environment file
setup_environment() {
    echo "🔐 Setting up environment..."
    
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        if [ -f "$PROJECT_ROOT/.env.example" ]; then
            cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
            
            # Generate secure keys
            SECRET_KEY=$(openssl rand -hex 32)
            JWT_SECRET=$(openssl rand -hex 32)
            
            # Update .env with generated keys
            sed -i.bak "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" "$PROJECT_ROOT/.env"
            sed -i.bak "s/JWT_SECRET=.*/JWT_SECRET=$JWT_SECRET/" "$PROJECT_ROOT/.env"
            
            log_info "Environment file created with secure keys"
            log_warn "Please edit .env and add your Fabric API credentials"
        else
            log_error ".env.example not found"
            exit 1
        fi
    else
        log_info "Environment file already exists"
    fi
}

# Setup git hooks
setup_git_hooks() {
    echo "🪝 Setting up git hooks..."
    
    if [ -f "$PROJECT_ROOT/.githooks/pre-commit" ]; then
        chmod +x "$PROJECT_ROOT/.githooks/pre-commit"
        git config core.hooksPath .githooks
        log_info "Git hooks configured"
    else
        log_warn "Git hooks not found"
    fi
}

# Build Docker images
build_docker_images() {
    echo "🐳 Building Docker images..."
    
    cd "$PROJECT_ROOT"
    
    # Use docker compose or docker-compose
    if docker compose version >/dev/null 2>&1; then
        DOCKER_COMPOSE="docker compose"
    else
        DOCKER_COMPOSE="docker-compose"
    fi
    
    # Build images
    $DOCKER_COMPOSE build --progress plain || {
        log_error "Docker build failed"
        echo "Checking docker daemon..."
        docker version || log_error "Docker daemon not running"
        exit 1
    }
    
    log_info "Docker images built successfully"
}

# Verify setup
verify_setup() {
    echo "🔍 Verifying setup..."
    
    local issues=()
    
    # Check critical files
    [ -f "$BACKEND_DIR/composer.json" ] || issues+=("backend/composer.json missing")
    [ -f "$BACKEND_DIR/composer.lock" ] || issues+=("backend/composer.lock missing")
    [ -f "$FRONTEND_DIR/requirements/base.txt" ] || issues+=("frontend/requirements/base.txt missing")
    [ -f "$PROJECT_ROOT/.env" ] || issues+=("/.env missing")
    
    # Check Docker images
    docker images | grep -q "agtsdbx" || issues+=("Docker images not built")
    
    if [ ${#issues[@]} -gt 0 ]; then
        log_error "Setup verification failed:"
        for issue in "${issues[@]}"; do
            echo "  - $issue"
        done
        exit 1
    fi
    
    log_info "Setup verification passed"
}

# Main execution
main() {
    cd "$PROJECT_ROOT"
    
    check_prerequisites
    fix_dockerfile
    create_directories
    setup_python_modules
    generate_composer_lock
    setup_environment
    setup_git_hooks
    build_docker_images
    verify_setup
    
    echo ""
    echo "✨ Setup completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Edit .env and add your Fabric API credentials"
    echo "2. Run 'docker compose up -d' to start services"
    echo "3. Access the application at http://localhost:8080"
    echo ""
    echo "For CI/CD, use the improved workflow: .github/workflows/ci-improved.yml"
}

# Run main function
main "$@"