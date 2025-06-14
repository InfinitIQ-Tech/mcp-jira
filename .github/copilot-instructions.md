This is a python based repository using the jira pip package via the Model Context Protocol. This enables users utilizing MCP-enabled LLMS to work with jira in natural language rather than learning the API themselves.

NOTE: There is an ongoing effort to convert from the jira pip package to utilizing the V3 REST API directly.

## Code Standards

### Development Flow
- Build/Run: to ensure compatibilty with the end-user, use `uv` as this is what we recommended.
  - `uv run mcp-server-jira`
- Test: to ensure functionality, create and run unit tests using pytest

## Key Guidelines
1. Think like "Uncle Bob" (Robert Martin)
2. Write clean, modular code that follows the Single Responsibility Principle
3. Ensure best-practices with MCP servers are followed by referring to `/MCPReadme.md`
4. Ensure instructions to agents are updated via `@server.list_tools()` - this follows a specific schema so don't be creative with keys.
5. Maintain existing code structure and organization unless otherwise directed
6. Use dependency injection patterns where appropriate
7. Write unit tests for new functionality.
8. Document public APIs and complex logic. Suggest changes to the `docs/` folder when appropriate.
9. Use black, isort, and mypy for code quality
