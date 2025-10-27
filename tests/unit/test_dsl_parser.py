"""Unit tests for DSL parser."""

import pytest
from comfy_mcp.dsl import DSLParser, Workflow, Section, Node, Property, Connection


class TestDSLParser:
    """Test DSL parser functionality."""
    
    def test_parse_simple_workflow(self, dsl_parser: DSLParser, sample_dsl: str):
        """Test parsing a simple workflow."""
        workflow = dsl_parser.parse(sample_dsl)
        
        assert isinstance(workflow, Workflow)
        assert len(workflow.sections) == 4
        
        # Check section names
        section_names = [s.header for s in workflow.sections]
        assert "Model Loading" in section_names
        assert "Text Conditioning" in section_names
        assert "Generation" in section_names
        assert "Output" in section_names
    
    def test_parse_node_with_properties(self, dsl_parser: DSLParser):
        """Test parsing a node with various property types."""
        dsl = '''## Test

node1: NodeType
  text_prop: hello world
  int_prop: 42
  float_prop: 3.14
  bool_prop: true
  connection_prop: @other.output
'''
        
        workflow = dsl_parser.parse(dsl)
        section = workflow.sections[0]
        node = section.nodes[0]
        
        assert node.name == "node1"
        assert node.node_type == "NodeType"
        assert len(node.properties) == 5
        
        props_by_name = {p.name: p.value for p in node.properties}
        assert props_by_name["text_prop"] == "hello world"
        assert props_by_name["int_prop"] == 42
        assert props_by_name["float_prop"] == 3.14
        assert props_by_name["bool_prop"] is True
        assert isinstance(props_by_name["connection_prop"], Connection)
        assert props_by_name["connection_prop"].node == "other"
        assert props_by_name["connection_prop"].output == "output"
    
    def test_parse_connections(self, dsl_parser: DSLParser):
        """Test parsing connections between nodes."""
        dsl = '''## Test

input_node: InputType
  param: value

output_node: OutputType
  input_param: @input_node.output
  another_input: @input_node.model
'''
        
        workflow = dsl_parser.parse(dsl)
        section = workflow.sections[0]
        output_node = section.nodes[1]
        
        connections = [p for p in output_node.properties if isinstance(p.value, Connection)]
        assert len(connections) == 2
        
        conn1 = connections[0].value
        assert conn1.node == "input_node"
        assert conn1.output == "output"
        
        conn2 = connections[1].value  
        assert conn2.node == "input_node"
        assert conn2.output == "model"
    
    def test_parse_empty_workflow(self, dsl_parser: DSLParser):
        """Test parsing an empty workflow."""
        workflow = dsl_parser.parse("")
        assert isinstance(workflow, Workflow)
        assert len(workflow.sections) == 0
    
    def test_parse_invalid_syntax(self, dsl_parser: DSLParser):
        """Test parsing invalid DSL syntax."""
        invalid_dsl = '''## Test

invalid syntax here
not a valid node definition
'''
        
        with pytest.raises(Exception):
            dsl_parser.parse(invalid_dsl)
    
    def test_workflow_string_representation(self, dsl_parser: DSLParser, sample_dsl: str):
        """Test that workflow can be converted back to string."""
        workflow = dsl_parser.parse(sample_dsl)
        workflow_str = str(workflow)
        
        # Should be able to parse the string representation
        workflow2 = dsl_parser.parse(workflow_str)
        
        assert len(workflow.sections) == len(workflow2.sections)
        assert workflow.sections[0].header == workflow2.sections[0].header
        
    def test_node_string_representation(self, dsl_parser: DSLParser):
        """Test node string representation."""
        dsl = '''## Test

test_node: TestType
  param1: value1
  param2: 42
'''
        
        workflow = dsl_parser.parse(dsl)
        node = workflow.sections[0].nodes[0]
        node_str = str(node)
        
        assert "test_node: TestType" in node_str
        assert "param1: value1" in node_str
        assert "param2: 42" in node_str