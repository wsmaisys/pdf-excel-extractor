FROM python:3.11-slim

WORKDIR /app

# 1. Install necessary system packages for dependencies (e.g., Pandas/NumPy)
# We use apt-get install here for *runtime* libraries like libgfortran-dev.
# We keep these minimal packages in the final image, as they are *required* for the installed wheels to run.
# I'm adding 'libgfortran5' as a common necessity for scientific packages.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgfortran5 \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Python dependencies
# Copy requirements first to leverage Docker layer caching.
COPY requirements.txt ./
RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# 3. Copy application code and set environment variables
# Note: I removed the complex build-essential steps as python:3.11-slim often uses pre-built wheels
# which should be used instead of compiling everything from source on a clean install.
COPY . /app

# Use unbuffered output for logs
ENV PYTHONUNBUFFERED=1

# Expose the application port
EXPOSE 8000

# Start the FastAPI server with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]