# === Stage 1: Build stage with tools ===
FROM python:3.11-slim AS builder

# Install system build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set workdir
WORKDIR /app

# Copy dependencies and install to a temporary directory
COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

# === Stage 2: Final slim image ===
FROM python:3.11-slim

# Set envs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set workdir
WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /install /usr/local

# Copy app code
COPY . .

# Create necessary directories
RUN mkdir -p curated_excels outputs frontend static_data utils

# Expose port
EXPOSE 5000

# Run the app with Uvicorn with extended timeout for long-running requests
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "2", "--timeout-keep-alive", "600"]

