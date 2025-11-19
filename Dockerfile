FROM python:3.11-slim

WORKDIR /app

# Keep image lean: install build deps only for wheel compilation, then remove them
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install dependencies from requirements. Copy only requirements
# first so layers cache when sources change but deps don't.
COPY requirements.txt ./
RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Remove build tools to reduce final image size
RUN apt-get purge -y --auto-remove build-essential gcc || true && rm -rf /var/lib/apt/lists/*

# Copy application code after dependencies are installed
COPY . /app

# Use unbuffered output for logs and set a small PYTHONPATH
ENV PYTHONUNBUFFERED=1

# Expose the application port
EXPOSE 8000

# Start the FastAPI server with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
