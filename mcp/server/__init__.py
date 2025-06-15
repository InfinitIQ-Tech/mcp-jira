"""
Stub package for mcp.server to satisfy imports in top-level server module.
"""
class Server:
    def __init__(self, *args, **kwargs):
        """
        Initializes the Server stub with arbitrary arguments.
        
        This constructor accepts any arguments but performs no initialization.
        """
        pass

    def list_tools(self):
        """
        Returns a decorator that leaves the decorated function unchanged.
        
        This method is a stub and does not modify or register the function in any way.
        """
        def decorator(fn): return fn
        return decorator

    def call_tool(self):
        """
        Returns a decorator that leaves the decorated function unchanged.
        
        Use this as a placeholder for tool registration in stub implementations.
        """
        def decorator(fn): return fn
        return decorator

    def create_initialization_options(self):
        """
        Returns an empty dictionary representing initialization options.
        """
        return {}

    async def run(self, *args, **kwargs):
        """
        Placeholder asynchronous run method with no implementation.
        """
        pass
