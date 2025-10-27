"""Unit tests for template functionality."""

import pytest
from comfy_mcp.templates import TemplateManager, TEMPLATES


class TestTemplateManager:
    """Test template manager functionality."""
    
    @pytest.fixture
    def template_manager(self):
        """Create template manager for testing."""
        return TemplateManager()
    
    def test_list_templates(self, template_manager: TemplateManager):
        """Test listing all templates."""
        templates = template_manager.list_templates()
        
        assert isinstance(templates, list)
        assert len(templates) > 0
        
        # Check template structure
        template = templates[0]
        required_keys = ["name", "description", "category", "tags", "difficulty", "required_models", "parameters"]
        for key in required_keys:
            assert key in template
    
    def test_get_template(self, template_manager: TemplateManager):
        """Test getting specific template."""
        template_info = template_manager.get_template_info("text2img_basic")
        
        assert template_info is not None
        assert template_info["name"] == "text2img_basic"
        assert template_info["difficulty"] == "beginner"
        assert "parameters" in template_info
        assert "dsl_preview" in template_info
    
    def test_get_nonexistent_template(self, template_manager: TemplateManager):
        """Test getting template that doesn't exist."""
        template_info = template_manager.get_template_info("nonexistent")
        assert template_info is None
    
    def test_search_templates_by_query(self, template_manager: TemplateManager):
        """Test searching templates by query."""
        results = template_manager.search_templates(query="text")
        
        assert isinstance(results, list)
        assert len(results) > 0
        
        # Should find text2img_basic
        names = [r["name"] for r in results]
        assert "text2img_basic" in names
    
    def test_search_templates_by_category(self, template_manager: TemplateManager):
        """Test searching templates by category."""
        results = template_manager.search_templates(category="Generation")
        
        assert isinstance(results, list)
        assert len(results) > 0
        
        # All results should be in Generation category
        for result in results:
            assert result["category"] == "Generation"
    
    def test_search_templates_by_tags(self, template_manager: TemplateManager):
        """Test searching templates by tags."""
        results = template_manager.search_templates(tags=["text2img"])
        
        assert isinstance(results, list)
        assert len(results) > 0
        
        # All results should have text2img tag
        for result in results:
            assert "text2img" in result["tags"]
    
    def test_search_templates_by_difficulty(self, template_manager: TemplateManager):
        """Test searching templates by difficulty."""
        results = template_manager.search_templates(difficulty="beginner")
        
        assert isinstance(results, list)
        assert len(results) > 0
        
        # All results should be beginner level
        for result in results:
            assert result["difficulty"] == "beginner"
    
    def test_generate_workflow_with_defaults(self, template_manager: TemplateManager):
        """Test generating workflow with default parameters."""
        dsl_content = template_manager.generate_workflow("text2img_basic")
        
        assert isinstance(dsl_content, str)
        assert len(dsl_content) > 0
        assert "CheckpointLoaderSimple" in dsl_content
        assert "a beautiful landscape" in dsl_content  # Default prompt
    
    def test_generate_workflow_with_custom_parameters(self, template_manager: TemplateManager):
        """Test generating workflow with custom parameters."""
        parameters = {
            "prompt": "cyberpunk city",
            "width": "768",
            "height": "512"
        }
        
        dsl_content = template_manager.generate_workflow("text2img_basic", parameters)
        
        assert isinstance(dsl_content, str)
        assert "cyberpunk city" in dsl_content
        assert "width: 768" in dsl_content
        assert "height: 512" in dsl_content
    
    def test_generate_workflow_nonexistent_template(self, template_manager: TemplateManager):
        """Test generating workflow from nonexistent template."""
        dsl_content = template_manager.generate_workflow("nonexistent")
        assert dsl_content is None
    
    def test_validate_parameters_valid(self, template_manager: TemplateManager):
        """Test parameter validation with valid parameters."""
        # Get all required parameters for the template
        template = template_manager.get_template("text2img_basic")
        required_params = template_manager._extract_parameters_from_dsl(template.dsl_content)
        
        # Provide valid values for all required parameters
        parameters = {
            "prompt": "test prompt",
            "negative_prompt": "blurry",
            "width": "512",
            "height": "512",
            "steps": "20",
            "cfg": "7.0",
            "seed": "42"
        }
        
        validation = template_manager.validate_parameters("text2img_basic", parameters)
        
        assert validation["valid"] is True
        assert len(validation["errors"]) == 0
    
    def test_validate_parameters_invalid_width(self, template_manager: TemplateManager):
        """Test parameter validation with invalid width."""
        parameters = {
            "width": "invalid",
            "height": "512"
        }
        
        validation = template_manager.validate_parameters("text2img_basic", parameters)
        
        assert validation["valid"] is False
        assert len(validation["errors"]) > 0
        assert any("width" in error.lower() for error in validation["errors"])
    
    def test_validate_parameters_out_of_range(self, template_manager: TemplateManager):
        """Test parameter validation with out-of-range values."""
        parameters = {
            "steps": "200",  # Too high
            "cfg": "50.0"    # Too high
        }
        
        validation = template_manager.validate_parameters("text2img_basic", parameters)
        
        assert validation["valid"] is False
        assert len(validation["errors"]) >= 2
    
    def test_validate_parameters_nonexistent_template(self, template_manager: TemplateManager):
        """Test parameter validation for nonexistent template."""
        validation = template_manager.validate_parameters("nonexistent", {})
        
        assert validation["valid"] is False
        assert "not found" in validation["errors"][0].lower()
    
    def test_extract_parameters_from_dsl(self, template_manager: TemplateManager):
        """Test extracting parameter placeholders from DSL."""
        dsl = "text: {prompt}\nwidth: {width}\nheight: {height}"
        
        params = template_manager._extract_parameters_from_dsl(dsl)
        
        assert "prompt" in params
        assert "width" in params
        assert "height" in params
        assert len(params) == 3


class TestTemplateDefinitions:
    """Test template definitions and structure."""
    
    def test_all_templates_have_required_fields(self):
        """Test that all templates have required fields."""
        required_fields = ["name", "description", "category", "tags", "dsl_content"]
        
        for name, template in TEMPLATES.items():
            # Template name is the display name, not the key
            assert hasattr(template, 'name')
            
            for field in required_fields:
                assert hasattr(template, field)
                assert getattr(template, field) is not None
    
    def test_template_dsl_content_valid(self):
        """Test that template DSL content is valid."""
        from comfy_mcp.dsl import DSLParser
        
        parser = DSLParser()
        
        for name, template in TEMPLATES.items():
            # Skip templates with parameters for this test
            if template.parameters:
                continue
                
            try:
                # Should be able to parse the DSL
                workflow_ast = parser.parse(template.dsl_content)
                assert workflow_ast is not None
                assert len(workflow_ast.sections) > 0
            except Exception as e:
                pytest.fail(f"Template '{name}' has invalid DSL: {e}")
    
    def test_template_categories_consistent(self):
        """Test that template categories are consistent."""
        categories = set()
        for template in TEMPLATES.values():
            categories.add(template.category)
        
        # Should have reasonable categories
        expected_categories = {"Generation", "Enhancement", "Editing", "Controlled Generation", "Batch Operations", "Artistic"}
        assert categories.issubset(expected_categories)
    
    def test_template_difficulties_valid(self):
        """Test that template difficulties are valid."""
        valid_difficulties = {"beginner", "intermediate", "advanced"}
        
        for template in TEMPLATES.values():
            assert template.difficulty in valid_difficulties
    
    def test_template_tags_not_empty(self):
        """Test that all templates have tags."""
        for template in TEMPLATES.values():
            assert isinstance(template.tags, list)
            assert len(template.tags) > 0