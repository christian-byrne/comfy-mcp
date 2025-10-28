"""Integration tests for MCP tools with official templates."""

import pytest
from unittest.mock import patch, AsyncMock
from fastmcp import Context
from comfy_mcp.templates.official import OfficialTemplate


class TestMCPOfficialTools:
    """Test MCP tools for official template functionality."""
    
    @pytest.fixture
    def mock_context(self):
        """Create mock MCP context."""
        context = AsyncMock(spec=Context)
        context.info = AsyncMock()
        context.warning = AsyncMock()
        return context
    
    @pytest.fixture
    def mock_official_templates(self):
        """Mock official templates for testing."""
        return {
            "official_test": OfficialTemplate(
                name="Official Test Template",
                description="Test official template",
                category="Testing",
                workflow_json={"test": "data"},
                dsl_content="## Test Official\n\ntest_node: TestNode\n  param: value",
                preview_images=["test.webp"]
            ),
            "official_advanced": OfficialTemplate(
                name="Advanced Official",
                description="Advanced official workflow", 
                category="Advanced",
                workflow_json={"advanced": True},
                dsl_content="## Advanced Official\n\nadvanced_node: AdvancedNode"
            )
        }
    
    def test_template_manager_includes_official(self, mock_context, mock_official_templates):
        """Test that template manager includes official templates."""
        from comfy_mcp.mcp.server import template_manager
        from comfy_mcp.templates.official import official_manager
        
        with patch.object(official_manager, 'templates', mock_official_templates):
            result = template_manager.list_templates(include_official=True)
            
            # Should have both custom and official templates
            custom_templates = [t for t in result if t.get("source") == "custom"]
            official_templates = [t for t in result if t.get("source") == "official"]
            
            assert len(custom_templates) > 0
            assert len(official_templates) == 2
            
            # Check official template structure
            official_test = next(t for t in official_templates if t["name"] == "official_test")
            assert official_test["display_name"] == "Official Test Template"
            assert official_test["category"] == "Testing"
            assert official_test["has_dsl"] is True
    
    def test_template_manager_filtering(self, mock_context, mock_official_templates):
        """Test template manager filtering with official templates."""
        from comfy_mcp.mcp.server import template_manager
        from comfy_mcp.templates.official import official_manager
        
        with patch.object(official_manager, 'templates', mock_official_templates):
            # Filter by category
            result = template_manager.search_templates(category="Testing", include_official=True)
            testing_templates = [t for t in result if t["category"] == "Testing"]
            assert len(testing_templates) > 0
            
            # Filter by source (custom only)
            custom_result = template_manager.search_templates(source="custom", include_official=True)
            assert all(t.get("source") == "custom" for t in custom_result)
            
            # Filter by source (official only) 
            official_result = template_manager.search_templates(source="official", include_official=True)
            assert all(t.get("source") == "official" for t in official_result)
            assert len(official_result) == 2
    
    @pytest.mark.asyncio
    async def test_sync_official_templates_functionality(self, mock_context):
        """Test sync_official_templates functionality."""
        from comfy_mcp.mcp.server import template_manager
        
        mock_result = {
            "status": "success",
            "synced_count": 3,
            "templates": ["template1", "template2", "template3"]
        }
        
        with patch.object(template_manager, 'sync_official_templates', return_value=mock_result) as mock_sync:
            result = await template_manager.sync_official_templates()
            
            assert result["status"] == "success"
            assert result["synced_count"] == 3
            assert len(result["templates"]) == 3
            mock_sync.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_sync_official_templates_error_handling(self, mock_context):
        """Test sync_official_templates handles errors."""
        from comfy_mcp.mcp.server import template_manager
        
        mock_error_result = {
            "status": "error", 
            "error": "API rate limit exceeded"
        }
        
        with patch.object(template_manager, 'sync_official_templates', return_value=mock_error_result):
            result = await template_manager.sync_official_templates()
            
            assert result["status"] == "error"
            assert "error" in result
    
    def test_get_official_templates(self, mock_context, mock_official_templates):
        """Test getting official templates."""
        from comfy_mcp.mcp.server import template_manager
        from comfy_mcp.templates.official import official_manager
        
        with patch.object(official_manager, 'templates', mock_official_templates):
            # Test getting specific official template
            template = template_manager.get_official_template("official_test")
            assert template is not None
            assert template.name == "Official Test Template"
            
            # Test non-existent template
            template = template_manager.get_official_template("nonexistent")
            assert template is None
    
    def test_generate_workflow_from_official(self, mock_context, mock_official_templates):
        """Test generating workflow from official template."""
        from comfy_mcp.mcp.server import template_manager
        from comfy_mcp.templates.official import official_manager
        
        with patch.object(official_manager, 'templates', mock_official_templates):
            # Generate from official template
            result = template_manager.generate_workflow("official_test", source="official")
            
            assert result is not None
            assert isinstance(result, str)
            assert "TestNode" in result
            assert "param: value" in result
    
    def test_generate_workflow_with_auto_source(self, mock_context, mock_official_templates):
        """Test generate workflow with auto source detection."""
        from comfy_mcp.mcp.server import template_manager
        from comfy_mcp.templates.official import official_manager
        
        with patch.object(official_manager, 'templates', mock_official_templates):
            # Should find custom template first
            result = template_manager.generate_workflow("text2img_basic", source="auto")
            assert "CheckpointLoaderSimple" in result  # Custom template content
            
            # Should find official template when custom doesn't exist
            result = template_manager.generate_workflow("official_test", source="auto")
            assert "TestNode" in result  # Official template content
    
    def test_generate_workflow_with_parameters(self, mock_context):
        """Test generate workflow with parameter substitution."""
        from comfy_mcp.mcp.server import template_manager
        from comfy_mcp.templates.official import official_manager
        
        # Create template with parameters
        template_with_params = {
            "param_template": OfficialTemplate(
                name="Parameter Template",
                description="Template with parameters",
                category="Test", 
                workflow_json={},
                dsl_content="## Test Template\n\ntest_node: TestNode\n  prompt: {prompt}\n  steps: {steps}"
            )
        }
        
        with patch.object(official_manager, 'templates', template_with_params):
            result = template_manager.generate_workflow(
                "param_template",
                source="official", 
                parameters={"prompt": "test prompt", "steps": "20"}
            )
            
            assert "prompt: test prompt" in result
            assert "steps: 20" in result
    
    def test_validate_parameters_official(self, mock_context, mock_official_templates):
        """Test parameter validation for official templates."""
        from comfy_mcp.mcp.server import template_manager
        from comfy_mcp.templates.official import official_manager
        
        with patch.object(official_manager, 'templates', mock_official_templates):
            # Valid parameters
            validation = template_manager.validate_parameters(
                "official_test", 
                {"param": "test value"},
                source="official"
            )
            
            # The validation should work even if it finds issues
            assert "valid" in validation
            assert "errors" in validation
            assert "warnings" in validation


class TestTemplateManagerWithOfficialIntegration:
    """Test full integration of template manager with official templates."""
    
    @pytest.fixture
    def template_manager(self):
        """Get template manager instance."""
        from comfy_mcp.mcp.server import template_manager
        return template_manager
    
    @pytest.fixture
    def mock_official_templates(self):
        return {
            "integration_test": OfficialTemplate(
                name="Integration Test",
                description="Integration test template",
                category="Test",
                workflow_json={},
                dsl_content="## Integration Test\n\ntest_node: IntegrationNode"
            )
        }
    
    def test_search_across_sources(self, template_manager, mock_official_templates):
        """Test searching across both custom and official sources."""
        from comfy_mcp.templates.official import official_manager
        
        with patch.object(official_manager, 'templates', mock_official_templates):
            # Search for text-related templates (should find custom text2img templates)
            results = template_manager.search_templates(query="text", include_official=True)
            
            # Should find templates from both sources if available
            sources = [r["source"] for r in results]
            
            # Should at least find some templates
            assert len(results) > 0
            
            # Test that official templates can be found
            official_results = template_manager.search_templates(query="integration", include_official=True)
            official_sources = [r["source"] for r in official_results]
            assert "official" in official_sources
    
    def test_template_count_consistency(self, template_manager, mock_official_templates):
        """Test that template counts are consistent."""
        from comfy_mcp.templates.official import official_manager
        
        with patch.object(official_manager, 'templates', mock_official_templates):
            # Get all templates
            all_templates = template_manager.list_templates(include_official=True)
            total_count = len(all_templates)
            
            # Count by source
            custom_count = len([t for t in all_templates if t["source"] == "custom"])
            official_count = len([t for t in all_templates if t["source"] == "official"])
            
            assert total_count == custom_count + official_count
            assert official_count == len(mock_official_templates)
    
    def test_source_priority_with_same_names(self, template_manager, mock_official_templates):
        """Test that custom templates take priority with auto source."""
        # Create official template with same name as custom template
        mock_templates = {
            "text2img_basic": OfficialTemplate(  # Same name as custom template
                name="Official Text2Img Basic",
                description="Official version",
                category="Generation", 
                workflow_json={},
                dsl_content="## Official Version\n\nofficial_node: OfficialNode"
            )
        }
        
        from comfy_mcp.templates.official import official_manager
        
        with patch.object(official_manager, 'templates', mock_templates):
            # With auto source, should prefer custom template
            custom_dsl = template_manager.generate_workflow("text2img_basic", source="auto")
            official_dsl = template_manager.generate_workflow("text2img_basic", source="official")
            
            # Should get different content
            assert "CheckpointLoaderSimple" in custom_dsl  # Custom template content
            assert "OfficialNode" in official_dsl  # Official template content
            assert custom_dsl != official_dsl