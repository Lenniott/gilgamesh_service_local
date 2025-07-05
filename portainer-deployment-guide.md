# Gilgamesh Media Service - Portainer Deployment Guide

## 🐳 **Portainer UI Deployment Instructions**

### **Step 1: Build the Image**

1. **In Portainer UI:**
   - Go to **Images** → **Build a new image**
   - **Image name:** `gilgamesh-media-service:latest`
   - **Build method:** Upload or Git repository
   - **Upload the project folder** or use Git URL
   - Click **Build the image**

### **Step 2: Create the Container**

1. **In Portainer UI:**
   - Go to **Containers** → **Add container**
   - **Name:** `gilgamesh-media-service`
   - **Image:** `gilgamesh-media-service:latest`

### **Step 3: Network Configuration**

1. **Network settings:**
   - **Network:** `n8n_net`
   - This connects to your existing PostgreSQL and Qdrant containers

### **Step 4: Port Configuration**

1. **Port mapping:**
   - **Container port:** `8500`
   - **Host port:** `8500`
   - **Protocol:** TCP

### **Step 5: Environment Variables**

Add these environment variables in Portainer:

```bash
# Database Configuration (Your existing PostgreSQL)
PG_DBNAME=n8ndb
PG_USER=n8n
PG_PASSWORD=ohgodiconfessimamess
PG_HOST=postgres
PG_PORT=5432

# AI Provider Configuration
AI_PROVIDER=openai
OPENAI_API_KEY=your-openai-api-key-here
GEMINI_API_KEY=your-gemini-api-key-here

# Qdrant Configuration (Your existing Qdrant)
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=findme-gagme-putme-inabunnyranch
```

### **Step 6: Volume Mounts**

1. **Create volumes for temp and cache:**
   - **Container path:** `/app/temp` → **Host path:** `gilgamesh_temp`
   - **Container path:** `/app/cache` → **Host path:** `gilgamesh_cache`

### **Step 7: Restart Policy**

1. **Restart policy:** `Unless stopped`

### **Step 8: Deploy**

1. Click **Deploy the container**

---

## 🗄️ **Database Setup**

Since you're using the existing `n8ndb` database, you need to create the Gilgamesh table:

### **Option 1: Run SQL in your PostgreSQL container**

1. **Connect to PostgreSQL container:**
   ```bash
   docker exec -it postgres psql -U n8n -d n8ndb
   ```

2. **Run the table creation script:**
   ```sql
   -- Create the simple_videos table in public schema
   CREATE TABLE IF NOT EXISTS public.simple_videos (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       url TEXT NOT NULL,
       carousel_index INTEGER DEFAULT 0,
       video_base64 TEXT,
       transcript JSONB,
       descriptions JSONB,
       tags TEXT[],
       metadata JSONB,
       created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
       updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
   );

   -- Create unique constraint for URL + carousel_index combination
   CREATE UNIQUE INDEX IF NOT EXISTS idx_simple_videos_url_carousel 
   ON public.simple_videos(url, carousel_index);

   -- Create indexes for efficient querying
   CREATE INDEX IF NOT EXISTS idx_simple_videos_url ON public.simple_videos(url);
   CREATE INDEX IF NOT EXISTS idx_simple_videos_created_at ON public.simple_videos(created_at DESC);
   CREATE INDEX IF NOT EXISTS idx_simple_videos_updated_at ON public.simple_videos(updated_at DESC);

   -- GIN indexes for JSON and array fields
   CREATE INDEX IF NOT EXISTS idx_simple_videos_transcript_gin 
   ON public.simple_videos USING GIN(transcript);
   CREATE INDEX IF NOT EXISTS idx_simple_videos_descriptions_gin 
   ON public.simple_videos USING GIN(descriptions);
   CREATE INDEX IF NOT EXISTS idx_simple_videos_tags_gin 
   ON public.simple_videos USING GIN(tags);
   CREATE INDEX IF NOT EXISTS idx_simple_videos_metadata_gin 
   ON public.simple_videos USING GIN(metadata);

   -- Update trigger
   CREATE OR REPLACE FUNCTION update_updated_at_column()
   RETURNS TRIGGER AS $$
   BEGIN
       NEW.updated_at = NOW();
       RETURN NEW;
   END;
   $$ language 'plpgsql';

   CREATE TRIGGER IF NOT EXISTS update_simple_videos_updated_at
       BEFORE UPDATE ON public.simple_videos
       FOR EACH ROW
       EXECUTE FUNCTION update_updated_at_column();
   ```

### **Option 2: Auto-setup via container**

1. **After container is running, exec into it:**
   ```bash
   docker exec -it gilgamesh-media-service python setup_simple_db.py
   ```

---

## 🔍 **Verification**

### **Check container health:**
```bash
curl http://localhost:8500/health
```

### **Check API documentation:**
```bash
curl http://localhost:8500/docs
```

### **Test database connection:**
```bash
docker exec -it gilgamesh-media-service python -c "
import asyncio
import sys
sys.path.append('app')
from app.db_connections import get_db_connections

async def test():
    db = await get_db_connections()
    results = await db.test_all_connections()
    print('PostgreSQL:', '✅' if results.get('postgresql') else '❌')
    print('Qdrant:', '✅' if results.get('qdrant') else '❌')
    print('OpenAI:', '✅' if results.get('openai') else '❌')

asyncio.run(test())
"
```

---

## 🚀 **Service Endpoints**

Once deployed:
- **API:** http://localhost:8500
- **Health:** http://localhost:8500/health  
- **Docs:** http://localhost:8500/docs
- **OpenAPI:** http://localhost:8500/openapi.json

---

## 🔧 **Troubleshooting**

### **Container won't start:**
1. Check logs in Portainer UI
2. Verify environment variables are set correctly
3. Ensure network connectivity to postgres and qdrant containers

### **Database connection issues:**
1. Verify PostgreSQL container is running
2. Check if `simple_videos` table exists
3. Verify network connectivity between containers

### **Qdrant connection issues:**
1. Verify Qdrant container is running
2. Test API key is correct
3. Check network connectivity

---

## 📝 **Notes**

- The container will automatically connect to your existing `n8ndb` database
- All Gilgamesh data will be stored in the `public.simple_videos` table
- Your existing n8n data will not be affected
- The service will use your existing Qdrant instance for vector storage 