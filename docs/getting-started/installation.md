# Installation

AutoMCP can be installed using pip, the Python package manager. Follow the steps below to get started.

## Requirements

- Python 3.9 or higher
- pip (Python package manager)

## Installing from PyPI

The recommended way to install AutoMCP is through pip:

```bash
pip install automcp
```

## Development Installation

For development or the latest features, you can install AutoMCP directly from the GitHub repository:

```bash
git clone https://github.com/jroakes/AutoMCP.git
cd AutoMCP
pip install -e .
```

## Verifying Installation

After installation, verify that AutoMCP is correctly installed by running:

```bash
automcp --help
```

You should see output listing the available commands and options.

## Dependencies

AutoMCP automatically installs several dependencies:

- `fastapi`: For serving the MCP API
- `uvicorn`: ASGI server for FastAPI
- `pydantic`: Data validation and settings management
- `requests`: HTTP requests library
- `PyYAML`: YAML parsing for configuration files
- `chromadb`: Vector database for documentation storage
- `colorama`: Terminal text coloring

## Configuration

After installation, you'll need to create configuration files for the APIs you want to expose. See the Configuration Guides for details. 