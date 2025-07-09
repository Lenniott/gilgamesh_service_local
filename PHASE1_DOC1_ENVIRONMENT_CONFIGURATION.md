# Environment & Configuration Documentation

## Overview
This document covers all environment variables, configuration files, and settings for the Gilgamesh Media Processing Service. The system uses a multi-environment approach with Docker containerization and supports both development and production deployments.

## Current Implementation
The system uses environment variables for configuration management with support for:
- Database connections (PostgreSQL)
- AI provider configuration (OpenAI/Gemini)
- Vector database setup (Qdrant)
- Rate limiting and performance tuning
- Docker container orchestration

## Architecture
- **Configuration Management**: Environment variables with .env file support
- **Multi-Environment**: Development, production, and Portainer-specific configurations
- **Docker Integration**: Containerized deployment with volume mounts
- **Health Monitoring**: Built-in health checks and monitoring endpoints
- **Security**: Non-root user execution and secure credential management

## Configuration

### Environment Variables

#### Database Configuration
```
PG_DBNAME=gilgamesh_media          # PostgreSQL database name (public schema)
PG_USER=postgres                    # PostgreSQL username
PG_PASSWORD=your_secure_password    # PostgreSQL password
PG_HOST=localhost                   # PostgreSQL host (default: localhost)
PG_PORT=5432                        # PostgreSQL port (default: 5432)
```

#### AI Provider Configuration
```
AI_PROVIDER=gemini                  # AI provider: "openai" or "gemini" (default: gemini for cost)
OPENAI_API_KEY=sk-your-key-here    # OpenAI API key for GPT-4 Vision (fallback)
GEMINI_API_KEY=your-gemini-key     # Google Gemini API key for Gemini 2.0 Flash (primary)
GEMINI_BATCH_SIZE=10               # Number of frames to batch for scene analysis (cost optimization)
```

#### Vector Database Configuration
```
QDRANT_URL=http://localhost:6333    # Qdrant vector database URL
QDRANT_API_KEY=your-qdrant-key     # Qdrant API key for authentication
```

#### Performance & Rate Limiting
```
MAX_CONCURRENT_REQUESTS=10          # Maximum concurrent API requests (default: 10)
REQUEST_TIMEOUT_SECONDS=30          # Request timeout in seconds (default: 30)
ENVIRONMENT=production              # Environment: "development" or "production"
LOG_LEVEL=INFO                      # Logging level: DEBUG, INFO, WARNING, ERROR
```

### Configuration Files

#### 1. Environment Files
- **`env.example`**: Template for development environment
- **`portainer.env`**: Production configuration for Portainer deployment
- **`env.portainer.example`**: Example Portainer environment template

#### 2. Docker Configuration
- **`docker-compose.yml`**: Main Docker Compose configuration
- **`docker-compose.portainer.yml`**: Portainer-specific Docker Compose
- **`Dockerfile`**: Multi-stage container build configuration

#### 3. Database Setup
- **`create_simple_videos_table.sql`**: Main database schema
- **`create_video_clips_table.sql`**: Video clips storage schema
- **`add_vectorization_tracking.sql`**: Vectorization tracking schema

### Environment-Specific Configurations

#### Development Environment
```bash
# Copy template and configure
cp env.example .env

# Required variables for development
PG_DBNAME=gilgamesh_media
PG_USER=postgres
PG_PASSWORD=your_secure_password
PG_HOST=localhost
PG_PORT=5432
AI_PROVIDER=openai
OPENAI_API_KEY=sk-your-openai-api-key-here
GEMINI_API_KEY=your-gemini-api-key-here
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your-qdrant-api-key-here
```

#### Production Environment (Portainer/Umbrel)
```bash
# Production configuration for Portainer UI on Umbrel
PG_DBNAME=n8ndb
PG_USER=n8n
PG_PASSWORD=ohgodiconfessimamess
PG_HOST=postgres
PG_PORT=5432
AI_PROVIDER=gemini
OPENAI_API_KEY=your-openai-api-key-here
GEMINI_API_KEY=your-gemini-api-key-here
GEMINI_BATCH_SIZE=10
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=findme-gagme-putme-inabunnyranch
ENVIRONMENT=production
LOG_LEVEL=INFO

# Custom volumes for Umbrel/Portainer deployment
# - gilgamesh_storage: /storage/clips (video clips)
# - gilgamesh_cache: /app/cache (temporary files)
# - gilgamesh_temp: /app/temp (processing artifacts)
```

## Dependencies

### External Dependencies
- **PostgreSQL 15**: Database server with asyncpg and psycopg2 drivers (public schema)
- **Qdrant**: Vector database for AI embeddings and similarity search
- **Google Gemini API**: Primary AI provider for scene analysis (cost-effective)
- **OpenAI API**: Fallback AI provider when Gemini credits exhausted. 
- **FFmpeg**: Video processing and manipulation
- **OpenCV**: Computer vision and video analysis
- **yt-dlp**: YouTube and social media video downloading
- **instaloader**: Instagram content downloading

### Internal Dependencies
- **FastAPI**: Web framework for API endpoints
- **uvicorn**: ASGI server for running the application
- **asyncpg**: Async PostgreSQL driver
- **qdrant-client**: Qdrant vector database client
- **openai**: OpenAI API client library
- **google-generativeai**: Google Gemini API client
- **moviepy**: Video editing and processing
- **openai-whisper**: Audio transcription

## Implementation Details

### Database Connection Management
```python
# Connection parameters from environment
PG_PARAMS = {
    "dbname": os.getenv("PG_DBNAME"),
    "user": os.getenv("PG_USER"), 
    "password": os.getenv("PG_PASSWORD"),
    "host": os.getenv("PG_HOST"),
    "port": os.getenv("PG_PORT"),
}

# Async connection string
connection_string = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
```

### AI Provider Selection
```python
# Provider configuration (default to gemini for cost efficiency)
AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini")
GEMINI_BATCH_SIZE = int(os.getenv("GEMINI_BATCH_SIZE", 10))

# Provider-specific clients
if AI_PROVIDER == "gemini":
    client = genai.GenerativeModel('gemini-2.0-flash-exp')
    # Batch frames for cost optimization
    batch_size = GEMINI_BATCH_SIZE
elif AI_PROVIDER == "openai":
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    # OpenAI for fallback when Gemini credits exhausted
```

### Rate Limiting Configuration
```python
# Rate limiting parameters
MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", 10))
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", 30))

# Circuit breaker settings
failure_threshold = 5
success_threshold = 3
timeout_seconds = 300
```

## Performance & Optimization

### Current Performance Characteristics
- **Concurrent Requests**: 10 simultaneous API requests
- **Request Timeout**: 30 seconds per request
- **Database Pool**: 1-10 connections with 60-second timeout
- **Circuit Breaker**: 5 failures trigger circuit breaker for 5 minutes
- **Rate Limiting**: Exponential backoff with jitter for API calls

### Optimization Opportunities
- **Connection Pooling**: Database connection pooling for better performance
- **Caching**: Redis integration for caching expensive operations
- **Async Processing**: Background task processing for long-running operations
- **CDN Integration**: Static file serving and video delivery optimization

## Error Handling

### Common Error Scenarios
1. **Database Connection Failures**: Automatic retry with exponential backoff
2. **AI API Rate Limits**: Circuit breaker pattern with provider switching
3. **Video Processing Failures**: Graceful degradation with error reporting
4. **Memory Issues**: Resource monitoring and cleanup procedures

### Error Recovery Procedures
- **Circuit Breaker**: Automatic service recovery testing
- **Provider Fallback**: Switch from Gemini to OpenAI when credits exhausted
- **Batch Processing**: Frame batching for cost optimization
- **Database Reconnection**: Automatic connection pool recovery
- **Health Checks**: Regular endpoint monitoring and alerting

## Security Considerations

### Authentication and Authorization
- **API Key Management**: Secure storage of OpenAI and Gemini API keys
- **Database Credentials**: Encrypted password storage and rotation
- **Container Security**: Non-root user execution in Docker containers
- **Network Security**: Internal Docker network isolation

### Data Protection
- **Environment Variables**: Secure credential management
- **Volume Mounts**: Isolated storage for temporary files
- **Input Validation**: URL validation and sanitization
- **Error Logging**: Secure error reporting without sensitive data exposure

## Testing

### Configuration Testing
```python
# Test database connections
async def test_all_connections():
    results = await db_connections.connect_all()
    return results

# Test AI provider connections
async def test_ai_connections():
    openai_status = await test_openai_connection()
    gemini_status = await test_gemini_connection()
    return {"openai": openai_status, "gemini": gemini_status}
```

### Environment Validation
- **Required Variables**: Validation of all required environment variables
- **Connection Testing**: Database and AI provider connectivity tests
- **Health Checks**: Regular endpoint monitoring and status reporting

## Deployment

### Docker Deployment
```bash
# Development deployment
docker-compose up -d

# Production deployment (Portainer UI on Umbrel)
docker-compose -f docker-compose.portainer.yml up -d

# Custom volumes for Umbrel deployment
# - gilgamesh_storage: Persistent video clip storage
# - gilgamesh_cache: Temporary processing cache
# - gilgamesh_temp: Processing artifacts
```

### Environment Setup
1. **Copy Environment Template**: `cp env.example .env`
2. **Configure Variables**: Update with actual API keys and credentials
3. **Start Services**: `docker-compose up -d`
4. **Verify Health**: Check `/health` endpoint

### Health Checks
- **Application Health**: `GET /health` - Service status and dependencies
- **Rate Limits**: `GET /rate-limits` - Current usage statistics
- **Database Health**: PostgreSQL connection status
- **AI Provider Health**: OpenAI/Gemini API connectivity

## Troubleshooting

### Common Issues
1. **Database Connection Failures**
   - Verify PostgreSQL is running
   - Check credentials in environment variables
   - Ensure network connectivity

2. **AI API Errors**
   - Validate API keys are correct
   - Check rate limits and quotas
   - Verify provider selection

3. **Video Processing Failures**
   - Ensure FFmpeg is installed
   - Check available disk space
   - Verify video URL accessibility

### Debugging
- **Log Analysis**: Check application logs for error details
- **Health Endpoints**: Use `/health` and `/rate-limits` for status
- **Docker Logs**: `docker-compose logs gilgamesh-api`
- **Database Queries**: Direct PostgreSQL connection for data verification

## Future Improvements

### Planned Enhancements
1. **Redis Integration**: Caching layer for improved performance
2. **Monitoring**: Prometheus metrics and Grafana dashboards
3. **Secrets Management**: Kubernetes secrets or HashiCorp Vault
4. **Multi-Region**: Geographic distribution for better latency

### Technical Debt
- **Configuration Validation**: Schema validation for environment variables
- **Error Handling**: More granular error types and recovery strategies
- **Testing**: Comprehensive integration tests for all configurations
- **Documentation**: Automated configuration documentation generation

## Related Documentation
- **Database Architecture**: See Phase 1, Document 3
- **Vector Store Setup**: See Phase 1, Document 4
- **API Design**: See Phase 2, Document 8
- **Docker Configuration**: See Phase 4, Document 10

## Notes
- **Environment Isolation**: Each environment has separate configuration files
- **Security First**: All sensitive data stored in environment variables
- **Docker Best Practices**: Multi-stage builds and non-root execution
- **Health Monitoring**: Comprehensive health checks for all dependencies
- **Migration Considerations**: Environment variables must be updated during migrations
- **Database Schema**: Uses public schema in PostgreSQL
- **Cost Optimization**: Gemini as primary provider with OpenAI fallback
- **Frame Batching**: Configurable batch size for scene analysis cost reduction
- **Umbrel Integration**: Custom volumes for Portainer UI deployment 