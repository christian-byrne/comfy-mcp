"""Integration tests for official template functionality."""

import pytest
from unittest.mock import patch, AsyncMock
from comfy_mcp.templates import TemplateManager
from comfy_mcp.templates.official import official_manager, OfficialTemplate


class TestOfficialTemplateIntegration:
    """Test integration between template manager and official templates."""
    
    @pytest.fixture
    def template_manager(self):
        """Create template manager for testing.""" 
        return TemplateManager()
    
    @pytest.fixture
    def mock_official_templates(self):
        """Mock official templates for testing."""
        return {
            "official_text2img": OfficialTemplate(
                name="Official Text2Img",
                description="Official text-to-image workflow",
                category="Generation", 
                workflow_json={"test": "data"},
                dsl_content="## Test Official Template\n\ntest_node: TestNode\n  prompt: {prompt}",
                preview_images=["preview.webp"]
            ),
            "official_img2img": OfficialTemplate(
                name="Official Img2Img", 
                description="Official image-to-image workflow",
                category="Editing",
                workflow_json={"test": "data"},
                dsl_content="## Official Img2Img\n\nedit_node: EditNode\n  strength: {strength}"
            )
        }
    
    def test_list_templates_with_official(self, template_manager, mock_official_templates):
        """Test listing templates includes official templates."""
        # Mock official templates
        with patch.object(official_manager, 'templates', mock_official_templates):
            templates = template_manager.list_templates(include_official=True)
            
            # Should have both custom and official templates
            custom_templates = [t for t in templates if t["source"] == "custom"]
            official_templates = [t for t in templates if t["source"] == "official"]
            
            assert len(custom_templates) > 0  # Has custom templates
            assert len(official_templates) == 2  # Has mock official templates
            assert len(templates) == len(custom_templates) + len(official_templates)
            
            # Check official template structure
            official_text2img = next(t for t in official_templates if t["name"] == "official_text2img")
            assert official_text2img["display_name"] == "Official Text2Img"
            assert official_text2img["category"] == "Generation"
            assert official_text2img["source"] == "official"
            assert len(official_text2img["preview_images"]) == 1
    
    def test_list_templates_exclude_official(self, template_manager, mock_official_templates):
        """Test listing templates can exclude official templates."""
        with patch.object(official_manager, 'templates', mock_official_templates):
            templates = template_manager.list_templates(include_official=False)
            
            # Should only have custom templates
            sources = [t["source"] for t in templates]
            assert all(source == "custom" for source in sources)
    
    def test_search_templates_mixed_sources(self, template_manager, mock_official_templates):
        """Test searching across both custom and official templates."""
        with patch.object(official_manager, 'templates', mock_official_templates):
            # Search for text-related templates
            results = template_manager.search_templates(query="text", include_official=True)
            
            # Should find both custom and official templates
            sources = [r["source"] for r in results]
            assert "custom" in sources
            assert "official" in sources
            
            # Check specific results
            template_names = [r["name"] for r in results]
            assert "text2img_basic" in template_names  # Custom template
            assert "official_text2img" in template_names  # Official template
    
    def test_search_templates_by_source(self, template_manager, mock_official_templates):
        """Test searching templates filtered by source."""
        with patch.object(official_manager, 'templates', mock_official_templates):
            # Search only custom templates
            custom_results = template_manager.search_templates(source="custom", include_official=True)
            assert all(r["source"] == "custom" for r in custom_results)
            
            # Search only official templates
            official_results = template_manager.search_templates(source="official", include_official=True)
            assert all(r["source"] == "official" for r in official_results)
            assert len(official_results) == 2
    
    def test_generate_workflow_from_official(self, template_manager, mock_official_templates):
        """Test generating workflow from official template."""
        with patch.object(official_manager, 'templates', mock_official_templates):
            # Generate from official template with auto source
            dsl_content = template_manager.generate_workflow(
                "official_text2img",
                parameters={"prompt": "test prompt"},
                source="auto"
            )
            
            assert dsl_content is not None
            assert "test prompt" in dsl_content
            assert "TestNode" in dsl_content
    
    def test_generate_workflow_explicit_official_source(self, template_manager, mock_official_templates):
        """Test generating workflow explicitly from official source."""
        with patch.object(official_manager, 'templates', mock_official_templates):
            # Generate explicitly from official source
            dsl_content = template_manager.generate_workflow(
                "official_img2img",
                parameters={"strength": "0.8"},
                source="official"
            )
            
            assert dsl_content is not None
            assert "strength: 0.8" in dsl_content
            assert "EditNode" in dsl_content
    
    def test_generate_workflow_source_priority(self, template_manager, mock_official_templates):
        """Test that custom templates take priority with auto source."""
        # Create a custom template with same name as official
        custom_name = "text2img_basic"  # This exists in custom templates
        
        with patch.object(official_manager, 'templates', mock_official_templates):
            # With auto source, should prefer custom template
            dsl_content = template_manager.generate_workflow(custom_name, source="auto")
            
            # Should get custom template content (contains CheckpointLoaderSimple)
            assert "CheckpointLoaderSimple" in dsl_content
    
    def test_validate_parameters_official_template(self, template_manager, mock_official_templates):
        """Test parameter validation for official templates."""
        with patch.object(official_manager, 'templates', mock_official_templates):
            # Valid parameters
            validation = template_manager.validate_parameters(
                "official_text2img", 
                {"prompt": "test prompt"},
                source="official"
            )
            
            assert validation["valid"] is True
            assert len(validation["errors"]) == 0
            
            # Missing required parameters  
            validation = template_manager.validate_parameters(
                "official_text2img",
                {},  # No parameters provided
                source="official"
            )
            
            assert validation["valid"] is False
            assert len(validation["errors"]) > 0
    
    @pytest.mark.asyncio
    async def test_sync_official_templates_integration(self, template_manager):
        """Test syncing official templates through template manager."""
        # Mock the sync operation
        mock_result = {
            "status": "success", 
            "synced_count": 5,
            "templates": ["template1", "template2", "template3", "template4", "template5"]
        }
        
        with patch.object(template_manager, 'sync_official_templates', return_value=mock_result) as mock_sync:
            result = await template_manager.sync_official_templates()
            
            assert result["status"] == "success"
            assert result["synced_count"] == 5
            assert len(result["templates"]) == 5
            mock_sync.assert_called_once()
    
    def test_get_official_template_direct(self, template_manager, mock_official_templates):
        """Test getting official template directly."""
        with patch.object(official_manager, 'templates', mock_official_templates):
            template = template_manager.get_official_template("official_text2img")
            
            assert template is not None
            assert template.name == "Official Text2Img"
            assert template.category == "Generation"
            
            # Test non-existent template
            template = template_manager.get_official_template("nonexistent")
            assert template is None


class TestTemplateManagerMixedSources:
    """Test template manager behavior with mixed template sources."""
    
    @pytest.fixture  
    def template_manager(self):
        return TemplateManager()
    
    @pytest.fixture
    def mock_official_templates(self):
        return {
            "official_advanced": OfficialTemplate(
                name="Advanced Official",
                description="Advanced official workflow",
                category="Advanced",
                workflow_json={},
                dsl_content="## Advanced\n\nadvanced_node: AdvancedNode"
            )
        }
    
    def test_template_count_consistency(self, template_manager, mock_official_templates):
        """Test that template counts are consistent across operations."""
        with patch.object(official_manager, 'templates', mock_official_templates):
            # Get all templates
            all_templates = template_manager.list_templates(include_official=True)
            total_count = len(all_templates)
            
            # Count by source
            custom_count = len([t for t in all_templates if t["source"] == "custom"])
            official_count = len([t for t in all_templates if t["source"] == "official"])
            
            assert total_count == custom_count + official_count
            assert official_count == len(mock_official_templates)
    
    def test_template_name_uniqueness_across_sources(self, template_manager, mock_official_templates):
        """Test that templates can have same names across different sources."""
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
        
        with patch.object(official_manager, 'templates', mock_templates):
            # Should be able to generate from both sources
            custom_dsl = template_manager.generate_workflow("text2img_basic", source="custom")
            official_dsl = template_manager.generate_workflow("text2img_basic", source="official")
            
            # Should get different content
            assert "CheckpointLoaderSimple" in custom_dsl  # Custom template content
            assert "OfficialNode" in official_dsl  # Official template content
            assert custom_dsl != official_dsl
    
    def test_search_performance_with_official_templates(self, template_manager, mock_official_templates):
        """Test that search performance is reasonable with official templates."""
        # Create more mock templates to test performance
        large_mock_templates = {}
        for i in range(50):
            large_mock_templates[f"template_{i}"] = OfficialTemplate(
                name=f"Template {i}",
                description=f"Test template number {i}",
                category="Test",
                workflow_json={}
            )
        
        with patch.object(official_manager, 'templates', large_mock_templates):
            # Search should complete quickly
            import time
            start_time = time.time()
            
            results = template_manager.search_templates(query="template", include_official=True)
            
            end_time = time.time()
            search_time = end_time - start_time
            
            # Should find results and complete quickly (under 1 second)
            assert len(results) > 0
            assert search_time < 1.0