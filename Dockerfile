FROM python:3.10-slim

WORKDIR /app

# Copy source code and requirements
COPY src/ ./src/
COPY pyproject.toml README.md ./

# Install the package and its dependencies
# Note: In production environments, proper SSL certificates should be used
# The --trusted-host flags are included to handle CI/CD environments with certificate issues
RUN pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org --no-cache-dir --upgrade pip && \
    pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org --no-cache-dir .

# Set the entrypoint
ENTRYPOINT ["python", "-m", "mcp_server_jira"]