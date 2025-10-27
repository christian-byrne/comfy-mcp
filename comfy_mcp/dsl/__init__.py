"""DSL package for ComfyUI workflow management.

This package provides parsing and conversion between ComfyUI's JSON format
and a human-readable Domain Specific Language (DSL).

Classes:
    DSLParser: Parse DSL text into Abstract Syntax Tree
    DslToJsonConverter: Convert DSL AST to ComfyUI JSON format
    JsonToDslConverter: Convert ComfyUI JSON to DSL AST
    
    Workflow: Root AST node representing a complete workflow
    Section: AST node representing a workflow section
    Node: AST node representing a workflow node
    Property: AST node representing a node property
    Connection: AST node representing a connection between nodes

Functions:
    is_full_workflow_format: Check if JSON is in full ComfyUI format
    full_workflow_to_simplified: Convert full format to simplified
"""

from .parser import DSLParser
from .converter import (
    DslToJsonConverter,
    JsonToDslConverter,
    is_full_workflow_format,
    full_workflow_to_simplified,
)
from .ast_nodes import Workflow, Section, Node, Property, Connection

__all__ = [
    "DSLParser",
    "DslToJsonConverter",
    "JsonToDslConverter",
    "is_full_workflow_format", 
    "full_workflow_to_simplified",
    "Workflow",
    "Section",
    "Node", 
    "Property",
    "Connection",
]