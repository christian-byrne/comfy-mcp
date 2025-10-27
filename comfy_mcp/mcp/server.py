"""ComfyUI Workflow MCP Server

Provides tools for reading, writing, and managing ComfyUI workflows.
Agents work entirely in DSL format - JSON conversion is transparent.
"""

import sys
import json
from pathlib import Path
from collections import Counter
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError

# Import version for CLI
try:
    from comfy_mcp import __version__
except ImportError:
    __version__ = "unknown"

# Import from DSL package
from ..dsl import (
    DSLParser,
    DslToJsonConverter,
    JsonToDslConverter,
    is_full_workflow_format,
    full_workflow_to_simplified,
    Connection,
)

# Import template functionality
from ..templates import TemplateManager

# Create MCP server
mcp = FastMCP("ComfyUI Workflow Manager 🎨")

# Security: Define allowed base directory for file operations
WORKFLOWS_BASE = Path.cwd() / "workflows"
WORKFLOWS_BASE.mkdir(exist_ok=True)

# Initialize template manager
template_manager = TemplateManager()


def validate_path(filepath: str, base: Path = WORKFLOWS_BASE) -> Path:
    """Validate file path is within allowed directory"""
    path = Path(filepath).resolve()
    try:
        path.relative_to(base.resolve())
        return path
    except ValueError:
        raise ToolError(f"Access denied: {filepath} is outside allowed directory")


# ===== FILE OPERATION TOOLS =====

@mcp.tool
async def read_workflow(ctx: Context, filepath: str) -> str:
    """Read a workflow file and return it as DSL format.

    Supports both JSON and DSL input files. Automatically detects format
    and converts JSON to DSL transparently.

    Args:
        filepath: Path to workflow file (.json or .dsl)

    Returns:
        Workflow content in DSL format

    Examples:
        read_workflow("workflows/my_workflow.json")
        read_workflow("../dsl/examples/dsl/simple.dsl")
    """
    await ctx.info(f"Reading workflow from {filepath}")

    try:
        path = Path(filepath).resolve()

        # Allow access to dsl/examples directory
        if "examples" not in str(path):
            path = validate_path(filepath)

        if not path.exists():
            raise ToolError(f"File not found: {filepath}")

        content = path.read_text()

        # If already DSL, return as-is
        if path.suffix == ".dsl":
            await ctx.info("File is already in DSL format")
            return content

        # If JSON, convert to DSL
        if path.suffix == ".json":
            await ctx.info("Converting JSON to DSL...")

            workflow = json.loads(content)

            # Handle full ComfyUI format
            if is_full_workflow_format(workflow):
                workflow = full_workflow_to_simplified(workflow)

            # Convert to DSL
            converter = JsonToDslConverter()
            workflow_ast = converter.convert(workflow)
            dsl_text = str(workflow_ast)

            await ctx.info(f"✓ Converted to DSL ({len(dsl_text)} chars)")
            return dsl_text

        raise ToolError(f"Unsupported file format: {path.suffix}")

    except json.JSONDecodeError as e:
        raise ToolError(f"Invalid JSON in {filepath}: {e}")
    except Exception as e:
        raise ToolError(f"Error reading workflow: {e}")


@mcp.tool
async def write_workflow(
    ctx: Context,
    filepath: str,
    dsl: str,
    format: str = "json"
) -> dict:
    """Write a workflow to disk.

    Takes DSL content and writes it to disk. By default, converts to JSON format.
    Can optionally save as .dsl format directly.

    Args:
        filepath: Destination file path
        dsl: Workflow content in DSL format
        format: Output format ("json" or "dsl", default: "json")

    Returns:
        Status dict with path, size, and format info

    Examples:
        write_workflow("workflows/new_workflow.json", dsl_content)
        write_workflow("workflows/backup.dsl", dsl_content, format="dsl")
    """
    await ctx.info(f"Writing workflow to {filepath}")

    try:
        path = validate_path(filepath)

        # Check if file exists
        if path.exists():
            await ctx.info(f"⚠️  File {filepath} already exists, will overwrite")

        if format == "dsl":
            # Write DSL directly
            path.write_text(dsl)
            await ctx.info(f"✓ Wrote DSL to {filepath}")

        elif format == "json":
            # Convert DSL to JSON
            await ctx.info("Converting DSL to JSON...")

            parser = DSLParser()
            workflow_ast = parser.parse(dsl)

            converter = DslToJsonConverter()
            json_workflow = converter.convert(workflow_ast)

            json_content = json.dumps(json_workflow, indent=2)
            path.write_text(json_content)

            await ctx.info(f"✓ Wrote JSON to {filepath}")

        else:
            raise ToolError(f"Unsupported format: {format}. Use 'json' or 'dsl'")

        return {
            "status": "success",
            "path": str(path),
            "size": path.stat().st_size,
            "format": format
        }

    except Exception as e:
        raise ToolError(f"Error writing workflow: {e}")


@mcp.tool
def list_workflows(directory: str = "workflows", pattern: str = "*") -> list[dict]:
    """List workflow files in a directory.

    Discovers workflow files (.json and .dsl) in the specified directory.
    Supports glob patterns for filtering.

    Args:
        directory: Directory to search (default: "workflows")
        pattern: Glob pattern for filtering (default: "*" for all files)

    Returns:
        List of workflow info dicts with name, size, modified time

    Examples:
        list_workflows()
        list_workflows("workflows", "*.json")
        list_workflows("../dsl/examples/dsl")
    """
    try:
        base = Path(directory)

        # Allow listing in dsl/examples without validation
        if "examples" in str(directory):
            search_path = base
        else:
            search_path = validate_path(str(base))

        if not search_path.exists():
            raise ToolError(f"Directory not found: {directory}")

        # Find workflow files
        workflows = []
        for ext in [".json", ".dsl"]:
            for path in search_path.glob(f"{pattern}{ext}"):
                if path.is_file():
                    stat = path.stat()
                    workflows.append({
                        "name": path.name,
                        "path": str(path),
                        "size": stat.st_size,
                        "modified": stat.st_mtime,
                        "format": ext[1:]  # Remove leading dot
                    })

        # Sort by name
        workflows.sort(key=lambda w: w["name"])

        return workflows

    except Exception as e:
        raise ToolError(f"Error listing workflows: {e}")


# ===== VALIDATION TOOLS =====

@mcp.tool
def validate_workflow(dsl: str) -> dict:
    """Validate DSL workflow syntax.

    Parses DSL and checks for syntax errors without executing the workflow.
    Returns validation status and any errors found.

    Args:
        dsl: Workflow content in DSL format

    Returns:
        Validation result with is_valid, errors, and warnings

    Examples:
        validate_workflow(dsl_content)
    """
    try:
        parser = DSLParser()
        workflow_ast = parser.parse(dsl)

        # If parsing succeeded, it's valid
        return {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "node_count": sum(len(section.nodes) for section in workflow_ast.sections),
            "section_count": len(workflow_ast.sections)
        }

    except Exception as e:
        return {
            "is_valid": False,
            "errors": [str(e)],
            "warnings": [],
            "message": "DSL syntax error"
        }


@mcp.tool
def get_workflow_info(dsl: str) -> dict:
    """Analyze workflow structure and return metadata.

    Parses DSL and extracts structural information like node types,
    sections, and connections without executing the workflow.

    Args:
        dsl: Workflow content in DSL format

    Returns:
        Workflow metadata including nodes, sections, and connections

    Examples:
        get_workflow_info(dsl_content)
    """
    try:
        parser = DSLParser()
        workflow_ast = parser.parse(dsl)

        # Collect node information
        node_types = []
        sections = []
        connections = []

        for section in workflow_ast.sections:
            section_info = {
                "name": section.header,
                "node_count": len(section.nodes),
                "nodes": []
            }

            for node in section.nodes:
                node_types.append(node.node_type)
                section_info["nodes"].append({
                    "name": node.name,
                    "type": node.node_type,
                    "property_count": len(node.properties)
                })

                # Find connections
                for prop in node.properties:
                    if isinstance(prop.value, Connection):
                        connections.append({
                            "from": prop.value.node,
                            "output": prop.value.output,
                            "to": node.name,
                            "input": prop.name
                        })

            sections.append(section_info)

        # Count unique node types
        node_type_counts = dict(Counter(node_types))

        return {
            "node_count": len(node_types),
            "section_count": len(sections),
            "connection_count": len(connections),
            "node_types": node_type_counts,
            "sections": sections,
            "connections": connections
        }

    except Exception as e:
        raise ToolError(f"Error analyzing workflow: {e}")


# ===== TEMPLATE TOOLS =====

@mcp.tool
def list_templates(
    category: str = None,
    difficulty: str = None,
    tag: str = None
) -> list[dict]:
    """List available workflow templates.
    
    Discover workflow templates by category, difficulty, or tags.
    Templates provide ready-to-use workflows for common use cases.
    
    Args:
        category: Filter by category (Generation, Enhancement, Editing, etc.)
        difficulty: Filter by difficulty (beginner, intermediate, advanced)
        tag: Filter by tag (text2img, inpainting, controlnet, etc.)
    
    Returns:
        List of template metadata with names, descriptions, and parameters
    
    Examples:
        list_templates()
        list_templates(category="Generation")
        list_templates(difficulty="beginner")
        list_templates(tag="text2img")
    """
    try:
        # Convert filters to search parameters
        tags = [tag] if tag else None
        
        results = template_manager.search_templates(
            category=category,
            tags=tags,
            difficulty=difficulty
        )
        
        return results
        
    except Exception as e:
        raise ToolError(f"Error listing templates: {e}")


@mcp.tool
def get_template(template_name: str) -> dict:
    """Get detailed information about a specific template.
    
    Retrieves complete template information including parameters,
    requirements, and DSL preview.
    
    Args:
        template_name: Name of the template to retrieve
    
    Returns:
        Template details with parameters and DSL preview
    
    Examples:
        get_template("text2img_basic")
        get_template("controlnet_pose")
    """
    try:
        template_info = template_manager.get_template_info(template_name)
        
        if template_info is None:
            raise ToolError(f"Template '{template_name}' not found")
        
        return template_info
        
    except Exception as e:
        raise ToolError(f"Error getting template: {e}")


@mcp.tool
def generate_from_template(
    template_name: str,
    parameters: dict = None,
    save_path: str = None
) -> dict:
    """Generate a workflow from a template with custom parameters.
    
    Creates a complete DSL workflow by substituting parameters into
    the template. Optionally saves to file.
    
    Args:
        template_name: Name of the template to use
        parameters: Dictionary of parameter values to substitute
        save_path: Optional path to save the generated workflow
    
    Returns:
        Generated DSL content and validation results
    
    Examples:
        generate_from_template("text2img_basic", {"prompt": "sunset"})
        generate_from_template("img2img", {"image_path": "input.png"}, "workflows/my_img2img.dsl")
    """
    try:
        # Validate template exists
        template = template_manager.get_template(template_name)
        if template is None:
            raise ToolError(f"Template '{template_name}' not found")
        
        # Validate parameters if provided
        if parameters:
            validation = template_manager.validate_parameters(template_name, parameters)
            if not validation["valid"]:
                return {
                    "status": "error",
                    "errors": validation["errors"],
                    "warnings": validation.get("warnings", [])
                }
        
        # Generate the workflow
        dsl_content = template_manager.generate_workflow(template_name, parameters)
        
        if dsl_content is None:
            raise ToolError(f"Failed to generate workflow from template '{template_name}'")
        
        result = {
            "status": "success",
            "template_name": template_name,
            "dsl_content": dsl_content,
            "parameters_used": parameters or {},
            "warnings": []
        }
        
        # Add warnings if any
        if parameters:
            validation = template_manager.validate_parameters(template_name, parameters)
            result["warnings"] = validation.get("warnings", [])
        
        # Save to file if requested
        if save_path:
            try:
                path = validate_path(save_path)
                path.write_text(dsl_content)
                result["saved_to"] = str(path)
                result["file_size"] = path.stat().st_size
            except Exception as e:
                result["warnings"].append(f"Failed to save to {save_path}: {e}")
        
        return result
        
    except Exception as e:
        raise ToolError(f"Error generating from template: {e}")


@mcp.tool
def search_templates(query: str) -> list[dict]:
    """Search templates by name, description, or tags.
    
    Performs fuzzy search across template metadata to find
    relevant workflow templates.
    
    Args:
        query: Search query (searches name, description, tags)
    
    Returns:
        List of matching templates
    
    Examples:
        search_templates("pose")
        search_templates("upscaling")
        search_templates("text to image")
    """
    try:
        results = template_manager.search_templates(query=query)
        return results
        
    except Exception as e:
        raise ToolError(f"Error searching templates: {e}")


@mcp.tool
def validate_template_parameters(
    template_name: str,
    parameters: dict
) -> dict:
    """Validate parameters for a template without generating.
    
    Checks if provided parameters are valid for the template
    and returns detailed validation results.
    
    Args:
        template_name: Name of the template
        parameters: Dictionary of parameters to validate
    
    Returns:
        Validation results with errors and warnings
    
    Examples:
        validate_template_parameters("text2img_basic", {"width": "512"})
    """
    try:
        validation = template_manager.validate_parameters(template_name, parameters)
        return validation
        
    except Exception as e:
        raise ToolError(f"Error validating parameters: {e}")


# ===== MCP RESOURCES =====

@mcp.resource("comfyui://examples/simple")
async def example_simple() -> str:
    """Basic text-to-image workflow example"""
    example_path = Path(__file__).parent.parent / "dsl" / "examples" / "dsl" / "simple.dsl"
    if example_path.exists():
        return example_path.read_text()
    return "# Example not found"


@mcp.resource("comfyui://examples/flux_kontext")
async def example_flux_kontext() -> str:
    """Flux Kontext workflow example (converted from real workflow)"""
    example_path = Path(__file__).parent.parent / "dsl" / "examples" / "dsl" / "flux_kontext_converted.dsl"
    if example_path.exists():
        return example_path.read_text()
    return "# Example not found"


@mcp.resource("comfyui://templates/catalog")
async def template_catalog() -> str:
    """Complete template catalog with descriptions and examples"""
    catalog = template_manager.list_templates()
    
    output = "# ComfyUI Workflow Template Catalog\n\n"
    
    # Group by category
    categories = {}
    for template in catalog:
        cat = template["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(template)
    
    for category, templates in categories.items():
        output += f"## {category}\n\n"
        
        for template in templates:
            output += f"### {template['name']}\n"
            output += f"**Difficulty:** {template['difficulty']}\n\n"
            output += f"{template['description']}\n\n"
            output += f"**Tags:** {', '.join(template['tags'])}\n\n"
            
            if template['required_models']:
                output += f"**Required Models:** {', '.join(template['required_models'])}\n\n"
            
            if template['parameters']:
                output += "**Parameters:**\n"
                for param, default in template['parameters'].items():
                    output += f"- `{param}`: {default}\n"
                output += "\n"
            
            output += "---\n\n"
    
    return output


@mcp.resource("comfyui://templates/getting-started")
async def template_getting_started() -> str:
    """Template usage guide and examples"""
    return """# Getting Started with Templates

Templates provide pre-built workflows for common ComfyUI use cases. They use parameter substitution to make workflows customizable while maintaining simplicity.

## Basic Usage

1. **List available templates:**
   ```
   list_templates()
   ```

2. **Get template details:**
   ```
   get_template("text2img_basic")
   ```

3. **Generate workflow from template:**
   ```
   generate_from_template("text2img_basic", {
     "prompt": "a beautiful sunset over mountains",
     "width": "768",
     "height": "512"
   })
   ```

4. **Save generated workflow:**
   ```
   generate_from_template("img2img", {
     "image_path": "input.png",
     "prompt": "oil painting style"
   }, "workflows/my_img2img.dsl")
   ```

## Template Categories

- **Generation**: Text-to-image, basic generation workflows
- **Enhancement**: Upscaling, improvement workflows  
- **Editing**: Inpainting, image modification
- **Controlled Generation**: ControlNet, guided generation
- **Batch Operations**: Processing multiple images
- **Artistic**: Style transfer, creative workflows

## Difficulty Levels

- **Beginner**: Simple workflows with minimal parameters
- **Intermediate**: Moderate complexity, some advanced features
- **Advanced**: Complex workflows requiring deep ComfyUI knowledge

## Tips

1. Start with beginner templates to learn the basics
2. Use `validate_template_parameters()` to check your parameters
3. Templates include parameter validation and helpful error messages
4. Generated workflows can be further customized manually
5. Search templates by tags to find specific functionality

## Example Workflow

```dsl
# Generate a basic text-to-image workflow
workflow = generate_from_template("text2img_basic", {
  "prompt": "cyberpunk city at night, neon lights",
  "negative_prompt": "blurry, low quality, artifacts",
  "width": "768",
  "height": "512", 
  "steps": "25",
  "cfg": "7.5"
})

# Execute the workflow
execute_workflow(workflow["dsl_content"])
```
"""


@mcp.resource("comfyui://docs/syntax")
async def docs_syntax() -> str:
    """DSL syntax reference and examples"""
    return """# ComfyUI DSL Syntax Reference

## Basic Structure

```dsl
## Section Name

node_name: NodeType
  param: value
  number: 42
  boolean: true
  connection: @other_node.output
```

## Data Types

- **Strings**: Unquoted or quoted text
- **Numbers**: Integers or floats (42, 3.14)
- **Booleans**: true or false
- **Connections**: @node_name.output_name

## Examples

### Simple Text2Img

```dsl
## Model Loading

checkpoint: CheckpointLoaderSimple
  ckpt_name: model.safetensors

## Text Conditioning

positive: CLIPTextEncode
  text: "a beautiful landscape"
  clip: @checkpoint.clip

## Generation

latent: EmptyLatentImage
  width: 512
  height: 512

sampler: KSampler
  model: @checkpoint.model
  positive: @positive.conditioning
  latent_image: @latent.latent
  seed: 42
  steps: 20

## Output

decode: VAEDecode
  samples: @sampler.latent
  vae: @checkpoint.vae

save: SaveImage
  images: @decode.image
```

## Tips

1. Use descriptive node names
2. Group related nodes in sections
3. Use connections (@) to link nodes
4. Validate before executing
"""


# ===== EXECUTION TOOLS =====

import httpx
import asyncio
import websockets
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime

# ComfyUI server configuration
DEFAULT_COMFYUI_SERVER = "127.0.0.1:8188"

class ComfyUIClient:
    """Client for ComfyUI API operations"""
    
    def __init__(self, server_address: str = DEFAULT_COMFYUI_SERVER):
        self.server_address = server_address
        self.base_url = f"http://{server_address}"
        self.ws_url = f"ws://{server_address}/ws"
        self.client_id = str(uuid.uuid4())
    
    async def queue_prompt(self, workflow: Dict[str, Any]) -> str:
        """Submit workflow for execution"""
        data = {
            "prompt": workflow,
            "client_id": self.client_id
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/prompt",
                json=data,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            result = response.json()
            
            if "error" in result:
                raise ToolError(f"ComfyUI error: {result['error']}")
            
            return result.get("prompt_id")
    
    async def get_history(self, prompt_id: str) -> Dict[str, Any]:
        """Get execution history and results"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/history/{prompt_id}")
            response.raise_for_status()
            return response.json()
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/queue")
            response.raise_for_status()
            return response.json()
    
    async def download_image(self, filename: str, subfolder: str = "", folder_type: str = "output") -> bytes:
        """Download generated image"""
        params = {
            "filename": filename,
            "subfolder": subfolder,
            "type": folder_type
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/view", params=params)
            response.raise_for_status()
            return response.content


@mcp.tool
async def execute_workflow(
    ctx: Context,
    dsl: str,
    server_address: str = DEFAULT_COMFYUI_SERVER,
    wait_for_completion: bool = True,
    timeout_seconds: int = 300
) -> Dict[str, Any]:
    """Execute a DSL workflow on ComfyUI server.
    
    Converts DSL to JSON and submits to ComfyUI for execution.
    Can optionally wait for completion and return results.
    
    Args:
        dsl: Workflow content in DSL format
        server_address: ComfyUI server address (default: 127.0.0.1:8188)
        wait_for_completion: Whether to wait for execution to complete
        timeout_seconds: Maximum time to wait for completion
    
    Returns:
        Execution result with prompt_id, status, and outputs if completed
    
    Examples:
        execute_workflow(dsl_content)
        execute_workflow(dsl_content, server_address="192.168.1.100:8188")
        execute_workflow(dsl_content, wait_for_completion=False)
    """
    await ctx.info(f"Executing workflow on {server_address}")
    
    try:
        # Convert DSL to JSON workflow
        await ctx.info("Converting DSL to ComfyUI JSON format...")
        parser = DSLParser()
        workflow_ast = parser.parse(dsl)
        
        converter = DslToJsonConverter()
        workflow_json = converter.convert(workflow_ast)
        
        await ctx.info(f"✓ Converted to JSON ({len(workflow_json)} nodes)")
        
        # Initialize ComfyUI client
        client = ComfyUIClient(server_address)
        
        # Submit workflow
        await ctx.info("Submitting workflow to ComfyUI...")
        prompt_id = await client.queue_prompt(workflow_json)
        await ctx.info(f"✓ Submitted with prompt_id: {prompt_id}")
        
        result = {
            "prompt_id": prompt_id,
            "server_address": server_address,
            "submitted_at": datetime.now().isoformat(),
            "status": "queued"
        }
        
        if not wait_for_completion:
            await ctx.info("Not waiting for completion (use get_job_status to check)")
            return result
        
        # Wait for completion
        await ctx.info(f"Waiting for completion (timeout: {timeout_seconds}s)...")
        
        start_time = asyncio.get_event_loop().time()
        while True:
            # Check if timeout exceeded
            if asyncio.get_event_loop().time() - start_time > timeout_seconds:
                result["status"] = "timeout"
                result["message"] = f"Execution exceeded {timeout_seconds}s timeout"
                await ctx.info("⚠️ Execution timed out")
                return result
            
            # Check execution status
            history = await client.get_history(prompt_id)
            
            if prompt_id in history:
                execution = history[prompt_id]
                status = execution.get("status", {})
                
                if status.get("completed", False):
                    result["status"] = "completed" if status.get("status_str") == "success" else "failed"
                    result["completed_at"] = datetime.now().isoformat()
                    result["execution_time"] = f"{asyncio.get_event_loop().time() - start_time:.1f}s"
                    
                    # Extract outputs
                    outputs = execution.get("outputs", {})
                    result["outputs"] = {}
                    
                    for node_id, output in outputs.items():
                        if "images" in output:
                            result["outputs"][node_id] = {
                                "type": "images",
                                "images": output["images"]
                            }
                    
                    if result["status"] == "completed":
                        await ctx.info(f"✅ Workflow completed successfully in {result['execution_time']}")
                        if result["outputs"]:
                            total_images = sum(len(out.get("images", [])) for out in result["outputs"].values())
                            await ctx.info(f"Generated {total_images} image(s)")
                    else:
                        await ctx.info(f"❌ Workflow failed: {status.get('messages', [])}")
                    
                    return result
            
            # Wait before checking again
            await asyncio.sleep(2)
            
    except Exception as e:
        raise ToolError(f"Failed to execute workflow: {e}")


@mcp.tool
async def get_job_status(
    ctx: Context,
    prompt_id: str,
    server_address: str = DEFAULT_COMFYUI_SERVER,
    download_images: bool = False,
    image_save_path: str = "outputs"
) -> Dict[str, Any]:
    """Get status and results of a ComfyUI job.
    
    Checks execution status and optionally downloads generated images.
    
    Args:
        prompt_id: The prompt ID returned by execute_workflow
        server_address: ComfyUI server address
        download_images: Whether to download generated images
        image_save_path: Directory to save images (relative to workflows/)
    
    Returns:
        Job status with completion info and image paths if downloaded
    
    Examples:
        get_job_status("12345-abcde-67890")
        get_job_status("12345-abcde-67890", download_images=True)
    """
    await ctx.info(f"Checking job status for {prompt_id}")
    
    try:
        client = ComfyUIClient(server_address)
        
        # Get execution history
        history = await client.get_history(prompt_id)
        
        if prompt_id not in history:
            # Check queue
            queue = await client.get_queue_status()
            
            # Check if still in queue
            for item in queue.get("queue_running", []) + queue.get("queue_pending", []):
                if item[1] == prompt_id:
                    return {
                        "prompt_id": prompt_id,
                        "status": "running" if item in queue.get("queue_running", []) else "queued",
                        "position": queue.get("queue_pending", []).index(item) + 1 if item in queue.get("queue_pending", []) else 0
                    }
            
            return {
                "prompt_id": prompt_id,
                "status": "not_found",
                "message": "Job not found in history or queue"
            }
        
        # Parse execution results
        execution = history[prompt_id]
        status = execution.get("status", {})
        
        result = {
            "prompt_id": prompt_id,
            "status": "completed" if status.get("completed", False) and status.get("status_str") == "success" else "failed" if status.get("completed", False) else "running",
            "messages": status.get("messages", [])
        }
        
        # Extract outputs if completed
        if status.get("completed", False):
            outputs = execution.get("outputs", {})
            result["outputs"] = {}
            
            for node_id, output in outputs.items():
                if "images" in output:
                    result["outputs"][node_id] = {
                        "type": "images",
                        "count": len(output["images"]),
                        "images": output["images"]
                    }
            
            if download_images and result["outputs"]:
                await ctx.info("Downloading generated images...")
                
                # Create save directory
                save_dir = Path(image_save_path)
                save_dir.mkdir(parents=True, exist_ok=True)
                
                downloaded_files = []
                
                for node_id, output in result["outputs"].items():
                    if output["type"] == "images":
                        for i, image_info in enumerate(output["images"]):
                            # Download image
                            image_data = await client.download_image(
                                image_info["filename"],
                                image_info["subfolder"],
                                image_info["type"]
                            )
                            
                            # Save with descriptive name
                            filename = f"{prompt_id}_{node_id}_{i:03d}_{image_info['filename']}"
                            file_path = save_dir / filename
                            
                            file_path.write_bytes(image_data)
                            downloaded_files.append(str(file_path))
                
                result["downloaded_files"] = downloaded_files
                await ctx.info(f"✓ Downloaded {len(downloaded_files)} image(s) to {save_dir}")
        
        return result
        
    except Exception as e:
        raise ToolError(f"Failed to get job status: {e}")


@mcp.tool
async def list_comfyui_queue(
    ctx: Context,
    server_address: str = DEFAULT_COMFYUI_SERVER
) -> Dict[str, Any]:
    """List current ComfyUI execution queue.
    
    Shows running and pending jobs in the ComfyUI queue.
    
    Args:
        server_address: ComfyUI server address
    
    Returns:
        Queue information with running and pending jobs
    
    Examples:
        list_comfyui_queue()
        list_comfyui_queue("192.168.1.100:8188")
    """
    await ctx.info(f"Fetching queue status from {server_address}")
    
    try:
        client = ComfyUIClient(server_address)
        queue = await client.get_queue_status()
        
        result = {
            "server_address": server_address,
            "queue_running": len(queue.get("queue_running", [])),
            "queue_pending": len(queue.get("queue_pending", [])),
            "running_jobs": [],
            "pending_jobs": []
        }
        
        # Format running jobs
        for item in queue.get("queue_running", []):
            result["running_jobs"].append({
                "prompt_id": item[1],
                "submitted_at": item[2],
                "position": 0  # Currently running
            })
        
        # Format pending jobs
        for i, item in enumerate(queue.get("queue_pending", [])):
            result["pending_jobs"].append({
                "prompt_id": item[1],
                "submitted_at": item[2],
                "position": i + 1
            })
        
        await ctx.info(f"✓ Queue: {result['queue_running']} running, {result['queue_pending']} pending")
        return result
        
    except Exception as e:
        raise ToolError(f"Failed to get queue status: {e}")


# ===== CLI SUPPORT =====

def main():
    """Main entry point for the CLI."""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(
        description="ComfyUI MCP Server - DSL-first workflow management"
    )
    parser.add_argument(
        "--comfyui-server",
        default="127.0.0.1:8188",
        help="ComfyUI server address (default: 127.0.0.1:8188)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"comfy-mcp {__version__}"
    )
    
    args = parser.parse_args()
    
    # Set global ComfyUI server if specified  
    global DEFAULT_COMFYUI_SERVER
    if args.comfyui_server != "127.0.0.1:8188":
        DEFAULT_COMFYUI_SERVER = args.comfyui_server
    
    # Configure logging
    import logging
    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=level)
    
    print(f"🎨 Starting ComfyUI MCP Server")
    print(f"   ComfyUI: {args.comfyui_server}")
    print(f"   Debug: {args.debug}")
    print(f"   Use Ctrl+C to stop")
    
    try:
        mcp.run()
    except KeyboardInterrupt:
        print("\n👋 ComfyUI MCP Server stopped")
        sys.exit(0)


# ===== MAIN =====

if __name__ == "__main__":
    main()
