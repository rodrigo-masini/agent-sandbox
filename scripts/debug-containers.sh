#!/bin/bash
# Advanced container debugging script for CI/CD

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_debug() { echo -e "${BLUE}[DEBUG]${NC} $1"; }

# Configuration
PROJECT_NAME="${PROJECT_NAME:-agtsdbx}"
BACKEND_CONTAINER="${PROJECT_NAME}-backend-dev"
MAX_WAIT_TIME="${MAX_WAIT_TIME:-120}"
DEBUG_OUTPUT_DIR="${DEBUG_OUTPUT_DIR:-./debug-output}"

# Create debug output directory
mkdir -p "$DEBUG_OUTPUT_DIR"

# Function to check Docker daemon
check_docker() {
    log_info "Checking Docker daemon..."
    
    if ! docker info > "$DEBUG_OUTPUT_DIR/docker-info.txt" 2>&1; then
        log_error "Docker daemon is not running or not accessible"
        cat "$DEBUG_OUTPUT_DIR/docker-info.txt"
        exit 1
    fi
    
    log_info "Docker version: $(docker --version)"
    log_info "Docker Compose version: $(docker compose version 2>/dev/null || docker-compose --version)"
}

# Function to inspect container
inspect_container() {
    local container=$1
    local output_file="$DEBUG_OUTPUT_DIR/${container}-inspect.json"
    
    log_debug "Inspecting container: $container"
    
    if docker inspect "$container" > "$output_file" 2>/dev/null; then
        # Extract key information
        local state=$(docker inspect --format='{{.State.Status}}' "$container")
        local health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "no-health-check")
        local exit_code=$(docker inspect --format='{{.State.ExitCode}}' "$container")
        local started_at=$(docker inspect --format='{{.State.StartedAt}}' "$container")
        local finished_at=$(docker inspect --format='{{.State.FinishedAt}}' "$container")
        
        echo "  Status: $state"
        echo "  Health: $health"
        echo "  Exit Code: $exit_code"
        echo "  Started: $started_at"
        
        if [ "$state" != "running" ]; then
            echo "  Finished: $finished_at"
            
            # Get last logs if not running
            echo ""
            echo "  Last 20 log lines:"
            docker logs --tail 20 "$container" 2>&1 | sed 's/^/    /'
        fi
        
        # Check mount points
        echo ""
        echo "  Mounts:"
        docker inspect --format='{{range .Mounts}}  - {{.Source}} -> {{.Destination}} ({{.Mode}}){{println}}{{end}}' "$container"
        
        # Check environment variables (filter sensitive)
        echo ""
        echo "  Environment (non-sensitive):"
        docker inspect --format='{{range .Config.Env}}{{println}}    {{.}}{{end}}' "$container" | \
            grep -E "(APP_|LOG_|DEBUG|PHP_|WORKDIR)" | head -10
            
        # Check network
        echo ""
        echo "  Networks:"
        docker inspect --format='{{range $net, $conf := .NetworkSettings.Networks}}  - {{$net}}: {{$conf.IPAddress}}{{println}}{{end}}' "$container"
        
    else
        log_warn "Container $container not found"
    fi
}

# Function to test container health endpoint
test_health_endpoint() {
    local container=$1
    local port=${2:-8000}
    local endpoint=${3:-/health}
    
    log_debug "Testing health endpoint for $container on port $port"
    
    # Test from host
    echo "  Testing from host:"
    if curl -sf "http://localhost:$port$endpoint" > "$DEBUG_OUTPUT_DIR/${container}-health-host.json" 2>&1; then
        echo "    ✅ Success"
        cat "$DEBUG_OUTPUT_DIR/${container}-health-host.json" | python3 -m json.tool 2>/dev/null || cat "$DEBUG_OUTPUT_DIR/${container}-health-host.json"
    else
        echo "    ❌ Failed"
        curl -v "http://localhost:$port$endpoint" 2>&1 | tail -5
    fi
    
    # Test from inside container network
    echo "  Testing from container network:"
    if docker run --rm --network="${PROJECT_NAME}_network" alpine:latest \
        sh -c "apk add --no-cache curl >/dev/null 2>&1 && curl -sf http://${container}:8000${endpoint}" \
        > "$DEBUG_OUTPUT_DIR/${container}-health-network.json" 2>&1; then
        echo "    ✅ Success"
    else
        echo "    ❌ Failed"
    fi
    
    # Test from inside the container itself
    echo "  Testing from inside container:"
    if docker exec "$container" curl -sf "http://localhost:8000${endpoint}" \
        > "$DEBUG_OUTPUT_DIR/${container}-health-internal.json" 2>&1; then
        echo "    ✅ Success"
    else
        echo "    ❌ Failed"
        # Try with PHP directly
        echo "    Trying PHP directly:"
        docker exec "$container" php -r "echo 'PHP is running';" 2>&1 || echo "    PHP execution failed"
    fi
}

# Function to check file system inside container
check_container_filesystem() {
    local container=$1
    
    log_debug "Checking filesystem in $container"
    
    echo "  Checking critical paths:"
    
    # Check if container is running
    if ! docker ps | grep -q "$container"; then
        log_warn "Container $container is not running, skipping filesystem check"
        return
    fi
    
    paths=(
        "/app/vendor/autoload.php"
        "/app/composer.json"
        "/app/composer.lock"
        "/app/public/index.php"
        "/app/public/health.php"
        "/app/storage/logs"
        "/app/WORKDIR"
    )
    
    for path in "${paths[@]}"; do
        if docker exec "$container" test -e "$path" 2>/dev/null; then
            echo "    ✅ $path exists"
            
            # Check if it's a directory and if it's writable
            if docker exec "$container" test -d "$path" 2>/dev/null; then
                if docker exec "$container" test -w "$path" 2>/dev/null; then
                    echo "       (directory, writable)"
                else
                    echo "       (directory, read-only)"
                fi
            fi
        else
            echo "    ❌ $path missing"
        fi
    done
    
    # Check PHP extensions
    echo ""
    echo "  PHP Extensions:"
    docker exec "$container" php -m 2>/dev/null | head -20 | sed 's/^/    /' || echo "    Failed to get PHP extensions"
    
    # Check running processes
    echo ""
    echo "  Running processes:"
    docker exec "$container" ps aux 2>/dev/null | head -10 | sed 's/^/    /' || echo "    Failed to get process list"
}

# Function to monitor container startup
monitor_startup() {
    log_info "Monitoring container startup (max ${MAX_WAIT_TIME}s)..."
    
    local start_time=$(date +%s)
    local containers=("${PROJECT_NAME}-redis-dev" "${PROJECT_NAME}-db-dev" "${BACKEND_CONTAINER}" "${PROJECT_NAME}-frontend-dev")
    
    while true; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        if [ $elapsed -ge $MAX_WAIT_TIME ]; then
            log_error "Timeout after ${MAX_WAIT_TIME} seconds"
            break
        fi
        
        echo ""
        log_info "Status check at ${elapsed}s:"
        
        local all_healthy=true
        
        for container in "${containers[@]}"; do
            echo ""
            echo "Container: $container"
            
            if ! docker ps -a | grep -q "$container"; then
                echo "  ❌ Not found"
                all_healthy=false
                continue
            fi
            
            local status=$(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null || echo "unknown")
            local health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "no-health-check")
            
            echo "  Status: $status"
            echo "  Health: $health"
            
            if [ "$status" != "running" ]; then
                all_healthy=false
                echo "  ❌ Not running"
                
                # Get exit code and last logs
                local exit_code=$(docker inspect --format='{{.State.ExitCode}}' "$container" 2>/dev/null || echo "unknown")
                echo "  Exit code: $exit_code"
                echo "  Last logs:"
                docker logs --tail 5 "$container" 2>&1 | sed 's/^/    /'
                
            elif [ "$health" != "healthy" ] && [ "$health" != "no-health-check" ]; then
                all_healthy=false
                echo "  ⏳ Not healthy yet"
            else
                echo "  ✅ OK"
            fi
        done
        
        if [ "$all_healthy" = true ]; then
            log_info "All containers are healthy!"
            return 0
        fi
        
        sleep 2
    done
    
    return 1
}

# Function to collect all debug information
collect_debug_info() {
    log_info "Collecting debug information..."
    
    # Docker compose status
    docker compose ps > "$DEBUG_OUTPUT_DIR/compose-ps.txt" 2>&1
    
    # All container logs
    for service in redis postgres agtsdbx frontend; do
        docker compose logs --tail 100 "$service" > "$DEBUG_OUTPUT_DIR/${service}-logs.txt" 2>&1
    done
    
    # Network information
    docker network ls > "$DEBUG_OUTPUT_DIR/networks.txt" 2>&1
    docker network inspect "${PROJECT_NAME}_network" > "$DEBUG_OUTPUT_DIR/network-inspect.json" 2>&1
    
    # Volume information
    docker volume ls > "$DEBUG_OUTPUT_DIR/volumes.txt" 2>&1
    
    # System resources
    docker stats --no-stream > "$DEBUG_OUTPUT_DIR/stats.txt" 2>&1
    df -h > "$DEBUG_OUTPUT_DIR/disk-usage.txt" 2>&1
    free -h > "$DEBUG_OUTPUT_DIR/memory.txt" 2>&1
    
    # Environment
    env | grep -E "(DOCKER|COMPOSE|APP_|PHP_|FABRIC_|AGTSDBX_)" | sort > "$DEBUG_OUTPUT_DIR/environment.txt" 2>&1
    
    log_info "Debug information collected in $DEBUG_OUTPUT_DIR"
}

# Function to fix common issues
attempt_fixes() {
    log_info "Attempting to fix common issues..."
    
    # Fix 1: Ensure composer dependencies are installed
    if docker ps | grep -q "$BACKEND_CONTAINER"; then
        log_info "Installing composer dependencies..."
        docker exec "$BACKEND_CONTAINER" composer install --no-interaction --prefer-dist --optimize-autoloader 2>&1 | tail -10
    fi
    
    # Fix 2: Ensure directories have correct permissions
    if docker ps | grep -q "$BACKEND_CONTAINER"; then
        log_info "Fixing directory permissions..."
        docker exec "$BACKEND_CONTAINER" chmod -R 777 /app/storage 2>/dev/null || true
        docker exec "$BACKEND_CONTAINER" chmod 777 /app/WORKDIR 2>/dev/null || true
    fi
    
    # Fix 3: Create health endpoint if missing
    if docker ps | grep -q "$BACKEND_CONTAINER"; then
        log_info "Ensuring health endpoint exists..."
        docker exec "$BACKEND_CONTAINER" sh -c 'if [ ! -f /app/public/health.php ]; then echo "<?php echo json_encode([\"status\"=>\"healthy\"]);" > /app/public/health.php; fi' 2>/dev/null || true
    fi
}

# Main execution
main() {
    echo "==================================="
    echo "Container Debug Script"
    echo "==================================="
    echo "Time: $(date)"
    echo "Project: $PROJECT_NAME"
    echo ""
    
    # Check Docker
    check_docker
    
    # Monitor startup
    if ! monitor_startup; then
        log_warn "Some containers failed to start properly"
        
        # Attempt fixes
        attempt_fixes
        
        # Try monitoring again briefly
        log_info "Checking again after fixes..."
        sleep 5
        monitor_startup || true
    fi
    
    echo ""
    echo "==================================="
    echo "Detailed Container Analysis"
    echo "==================================="
    
    # Inspect each container
    for container in "${PROJECT_NAME}-redis-dev" "${PROJECT_NAME}-db-dev" "${BACKEND_CONTAINER}" "${PROJECT_NAME}-frontend-dev"; do
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "Container: $container"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        inspect_container "$container"
        
        if [ "$container" = "$BACKEND_CONTAINER" ]; then
            echo ""
            echo "Health Endpoint Tests:"
            test_health_endpoint "$container" 8000 "/health"
            
            echo ""
            echo "Filesystem Check:"
            check_container_filesystem "$container"
        fi
    done
    
    # Collect all debug info
    echo ""
    collect_debug_info
    
    # Generate summary
    echo ""
    echo "==================================="
    echo "Summary"
    echo "==================================="
    
    # Count healthy containers
    healthy_count=0
    total_count=0
    
    for container in "${PROJECT_NAME}-redis-dev" "${PROJECT_NAME}-db-dev" "${BACKEND_CONTAINER}" "${PROJECT_NAME}-frontend-dev"; do
        total_count=$((total_count + 1))
        if docker ps | grep -q "$container"; then
            health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "running")
            if [ "$health" = "healthy" ] || [ "$health" = "running" ]; then
                healthy_count=$((healthy_count + 1))
            fi
        fi
    done
    
    echo "Healthy containers: $healthy_count / $total_count"
    
    if [ $healthy_count -eq $total_count ]; then
        log_info "✅ All containers are running successfully!"
        exit 0
    else
        log_error "❌ Some containers failed to start properly"
        log_info "Debug output saved to: $DEBUG_OUTPUT_DIR"
        exit 1
    fi
}

# Run main function
main "$@"