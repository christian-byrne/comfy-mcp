"""MCP Server package for ComfyUI workflow management.

This package provides a Model Context Protocol (MCP) server that exposes
ComfyUI workflow management tools to AI agents.

The server provides both file operations and execution capabilities:

File Operations:
    - read_workflow: Read JSON/DSL files, convert to DSL
    - write_workflow: Write DSL as JSON/DSL files  
    - list_workflows: Discover workflow files
    - validate_workflow: Validate DSL syntax
    - get_workflow_info: Analyze workflow structure

Execution Operations:
    - execute_workflow: Run DSL workflows on ComfyUI
    - get_job_status: Monitor execution & download images
    - list_comfyui_queue: View ComfyUI queue status

Example:
    Start the MCP server:
    
    >>> from comfy_mcp.mcp.server import mcp
    >>> if __name__ == "__main__":
    ...     mcp.run()
"""

from .server import mcp, DEFAULT_COMFYUI_SERVER

__all__ = [
    "mcp",
    "DEFAULT_COMFYUI_SERVER",
]