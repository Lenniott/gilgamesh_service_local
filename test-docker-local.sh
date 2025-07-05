#!/bin/bash
# Test Docker Setup Locally

set -e

echo "🧪 Testing Gilgamesh Docker Setup Locally"
echo "=========================================="

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp env.example .env
    echo "⚠️  Please edit .env file with your API keys before continuing!"
    echo "   Required: OPENAI_API_KEY or GEMINI_API_KEY"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running!"
    exit 1
fi

echo "✅ Docker is running"

# Create temp and cache directories
echo "📁 Creating directories..."
mkdir -p temp cache

# Build the image
echo "🔨 Building Docker image..."
docker build -t gilgamesh-test:latest .

if [ $? -eq 0 ]; then
    echo "✅ Docker image built successfully"
else
    echo "❌ Docker image build failed"
    exit 1
fi

# Test just the API container first (without databases)
echo "🚀 Testing API container..."
docker run --rm -d \
    --name gilgamesh-test \
    -p 8500:8500 \
    -e AI_PROVIDER=openai \
    -e OPENAI_API_KEY=${OPENAI_API_KEY:-test} \
    -e PG_HOST=localhost \
    -e PG_DBNAME=test \
    -e PG_USER=test \
    -e PG_PASSWORD=test \
    -e QDRANT_URL=http://localhost:6333 \
    -v $(pwd)/temp:/app/temp \
    -v $(pwd)/cache:/app/cache \
    gilgamesh-test:latest

# Wait for container to start
echo "⏳ Waiting for container to start..."
sleep 10

# Test health endpoint
echo "🔍 Testing health endpoint..."
if curl -f http://localhost:8500/health > /dev/null 2>&1; then
    echo "✅ Health endpoint is working!"
else
    echo "❌ Health endpoint failed"
    echo "📋 Container logs:"
    docker logs gilgamesh-test
    docker stop gilgamesh-test
    exit 1
fi

# Test docs endpoint
echo "🔍 Testing docs endpoint..."
if curl -f http://localhost:8500/docs > /dev/null 2>&1; then
    echo "✅ Docs endpoint is working!"
else
    echo "⚠️  Docs endpoint might have issues"
fi

# Stop test container
echo "🛑 Stopping test container..."
docker stop gilgamesh-test

echo ""
echo "🎉 Basic Docker setup test passed!"
echo ""
echo "🚀 Ready for full stack testing:"
echo "   docker-compose up -d"
echo ""
echo "📊 Next steps:"
echo "   1. Update .env with your API keys"
echo "   2. Run: docker-compose up -d"
echo "   3. Test: curl http://localhost:8500/health"
echo "   4. Docs: http://localhost:8500/docs" 