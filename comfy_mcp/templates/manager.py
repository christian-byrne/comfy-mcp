"""Template management functionality."""

import re
from typing import Dict, List, Optional, Any
from .templates import TEMPLATES, WorkflowTemplate


class TemplateManager:
    """Manages workflow templates with parameter substitution."""
    
    def __init__(self):
        self.templates = TEMPLATES
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """List all available templates with metadata."""
        return [
            {
                "name": name,
                "description": template.description,
                "category": template.category,
                "tags": template.tags,
                "difficulty": template.difficulty,
                "required_models": template.required_models or [],
                "parameters": template.parameters or {}
            }
            for name, template in self.templates.items()
        ]
    
    def get_template(self, name: str) -> Optional[WorkflowTemplate]:
        """Get a specific template by name."""
        return self.templates.get(name)
    
    def search_templates(
        self, 
        query: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        difficulty: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search templates by various criteria."""
        results = []
        
        for name, template in self.templates.items():
            # Check query match (name, description, tags)
            if query:
                query_lower = query.lower()
                if not any([
                    query_lower in name.lower(),
                    query_lower in template.description.lower(),
                    any(query_lower in tag.lower() for tag in template.tags)
                ]):
                    continue
            
            # Check category
            if category and template.category.lower() != category.lower():
                continue
            
            # Check tags
            if tags:
                if not any(tag.lower() in [t.lower() for t in template.tags] for tag in tags):
                    continue
            
            # Check difficulty
            if difficulty and template.difficulty.lower() != difficulty.lower():
                continue
            
            results.append({
                "name": name,
                "description": template.description,
                "category": template.category,
                "tags": template.tags,
                "difficulty": template.difficulty,
                "required_models": template.required_models or [],
                "parameters": template.parameters or {}
            })
        
        return results
    
    def generate_workflow(
        self, 
        template_name: str, 
        parameters: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """Generate a workflow DSL from template with parameter substitution."""
        template = self.templates.get(template_name)
        if not template:
            return None
        
        # Start with template's default parameters
        final_params = template.parameters.copy() if template.parameters else {}
        
        # Override with provided parameters
        if parameters:
            final_params.update(parameters)
        
        # Substitute parameters in DSL content
        dsl_content = template.dsl_content
        
        for param_name, param_value in final_params.items():
            # Replace {param_name} with actual value
            placeholder = f"{{{param_name}}}"
            dsl_content = dsl_content.replace(placeholder, str(param_value))
        
        return dsl_content
    
    def validate_parameters(
        self, 
        template_name: str, 
        parameters: Dict[str, str]
    ) -> Dict[str, List[str]]:
        """Validate parameters for a template."""
        template = self.templates.get(template_name)
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
        template = self.templates.get(template_name)
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