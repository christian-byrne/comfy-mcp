"""Converter between DSL AST and ComfyUI JSON format."""

import json
from typing import Any
from pathlib import Path
from .ast_nodes import Workflow, Section, Node, Property, Connection


# Default output mappings for common ComfyUI nodes
# Maps node_type -> output_name -> output_index
DEFAULT_OUTPUT_MAPPINGS = {
    "CheckpointLoaderSimple": {"model": 0, "clip": 1, "vae": 2},
    "CheckpointLoader": {"model": 0, "clip": 1, "vae": 2},
    "CLIPTextEncode": {"conditioning": 0},
    "EmptyLatentImage": {"latent": 0},
    "KSampler": {"latent": 0},
    "VAEDecode": {"image": 0},
    "VAEEncode": {"latent": 0},
    "LoadImage": {"image": 0, "mask": 1},
    "SaveImage": {},
}


class DslToJsonConverter:
    """Convert DSL workflow to ComfyUI JSON format."""

    def __init__(self, output_mappings: dict[str, dict[str, int]] | None = None):
        """Initialize converter with output mappings."""
        self.output_mappings = output_mappings or DEFAULT_OUTPUT_MAPPINGS
        self.node_id_map: dict[str, str] = {}
        self.node_type_map: dict[str, str] = {}
        self.next_id = 1

    def convert(self, workflow: Workflow) -> dict[str, Any]:
        """Convert workflow AST to ComfyUI JSON."""
        self.node_id_map = {}
        self.node_type_map = {}
        self.next_id = 1

        result = {}

        # First pass: assign IDs and build type map
        for section in workflow.sections:
            for node in section.nodes:
                node_id = str(self.next_id)
                self.node_id_map[node.name] = node_id
                self.node_type_map[node.name] = node.node_type
                self.next_id += 1

        # Second pass: convert nodes with connections
        for section in workflow.sections:
            for node in section.nodes:
                node_id = self.node_id_map[node.name]
                result[node_id] = self._convert_node(node)

        return result

    def _convert_node(self, node: Node) -> dict[str, Any]:
        """Convert a single node to ComfyUI format."""
        inputs = {}

        for prop in node.properties:
            inputs[prop.name] = self._convert_value(prop.value, node.node_type)

        return {
            "class_type": node.node_type,
            "inputs": inputs,
        }

    def _convert_value(self, value: Any, node_type: str) -> Any:
        """Convert property value to ComfyUI format."""
        if isinstance(value, Connection):
            # Convert named connection to [node_id, output_index]
            node_id = self.node_id_map[value.node]
            output_index = self._get_output_index(value.node, value.output)
            return [node_id, output_index]
        elif isinstance(value, bool):
            return value
        elif isinstance(value, (int, float)):
            return value
        else:
            return str(value)

    def _get_output_index(self, node_name: str, output_name: str) -> int:
        """Get output index for a node's output."""
        if node_name in self.node_type_map:
            node_type = self.node_type_map[node_name]
            if node_type in self.output_mappings:
                return self.output_mappings[node_type].get(output_name, 0)
        return 0


class JsonToDslConverter:
    """Convert ComfyUI JSON to DSL workflow."""

    def __init__(self, output_mappings: dict[str, dict[str, int]] | None = None):
        """Initialize converter with output mappings."""
        self.output_mappings = output_mappings or DEFAULT_OUTPUT_MAPPINGS
        # Build reverse mapping: node_type -> output_index -> output_name
        self.reverse_mappings: dict[str, dict[int, str]] = {}
        for node_type, mapping in self.output_mappings.items():
            self.reverse_mappings[node_type] = {idx: name for name, idx in mapping.items()}

    def convert(self, json_data: dict[str, Any]) -> Workflow:
        """Convert ComfyUI JSON to workflow AST."""
        # Create friendly names for nodes
        node_names = self._generate_node_names(json_data)

        # Group nodes into sections by type
        sections_dict: dict[str, list[Node]] = {}

        for node_id, node_data in json_data.items():
            node_type = node_data["class_type"]
            section_name = self._infer_section_name(node_type)

            node_name = node_names[node_id]
            inputs = node_data.get("inputs", {})

            properties = []
            for prop_name, prop_value in inputs.items():
                converted_value = self._convert_value(
                    prop_value, node_id, node_names, json_data
                )
                properties.append(Property(name=prop_name, value=converted_value))

            node = Node(name=node_name, node_type=node_type, properties=properties)

            if section_name not in sections_dict:
                sections_dict[section_name] = []
            sections_dict[section_name].append(node)

        # Create sections
        sections = [
            Section(header=section_name, nodes=nodes)
            for section_name, nodes in sections_dict.items()
        ]

        return Workflow(sections=sections)

    def _generate_node_names(self, json_data: dict[str, Any]) -> dict[str, str]:
        """Generate friendly names for nodes."""
        names = {}
        type_counts: dict[str, int] = {}

        for node_id, node_data in json_data.items():
            node_type = node_data["class_type"]
            base_name = self._type_to_name(node_type)

            # Add number suffix if we have multiple of same type
            if base_name not in type_counts:
                type_counts[base_name] = 0
                names[node_id] = base_name
            else:
                type_counts[base_name] += 1
                names[node_id] = f"{base_name}_{type_counts[base_name]}"

        return names

    def _type_to_name(self, node_type: str) -> str:
        """Convert node type to friendly name."""
        # Common mappings
        mappings = {
            "CheckpointLoaderSimple": "checkpoint",
            "CheckpointLoader": "checkpoint",
            "CLIPTextEncode": "text_encode",
            "EmptyLatentImage": "empty_latent",
            "KSampler": "sampler",
            "VAEDecode": "decode",
            "VAEEncode": "encode",
            "LoadImage": "load_image",
            "SaveImage": "save",
        }
        return mappings.get(node_type, node_type.lower())

    def _infer_section_name(self, node_type: str) -> str:
        """Infer section name from node type."""
        if "Checkpoint" in node_type or "Loader" in node_type:
            return "Model Loading"
        elif "CLIP" in node_type or "TextEncode" in node_type:
            return "Text Conditioning"
        elif "Latent" in node_type:
            return "Latent"
        elif "Sampler" in node_type or "KSampler" in node_type:
            return "Sampling"
        elif "VAE" in node_type or "Save" in node_type:
            return "Output"
        else:
            return "Processing"

    def _convert_value(
        self,
        value: Any,
        current_node_id: str,
        node_names: dict[str, str],
        json_data: dict[str, Any],
    ) -> Any:
        """Convert property value from ComfyUI format."""
        if isinstance(value, list) and len(value) == 2:
            # Connection: [node_id, output_index]
            target_node_id = str(value[0])
            output_index = value[1]

            target_node_name = node_names[target_node_id]
            target_node_type = json_data[target_node_id]["class_type"]

            # Get output name from index
            output_name = self._get_output_name(target_node_type, output_index)

            return Connection(node=target_node_name, output=output_name)
        elif isinstance(value, bool):
            return value
        elif isinstance(value, (int, float)):
            return value
        else:
            return str(value)

    def _get_output_name(self, node_type: str, output_index: int) -> str:
        """Get output name from node type and index."""
        if node_type in self.reverse_mappings:
            return self.reverse_mappings[node_type].get(output_index, f"output_{output_index}")
        return f"output_{output_index}"


def load_json_workflow(path: str | Path) -> dict[str, Any]:
    """Load ComfyUI workflow from JSON file."""
    with open(path) as f:
        return json.load(f)


def save_json_workflow(workflow: dict[str, Any], path: str | Path) -> None:
    """Save ComfyUI workflow to JSON file."""
    with open(path, "w") as f:
        json.dump(workflow, f, indent=2)


def is_full_workflow_format(workflow: dict[str, Any]) -> bool:
    """Check if workflow is in full ComfyUI format (with nodes array) vs simplified API format."""
    return "nodes" in workflow and isinstance(workflow.get("nodes"), list)


def full_workflow_to_simplified(workflow: dict[str, Any]) -> dict[str, Any]:
    """Convert full ComfyUI workflow format to simplified API format.

    Full format has: {"nodes": [...], "links": [...], ...}
    Simplified format: {"1": {"class_type": "...", "inputs": {...}}, ...}
    """
    if not is_full_workflow_format(workflow):
        return workflow  # Already in simplified format

    simplified = {}
    nodes = workflow.get("nodes", [])
    links = workflow.get("links", [])

    # Build a mapping of link_id -> link_data for quick lookup
    # Links format: [link_id, source_node_id, source_slot, target_node_id, target_slot, type]
    link_map = {}
    for link in links:
        if len(link) >= 6:
            link_id, source_node_id, source_slot, target_node_id, target_slot, link_type = link[:6]
            link_map[link_id] = {
                "source_node_id": source_node_id,
                "source_slot": source_slot,
                "target_node_id": target_node_id,
                "target_slot": target_slot,
                "type": link_type,
            }

    # Build node_id -> node_data mapping for finding connected nodes
    node_by_id = {node["id"]: node for node in nodes}

    # Convert each node to simplified format
    for node in nodes:
        node_id = str(node["id"])
        node_type = node.get("type", "Unknown")

        # Extract inputs from the node
        inputs = {}

        # Process widgets_values - these become scalar inputs
        widgets_values = node.get("widgets_values", [])

        # Process input connections
        node_inputs = node.get("inputs", [])
        widget_index = 0  # Track which widget value we're on

        for i, input_def in enumerate(node_inputs):
            input_name = input_def.get("name", f"input_{i}")

            # Check if this input is connected via a link
            link_id = input_def.get("link")
            if link_id and link_id in link_map:
                # This input is connected to another node
                link_data = link_map[link_id]
                source_node_id = str(link_data["source_node_id"])
                source_slot = link_data["source_slot"]

                # Format as [node_id, slot_index] for simplified format
                inputs[input_name] = [source_node_id, source_slot]
            elif widget_index < len(widgets_values):
                # Use widget value if available and not connected
                inputs[input_name] = widgets_values[widget_index]
                widget_index += 1

        # Add remaining widget values with generic names
        # These are typically node parameters that don't have input connections
        param_counter = 0
        while widget_index < len(widgets_values):
            # Use generic names for unmapped widgets
            widget_name = f"param_{param_counter}"
            inputs[widget_name] = widgets_values[widget_index]
            widget_index += 1
            param_counter += 1

        # Also include properties if they're not already in inputs
        properties = node.get("properties", {})
        for key, value in properties.items():
            if key not in inputs and key != "Node name for S&R":
                inputs[key] = value

        simplified[node_id] = {
            "class_type": node_type,
            "inputs": inputs,
        }

    return simplified


def is_full_workflow_format(data: dict[str, Any]) -> bool:
    """Check if data is in full ComfyUI workflow format.
    
    Full format has 'workflow' key containing the actual nodes.
    Simplified format has node IDs as top-level keys.
    """
    if not isinstance(data, dict):
        return False
    
    # Full format indicators
    if "workflow" in data and isinstance(data["workflow"], dict):
        return True
        
    # If we have "nodes" or "links" at top level, it's likely full format
    if "nodes" in data or "links" in data:
        return True
        
    return False


def full_workflow_to_simplified(full_data: dict[str, Any]) -> dict[str, Any]:
    """Convert full ComfyUI workflow format to simplified API format.
    
    Args:
        full_data: Full workflow format with 'workflow', 'extra', etc.
        
    Returns:
        Simplified format with node IDs as keys
    """
    if not is_full_workflow_format(full_data):
        return full_data
        
    # Extract the workflow part
    if "workflow" in full_data:
        return full_data["workflow"]
    
    # If it has nodes/links at top level, convert from node list format
    if "nodes" in full_data:
        nodes = full_data["nodes"]
        links = full_data.get("links", [])
        
        # Build link mapping
        link_map = {}
        for link in links:
            link_id = link[0]
            source_node_id = link[1]
            source_slot = link[2]
            target_node_id = link[3]
            target_slot = link[4]
            
            link_map[link_id] = {
                "source_node_id": source_node_id,
                "source_slot": source_slot,
                "target_node_id": target_node_id,
                "target_slot": target_slot,
            }
        
        return convert_nodes_format_to_simplified(nodes, link_map)
    
    return full_data
