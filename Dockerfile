FROM python:3.9-slim

WORKDIR /app

# Install uv for dependency management
RUN pip install --no-cache-dir uv

# Copy pyproject.toml and uv.lock (if it exists)
COPY pyproject.toml uv.lock* ./

# Install dependencies using uv
RUN uv pip install --no-cache-dir -e .

# Copy source code
COPY src/ ./src/
COPY README.md ./

# Set the entrypoint
ENTRYPOINT ["python", "-m", "mcp_server_jira"]