import os
import uuid
import json
import asyncio
from typing import Dict, List, Optional, Union, Any
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
import asyncpg
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import openai
from openai import AsyncOpenAI
import logging

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# --- POSTGRESQL CONNECTION ---
PG_PARAMS = {
    "dbname": os.getenv("PG_DBNAME"),
    "user": os.getenv("PG_USER"), 
    "password": os.getenv("PG_PASSWORD"),
    "host": os.getenv("PG_HOST"),
    "port": os.getenv("PG_PORT"),
}

# --- QDRANT CONNECTION ---
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

# --- OPENAI CONNECTION ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class DatabaseConnections:
    """Unified database connections manager for PostgreSQL, Qdrant, and OpenAI."""
    
    def __init__(self):
        self.pg_pool = None
        self.qdrant_client = None
        self.openai_client = None
        self._pg_connection_string = self._build_pg_connection_string()
    
    def _build_pg_connection_string(self) -> str:
        """Build PostgreSQL connection string for asyncpg."""
        return f"postgresql://{PG_PARAMS['user']}:{PG_PARAMS['password']}@{PG_PARAMS['host']}:{PG_PARAMS['port']}/{PG_PARAMS['dbname']}"
    
    async def connect_all(self) -> Dict[str, bool]:
        """Connect to all databases and return status."""
        results = {}
        
        # Connect to PostgreSQL
        try:
            self.pg_pool = await asyncpg.create_pool(
                self._pg_connection_string,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            results['postgresql'] = True
            logger.info("✅ PostgreSQL connection established")
        except Exception as e:
            logger.error(f"❌ PostgreSQL connection failed: {e}")
            results['postgresql'] = False
        
        # Connect to Qdrant
        try:
            if QDRANT_URL and QDRANT_API_KEY:
                self.qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
                # Test connection
                collections = self.qdrant_client.get_collections()
                results['qdrant'] = True
                logger.info("✅ Qdrant connection established")
            else:
                logger.warning("⚠️ Qdrant credentials missing - vectorization disabled")
                results['qdrant'] = False
        except Exception as e:
            logger.error(f"❌ Qdrant connection failed: {e}")
            results['qdrant'] = False
        
        # Connect to OpenAI
        try:
            if OPENAI_API_KEY:
                self.openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
                # Test with a simple embedding
                response = await self.openai_client.embeddings.create(
                    input="test",
                    model="text-embedding-3-small"
                )
                results['openai'] = True
                logger.info("✅ OpenAI connection established")
            else:
                logger.warning("⚠️ OpenAI API key missing - embeddings disabled")
                results['openai'] = False
        except Exception as e:
            logger.error(f"❌ OpenAI connection failed: {e}")
            results['openai'] = False
        
        return results
    
    async def close_all(self):
        """Close all database connections."""
        if self.pg_pool:
            await self.pg_pool.close()
            logger.info("PostgreSQL pool closed")
        
        if self.qdrant_client:
            # Qdrant client doesn't need explicit closing
            self.qdrant_client = None
            logger.info("Qdrant client closed")
    
    # --- POSTGRESQL METHODS ---
    
    def connect_postgres_sync(self):
        """Connect to PostgreSQL database synchronously (for compatibility)."""
        conn = psycopg2.connect(**PG_PARAMS)
        return conn

    def get_pg_connection_context(self):
        """Get PostgreSQL connection context manager from pool."""
        if not self.pg_pool:
            raise RuntimeError("PostgreSQL pool not initialized. Call connect_all() first.")
        return self.pg_pool.acquire()
    
    async def get_pg_connection(self):
        """Get PostgreSQL connection from pool (for non-context manager usage)."""
        if not self.pg_pool:
            await self.connect_all()
        return await self.pg_pool.acquire()
    
    # --- QDRANT METHODS ---
    
    def get_qdrant_client(self) -> Optional[QdrantClient]:
        """Get Qdrant client."""
        return self.qdrant_client
    
    async def ensure_collection_exists(self, collection_name: str, vector_size: int = 1536):
        """Ensure Qdrant collection exists with proper configuration."""
        if not self.qdrant_client:
            logger.warning("Qdrant client not available")
            return False
        
        try:
            collections = self.qdrant_client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if collection_name not in collection_names:
                self.qdrant_client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=vector_size,  # OpenAI text-embedding-3-small dimensions
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"✅ Created Qdrant collection: {collection_name}")
            else:
                logger.info(f"📋 Qdrant collection already exists: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to ensure collection {collection_name}: {e}")
            return False
    
    # --- OPENAI METHODS ---
    
    def get_openai_client(self) -> Optional[AsyncOpenAI]:
        """Get OpenAI client."""
        return self.openai_client
    
    async def generate_embedding(self, text: str, model: str = "text-embedding-3-small") -> Optional[List[float]]:
        """Generate embedding for text using OpenAI."""
        if not self.openai_client:
            logger.warning("OpenAI client not available")
            return None
        
        try:
            response = await self.openai_client.embeddings.create(
                input=text.replace("\n", " "),  # Clean newlines
                model=model
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"❌ Failed to generate embedding: {e}")
            return None
    
    # --- VECTOR STORAGE METHODS ---
    
    async def store_vector(self, collection_name: str, vector_id: str, 
                          embedding: List[float], metadata: Dict[str, Any]) -> bool:
        """Store vector in Qdrant with metadata."""
        if not self.qdrant_client:
            logger.warning("Qdrant client not available")
            return False
        
        try:
            point = PointStruct(
                id=vector_id,
                vector=embedding,
                payload=metadata
            )
            
            self.qdrant_client.upsert(
                collection_name=collection_name,
                points=[point]
            )
            logger.debug(f"✅ Stored vector {vector_id} in {collection_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to store vector {vector_id}: {e}")
            return False
    
    # --- TEST METHODS ---
    
    async def test_all_connections(self) -> Dict[str, bool]:
        """Test all database connections."""
        results = {}
        
        # Test PostgreSQL
        try:
            async with self.get_pg_connection_context() as conn:
                await conn.fetchval("SELECT 1")
            results['postgresql'] = True
        except Exception as e:
            logger.error(f"PostgreSQL test failed: {e}")
            results['postgresql'] = False
        
        # Test Qdrant
        try:
            if self.qdrant_client:
                collections = self.qdrant_client.get_collections()
                results['qdrant'] = True
            else:
                results['qdrant'] = False
        except Exception as e:
            logger.error(f"Qdrant test failed: {e}")
            results['qdrant'] = False
        
        # Test OpenAI
        try:
            if self.openai_client:
                await self.generate_embedding("test")
                results['openai'] = True
            else:
                results['openai'] = False
        except Exception as e:
            logger.error(f"OpenAI test failed: {e}")
            results['openai'] = False
        
        return results

# Global instance
db_connections = DatabaseConnections()

# --- CONVENIENCE FUNCTIONS ---

async def get_db_connections() -> DatabaseConnections:
    """Get the global database connections instance."""
    if not db_connections.pg_pool:
        await db_connections.connect_all()
    return db_connections

def connect_postgres():
    """Connect to PostgreSQL database synchronously (for compatibility)."""
    conn = psycopg2.connect(**PG_PARAMS)
    return conn

def test_postgres_connection():
    """Test PostgreSQL connection synchronously."""
    try:
        conn = psycopg2.connect(**PG_PARAMS)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"PostgreSQL connection failed: {e}")
        return False

def connect_qdrant():
    """Connect to Qdrant vector database."""
    qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    return qdrant

def test_qdrant_connection():
    """Test Qdrant connection."""
    try:
        qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        collections = qdrant.get_collections()
        return True
    except Exception as e:
        print(f"Qdrant connection failed: {e}")
        return False

def test_openai_connection():
    """Test OpenAI API connection."""
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.embeddings.create(
            input="test",
            model="text-embedding-3-small"
        )
        return True
    except Exception as e:
        print(f"OpenAI connection failed: {e}")
        return False

# --- USAGE EXAMPLE ---
if __name__ == "__main__":
    async def main():
        # Test all connections
        print("Testing connections...")
        
        # Initialize connections
        connections = await get_db_connections()
        results = await connections.test_all_connections()
        
        print(f"PostgreSQL: {'✓' if results.get('postgresql') else '✗'}")
        print(f"Qdrant: {'✓' if results.get('qdrant') else '✗'}")
        print(f"OpenAI: {'✓' if results.get('openai') else '✗'}")
        
        if all(results.values()):
            print("All connections successful!")
            
            # Example: Ensure collection exists
            await connections.ensure_collection_exists("gilgamesh_transcripts")
            await connections.ensure_collection_exists("gilgamesh_scenes")
            
        else:
            print("Some connections failed. Check your .env file.")
        
        await connections.close_all()
    
    # Run the test
    asyncio.run(main()) 