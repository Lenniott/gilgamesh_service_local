# Gilgamesh Media Processing Service
# Updated for Python 3.11+ with all dependencies and optimizations

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install system dependencies required for video processing and AI
RUN apt-get update && apt-get install -y \
    # FFmpeg for video processing
    ffmpeg \
    # OpenCV dependencies
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-dev \
    libgomp1 \
    # Audio processing dependencies
    libasound2-dev \
    libportaudio2 \
    libportaudiocpp0 \
    portaudio19-dev \
    # Build dependencies for some Python packages
    build-essential \
    # curl for health checks
    curl \
    # Git for some packages
    git \
    # Clean up to reduce image size
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app

# Set the working directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy database setup files
COPY create_simple_videos_table.sql .
COPY setup_simple_db.py .

# Copy the application code
COPY app/ ./app/

# Create necessary directories and set permissions
RUN mkdir -p /app/temp /app/cache && \
    chown -R app:app /app

# Switch to non-root user
USER app

# Health check (using wget since curl might have permission issues)
HEALTHCHECK --interval=30s --timeout=30s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8500/health || exit 1

# Expose the port
EXPOSE 8500

# Run the application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8500", "--workers", "1"]
