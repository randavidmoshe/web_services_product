#!/bin/bash
# Build agent installer using Docker
# This works now because web UI doesn't need display server!

set -e

echo "=========================================="
echo "Building Form Discoverer Agent in Docker"
echo "=========================================="

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf dist/installers
mkdir -p dist/installers

# Build Docker image and run
echo ""
echo "Building Docker image..."
docker-compose -f docker-compose.build.yml build

echo ""
echo "Running build in container..."
docker-compose -f docker-compose.build.yml up

echo ""
echo "=========================================="
echo "Build complete!"
echo "=========================================="
ls -lh dist/installers/

# Clean up
docker-compose -f docker-compose.build.yml down

echo ""
echo "Installer location: dist/installers/"
