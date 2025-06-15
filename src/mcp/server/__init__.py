"""
Stub package for mcp.server to satisfy imports.
"""

class Server:
    """Stubbed Server class"""
    def __init__(self, *args, **kwargs):
        pass

    def list_tools(self):
        def decorator(fn):
            return fn
        return decorator

    def call_tool(self):
        def decorator(fn):
            return fn
        return decorator

    def create_initialization_options(self):
        return {}

    async def run(self, *args, **kwargs):
        pass
