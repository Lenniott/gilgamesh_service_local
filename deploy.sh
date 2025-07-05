#!/bin/bash
# Gilgamesh Media Service Deployment Script

set -e

echo "🚀 Deploying Gilgamesh Media Processing Service"
echo "================================================"

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "💡 Create .env file with required variables:"
    echo "   PG_DBNAME=your_database"
    echo "   PG_USER=your_user"
    echo "   PG_PASSWORD=your_password"
    echo "   PG_HOST=postgres"
    echo "   OPENAI_API_KEY=your_openai_key"
    echo "   GEMINI_API_KEY=your_gemini_key (optional)"
    echo "   AI_PROVIDER=openai"
    exit 1
fi

# Load environment variables
source .env

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p temp cache

# Build and start services
echo "🔨 Building Docker images..."
docker-compose build

echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🔍 Checking service health..."
if curl -f http://localhost:8500/health > /dev/null 2>&1; then
    echo "✅ Gilgamesh API is healthy!"
else
    echo "❌ Gilgamesh API health check failed"
    echo "📋 Checking logs..."
    docker-compose logs gilgamesh-api
    exit 1
fi

# Test database connection
echo "🗄️  Testing database setup..."
if docker-compose exec -T gilgamesh-api python setup_simple_db.py; then
    echo "✅ Database setup successful!"
else
    echo "❌ Database setup failed"
    echo "📋 Checking logs..."
    docker-compose logs postgres
    exit 1
fi

echo ""
echo "🎉 Deployment successful!"
echo "📊 Service Status:"
echo "   • API: http://localhost:8500"
echo "   • Health: http://localhost:8500/health"
echo "   • Docs: http://localhost:8500/docs"
echo "   • PostgreSQL: localhost:5432"
echo "   • Qdrant: http://localhost:6333"
echo ""
echo "🔧 Management Commands:"
echo "   • View logs: docker-compose logs -f"
echo "   • Stop services: docker-compose down"
echo "   • Restart: docker-compose restart"
echo "   • Update: git pull && docker-compose build && docker-compose up -d" 