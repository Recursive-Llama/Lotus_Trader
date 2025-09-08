"""
LLM Management Interface - Easy-to-use interface for managing LLM services
Provides simple, one-line operations for common management tasks
"""

import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
import json

logger = logging.getLogger(__name__)

class LLMManagementInterface:
    """
    Easy-to-use interface for managing LLM services
    Provides simple, one-line operations for common management tasks
    """
    
    def __init__(self, services_manager):
        self.services_manager = services_manager
        self.prompt_manager = None  # Will be initialized when prompt management is available
        
        logger.info("LLMManagementInterface initialized")
    
    def adjust_service_prompt(self, service_name: str, prompt_name: str, new_prompt: str) -> bool:
        """
        Easy one-line prompt adjustment
        
        Args:
            service_name: Name of the service
            prompt_name: Name of the prompt to adjust
            new_prompt: New prompt content
            
        Returns:
            bool: True if adjustment successful
        """
        try:
            if not self.prompt_manager:
                logger.error("Prompt manager not available")
                return False
            
            # Update prompt using prompt manager
            success = self.prompt_manager.update_prompt(service_name, prompt_name, new_prompt)
            
            if success:
                logger.info(f"Successfully adjusted prompt {prompt_name} for service {service_name}")
            else:
                logger.error(f"Failed to adjust prompt {prompt_name} for service {service_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error adjusting service prompt: {e}")
            return False
    
    def create_new_service(self, service_name: str, service_config: Dict[str, Any]) -> bool:
        """
        Create a new LLM service
        
        Args:
            service_name: Name of the new service
            service_config: Configuration for the new service
            
        Returns:
            bool: True if creation successful
        """
        try:
            # Validate required fields
            required_fields = ['model', 'capabilities', 'prompts']
            for field in required_fields:
                if field not in service_config:
                    logger.error(f"Missing required field: {field}")
                    return False
            
            # Create service configuration
            from .llm_services_manager import LLMServiceConfig
            service_config_obj = LLMServiceConfig(
                service_name=service_name,
                model=service_config['model'],
                capabilities=service_config['capabilities'],
                prompts=service_config['prompts'],
                max_tokens=service_config.get('max_tokens', 1000),
                temperature=service_config.get('temperature', 0.7),
                enabled=service_config.get('enabled', True),
                priority=service_config.get('priority', 2),
                dependencies=service_config.get('dependencies', [])
            )
            
            # Register the service
            success = self.services_manager.register_llm_service(service_name, service_config_obj)
            
            if success:
                logger.info(f"Successfully created new service: {service_name}")
            else:
                logger.error(f"Failed to create new service: {service_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error creating new service: {e}")
            return False
    
    def remove_service(self, service_name: str) -> bool:
        """
        Remove an LLM service
        
        Args:
            service_name: Name of the service to remove
            
        Returns:
            bool: True if removal successful
        """
        try:
            success = self.services_manager.remove_llm_service(service_name)
            
            if success:
                logger.info(f"Successfully removed service: {service_name}")
            else:
                logger.error(f"Failed to remove service: {service_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error removing service: {e}")
            return False
    
    def optimize_all_services(self) -> Dict[str, Any]:
        """
        Optimize all services based on performance
        
        Returns:
            Dict containing optimization results
        """
        try:
            optimization_results = self.services_manager.auto_optimize_services()
            
            logger.info(f"Optimized {len(optimization_results)} services")
            return optimization_results
            
        except Exception as e:
            logger.error(f"Error optimizing services: {e}")
            return {"error": str(e)}
    
    def get_service_performance(self) -> Dict[str, Any]:
        """
        Get performance report for all services
        
        Returns:
            Dict containing performance data
        """
        try:
            performance_report = self.services_manager.monitor_llm_performance()
            
            return performance_report
            
        except Exception as e:
            logger.error(f"Error getting service performance: {e}")
            return {"error": str(e)}
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        Get status of all services
        
        Returns:
            Dict containing service status information
        """
        try:
            status = self.services_manager.get_service_status()
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            return {"error": str(e)}
    
    def list_all_services(self) -> List[str]:
        """
        List all available services
        
        Returns:
            List of service names
        """
        try:
            services = self.services_manager.service_registry.list_all_services()
            
            return services
            
        except Exception as e:
            logger.error(f"Error listing services: {e}")
            return []
    
    def get_service_info(self, service_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific service
        
        Args:
            service_name: Name of the service
            
        Returns:
            Dict containing service information
        """
        try:
            service_info = self.services_manager.service_registry.get_service_info(service_name)
            
            return service_info
            
        except Exception as e:
            logger.error(f"Error getting service info for {service_name}: {e}")
            return {"error": str(e)}
    
    def enable_service(self, service_name: str) -> bool:
        """
        Enable a service
        
        Args:
            service_name: Name of the service to enable
            
        Returns:
            bool: True if successful
        """
        try:
            success = self.services_manager.adjust_llm_service(service_name, {'enabled': True})
            
            if success:
                logger.info(f"Successfully enabled service: {service_name}")
            else:
                logger.error(f"Failed to enable service: {service_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error enabling service: {e}")
            return False
    
    def disable_service(self, service_name: str) -> bool:
        """
        Disable a service
        
        Args:
            service_name: Name of the service to disable
            
        Returns:
            bool: True if successful
        """
        try:
            success = self.services_manager.adjust_llm_service(service_name, {'enabled': False})
            
            if success:
                logger.info(f"Successfully disabled service: {service_name}")
            else:
                logger.error(f"Failed to disable service: {service_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error disabling service: {e}")
            return False
    
    def update_service_model(self, service_name: str, new_model: str) -> bool:
        """
        Update the model for a service
        
        Args:
            service_name: Name of the service
            new_model: New model to use
            
        Returns:
            bool: True if successful
        """
        try:
            success = self.services_manager.adjust_llm_service(service_name, {'model': new_model})
            
            if success:
                logger.info(f"Successfully updated model for service {service_name} to {new_model}")
            else:
                logger.error(f"Failed to update model for service {service_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating service model: {e}")
            return False
    
    def update_service_temperature(self, service_name: str, new_temperature: float) -> bool:
        """
        Update the temperature for a service
        
        Args:
            service_name: Name of the service
            new_temperature: New temperature value (0.0 - 2.0)
            
        Returns:
            bool: True if successful
        """
        try:
            # Validate temperature range
            if not 0.0 <= new_temperature <= 2.0:
                logger.error(f"Temperature must be between 0.0 and 2.0, got {new_temperature}")
                return False
            
            success = self.services_manager.adjust_llm_service(service_name, {'temperature': new_temperature})
            
            if success:
                logger.info(f"Successfully updated temperature for service {service_name} to {new_temperature}")
            else:
                logger.error(f"Failed to update temperature for service {service_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating service temperature: {e}")
            return False
    
    def update_service_max_tokens(self, service_name: str, new_max_tokens: int) -> bool:
        """
        Update the max tokens for a service
        
        Args:
            service_name: Name of the service
            new_max_tokens: New max tokens value
            
        Returns:
            bool: True if successful
        """
        try:
            # Validate max tokens
            if new_max_tokens <= 0:
                logger.error(f"Max tokens must be positive, got {new_max_tokens}")
                return False
            
            success = self.services_manager.adjust_llm_service(service_name, {'max_tokens': new_max_tokens})
            
            if success:
                logger.info(f"Successfully updated max tokens for service {service_name} to {new_max_tokens}")
            else:
                logger.error(f"Failed to update max tokens for service {service_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating service max tokens: {e}")
            return False
    
    def get_prompt_for_task(self, service_name: str, task_type: str) -> str:
        """
        Get the appropriate prompt for a task type
        
        Args:
            service_name: Name of the service
            task_type: Type of task
            
        Returns:
            str: Prompt content
        """
        try:
            if not self.prompt_manager:
                # Return default prompt if prompt manager not available
                return f"Please analyze the following data for {task_type}: {{data}}"
            
            # Get prompt from prompt manager
            prompt = self.prompt_manager.get_prompt(service_name, task_type)
            
            return prompt
            
        except Exception as e:
            logger.error(f"Error getting prompt for task: {e}")
            return f"Please analyze the following data for {task_type}: {{data}}"
    
    def execute_service_task(self, service_name: str, task_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a specific task using a service
        
        Args:
            service_name: Name of the service to use
            task_type: Type of task to execute
            data: Data to process
            
        Returns:
            Dict containing task results
        """
        try:
            # Use the services manager to orchestrate the task
            result = self.services_manager.orchestrate_llm_services(task_type, data)
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing service task: {e}")
            return {"error": str(e)}
    
    def validate_service_dependencies(self, service_name: str) -> Dict[str, Any]:
        """
        Validate service dependencies
        
        Args:
            service_name: Name of the service to validate
            
        Returns:
            Dict containing validation results
        """
        try:
            validation_result = self.services_manager.service_registry.validate_service_dependencies(service_name)
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating service dependencies: {e}")
            return {"error": str(e)}
    
    def get_services_by_capability(self, capability: str) -> Dict[str, List[str]]:
        """
        Get services that have a specific capability
        
        Args:
            capability: Capability to search for
            
        Returns:
            Dict mapping service names to their matching capabilities
        """
        try:
            matching_services = self.services_manager.service_registry.get_services_by_capability(capability)
            
            # Convert to simpler format
            result = {}
            for service_name, capabilities in matching_services.items():
                result[service_name] = [cap.name for cap in capabilities]
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting services by capability: {e}")
            return {}
    
    def save_configuration(self, config_file: str) -> bool:
        """
        Save current configuration to file
        
        Args:
            config_file: Path to configuration file
            
        Returns:
            bool: True if successful
        """
        try:
            self.services_manager.save_configuration(config_file)
            logger.info(f"Successfully saved configuration to {config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            return False
    
    def load_configuration(self, config_file: str) -> bool:
        """
        Load configuration from file
        
        Args:
            config_file: Path to configuration file
            
        Returns:
            bool: True if successful
        """
        try:
            self.services_manager.load_configuration(config_file)
            logger.info(f"Successfully loaded configuration from {config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return False
    
    def get_management_summary(self) -> Dict[str, Any]:
        """
        Get a comprehensive management summary
        
        Returns:
            Dict containing management summary
        """
        try:
            summary = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'service_status': self.get_service_status(),
                'performance_report': self.get_service_performance(),
                'registry_status': self.services_manager.service_registry.get_registry_status(),
                'total_services': len(self.list_all_services()),
                'enabled_services': len([s for s in self.list_all_services() if self.get_service_info(s).get('status') == 'active'])
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting management summary: {e}")
            return {"error": str(e)}
