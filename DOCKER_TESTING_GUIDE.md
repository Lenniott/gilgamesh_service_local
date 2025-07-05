# 🐳 Docker Testing Guide - Local First, Then Portainer

## 🎯 **Testing Strategy**

1. **Local Docker Test** - Verify everything works on your machine
2. **Portainer Deployment** - Move to your Portainer setup

---

## 📋 **Pre-Flight Check**

### **Required Files** ✅
- `Dockerfile` - Updated for Python 3.11+
- `docker-compose.yml` - Full stack with PostgreSQL + Qdrant
- `requirements.txt` - All dependencies organized
- `env.example` - Environment template
- `test-docker-local.sh` - Automated testing script

### **System Requirements**
- Docker Desktop running
- 4GB+ RAM available
- Ports 8500, 5432, 6333 available

---

## 🧪 **Step 1: Local Docker Testing**

### **Quick Test (Recommended)**
```bash
# 1. Run the automated test
./test-docker-local.sh

# This will:
# - Create .env from template
# - Build the Docker image
# - Test the API container
# - Verify health endpoints
```

### **Manual Testing**

#### **1. Setup Environment**
```bash
# Copy environment template
cp env.example .env

# Edit with your API keys
nano .env  # or use your preferred editor
```

#### **2. Required Environment Variables**
```bash
# In .env file - REQUIRED
OPENAI_API_KEY=sk-your-actual-openai-key
# OR
GEMINI_API_KEY=your-actual-gemini-key

# Database (will be auto-created by Docker)
PG_DBNAME=gilgamesh_media
PG_USER=postgres
PG_PASSWORD=your_secure_password

# Qdrant (will be auto-created by Docker)
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your-qdrant-key
```

#### **3. Build and Test**
```bash
# Create directories
mkdir -p temp cache

# Build image
docker build -t gilgamesh-media-service:latest .

# Start full stack
docker-compose up -d

# Check logs
docker-compose logs -f gilgamesh-api
```

#### **4. Verify Services**
```bash
# Health check
curl http://localhost:8500/health
# Expected: {"status": "healthy"}

# API docs
open http://localhost:8500/docs

# Test simple endpoint
curl -X POST "http://localhost:8500/process/simple" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.instagram.com/p/test/", "describe": false, "transcribe": false, "save_video": false}'
```

#### **5. Database Verification**
```bash
# Check PostgreSQL
docker exec -it gilgamesh-postgres psql -U postgres -d gilgamesh_media -c "\dt"
# Should show: simple_videos table

# Check Qdrant
curl http://localhost:6333/collections
# Should return: collections list
```

---

## 🚀 **Step 2: Portainer Deployment**

### **After Local Success**

#### **1. Prepare for Portainer**
```bash
# Stop local stack
docker-compose down

# Create Portainer-specific .env
cp portainer.env .env.portainer

# Edit with your Portainer details
nano .env.portainer
```

#### **2. Portainer Configuration**
Use the values from `portainer.env`:
```bash
# Your existing PostgreSQL
PG_DBNAME=n8ndb
PG_USER=n8n
PG_PASSWORD=ohgodiconfessimamess
PG_HOST=postgres

# Your existing Qdrant
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=findme-gagme-putme-inabunnyranch

# Your AI keys
OPENAI_API_KEY=your-actual-key
```

#### **3. Database Setup in Portainer**
```bash
# Connect to your PostgreSQL container
docker exec -it postgres psql -U n8n -d n8ndb

# Run the table creation SQL from portainer-deployment-guide.md
# Creates simple_videos table in your existing database
```

#### **4. Deploy in Portainer UI**
Follow `portainer-deployment-guide.md`:
1. Build image: `gilgamesh-media-service:latest`
2. Create container with `n8n_net` network
3. Port mapping: `8500:8500`
4. Environment variables from `portainer.env`

---

## 🔍 **Troubleshooting**

### **Common Issues**

#### **Build Fails**
```bash
# Check Docker is running
docker info

# Clean build cache
docker system prune -f
docker build --no-cache -t gilgamesh-media-service:latest .
```

#### **Health Check Fails**
```bash
# Check container logs
docker logs gilgamesh-media-service

# Check if port is available
lsof -i :8500

# Manual health test
docker exec -it gilgamesh-media-service curl localhost:8500/health
```

#### **Database Connection Issues**
```bash
# Check PostgreSQL is running
docker exec -it gilgamesh-postgres pg_isready

# Check Qdrant is running
curl http://localhost:6333/health

# Test from container
docker exec -it gilgamesh-media-service python -c "
import asyncio
import sys
sys.path.append('app')
from app.db_connections import get_db_connections

async def test():
    db = await get_db_connections()
    results = await db.test_all_connections()
    print('Results:', results)

asyncio.run(test())
"
```

#### **Permission Issues**
```bash
# Fix temp/cache permissions
sudo chown -R $(id -u):$(id -g) temp cache

# Check container user
docker exec -it gilgamesh-media-service whoami
# Should be: app
```

---

## ✅ **Success Criteria**

### **Local Testing**
- [ ] Docker image builds without errors
- [ ] Health endpoint returns 200
- [ ] API docs accessible at /docs
- [ ] PostgreSQL table created
- [ ] Qdrant collections accessible
- [ ] Container logs show no errors

### **Portainer Deployment**
- [ ] Image builds in Portainer UI
- [ ] Container starts and stays running
- [ ] Health endpoint accessible from host
- [ ] Database table created in n8ndb
- [ ] No conflicts with existing n8n services

---

## 📊 **Performance Verification**

### **Test API Endpoints**
```bash
# Health check
curl http://localhost:8500/health

# List recent videos
curl http://localhost:8500/videos/recent

# Search functionality
curl "http://localhost:8500/videos/search?query=test"

# Process a simple request (no actual video)
curl -X POST "http://localhost:8500/process/simple" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.instagram.com/p/test/",
    "save_video": false,
    "transcribe": false,
    "describe": false
  }'
```

---

## 🎉 **Ready for Production**

Once both local and Portainer testing pass:
- ✅ Docker setup is verified
- ✅ Database integration works
- ✅ API endpoints functional
- ✅ Environment properly configured
- ✅ Ready for real video processing! 