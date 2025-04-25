# Documentation Scripts

This directory contains scripts for managing the AutoMCP documentation.

## Prerequisites

Before using these scripts, install the required packages:

```bash
pip install mkdocs mkdocs-material "mkdocstrings[python]" mkdocs-autorefs
```

Note: The quotes around `mkdocstrings[python]` are important in some shells to prevent square bracket interpretation.

## Available Scripts

### Build and Serve Documentation

Builds and serves the documentation locally at http://127.0.0.1:8000:

```bash
./scripts/docs/build_and_serve.sh
```

This script:
- Ensures required packages are installed
- Creates any missing directories
- Builds and serves the documentation using MkDocs

Press Ctrl+C to stop the local server.

### Initialize Documentation

This script is for initial setup or resetting documentation structure:

```bash
./scripts/docs/init_docs.sh
```

Use this only when:
- Setting up documentation for the first time
- Resetting the documentation structure
- Recreating base templates

## GitHub Actions Integration

Documentation is automatically deployed to GitHub Pages via the workflow in `.github/workflows/docs.yml`. The workflow:

1. Triggers on pushes to the main branch that affect documentation files
2. Sets up Python and installs dependencies
3. Deploys to GitHub Pages using MkDocs

## Customization

Edit `mkdocs.yml` in the project root to customize:
- Site theme and appearance
- Navigation structure
- Plugins and extensions
- Repository information 