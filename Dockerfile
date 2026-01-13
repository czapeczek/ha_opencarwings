# Minimal image to run the test suite for this repo
FROM python:3.11-slim

WORKDIR /app

# Install essential build tools (kept minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project
COPY . /app

# Keep Python output unbuffered for test logs
ENV PYTHONUNBUFFERED=1

# Upgrade pip and install test runner
RUN pip install --upgrade pip setuptools
RUN pip install pytest

# Default command runs the full test suite
CMD ["pytest", "tests", "-v"]
