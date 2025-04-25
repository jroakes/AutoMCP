#!/bin/bash
# Script to build and serve the AutoMCP documentation

# Exit on error
set -e

# Navigate to project root
cd "$(dirname "$0")/../.."
PROJECT_ROOT=$(pwd)

echo "=== Building and Serving AutoMCP Documentation ==="

# Ensure required packages are installed
pip install -q mkdocs mkdocs-material "mkdocstrings[python]" mkdocs-autorefs

# Create any missing directories
mkdir -p docs/api docs/getting-started docs/openapi docs/mcp docs/components docs/usage docs/development

# Build and serve the documentation
echo "Starting documentation server at http://127.0.0.1:8000"
echo "Press Ctrl+C to stop the server"
mkdocs serve 