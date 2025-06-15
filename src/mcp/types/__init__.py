"""
Stub package for mcp.types to satisfy imports.
"""

from typing import Any, Dict, Sequence, Union

class TextContent:
    def __init__(self, type: str, text: str):
        """
        Initializes a TextContent instance with a specified type and text.
        
        Args:
            type: The type of the text content.
            text: The textual content.
        """
        self.type = type
        self.text = text

class ImageContent:
    pass

class EmbeddedResource:
    pass

class Tool:
    def __init__(self, name: str, description: str, inputSchema: Dict[str, Any]):
        """
        Initializes a Tool instance with a name, description, and input schema.
        
        Args:
            name: The name of the tool.
            description: A brief description of the tool.
            inputSchema: A dictionary defining the expected input schema for the tool.
        """
        self.name = name
        self.description = description
        self.inputSchema = inputSchema
