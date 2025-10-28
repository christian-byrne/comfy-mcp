"""Unit tests for official template functionality."""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock
from comfy_mcp.templates.official import OfficialTemplateManager, OfficialTemplate


class TestOfficialTemplateManager:
    """Test official template manager functionality."""
    
    @pytest.fixture
    def manager(self):
        """Create official template manager for testing."""
        return OfficialTemplateManager()
    
    @pytest.fixture
    def sample_template_list(self):
        """Sample GitHub API response for template list."""
        return [
            {
                "name": "sample_workflow.json",  # Changed from test_workflow to avoid exclusion
                "type": "file",
                "size": 1024,  # Add size to pass filtering
                "download_url": "https://api.github.com/test.json"
            },
            {
                "name": "sample_workflow.webp", 
                "type": "file",
                "size": 2048,
                "download_url": "https://api.github.com/test.webp"
            },
            {
                "name": "another_template.json",
                "type": "file",
                "size": 1500,  # Add size to pass filtering
                "download_url": "https://api.github.com/another.json"
            }
        ]
    
    @pytest.fixture
    def sample_workflow_json(self):
        """Sample workflow JSON in full format."""
        return {
            "id": "test-workflow-id",
            "revision": 0,
            "last_node_id": 3,
            "last_link_id": 2,
            "nodes": [
                {
                    "id": 1,
                    "type": "TestNode",
                    "inputs": [{"name": "input1", "type": "STRING"}],
                    "widgets_values": ["test value"]
                },
                {
                    "id": 2,
                    "type": "OutputNode", 
                    "inputs": [{"name": "input1", "type": "IMAGE"}]
                }
            ],
            "links": [
                [1, 1, 0, 2, 0]  # [link_id, source_node, source_slot, target_node, target_slot]
            ]
        }
    
    @pytest.mark.asyncio
    async def test_fetch_template_list(self, manager):
        """Test fetching template list from GitHub API."""
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=[{"name": "test.json"}])
            
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session.return_value)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_session.return_value.get.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await manager.fetch_template_list()
            
            assert result == [{"name": "test.json"}]
            mock_session.return_value.get.assert_called_once_with(
                f"{manager.GITHUB_API_BASE}/{manager.TEMPLATES_PATH}"
            )
    
    @pytest.mark.asyncio
    async def test_fetch_template_list_error(self, manager):
        """Test error handling when GitHub API fails."""
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 404
            
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session.return_value)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_session.return_value.get.return_value.__aexit__ = AsyncMock(return_value=None)
            
            with pytest.raises(Exception, match="Failed to fetch templates: 404"):
                await manager.fetch_template_list()
    
    @pytest.mark.asyncio
    async def test_download_workflow_json(self, manager, sample_workflow_json):
        """Test downloading workflow JSON file."""
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=json.dumps(sample_workflow_json))
            
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session.return_value)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_session.return_value.get.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await manager.download_workflow_json("https://test.com/workflow.json")
            
            assert result == sample_workflow_json
    
    @pytest.mark.asyncio
    async def test_sync_official_templates(self, manager, sample_template_list, sample_workflow_json):
        """Test syncing official templates."""
        # Mock the API calls
        with patch.object(manager, 'fetch_template_list', return_value=sample_template_list), \
             patch.object(manager, 'download_workflow_json', return_value=sample_workflow_json), \
             patch.object(manager, '_cache_templates', return_value=None):
            
            # Mock the DSL conversion
            with patch('comfy_mcp.dsl.is_full_workflow_format', return_value=True), \
                 patch('comfy_mcp.dsl.full_workflow_to_simplified', return_value={"1": {"class_type": "TestNode"}}):
                
                result = await manager.sync_official_templates()
                
                assert len(result) == 2  # Two JSON files in sample data
                assert "sample_workflow" in result
                assert "another_template" in result
                
                # Check template structure
                template = result["sample_workflow"]
                assert isinstance(template, OfficialTemplate)
                assert template.name == "Sample Workflow"
                assert template.category == "Miscellaneous"
                assert template.dsl_content is not None
                assert len(template.preview_images) == 1  # Should find the .webp file
    
    @pytest.mark.asyncio
    async def test_sync_handles_conversion_errors(self, manager, sample_template_list, sample_workflow_json):
        """Test sync handles DSL conversion errors gracefully."""
        with patch.object(manager, 'fetch_template_list', return_value=sample_template_list), \
             patch.object(manager, 'download_workflow_json', return_value=sample_workflow_json), \
             patch.object(manager, '_cache_templates', return_value=None):
            
            # Mock conversion to raise an error
            with patch('comfy_mcp.dsl.is_full_workflow_format', return_value=True), \
                 patch('comfy_mcp.dsl.full_workflow_to_simplified', side_effect=Exception("Conversion failed")):
                
                result = await manager.sync_official_templates()
                
                # Should still create templates but without DSL content
                assert len(result) == 2
                for template in result.values():
                    assert template.dsl_content is None
    
    @pytest.mark.asyncio  
    async def test_cache_templates(self, manager, tmp_path):
        """Test template caching functionality."""
        # Set cache directory to temp path
        manager.cache_dir = tmp_path
        
        templates = {
            "test": OfficialTemplate(
                name="Test Template",
                description="Test description", 
                category="Test",
                workflow_json={"test": "data"},
                dsl_content="test dsl"
            )
        }
        
        await manager._cache_templates(templates)
        
        cache_file = tmp_path / "official_templates.json"
        assert cache_file.exists()
        
        # Load and verify cache content
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
        
        assert "templates" in cache_data
        assert "test" in cache_data["templates"]
        assert cache_data["templates"]["test"]["name"] == "Test Template"
    
    @pytest.mark.asyncio
    async def test_load_cached_templates(self, manager, tmp_path):
        """Test loading templates from cache."""
        # Set cache directory to temp path
        manager.cache_dir = tmp_path
        
        # Create cache file
        cache_data = {
            "templates": {
                "cached_template": {
                    "name": "Cached Template",
                    "description": "From cache",
                    "category": "Test", 
                    "workflow_json": {"cached": True},
                    "dsl_content": "cached dsl",
                    "preview_images": [],
                    "source_url": "",
                    "last_updated": ""
                }
            },
            "last_sync": 1234567890
        }
        
        cache_file = tmp_path / "official_templates.json"
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)
        
        result = await manager._load_cached_templates()
        
        assert len(result) == 1
        assert "cached_template" in result
        assert result["cached_template"].name == "Cached Template"
    
    def test_infer_category(self, manager):
        """Test category inference from template names."""
        test_cases = [
            ("text2img_basic", "Text-to-Image"),
            ("image_editing_tool", "Image-to-Image"), 
            ("video_generation", "Video Generation"),
            ("inpainting_workflow", "Image Editing"),
            ("chat_assistant", "AI Chat"),
            ("audio_processor", "Audio"),
            ("3d_model_gen", "3D Generation"),
            ("random_workflow", "Miscellaneous")
        ]
        
        for template_name, expected_category in test_cases:
            result = manager._infer_category(template_name)
            assert result == expected_category
    
    def test_get_template(self, manager):
        """Test getting specific template."""
        # Add a template to manager
        test_template = OfficialTemplate(
            name="Test",
            description="Test template",
            category="Test",
            workflow_json={}
        )
        manager.templates["test"] = test_template
        
        result = manager.get_template("test")
        assert result == test_template
        
        # Test non-existent template
        result = manager.get_template("nonexistent")
        assert result is None
    
    def test_list_templates(self, manager):
        """Test listing all templates."""
        # Add templates to manager
        templates = {
            "template1": OfficialTemplate(
                name="Template 1",
                description="First template",
                category="Generation",
                workflow_json={},
                dsl_content="dsl content"
            ),
            "template2": OfficialTemplate(
                name="Template 2", 
                description="Second template",
                category="Editing",
                workflow_json={},
                dsl_content=None
            )
        }
        manager.templates = templates
        
        result = manager.list_templates()
        
        assert len(result) == 2
        assert result[0]["name"] == "template1"
        assert result[0]["display_name"] == "Template 1"
        assert result[0]["source"] == "official"
        assert result[0]["has_dsl"] is True
        assert result[1]["has_dsl"] is False
    
    def test_search_templates(self, manager):
        """Test searching templates."""
        # Add templates to manager
        templates = {
            "text_gen": OfficialTemplate(
                name="Text Generator",
                description="Generate text from prompts", 
                category="Generation",
                workflow_json={}
            ),
            "image_edit": OfficialTemplate(
                name="Image Editor",
                description="Edit images with AI",
                category="Editing", 
                workflow_json={}
            )
        }
        manager.templates = templates
        
        # Test query search
        result = manager.search_templates(query="text")
        assert len(result) == 1
        assert result[0]["name"] == "text_gen"
        
        # Test category search
        result = manager.search_templates(category="editing")
        assert len(result) == 1 
        assert result[0]["name"] == "image_edit"
        
        # Test combined search
        result = manager.search_templates(query="generate", category="generation")
        assert len(result) == 1
        assert result[0]["name"] == "text_gen"


class TestOfficialTemplate:
    """Test OfficialTemplate dataclass."""
    
    def test_create_template(self):
        """Test creating official template."""
        template = OfficialTemplate(
            name="Test Template",
            description="A test template",
            category="Testing",
            workflow_json={"nodes": []},
            dsl_content="test dsl",
            preview_images=["image1.webp"],
            source_url="https://github.com/test",
            last_updated="2024-01-01"
        )
        
        assert template.name == "Test Template"
        assert template.description == "A test template"
        assert template.category == "Testing"
        assert template.workflow_json == {"nodes": []}
        assert template.dsl_content == "test dsl"
        assert template.preview_images == ["image1.webp"]
        assert template.source_url == "https://github.com/test"
        assert template.last_updated == "2024-01-01"
    
    def test_template_defaults(self):
        """Test template with default values.""" 
        template = OfficialTemplate(
            name="Minimal Template",
            description="Minimal test",
            category="Test",
            workflow_json={}
        )
        
        assert template.dsl_content is None
        assert template.preview_images is None
        assert template.source_url == ""
        assert template.last_updated == ""