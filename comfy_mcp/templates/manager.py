"""Template management functionality."""

import re
import asyncio
from typing import Dict, List, Optional, Any
from .templates import TEMPLATES, WorkflowTemplate
from .official import official_manager, OfficialTemplate


class TemplateManager:
    """Manages workflow templates with parameter substitution."""
    
    def __init__(self):
        self.custom_templates = TEMPLATES
        self.official_templates_synced = False
    
    def list_templates(self, include_official: bool = True) -> List[Dict[str, Any]]:
        """List all available templates with metadata."""
        results = []
        
        # Add custom templates
        for name, template in self.custom_templates.items():
            results.append({
                "name": name,
                "description": template.description,
                "category": template.category,
                "tags": template.tags,
                "difficulty": template.difficulty,
                "required_models": template.required_models or [],
                "parameters": template.parameters or {},
                "source": "custom"
            })
        
        # Add official templates if requested
        if include_official and official_manager.templates:
            official_templates = official_manager.list_templates()
            results.extend(official_templates)
        
        return results
    
    def get_template(self, name: str) -> Optional[WorkflowTemplate]:
        """Get a specific custom template by name."""
        return self.custom_templates.get(name)
    
    def get_official_template(self, name: str) -> Optional[OfficialTemplate]:
        """Get a specific official template by name."""
        return official_manager.get_template(name)
    
    async def sync_official_templates(self) -> Dict[str, Any]:
        """Sync official ComfyUI templates."""
        try:
            templates = await official_manager.sync_official_templates()
            self.official_templates_synced = True
            return {
                "status": "success",
                "synced_count": len(templates),
                "templates": list(templates.keys())
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def search_templates(
        self, 
        query: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        difficulty: Optional[str] = None,
        source: Optional[str] = None,
        include_official: bool = True
    ) -> List[Dict[str, Any]]:
        """Search templates by various criteria."""
        # Get all templates first
        all_templates = self.list_templates(include_official=include_official)
        results = []
        
        for template_data in all_templates:
            # Check source filter
            if source and template_data.get("source") != source:
                continue
                
            # Check query match (name, description, category)
            if query:
                query_lower = query.lower()
                if not any([
                    query_lower in template_data["name"].lower(),
                    query_lower in template_data["description"].lower(),
                    query_lower in template_data["category"].lower(),
                ]):
                    # For custom templates, also check tags
                    if template_data.get("source") == "custom" and "tags" in template_data:
                        if not any(query_lower in tag.lower() for tag in template_data["tags"]):
                            continue
                    else:
                        continue
            
            # Check category
            if category and template_data["category"].lower() != category.lower():
                continue
            
            # Check tags (only for custom templates)
            if tags and template_data.get("source") == "custom":
                template_tags = template_data.get("tags", [])
                if not any(tag.lower() in [t.lower() for t in template_tags] for tag in tags):
                    continue
            
            # Check difficulty (only for custom templates)
            if difficulty and template_data.get("difficulty"):
                if template_data["difficulty"].lower() != difficulty.lower():
                    continue
            
            results.append(template_data)
        
        return results
    
    def generate_workflow(
        self, 
        template_name: str, 
        parameters: Optional[Dict[str, str]] = None,
        source: str = "auto"
    ) -> Optional[str]:
        """Generate a workflow DSL from template with parameter substitution."""
        # Try custom templates first, then official
        template = None
        dsl_content = None
        
        if source in ["auto", "custom"]:
            template = self.custom_templates.get(template_name)
            if template:
                dsl_content = template.dsl_content
        
        if not template and source in ["auto", "official"]:
            official_template = official_manager.get_template(template_name)
            if official_template and official_template.dsl_content:
                dsl_content = official_template.dsl_content
                # Create a minimal template-like object for parameter handling
                template = type('Template', (), {
                    'parameters': {},  # Official templates don't have default parameters
                    'dsl_content': dsl_content
                })()
        
        if not template or not dsl_content:
            return None
        
        # Start with template's default parameters
        final_params = template.parameters.copy() if hasattr(template, 'parameters') and template.parameters else {}
        
        # Override with provided parameters
        if parameters:
            final_params.update(parameters)
        
        # Substitute parameters in DSL content if any
        if final_params:
            for param_name, param_value in final_params.items():
                # Replace {param_name} with actual value
                placeholder = f"{{{param_name}}}"
                dsl_content = dsl_content.replace(placeholder, str(param_value))
        
        return dsl_content
    
    def validate_parameters(
        self, 
        template_name: str, 
        parameters: Dict[str, str],
        source: str = "auto"
    ) -> Dict[str, List[str]]:
        """Validate parameters for a template."""
        # Try to find template in custom or official
        template = None
        if source in ["auto", "custom"]:
            template = self.custom_templates.get(template_name)
        
        if not template and source in ["auto", "official"]:
            official_template = official_manager.get_template(template_name)
            if official_template and official_template.dsl_content:
                # Create minimal template object for validation
                template = type('Template', (), {
                    'parameters': {},
                    'dsl_content': official_template.dsl_content
                })()
        if not template:
            return {
                "valid": False,
                "errors": [f"Template '{template_name}' not found"],
                "warnings": []
            }
        
        errors = []
        warnings = []
        
        # Check for required parameters (those in template but not provided)
        template_params = template.parameters or {}
        required_params = set(self._extract_parameters_from_dsl(template.dsl_content))
        provided_params = set(parameters.keys())
        
        missing_params = required_params - provided_params
        if missing_params:
            errors.append(f"Missing required parameters: {', '.join(missing_params)}")
        
        # Check for extra parameters
        extra_params = provided_params - required_params
        if extra_params:
            warnings.append(f"Extra parameters will be ignored: {', '.join(extra_params)}")
        
        # Validate specific parameter types/constraints
        for param_name, param_value in parameters.items():
            if param_name in template_params:
                validation_errors = self._validate_parameter_value(
                    param_name, param_value, template_name
                )
                errors.extend(validation_errors)
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _extract_parameters_from_dsl(self, dsl_content: str) -> List[str]:
        """Extract parameter placeholders from DSL content."""
        # Find all {parameter_name} patterns
        pattern = r'\{([^}]+)\}'
        return list(set(re.findall(pattern, dsl_content)))
    
    def _validate_parameter_value(
        self, 
        param_name: str, 
        param_value: str, 
        template_name: str
    ) -> List[str]:
        """Validate a specific parameter value."""
        errors = []
        
        # Common validations
        if param_name in ['width', 'height']:
            try:
                val = int(param_value)
                if val <= 0 or val > 2048:
                    errors.append(f"{param_name} must be between 1 and 2048")
                if val % 64 != 0:
                    errors.append(f"{param_name} should be divisible by 64 for best results")
            except ValueError:
                errors.append(f"{param_name} must be a valid integer")
        
        elif param_name == 'steps':
            try:
                val = int(param_value)
                if val < 1 or val > 100:
                    errors.append("steps must be between 1 and 100")
            except ValueError:
                errors.append("steps must be a valid integer")
        
        elif param_name == 'cfg':
            try:
                val = float(param_value)
                if val < 1.0 or val > 20.0:
                    errors.append("cfg must be between 1.0 and 20.0")
            except ValueError:
                errors.append("cfg must be a valid number")
        
        elif param_name == 'seed':
            try:
                val = int(param_value)
                if val < 0:
                    errors.append("seed must be non-negative")
            except ValueError:
                errors.append("seed must be a valid integer")
        
        elif param_name in ['denoise', 'style_strength', 'control_strength']:
            try:
                val = float(param_value)
                if val < 0.0 or val > 1.0:
                    errors.append(f"{param_name} must be between 0.0 and 1.0")
            except ValueError:
                errors.append(f"{param_name} must be a valid number")
        
        return errors
    
    def get_template_info(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a template."""
        template = self.custom_templates.get(template_name)
        if not template:
            return None
        
        return {
            "name": template_name,
            "description": template.description,
            "category": template.category,
            "tags": template.tags,
            "difficulty": template.difficulty,
            "required_models": template.required_models or [],
            "parameters": template.parameters or {},
            "parameter_placeholders": self._extract_parameters_from_dsl(template.dsl_content),
            "dsl_preview": template.dsl_content[:500] + "..." if len(template.dsl_content) > 500 else template.dsl_content
        }