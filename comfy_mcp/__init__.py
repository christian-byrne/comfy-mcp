"""ComfyUI MCP Server - DSL-first workflow management for ComfyUI.

This package provides a Model Context Protocol (MCP) server that enables agents
to manage ComfyUI workflows using a human-readable Domain Specific Language (DSL).

The core design philosophy is DSL-first: agents work entirely in DSL format,
with JSON conversion happening transparently.

Example:
    Start the MCP server:
    
    >>> from comfy_mcp.mcp.server import run_server
    >>> run_server()
    
    Or use the CLI:
    
    $ python -m comfy_mcp.mcp.server

Key Features:
    - DSL-first workflow management
    - Transparent JSON conversion
    - ComfyUI execution integration
    - File operations (read/write/list)
    - Workflow validation and analysis
    - Real-time execution monitoring

Modules:
    dsl: Domain Specific Language parser and converter
    mcp: Model Context Protocol server implementation
"""

__version__ = "0.1.0"
__author__ = "Christian Byrne"
__email__ = ""
__license__ = "MIT"

from .dsl import DSLParser, DslToJsonConverter, JsonToDslConverter
from .mcp.server import DEFAULT_COMFYUI_SERVER

__all__ = [
    "DSLParser",
    "DslToJsonConverter", 
    "JsonToDslConverter",
    "DEFAULT_COMFYUI_SERVER",
]