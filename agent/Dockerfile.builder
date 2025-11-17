# Multi-stage Dockerfile for building Form Discoverer Agent installers
# This builds the agent in Docker (no GUI needed with web-based UI!)

FROM python:3.12-slim

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    binutils \
    upx-ucl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy requirements first (for caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir pyinstaller

# Copy agent source code
COPY . .

# Build the executable
RUN pyinstaller FormDiscovererAgent.spec --clean

# Create installer
RUN mkdir -p dist/installers && \
    cd dist && \
    tar -czf installers/FormDiscovererAgent-2.0.0-Linux.tar.gz FormDiscovererAgent

# Output directory will be mounted as volume
VOLUME ["/build/dist/installers"]

CMD ["echo", "Build complete! Installers in dist/installers/"]
