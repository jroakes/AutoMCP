# Installation

AutoMCP is installed by cloning the repository and installing dependencies using pip.

## Requirements

- Python 3.9 or higher
- pip (Python package manager)
- Git

## Installation Steps

```bash
# Clone the repository
git clone https://github.com/jroakes/automcp.git
cd automcp

# Install dependencies
pip install -r requirements.txt
```

## Verifying Installation

After installation, verify that AutoMCP is correctly installed by running:

```bash
python -m src.main --help
```

You should see output listing the available commands and options.

## Dependencies

AutoMCP's dependencies are listed in the `requirements.txt` file. Key dependencies include:

- `FastAPI`: For serving the MCP API
- `FastMCP`: For MCP server implementation
- `Crawl4AI`: For URL crawling and parsing
- `ChromaDB`: For vector storage
- `Requests`: For HTTP operations
- `PyYAML`: For YAML parsing
- `Tenacity`: For retry / API resiliency

## Configuration

After installation, you'll need to create configuration files for the APIs you want to expose. See the Configuration Guides for details. 