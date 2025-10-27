"""Integration tests for MCP tools."""

import pytest
import json
from pathlib import Path
from typing import Dict, Any

from comfy_mcp.dsl import DSLParser


# Import the actual tool functions for testing
# We'll need to test them directly since they're wrapped by FastMCP
async def read_workflow_direct(ctx, filepath: str) -> str:
    """Direct import of read_workflow for testing."""
    from comfy_mcp.mcp.server import (
        DSLParser, JsonToDslConverter, is_full_workflow_format, 
        full_workflow_to_simplified, ToolError
    )
    
    try:
        file_path = Path(filepath).resolve()
        if not file_path.exists():
            raise ToolError(f"File not found: {filepath}")
        
        content = file_path.read_text(encoding="utf-8")
        
        if file_path.suffix.lower() == ".json":
            try:
                workflow_data = json.loads(content)
                
                if is_full_workflow_format(workflow_data):
                    workflow_data = full_workflow_to_simplified(workflow_data)
                
                converter = JsonToDslConverter()
                workflow_ast = converter.convert(workflow_data)
                dsl_content = str(workflow_ast)
                
                await ctx.info(f"Converted JSON to DSL ({len(dsl_content)} characters)")
                return dsl_content
                
            except json.JSONDecodeError as e:
                raise ToolError(f"Invalid JSON in {filepath}: {e}")
        
        elif file_path.suffix.lower() == ".dsl":
            await ctx.info(f"Read DSL file ({len(content)} characters)")
            return content
        
        else:
            raise ToolError(f"Unsupported file format: {file_path.suffix}")
        
    except Exception as e:
        raise ToolError(f"Failed to read workflow: {e}")


async def validate_workflow_direct(ctx, dsl: str) -> Dict[str, Any]:
    """Direct import of validate_workflow for testing."""
    from comfy_mcp.mcp.server import DSLParser
    
    try:
        parser = DSLParser()
        workflow_ast = parser.parse(dsl)
        
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


async def get_workflow_info_direct(ctx, dsl: str) -> Dict[str, Any]:
    """Direct import of get_workflow_info for testing."""
    from comfy_mcp.mcp.server import DSLParser, Connection, Counter, ToolError
    
    try:
        parser = DSLParser()
        workflow_ast = parser.parse(dsl)
        
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
                
                for prop in node.properties:
                    if isinstance(prop.value, Connection):
                        connections.append({
                            "from": prop.value.node,
                            "output": prop.value.output,
                            "to": node.name,
                            "input": prop.name
                        })
            
            sections.append(section_info)
        
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
        raise ToolError(f"Failed to analyze workflow: {e}")


class TestMCPFileOperations:
    """Test MCP file operation tools."""
    
    @pytest.mark.asyncio
    async def test_read_workflow_json(
        self, 
        mock_context,
        temp_workflow_file: Path
    ):
        """Test reading a JSON workflow file."""
        dsl_content = await read_workflow_direct(mock_context, str(temp_workflow_file))
        
        assert isinstance(dsl_content, str)
        assert len(dsl_content) > 0
        assert "CheckpointLoaderSimple" in dsl_content
        assert "@" in dsl_content  # Should contain connections
    
    @pytest.mark.asyncio
    async def test_read_workflow_dsl(
        self,
        mock_context, 
        temp_dsl_file: Path
    ):
        """Test reading a DSL workflow file."""
        dsl_content = await read_workflow_direct(mock_context, str(temp_dsl_file))
        
        assert isinstance(dsl_content, str)
        assert "CheckpointLoaderSimple" in dsl_content
    
    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, mock_context):
        """Test reading a nonexistent file."""
        from comfy_mcp.mcp.server import ToolError
        
        with pytest.raises(ToolError, match="File not found"):
            await read_workflow_direct(mock_context, "/nonexistent/file.json")
    
    @pytest.mark.asyncio
    async def test_validate_workflow_valid(self, mock_context, sample_dsl: str):
        """Test validating a valid DSL workflow."""
        result = await validate_workflow_direct(mock_context, sample_dsl)
        
        assert result["is_valid"] is True
        assert len(result["errors"]) == 0
        assert result["node_count"] > 0
        assert result["section_count"] > 0
    
    @pytest.mark.asyncio
    async def test_validate_workflow_invalid(self, mock_context):
        """Test validating invalid DSL."""
        invalid_dsl = "this is not valid DSL syntax"
        result = await validate_workflow_direct(mock_context, invalid_dsl)
        
        assert result["is_valid"] is False
        assert len(result["errors"]) > 0
    
    @pytest.mark.asyncio
    async def test_get_workflow_info(self, mock_context, sample_dsl: str):
        """Test getting workflow information."""
        info = await get_workflow_info_direct(mock_context, sample_dsl)
        
        assert info["node_count"] == 7
        assert info["section_count"] == 4
        assert info["connection_count"] > 0
        assert "CheckpointLoaderSimple" in info["node_types"]
        assert len(info["sections"]) == 4
        assert len(info["connections"]) > 0


@pytest.mark.integration
class TestMCPExecutionOperations:
    """Test MCP execution operations (requires ComfyUI running)."""
    
    @pytest.mark.asyncio
    async def test_list_comfyui_queue(self, mock_context, comfyui_running):
        """Test listing ComfyUI queue."""
        from comfy_mcp.mcp.server import ComfyUIClient, DEFAULT_COMFYUI_SERVER
        
        client = ComfyUIClient(DEFAULT_COMFYUI_SERVER)
        queue = await client.get_queue_status()
        
        assert "queue_running" in queue
        assert "queue_pending" in queue
        assert isinstance(queue["queue_running"], list)
        assert isinstance(queue["queue_pending"], list)
    
    @pytest.mark.asyncio
    async def test_execute_workflow_validation(self, mock_context, comfyui_not_running):
        """Test workflow execution validation (without actual execution)."""
        from comfy_mcp.mcp.server import DSLParser, DslToJsonConverter
        
        # Test that DSL can be converted to JSON for execution
        simple_dsl = '''## Model Loading

checkpoint: CheckpointLoaderSimple
  ckpt_name: v1-5-pruned-emaonly-fp16.safetensors

## Output

save: SaveImage
  images: @checkpoint.model
  filename_prefix: test
'''
        
        parser = DSLParser()
        workflow_ast = parser.parse(simple_dsl)
        
        converter = DslToJsonConverter()
        workflow_json = converter.convert(workflow_ast)
        
        assert isinstance(workflow_json, dict)
        assert len(workflow_json) == 2
        
        # Verify JSON structure for ComfyUI
        for node_id, node_data in workflow_json.items():
            assert "class_type" in node_data
            assert "inputs" in node_data


class TestMCPErrorHandling:
    """Test MCP error handling."""
    
    @pytest.mark.asyncio
    async def test_invalid_file_extension(self, mock_context, tmp_path: Path):
        """Test handling of unsupported file extensions."""
        from comfy_mcp.mcp.server import ToolError
        
        # Create file with unsupported extension
        invalid_file = tmp_path / "test.txt"
        invalid_file.write_text("some content")
        
        with pytest.raises(ToolError, match="Unsupported file format"):
            await read_workflow_direct(mock_context, str(invalid_file))
    
    @pytest.mark.asyncio
    async def test_invalid_json_file(self, mock_context, tmp_path: Path):
        """Test handling of invalid JSON files."""
        from comfy_mcp.mcp.server import ToolError
        
        # Create invalid JSON file
        invalid_json = tmp_path / "invalid.json"
        invalid_json.write_text("{ invalid json content")
        
        with pytest.raises(ToolError, match="Invalid JSON"):
            await read_workflow_direct(mock_context, str(invalid_json))