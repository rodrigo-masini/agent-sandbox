#!/bin/bash
# Quick fix script for CI issues

echo "🚨 Applying quick fixes for CI..."

# Fix 1: Remove json extension from Dockerfile
echo "🔧 Fixing Dockerfile..."
sed -i 's/json//' backend/docker/Dockerfile
sed -i 's/  */ /g' backend/docker/Dockerfile
sed -i 's/ \\$/\\/' backend/docker/Dockerfile

# Fix 2: Generate composer.lock if missing
if [ ! -f backend/composer.lock ]; then
    echo "📦 Generating composer.lock..."
    docker run --rm \
        -v "$(pwd)/backend":/app \
        -w /app \
        composer:2.7 \
        update \
        --no-interaction \
        --prefer-dist \
        --ignore-platform-reqs \
        --no-scripts
fi

# Fix 3: Create Python module structure
echo "🐍 Creating Python modules..."
for dir in src src/app src/core src/clients src/tools src/ui src/ui/components src/ui/layouts; do
    mkdir -p "frontend/$dir"
    touch "frontend/$dir/__init__.py"
done

# Fix 4: Make scripts executable
chmod +x backend/scripts/*.sh 2>/dev/null || true
chmod +x scripts/*.sh 2>/dev/null || true

echo "✅ Quick fixes applied!"
echo ""
echo "You can now commit these changes and push to trigger CI."