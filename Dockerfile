FROM python:3.10-slim

WORKDIR /app

# Install uv for dependency management
# Note: In production environments, proper SSL certificates should be used
# The --trusted-host flags are included to handle CI/CD environments with certificate issues
RUN pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org --no-cache-dir uv

# Copy pyproject.toml and uv.lock (if it exists)
COPY pyproject.toml uv.lock* ./

# Copy source code and README (required for package build)
COPY src/ ./src/
COPY README.md ./

# Install dependencies using uv
# uv provides isolated virtual environments for MCP servers, preventing conflicts with global Python environment
RUN uv pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org --no-cache-dir --system -e .

# Set the entrypoint
ENTRYPOINT ["python", "-m", "mcp_server_jira"]