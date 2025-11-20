# Use the Debian Bullseye release for better dependency stability
FROM python:3.11-slim-bullseye

WORKDIR /app

# 1. System Dependency Installation
# Install build tools and other necessary system libraries.
# Keep build tools for the duration of Python package installation.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libgfortran5

# 2. Python Dependency Installation
# Copy requirements first to leverage Docker layer caching.
COPY requirements.txt ./
RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# 3. Cleanup: Now remove build tools and clean apt caches to reduce final image size.
RUN apt-get purge -y --auto-remove build-essential gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy application code after dependencies are installed
COPY . /app

# Use unbuffered output for logs
ENV PYTHONUNBUFFERED=1

# Expose the application port
EXPOSE 8000

# Start the FastAPI server with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]