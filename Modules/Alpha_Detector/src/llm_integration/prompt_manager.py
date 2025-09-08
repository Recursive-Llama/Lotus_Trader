"""
Prompt Management System for LLM Integration

Provides centralized management of prompts with templates, versioning,
and dynamic context injection capabilities.
"""

import os
import yaml
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class PromptManager:
    """
    Centralized prompt management system with template support
    """
    
    def __init__(self, prompts_dir: Optional[str] = None):
        """
        Initialize prompt manager
        
        Args:
            prompts_dir: Directory containing prompt templates (defaults to prompt_templates/)
        """
        if prompts_dir is None:
            # Default to prompt_templates directory relative to this file
            current_dir = Path(__file__).parent
            prompts_dir = current_dir / "prompt_templates"
        
        self.prompts_dir = Path(prompts_dir)
        self.prompts_dir.mkdir(exist_ok=True)
        
        # Load all prompt templates
        self.prompts = {}
        self._load_prompt_templates()
        
        logger.info(f"PromptManager initialized with {len(self.prompts)} templates")
    
    def _load_prompt_templates(self):
        """Load all prompt templates from the prompts directory"""
        
        if not self.prompts_dir.exists():
            logger.warning(f"Prompts directory does not exist: {self.prompts_dir}")
            return
        
        for yaml_file in self.prompts_dir.glob("*.yaml"):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    templates = yaml.safe_load(f)
                
                if templates:
                    for template_name, template_data in templates.items():
                        self.prompts[template_name] = template_data
                        logger.debug(f"Loaded prompt template: {template_name}")
                
            except Exception as e:
                logger.error(f"Error loading prompt template from {yaml_file}: {e}")
    
    def get_prompt(self, template_name: str, version: Optional[str] = None) -> Dict[str, Any]:
        """
        Get a prompt template by name and optional version
        
        Args:
            template_name: Name of the prompt template
            version: Optional version (defaults to 'latest')
            
        Returns:
            Prompt template data
        """
        
        if template_name not in self.prompts:
            raise ValueError(f"Prompt template '{template_name}' not found")
        
        template_data = self.prompts[template_name]
        
        # Handle versioning
        if version is None:
            version = template_data.get('latest_version', 'v1.0')
        
        if 'versions' in template_data:
            if version not in template_data['versions']:
                raise ValueError(f"Version '{version}' not found for template '{template_name}'")
            return template_data['versions'][version]
        
        # Single version template
        return template_data
    
    def get_prompt_text(self, template_name: str, version: Optional[str] = None) -> str:
        """
        Get the prompt text from a template
        
        Args:
            template_name: Name of the prompt template
            version: Optional version
            
        Returns:
            Prompt text string
        """
        
        template = self.get_prompt(template_name, version)
        return template.get('prompt', '')
    
    def format_prompt(self, 
                     template_name: str, 
                     context: Dict[str, Any], 
                     version: Optional[str] = None) -> str:
        """
        Format a prompt template with context data
        
        Args:
            template_name: Name of the prompt template
            context: Context data to inject
            version: Optional version
            
        Returns:
            Formatted prompt string
        """
        
        template = self.get_prompt(template_name, version)
        prompt_text = template.get('prompt', '')
        
        try:
            # Format the prompt with context
            formatted_prompt = prompt_text.format(**context)
            return formatted_prompt
            
        except KeyError as e:
            logger.error(f"Missing key in prompt template '{template_name}': {e}")
            raise ValueError(f"Template missing required key: {e}")
        except Exception as e:
            logger.error(f"Error formatting prompt '{template_name}': {e}")
            raise ValueError(f"Prompt formatting failed: {e}")
    
    def get_system_message(self, template_name: str, version: Optional[str] = None) -> Optional[str]:
        """
        Get system message from a prompt template
        
        Args:
            template_name: Name of the prompt template
            version: Optional version
            
        Returns:
            System message string or None
        """
        
        template = self.get_prompt(template_name, version)
        return template.get('system_message')
    
    def get_parameters(self, template_name: str, version: Optional[str] = None) -> Dict[str, Any]:
        """
        Get LLM parameters from a prompt template
        
        Args:
            template_name: Name of the prompt template
            version: Optional version
            
        Returns:
            LLM parameters dictionary
        """
        
        template = self.get_prompt(template_name, version)
        return template.get('parameters', {})
    
    def list_templates(self) -> List[str]:
        """
        List all available prompt templates
        
        Returns:
            List of template names
        """
        
        return list(self.prompts.keys())
    
    def get_template_info(self, template_name: str) -> Dict[str, Any]:
        """
        Get information about a prompt template
        
        Args:
            template_name: Name of the prompt template
            
        Returns:
            Template information
        """
        
        if template_name not in self.prompts:
            raise ValueError(f"Prompt template '{template_name}' not found")
        
        template_data = self.prompts[template_name]
        
        return {
            'name': template_name,
            'description': template_data.get('description', ''),
            'category': template_data.get('category', 'general'),
            'latest_version': template_data.get('latest_version', 'v1.0'),
            'versions': list(template_data.get('versions', {}).keys()) if 'versions' in template_data else ['v1.0'],
            'created_at': template_data.get('created_at', ''),
            'updated_at': template_data.get('updated_at', '')
        }
    
    def create_template(self, 
                       template_name: str, 
                       prompt_text: str,
                       description: str = "",
                       category: str = "general",
                       system_message: Optional[str] = None,
                       parameters: Optional[Dict[str, Any]] = None) -> bool:
        """
        Create a new prompt template
        
        Args:
            template_name: Name for the new template
            prompt_text: The prompt text
            description: Description of the template
            category: Category for organization
            system_message: Optional system message
            parameters: Optional LLM parameters
            
        Returns:
            True if successful, False otherwise
        """
        
        try:
            template_data = {
                'description': description,
                'category': category,
                'latest_version': 'v1.0',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'versions': {
                    'v1.0': {
                        'prompt': prompt_text,
                        'system_message': system_message,
                        'parameters': parameters or {},
                        'created_at': datetime.now(timezone.utc).isoformat()
                    }
                }
            }
            
            self.prompts[template_name] = template_data
            
            # Save to file
            self._save_template_to_file(template_name, template_data)
            
            logger.info(f"Created prompt template: {template_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating prompt template '{template_name}': {e}")
            return False
    
    def _save_template_to_file(self, template_name: str, template_data: Dict[str, Any]):
        """Save template to YAML file"""
        
        # Determine which file to save to based on category
        category = template_data.get('category', 'general')
        filename = f"{category}_prompts.yaml"
        filepath = self.prompts_dir / filename
        
        # Load existing data
        existing_data = {}
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    existing_data = yaml.safe_load(f) or {}
            except Exception as e:
                logger.warning(f"Error loading existing template file {filepath}: {e}")
        
        # Add new template
        existing_data[template_name] = template_data
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(existing_data, f, default_flow_style=False, indent=2)
    
    def validate_template(self, template_name: str, context: Dict[str, Any]) -> bool:
        """
        Validate that a template can be formatted with given context
        
        Args:
            template_name: Name of the template
            context: Context to validate against
            
        Returns:
            True if valid, False otherwise
        """
        
        try:
            self.format_prompt(template_name, context)
            return True
        except Exception as e:
            logger.error(f"Template validation failed for '{template_name}': {e}")
            return False


# Example usage and testing
if __name__ == "__main__":
    # Test the prompt manager
    try:
        manager = PromptManager()
        
        # List templates
        templates = manager.list_templates()
        print(f"Available templates: {templates}")
        
        # Test getting a template
        if templates:
            template_name = templates[0]
            info = manager.get_template_info(template_name)
            print(f"Template info for '{template_name}': {info}")
        
        print("✅ PromptManager test successful")
        
    except Exception as e:
        print(f"❌ Error testing PromptManager: {e}")

