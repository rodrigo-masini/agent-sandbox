#!/bin/bash
# scripts/fix-ci-issues.sh

echo "🔧 Fixing CI Issues..."

# Fix PHP code issues
echo "Fixing PHP code..."

# Fix CacheManager.php
sed -i.bak '84s/.*/            if (is_int($result) \&\& $ttl !== null \&\& $result == $value) {/' backend/src/Storage/CacheManager.php
sed -i '89s/.*/            return is_int($result) ? $result : 0;/' backend/src/Storage/CacheManager.php

# Fix SecurityManager.php  
sed -i.bak '15s/.*/        $this->config = $config ?: Config::getInstance();/' backend/src/Core/Security/SecurityManager.php
sed -i '16s/.*/        $this->logger = $logger ?: new Logger($this->config);/' backend/src/Core/Security/SecurityManager.php

# Ensure Python modules exist
echo "Creating Python modules..."
for dir in frontend/src frontend/src/app frontend/src/core frontend/src/clients frontend/src/tools frontend/src/ui; do
    mkdir -p $dir
    touch $dir/__init__.py
done

# Generate composer.lock if missing
if [ ! -f backend/composer.lock ]; then
    echo "Generating composer.lock..."
    cd backend
    docker run --rm -v $(pwd):/app -w /app composer:2.7 install --ignore-platform-reqs --no-scripts
    cd ..
fi

echo "✅ Fixes applied!"
echo ""
echo "Now commit and push these changes:"
echo "  git add -A"
echo "  git commit -m 'Fix CI pipeline issues'"
echo "  git push"