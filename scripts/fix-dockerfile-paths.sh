#!/bin/bash
# fix-dockerfile-paths.sh

echo "🔧 Fixing CI/CD Dockerfile paths..."

# Check if frontend Dockerfile exists at the correct location
if [ -f "frontend/Dockerfile" ] && [ ! -f "frontend/docker/Dockerfile" ]; then
    echo "✅ Frontend Dockerfile is at the correct location: frontend/Dockerfile"
else
    echo "⚠️  Frontend Dockerfile location issue detected"
fi

# Check if backend Dockerfile exists
if [ -f "backend/docker/Dockerfile" ]; then
    echo "✅ Backend Dockerfile is at the correct location: backend/docker/Dockerfile"
else
    echo "❌ Backend Dockerfile not found at backend/docker/Dockerfile"
fi

# Update docker-compose files to ensure they use correct paths
echo "📝 Verifying docker-compose.yml paths..."
grep -A2 "dockerfile:" docker-compose.yml

echo ""
echo "To fix the CI/CD pipeline, update the .github/workflows/ci.yml file with the changes above."