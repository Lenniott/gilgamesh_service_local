FROM python:3.11-slim

# System dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    tesseract-ocr \
    build-essential \
    gcc \
    libleptonica-dev \
    libtesseract-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only app code into the container
COPY app ./app

# Ensure Python can see the app package
ENV PYTHONPATH=/app

# Start FastAPI with correct module path
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8500"]
