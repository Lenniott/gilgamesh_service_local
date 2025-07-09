# Project Structure & Dependencies Documentation

## Overview
This document covers the complete project structure, folder organization, dependencies, and package management for the Gilgamesh Media Processing Service. The project follows a modular architecture with clear separation of concerns and comprehensive dependency management.

## Current Implementation
The project uses a structured approach with:
- **Modular Architecture**: Clear separation between core components
- **Dependency Management**: Comprehensive requirements.txt with version pinning
- **Containerization**: Multi-stage Docker builds with security best practices
- **Testing Framework**: Pytest with coverage and async support
- **Development Tools**: Virtual environments and IDE configuration

## Architecture

### Project Structure Overview
```
gilgamesh_service_local/
├── app/                          # Core application code
│   ├── __init__.py              # Python package initialization
│   ├── api/                     # API layer
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI application entry point
│   │   ├── endpoints.py         # API endpoint definitions
│   │   └── middleware.py        # Rate limiting and CORS
│   ├── core/                    # Core business logic
│   │   ├── __init__.py
│   │   ├── processor.py         # Main processing pipeline
│   │   ├── scene_detection.py   # Video scene detection
│   │   ├── ai_analysis.py       # AI-powered scene analysis
│   │   └── video_processing.py  # Video processing utilities
│   ├── database/                # Database layer
│   │   ├── __init__.py
│   │   ├── connections.py       # Database connection management
│   │   ├── operations.py        # PostgreSQL operations
│   │   ├── migrations.py        # Database migration utilities
│   │   └── vectorization.py     # Vector embedding generation
│   ├── services/                # External services
│   │   ├── __init__.py
│   │   ├── ai_rate_limiter.py   # Rate limiting and circuit breaker
│   │   ├── transcription.py     # Audio transcription
│   │   ├── downloaders.py       # Video download utilities
│   │   └── storage.py           # File-based clip storage
│   ├── utils/                   # Utilities and helpers
│   │   ├── __init__.py
│   │   ├── video_utils.py       # Video processing utilities
│   │   ├── clip_operations.py   # Clip file operations
│   │   ├── cleanup.py           # Resource cleanup
│   │   └── helpers.py           # Common utilities
│   ├── temp/                    # Temporary processing files
│   └── cache/                   # Processing cache
├── storage/                     # Persistent storage
│   ├── clips/                   # Video clip files
│   └── temp/                    # Temporary storage
├── documentation/               # Project documentation
│   ├── iterations/              # Context documents for iterations
│   ├── guidance/                # Project guidance and rules
│   ├── architecture/            # Architecture diagrams and docs
│   └── changelog/              # Version history and changes
├── tests/                       # Test files
│   ├── unit/                    # Unit tests
│   ├── integration/             # Integration tests
│   └── fixtures/                # Test data and fixtures
├── examples/                    # Example configurations
├── .venv/                       # Virtual environment
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Container build configuration
├── docker-compose.yml           # Development orchestration
├── docker-compose.portainer.yml # Production orchestration
├── pytest.ini                  # Testing configuration
├── .gitignore                  # Version control exclusions
├── CHANGELOG.md                # Project changelog
├── AI_PROJECT_RULES.md         # AI project rules and guidelines
├── PROJECT_VISION.md           # Project vision and goals
└── README.md                   # Project overview
```

## Configuration

### Core Dependencies

#### Web Framework & Server
```python
# Core web framework
fastapi==0.104.1              # Modern web framework for APIs
uvicorn[standard]==0.24.0     # ASGI server with standard extras
python-multipart==0.0.6       # File upload handling
```

#### Video Processing & Media Handling
```python
# Video processing and media handling
yt-dlp>=2023.11.16            # YouTube and social media downloading
instaloader>=4.10.3           # Instagram content downloading
moviepy>=1.0.3                # Video editing and processing
opencv-python-headless==4.8.1.78  # Computer vision (headless)
```

#### Audio Processing
```python
# Audio processing
openai-whisper>=20231117      # Audio transcription
```

#### AI and Machine Learning
```python
# AI and ML
openai>=1.0.0                 # OpenAI API client
google-generativeai>=0.3.0    # Google Gemini API client
```

#### Database Connections
```python
# Database connections
asyncpg>=0.29.0               # Async PostgreSQL driver
psycopg2-binary>=2.9.0        # PostgreSQL adapter
qdrant-client>=1.7.0          # Vector database client
```

#### Data Processing
```python
# Data processing
numpy==1.26.2                 # Numerical computing
pyyaml>=6.0.1                 # YAML configuration parsing
requests>=2.31.0              # HTTP client library
beautifulsoup4>=4.12.2        # HTML parsing
python-dotenv>=1.0.0          # Environment variable management
```

#### File Handling
```python
# File handling
aiofiles>=23.2.1              # Async file operations
```

#### Testing Framework
```python
# Testing (optional for production)
pytest>=8.0.0                 # Testing framework
pytest-asyncio>=0.23.5        # Async test support
pytest-cov>=4.1.0             # Coverage reporting
pytest-mock>=3.12.0           # Mocking utilities
httpx>=0.26.0                 # HTTP client for testing
```

#### Security and Performance
```python
# Security and performance
cryptography>=41.0.0          # Cryptographic utilities
```

### System Dependencies

#### Docker Container Dependencies
```dockerfile
# FFmpeg for video processing (handles all video/audio operations)
ffmpeg

# Minimal OpenCV dependencies (only for simple frame comparison)
libgl1-mesa-glx
libglib2.0-0

# Build dependencies
build-essential
curl
git
```

## Dependencies

### External Dependencies
- **Python 3.11+**: Core runtime environment
- **PostgreSQL 15**: Primary database for metadata storage (public schema)
- **Qdrant**: Vector database for AI embeddings
- **FFmpeg**: Video processing and manipulation (handles all video/audio operations)
- **OpenCV**: Simple image processing for frame comparison only
- **Google Gemini API**: Primary AI provider for scene analysis (cost-effective)
- **OpenAI API**: Fallback AI provider when Gemini credits exhausted

### Internal Dependencies
- **FastAPI**: Web framework for API endpoints
- **Uvicorn**: ASGI server for running the application
- **AsyncPG**: Async PostgreSQL driver for database operations
- **Qdrant Client**: Vector database client for embeddings
- **MoviePy**: Video editing and processing library
- **OpenAI Whisper**: Audio transcription
- **yt-dlp**: YouTube and social media video downloading
- **Instaloader**: Instagram content downloading

### Development Dependencies
- **Pytest**: Testing framework with async support
- **Pytest-cov**: Coverage reporting
- **Pytest-asyncio**: Async test support
- **Pytest-mock**: Mocking utilities
- **HTTPX**: HTTP client for testing

## Implementation Details

### Package Management
```bash
# Virtual environment setup
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Development dependencies
pip install pytest pytest-asyncio pytest-cov pytest-mock httpx
```

### Docker Build Process
```dockerfile
# Multi-stage build for optimization
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libgl1-mesa-glx \
    # ... other dependencies

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create directories and set permissions
RUN mkdir -p /app/temp /app/cache && \
    chown -R app:app /app
```

### Testing Configuration
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
addopts = -v --cov=app --cov-report=term-missing
markers =
    asyncio: mark a test as an async test
    slow: mark a test as slow (may take longer to run)
    integration: mark a test as an integration test
    unit: mark a test as a unit test
```

## Performance & Optimization

### Current Performance Characteristics
- **Python 3.11**: Latest stable version with performance improvements
- **Async Operations**: Full async/await support for I/O operations
- **Connection Pooling**: Database connection pooling for efficiency
- **Memory Management**: Proper cleanup of video processing artifacts
- **Caching**: Temporary file caching for repeated operations

### Optimization Opportunities
- **Dependency Optimization**: Remove unused dependencies
- **Image Size**: Multi-stage Docker builds for smaller images
- **Startup Time**: Lazy loading of heavy dependencies
- **Memory Usage**: Streaming video processing for large files
- **Parallel Processing**: Concurrent scene analysis

## Error Handling

### Common Dependency Issues
1. **System Dependencies**: Missing FFmpeg or OpenCV libraries
2. **Python Version**: Incompatible Python version (requires 3.11+)
3. **API Dependencies**: Missing API keys or rate limits
4. **Database Connections**: PostgreSQL or Qdrant connectivity issues
5. **File Permissions**: Storage directory access problems

### Error Recovery Procedures
- **Dependency Installation**: Automatic retry with fallback versions
- **System Dependencies**: Docker container includes all required libraries
- **API Failures**: Circuit breaker pattern with provider switching
- **Database Issues**: Connection pool recovery and reconnection
- **File System**: Automatic directory creation and permission setting

## Security Considerations

### Dependency Security
- **Version Pinning**: Specific versions to prevent supply chain attacks
- **Security Updates**: Regular dependency updates for security patches
- **Container Security**: Non-root user execution in Docker
- **API Key Management**: Secure environment variable storage
- **Input Validation**: Sanitization of all external inputs

### Best Practices
- **Virtual Environments**: Isolated Python environments
- **Dependency Scanning**: Regular security audits of dependencies
- **Minimal Dependencies**: Only essential packages included
- **Container Hardening**: Security-focused Docker configuration
- **Secret Management**: Environment-based credential storage

## Testing

### Unit Tests
```python
# Example test structure
tests/
├── test_api/
│   ├── test_rate_limiting.py
│   └── test_endpoints.py
├── test_processing/
│   ├── test_video_processing.py
│   └── test_scene_detection.py
└── test_integration/
    ├── test_database.py
    └── test_ai_services.py
```

### Integration Tests
- **Database Integration**: PostgreSQL and Qdrant connectivity
- **API Integration**: OpenAI and Gemini API testing
- **File System**: Storage and cache operations
- **Video Processing**: End-to-end video processing pipeline

### Performance Tests
- **Load Testing**: Concurrent request handling
- **Memory Usage**: Video processing memory consumption
- **API Limits**: Rate limiting and circuit breaker testing
- **Storage Performance**: File I/O and database operations

## Deployment

### Development Environment
```bash
# Local development setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload

# Or using Docker for local testing
docker-compose up -d
```

### Production Environment (Portainer Workflow)
```bash
# 1. Local Development & Testing
# - Develop and test locally with docker-compose
# - Ensure all functionality works as expected
docker-compose up -d

# 2. Code Deployment
# - Push changes to main branch
git push origin main

# 3. Portainer Image Creation
# - In Portainer UI: Create image from main branch
# - Build image with latest code changes

# 4. Container Deployment
# - Create container from the built image
# - Configure via Portainer UI:
#   - Environment Variables: Link to existing .env or configure in UI
#   - Network: Connect to existing PostgreSQL/Qdrant network
#   - Custom Volumes: 
#     - gilgamesh_storage: /storage/clips (persistent)
#     - gilgamesh_cache: /app/cache (temporary)
#     - gilgamesh_temp: /app/temp (processing)
#   - Port Mapping: 8500:8500 (or custom port)
```

### Health Checks
- **Dependency Health**: Verify all required packages are available
- **System Health**: Check system dependencies (FFmpeg, etc.)
- **API Health**: Test external API connectivity
- **Database Health**: Verify database connections

## Troubleshooting

### Common Issues
1. **Missing Dependencies**
   - Verify Python version (3.11+)
   - Install system dependencies (FFmpeg, OpenCV)
   - Check virtual environment activation

2. **Import Errors**
   - Verify package installation
   - Check Python path configuration
   - Validate import statements

3. **System Dependencies**
   - Ensure FFmpeg is installed
   - Verify OpenCV dependencies
   - Check audio processing libraries

4. **API Dependencies**
   - Validate API keys
   - Check rate limits
   - Verify network connectivity

### Debugging
- **Dependency Verification**: `pip list` to check installed packages
- **System Dependencies**: `ffmpeg -version` to verify installation
- **Import Testing**: `python -c "import package"` to test imports
- **Docker Logs**: `docker-compose logs` for container issues

## Future Improvements

### Planned Enhancements
1. **Dependency Management**: Poetry or Pipenv for better dependency management
2. **Security Scanning**: Automated dependency vulnerability scanning
3. **Performance Monitoring**: Dependency performance impact tracking
4. **Container Optimization**: Smaller Docker images with multi-stage builds

### Technical Debt
- **Version Updates**: Regular dependency updates for security
- **Unused Dependencies**: Remove unused packages
- **Documentation**: Better dependency documentation
- **Testing**: More comprehensive dependency testing

## Related Documentation
- **Environment Configuration**: See Phase 1, Document 1
- **Database Architecture**: See Phase 1, Document 3
- **API Design**: See Phase 2, Document 8
- **Docker Configuration**: See Phase 4, Document 10

## Notes
- **Python Version**: Requires Python 3.11+ for optimal performance
- **System Dependencies**: FFmpeg and OpenCV are critical for video processing
- **API Dependencies**: OpenAI and Gemini APIs require valid keys
- **Container Strategy**: Docker includes all system dependencies
- **Testing Strategy**: Comprehensive test coverage for all dependencies
- **Security Focus**: Regular dependency updates and security scanning
- **Deployment Workflow**: Local testing → Git push → Portainer image → Container deployment
- **Portainer Integration**: UI-based configuration for networks, volumes, and environment variables 