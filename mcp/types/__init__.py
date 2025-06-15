"""
Stub package for mcp.types to satisfy imports in server module.
"""
from typing import Any, Dict

class TextContent:
    def __init__(self, type: str, text: str):
        self.type = type
        self.text = text

class ImageContent:
    pass

class EmbeddedResource:
    pass

class Tool:
    def __init__(self, name: str, description: str, inputSchema: Dict[str, Any]):
        self.name = name
        self.description = description
        self.inputSchema = inputSchema
