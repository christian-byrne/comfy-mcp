"""AST node definitions for ComfyUI Workflow DSL."""

from typing import Any, Union
from pydantic import BaseModel, Field


class Connection(BaseModel):
    """Reference to another node's output."""
    node: str
    output: str

    def __str__(self) -> str:
        return f"@{self.node}.{self.output}"


class Property(BaseModel):
    """Node property/parameter."""
    name: str
    value: Union[Connection, int, float, bool, str]

    def __str__(self) -> str:
        if isinstance(self.value, Connection):
            return f"  {self.name}: {self.value}"
        elif isinstance(self.value, bool):
            return f"  {self.name}: {'true' if self.value else 'false'}"
        elif isinstance(self.value, (int, float)):
            return f"  {self.name}: {self.value}"
        else:
            return f"  {self.name}: {self.value}"


class Node(BaseModel):
    """Workflow node."""
    name: str
    node_type: str
    properties: list[Property] = Field(default_factory=list)

    def __str__(self) -> str:
        props = "\n".join(str(p) for p in self.properties)
        if props:
            return f"{self.name}: {self.node_type}\n{props}"
        return f"{self.name}: {self.node_type}"


class Section(BaseModel):
    """Workflow section with header and nodes."""
    header: str
    nodes: list[Node] = Field(default_factory=list)

    def __str__(self) -> str:
        nodes_str = "\n\n".join(str(n) for n in self.nodes)
        return f"## {self.header}\n\n{nodes_str}"


class Workflow(BaseModel):
    """Complete workflow containing sections."""
    sections: list[Section] = Field(default_factory=list)

    def __str__(self) -> str:
        result = "\n\n".join(str(s) for s in self.sections)
        # Add trailing newline if sections exist
        if self.sections:
            result += "\n"
        return result

    def get_node(self, name: str) -> Node | None:
        """Find node by name across all sections."""
        for section in self.sections:
            for node in section.nodes:
                if node.name == name:
                    return node
        return None

    def list_nodes(self) -> list[str]:
        """Get list of all node names."""
        return [
            node.name
            for section in self.sections
            for node in section.nodes
        ]
