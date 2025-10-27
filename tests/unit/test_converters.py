"""Unit tests for DSL converters."""

import pytest
from typing import Dict, Any

from comfy_mcp.dsl import (
    DSLParser, 
    DslToJsonConverter, 
    JsonToDslConverter,
    is_full_workflow_format,
    full_workflow_to_simplified
)


class TestDslToJsonConverter:
    """Test DSL to JSON conversion."""
    
    def test_convert_simple_workflow(
        self, 
        dsl_parser: DSLParser,
        dsl_to_json_converter: DslToJsonConverter,
        sample_dsl: str
    ):
        """Test converting DSL to JSON."""
        workflow_ast = dsl_parser.parse(sample_dsl)
        json_workflow = dsl_to_json_converter.convert(workflow_ast)
        
        assert isinstance(json_workflow, dict)
        assert len(json_workflow) == 7  # 7 nodes in sample workflow
        
        # Check node types are preserved
        node_types = [node["class_type"] for node in json_workflow.values()]
        expected_types = [
            "CheckpointLoaderSimple", "CLIPTextEncode", "CLIPTextEncode",
            "EmptyLatentImage", "KSampler", "VAEDecode", "SaveImage"
        ]
        assert all(t in node_types for t in expected_types)
    
    def test_convert_connections(
        self,
        dsl_parser: DSLParser, 
        dsl_to_json_converter: DslToJsonConverter
    ):
        """Test that connections are properly converted."""
        dsl = '''## Test

input_node: InputType
  param: value

output_node: OutputType
  connection_param: @input_node.output
'''
        
        workflow_ast = dsl_parser.parse(dsl)
        json_workflow = dsl_to_json_converter.convert(workflow_ast)
        
        # Find the output node
        output_node = None
        for node in json_workflow.values():
            if node["class_type"] == "OutputType":
                output_node = node
                break
        
        assert output_node is not None
        assert "connection_param" in output_node["inputs"]
        
        # Connection should be represented as [node_id, output_index]
        connection = output_node["inputs"]["connection_param"]
        assert isinstance(connection, list)
        assert len(connection) == 2
    
    def test_convert_property_types(
        self,
        dsl_parser: DSLParser,
        dsl_to_json_converter: DslToJsonConverter
    ):
        """Test that different property types are converted correctly."""
        dsl = '''## Test

test_node: TestType
  string_param: hello world
  int_param: 42
  float_param: 3.14
  bool_param: true
'''
        
        workflow_ast = dsl_parser.parse(dsl)
        json_workflow = dsl_to_json_converter.convert(workflow_ast)
        
        node = list(json_workflow.values())[0]
        inputs = node["inputs"]
        
        assert inputs["string_param"] == "hello world"
        assert inputs["int_param"] == 42
        assert inputs["float_param"] == 3.14
        assert inputs["bool_param"] is True


class TestJsonToDslConverter:
    """Test JSON to DSL conversion."""
    
    def test_convert_simple_workflow(
        self,
        json_to_dsl_converter: JsonToDslConverter,
        sample_json: Dict[str, Any]
    ):
        """Test converting JSON to DSL."""
        workflow_ast = json_to_dsl_converter.convert(sample_json)
        
        # Convert to string to verify structure
        dsl_text = str(workflow_ast)
        
        assert "CheckpointLoaderSimple" in dsl_text
        assert "CLIPTextEncode" in dsl_text
        assert "KSampler" in dsl_text
        assert "SaveImage" in dsl_text
        
        # Check that connections are converted to @ syntax
        assert "@" in dsl_text
    
    def test_convert_connections(
        self,
        json_to_dsl_converter: JsonToDslConverter
    ):
        """Test that JSON connections are converted to DSL @ syntax."""
        json_workflow = {
            "1": {
                "class_type": "InputNode",
                "inputs": {"param": "value"}
            },
            "2": {
                "class_type": "OutputNode", 
                "inputs": {"input_param": ["1", 0]}
            }
        }
        
        workflow_ast = json_to_dsl_converter.convert(json_workflow)
        dsl_text = str(workflow_ast)
        
        # Should contain connection syntax
        assert "@" in dsl_text
        # Verify the specific connection
        lines = dsl_text.split('\n')
        connection_line = next(line for line in lines if '@' in line)
        assert "input_param: @" in connection_line


class TestRoundTripConversion:
    """Test round-trip conversion between DSL and JSON."""
    
    def test_dsl_json_dsl_roundtrip(
        self,
        dsl_parser: DSLParser,
        dsl_to_json_converter: DslToJsonConverter, 
        json_to_dsl_converter: JsonToDslConverter,
        sample_dsl: str
    ):
        """Test DSL -> JSON -> DSL round trip."""
        # Parse original DSL
        original_ast = dsl_parser.parse(sample_dsl)
        
        # Convert to JSON
        json_workflow = dsl_to_json_converter.convert(original_ast)
        
        # Convert back to DSL
        roundtrip_ast = json_to_dsl_converter.convert(json_workflow)
        
        # Note: Section grouping may differ as JSON->DSL converter groups by node type
        # Focus on ensuring all nodes are preserved
        
        # Check that all original nodes are present
        original_nodes = []
        for section in original_ast.sections:
            for node in section.nodes:
                original_nodes.append(node.node_type)
        
        roundtrip_nodes = []
        for section in roundtrip_ast.sections:
            for node in section.nodes:
                roundtrip_nodes.append(node.node_type)
        
        assert sorted(original_nodes) == sorted(roundtrip_nodes)
    
    def test_json_dsl_json_roundtrip(
        self,
        dsl_parser: DSLParser,
        dsl_to_json_converter: DslToJsonConverter,
        json_to_dsl_converter: JsonToDslConverter, 
        sample_json: Dict[str, Any]
    ):
        """Test JSON -> DSL -> JSON round trip."""
        # Convert to DSL
        dsl_ast = json_to_dsl_converter.convert(sample_json)
        
        # Convert back to JSON
        roundtrip_json = dsl_to_json_converter.convert(dsl_ast)
        
        # Should have same number of nodes
        assert len(sample_json) == len(roundtrip_json)
        
        # Check that all node types are preserved
        original_types = [node["class_type"] for node in sample_json.values()]
        roundtrip_types = [node["class_type"] for node in roundtrip_json.values()]
        assert sorted(original_types) == sorted(roundtrip_types)


class TestWorkflowFormatHelpers:
    """Test workflow format detection and conversion helpers."""
    
    def test_is_full_workflow_format_simple(self, sample_json: Dict[str, Any]):
        """Test detecting simple workflow format."""
        assert not is_full_workflow_format(sample_json)
    
    def test_is_full_workflow_format_full(self):
        """Test detecting full workflow format."""
        full_format = {
            "workflow": {"nodes": []},
            "extra": {},
            "version": 0.4
        }
        assert is_full_workflow_format(full_format)
    
    def test_full_workflow_to_simplified(self, sample_json: Dict[str, Any]):
        """Test converting full format to simplified."""
        full_format = {
            "workflow": sample_json,
            "extra": {"info": "test"},
            "version": 0.4
        }
        
        simplified = full_workflow_to_simplified(full_format)
        assert simplified == sample_json