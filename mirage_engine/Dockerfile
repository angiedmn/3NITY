FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (whois CLI needed by python-whois library)
RUN apt-get update && apt-get install -y --no-install-recommends \
    whois \
    && rm -rf /var/lib/apt/lists/*

# Install python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose FastAPI port
EXPOSE 8000