# Jira MCP Server

A Model Context Protocol (MCP) server for interacting with Jira's REST API using the `jira-python` library. This server integrates with Claude Desktop and other MCP clients, allowing you to interact with Jira using natural language commands.

<a href="https://glama.ai/mcp/servers/@InfinitIQ-Tech/mcp-jira">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/@InfinitIQ-Tech/mcp-jira/badge" alt="Jira Server MCP server" />
</a>

## Features

- Get all accessible Jira projects
- Get details for a specific Jira issue
- Search issues using JQL (Jira Query Language)
- Create new Jira issues
- Add comments to issues
- Get available transitions for an issue
- Transition issues to new statuses

## Installation

### Prerequisites

- Python 3.9 or higher
- A Jira instance (Cloud, Server, or Data Center)
- [uv](https://github.com/astral-sh/uv) (optional but recommended for dependency management)

### Activate a virtual environment (recommended)

```bash
# Install a Virtual Environment (VENV) in the mcp server directory
python -m venv .
# Activate the virtual environment
source bin/activate
```
### Using uv (recommended)
```
# Install uv if you don't have it
pip install uv

# Install the Jira MCP server
uv pip install mcp-server-jira
```

### Using pip

```bash
pip install mcp-server-jira
```

## Configuration

### Environment Variables

Configure the server using environment variables:

- `JIRA_SERVER_URL`: URL of your Jira server
- `JIRA_AUTH_METHOD`: Authentication method ('basic_auth' or 'token_auth')
- `JIRA_USERNAME`: Username for basic auth
- `JIRA_PASSWORD`: Password for basic auth
- `JIRA_TOKEN`: API token or Personal Access Token

### Environment File (Local Development)

You can also create a `.env` file in the root directory with your configuration:

```
JIRA_SERVER_URL=https://your-jira-instance.atlassian.net
JIRA_AUTH_METHOD=basic_auth
JIRA_USERNAME=your_email@example.com
JIRA_TOKEN=your_api_token
```

## Usage

### Command Line

```bash
python -m mcp_server_jira
```

### Docker

```bash
docker build -t mcp-jira .
docker run --env-file .env -p 8080:8080 mcp-jira
```

## Claude Desktop Integration

To use this server with Claude Desktop:

1. Install the server using one of the methods above
2. In Claude Desktop:
   - Go to Settings -> Developer
   - Click Edit Config
   - Open the json configuraiton in your editor of choice
   - Add the following JSON:
(`NOTE`: The environment variables used are for token Auth and will not work with other authentication methods)
```json
{
  "mcpServers": {
    "jira": {
      "command": "<PATH TO UV> i.e. /Users/<MYUSERNAME>/.local/bin/uv",
      "args": [
          "--directory",
          "<PATH TO JIRA MCP>",
          "run",
          "mcp-server-jira"
      ],
      "env": {
          "JIRA_SERVER_URL": "https://<ORG>.atlassian.net/",
          "JIRA_AUTH_METHOD": "token_auth",
          "JIRA_USERNAME": "<USERNAME>",
          "JIRA_TOKEN": "<TOKEN>"
      }
    }
  }
}
```

3. Now you can interact with Jira by asking Claude questions like:
   - "Show me all my projects in Jira"
   - "Get details for issue PROJECT-123"
   - "Create a new bug in the PROJECT with summary 'Fix login issue'"
   - "Find all open bugs assigned to me"

## Authentication

The server supports multiple authentication methods:

### Basic Authentication

For Jira Server/Data Center with username and password:

```bash
JIRA_SERVER_URL="https://jira.example.com"
JIRA_AUTH_METHOD="basic_auth"
JIRA_USERNAME="your_username"
JIRA_PASSWORD="your_password"
```

### API Token (Jira Cloud)

For Jira Cloud using an API token:

```bash
JIRA_SERVER_URL="https://your-domain.atlassian.net"
JIRA_AUTH_METHOD="basic_auth"
JIRA_USERNAME="your_email@example.com"
JIRA_TOKEN="your_api_token"
```

### Personal Access Token (Jira Server/Data Center)

For Jira Server/Data Center (8.14+) using a PAT:

```bash
JIRA_SERVER_URL="https://jira.example.com"
JIRA_AUTH_METHOD="token_auth"
JIRA_TOKEN="your_personal_access_token"
```

## Available Tools

1. `get_projects`: Get all accessible Jira projects
2. `get_issue`: Get details for a specific Jira issue by key
3. `search_issues`: Search for Jira issues using JQL
4. `create_issue`: Create a new Jira issue
5. `add_comment`: Add a comment to a Jira issue
6. `get_transitions`: Get available workflow transitions for a Jira issue
7. `transition_issue`: Transition a Jira issue to a new status

## License
MIT