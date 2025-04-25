# Command Line Interface

AutoMCP provides a powerful command-line interface (CLI) for managing API configurations, serving MCP endpoints, and integrating with LLMs.

> **Note**
> A dedicated `automcp` console script may be added in a future release.  For now, invoke the CLI with `python -m src.main`.

## Basic Usage

```bash
python -m src.main [command] [options]
```

## Available Commands

| Command | Description |
|---------|-------------|
| `add` | Add an API configuration to AutoMCP |
| `list-servers` | List all registered API servers |
| `remove` | Remove an API server from the registry (optionally keep its data) |
| `delete` | **(Deprecated)** Delete an API server from the registry |
| `serve` | Start the MCP server |
| `install` | Install AutoMCP for specific platforms (e.g., Claude) |

## Command: add

The `add` command processes an API configuration file, crawls its documentation, and registers it with AutoMCP.

```bash
python -m src.main add --config <path>
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--config` | Path to API configuration file or directory with JSON configs | (required) |
| `--db-directory` | Directory to store the vector database | `./.chromadb` |
| `--registry-file` | Path to the server registry file | `./.automcp/registry.json` |

### Examples

Add a single API:
```bash
python -m src.main add --config ./ahrefs.json
```

Add multiple APIs from a directory:
```bash
python -m src.main add --config ./api_configs/
```

Specify a custom database directory:
```bash
python -m src.main add --config ./ahrefs.json --db-directory ./my_db/ahrefs
```

## Command: list-servers

The `list-servers` command displays all registered API servers.

```bash
python -m src.main list-servers
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--registry-file` | Path to the server registry file | `./.automcp/registry.json` |

### Example Output

```
Found 2 registered API server(s):

  - Ahrefs API (config: /path/to/ahrefs.json)
    Database: /path/to/.chromadb/ahrefs
    Added: 2023-09-15 14:30:22

  - DataForSEO API (config: /path/to/dataforseo.json)
    Database: /path/to/.chromadb/dataforseo
    Added: 2023-09-15 15:45:10
```

## Command: remove

The `remove` command removes an API server from the registry and optionally its data.

```bash
python -m src.main remove --name <server_name>
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--name` | Name of the API server to remove | (required) |
| `--keep-data` | Preserve the associated database directory | `false` |
| `--registry-file` | Path to the server registry file | `./.automcp/registry.json` |

### Examples

Remove a server and its database:
```bash
python -m src.main remove --name ahrefs
```

Remove a server but keep its database:
```bash
python -m src.main remove --name ahrefs --keep-data
```

## Command: delete

> **Warning**: This command is deprecated and will be removed in a future version. Use `remove` instead.

The `delete` command removes an API server from the registry (legacy version).

```bash
python -m src.main delete --name <server_name>
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--name` | Name of the API server to delete | (required) |
| `--clean` | Also delete the database directory | `false` |
| `--registry-file` | Path to the server registry file | `./.automcp/registry.json` |

### Examples

Delete a server:
```bash
python -m src.main delete --name ahrefs
```

Delete a server and its database:
```bash
python -m src.main delete --name ahrefs --clean
```

## Command: serve

The `serve` command starts the MCP server for all registered APIs or specified ones.

```bash
python -m src.main serve [options]
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--config` | Path to API configuration file or directory (optional) | Uses registry if not specified |
| `--host` | Host to bind the server to | `0.0.0.0` |
| `--port` | Port to bind the server to | `8000` |
| `--debug` | Enable debug mode | `false` |
| `--db-directory` | Directory to store the vector database | `./.chromadb` |
| `--registry-file` | Path to the server registry file | `./.automcp/registry.json` |

### Examples

Start server with all registered APIs:
```bash
python -m src.main serve
```

Start server with specific API configuration:
```bash
python -m src.main serve --config ./ahrefs.json
```

Start server on a different port:
```bash
python -m src.main serve --port 9000
```

Start server in debug mode:
```bash
python -m src.main serve --debug
```

## Command: install

The `install` command creates configuration files for specific platforms.

```bash
python -m src.main install <platform> [options]
```

Currently supported platforms:
- `claude`: Generate configuration for Claude LLM

### Options for `install claude`

| Option | Description | Default |
|--------|-------------|---------|
| `--config` | Path to API configuration file or directory (optional) | Uses registry if not specified |
| `--host` | Host where MCP server is running | `localhost` |
| `--port` | Port where MCP server is running | `8000` |
| `--output` | Path to write Claude configuration file | `.claude.json` |
| `--registry-file` | Path to the server registry file | `./.automcp/registry.json` |

### Examples

Generate Claude configuration for all registered APIs:
```bash
python -m src.main install claude
```

Generate Claude configuration for specific APIs:
```bash
python -m src.main install claude --config ./api_configs/
```

Specify a custom host and port:
```bash
python -m src.main install claude --host api.example.com --port 443
``` 