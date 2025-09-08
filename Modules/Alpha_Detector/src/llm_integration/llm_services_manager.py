"""
LLM Services Manager - Orchestrates all LLM services in the system
Acts as the "conductor of the LLM orchestra"
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import json
import uuid

from .openrouter_client import OpenRouterClient
from .service_registry import ServiceRegistry
from .llm_management_interface import LLMManagementInterface

logger = logging.getLogger(__name__)

@dataclass
class LLMServiceConfig:
    """Configuration for an LLM service"""
    service_name: str
    model: str
    capabilities: List[str]
    prompts: List[str]
    max_tokens: int = 1000
    temperature: float = 0.7
    enabled: bool = True
    priority: int = 1  # 1 = highest priority
    dependencies: List[str] = None
    performance_metrics: Dict[str, float] = None

@dataclass
class LLMServiceResult:
    """Result from an LLM service call"""
    service_name: str
    result: Any
    confidence: float
    reasoning: str
    execution_time: float
    tokens_used: int
    success: bool
    error_message: Optional[str] = None

class LLMServicesManager:
    """
    Manages all LLM services - creates, adjusts, removes, and orchestrates them
    This is the "conductor" of the LLM orchestra
    """
    
    def __init__(self, config_file: str = None):
        self.llm_services: Dict[str, LLMServiceConfig] = {}
        self.service_registry = ServiceRegistry()
        self.management_interface = LLMManagementInterface(self)
        self.performance_monitor = LLMPerformanceMonitor()
        self.openrouter_client = OpenRouterClient()
        
        # Load configuration if provided
        if config_file:
            self.load_configuration(config_file)
        
        # Initialize default services
        self._initialize_default_services()
        
        logger.info(f"LLMServicesManager initialized with {len(self.llm_services)} services")
    
    def _initialize_default_services(self):
        """Initialize default LLM services"""
        default_services = [
            LLMServiceConfig(
                service_name="signal_analysis",
                model="openrouter/anthropic/claude-3.5-sonnet",
                capabilities=["signal_analysis", "pattern_recognition"],
                prompts=["signal_analysis", "pattern_recognition"],
                max_tokens=1000,
                temperature=0.7,
                priority=1
            ),
            LLMServiceConfig(
                service_name="lesson_generation",
                model="openrouter/anthropic/claude-3.5-sonnet",
                capabilities=["lesson_generation", "learning_insights"],
                prompts=["lesson_generation", "learning_insights"],
                max_tokens=1500,
                temperature=0.8,
                priority=2
            ),
            LLMServiceConfig(
                service_name="threshold_optimization",
                model="openrouter/anthropic/claude-3.5-sonnet",
                capabilities=["threshold_optimization", "parameter_tuning"],
                prompts=["threshold_optimization", "parameter_tuning"],
                max_tokens=800,
                temperature=0.6,
                priority=1
            ),
            LLMServiceConfig(
                service_name="context_analysis",
                model="openrouter/anthropic/claude-3.5-sonnet",
                capabilities=["context_analysis", "information_synthesis"],
                prompts=["context_analysis", "information_synthesis"],
                max_tokens=1200,
                temperature=0.7,
                priority=2
            )
        ]
        
        for service_config in default_services:
            self.register_llm_service(service_config.service_name, service_config)
    
    def register_llm_service(self, service_name: str, service_config: Union[LLMServiceConfig, Dict]) -> bool:
        """
        Register a new LLM service
        
        Args:
            service_name: Name of the service
            service_config: Service configuration
            
        Returns:
            bool: True if registration successful
        """
        try:
            # Convert dict to LLMServiceConfig if needed
            if isinstance(service_config, dict):
                service_config = LLMServiceConfig(**service_config)
            
            # Validate service configuration
            if not self._validate_service_config(service_config):
                logger.error(f"Invalid service configuration for {service_name}")
                return False
            
            # Register in service registry
            self.service_registry.register(service_name, service_config)
            
            # Store service configuration
            self.llm_services[service_name] = service_config
            
            logger.info(f"Successfully registered LLM service: {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register LLM service {service_name}: {e}")
            return False
    
    def adjust_llm_service(self, service_name: str, adjustments: Dict[str, Any]) -> bool:
        """
        Adjust an existing LLM service
        
        Args:
            service_name: Name of the service to adjust
            adjustments: Dictionary of adjustments to make
            
        Returns:
            bool: True if adjustment successful
        """
        try:
            if service_name not in self.llm_services:
                logger.error(f"Service {service_name} not found")
                return False
            
            service_config = self.llm_services[service_name]
            
            # Apply adjustments
            for key, value in adjustments.items():
                if hasattr(service_config, key):
                    setattr(service_config, key, value)
                    logger.info(f"Adjusted {service_name}.{key} = {value}")
                else:
                    logger.warning(f"Unknown adjustment key: {key}")
            
            # Update service registry
            self.service_registry.update(service_name, service_config)
            
            logger.info(f"Successfully adjusted LLM service: {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to adjust LLM service {service_name}: {e}")
            return False
    
    def remove_llm_service(self, service_name: str) -> bool:
        """
        Remove an LLM service
        
        Args:
            service_name: Name of the service to remove
            
        Returns:
            bool: True if removal successful
        """
        try:
            if service_name not in self.llm_services:
                logger.error(f"Service {service_name} not found")
                return False
            
            # Check for dependencies
            dependent_services = self.service_registry.get_dependent_services(service_name)
            if dependent_services:
                logger.warning(f"Cannot remove {service_name}: {dependent_services} depend on it")
                return False
            
            # Remove from service registry
            self.service_registry.unregister(service_name)
            
            # Remove from services
            del self.llm_services[service_name]
            
            logger.info(f"Successfully removed LLM service: {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove LLM service {service_name}: {e}")
            return False
    
    def orchestrate_llm_services(self, task_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Orchestrate multiple LLM services for a complex task
        
        Args:
            task_type: Type of task to perform
            data: Data to process
            
        Returns:
            Dict containing results from all relevant services
        """
        try:
            # Find services capable of handling this task
            capable_services = self.service_registry.discover_services(task_type)
            
            if not capable_services:
                logger.warning(f"No services found for task type: {task_type}")
                return {"error": f"No services found for task type: {task_type}"}
            
            # Sort services by priority
            capable_services.sort(key=lambda s: self.llm_services[s].priority)
            
            results = {}
            
            # Execute services in priority order
            for service_name in capable_services:
                service_config = self.llm_services[service_name]
                
                if not service_config.enabled:
                    logger.info(f"Skipping disabled service: {service_name}")
                    continue
                
                try:
                    # Execute service
                    result = self._execute_service(service_name, task_type, data)
                    results[service_name] = result
                    
                    # Update performance metrics
                    self.performance_monitor.record_service_call(service_name, result)
                    
                except Exception as e:
                    logger.error(f"Service {service_name} failed: {e}")
                    results[service_name] = {
                        "error": str(e),
                        "success": False
                    }
            
            # Combine results
            combined_result = self._combine_service_results(results, task_type)
            
            return combined_result
            
        except Exception as e:
            logger.error(f"Failed to orchestrate LLM services for {task_type}: {e}")
            return {"error": str(e)}
    
    def _execute_service(self, service_name: str, task_type: str, data: Dict[str, Any]) -> LLMServiceResult:
        """Execute a single LLM service"""
        start_time = datetime.now()
        
        try:
            service_config = self.llm_services[service_name]
            
            # Get appropriate prompt for task type
            prompt = self.management_interface.get_prompt_for_task(service_name, task_type)
            
            # Prepare data for LLM
            formatted_data = self._format_data_for_llm(data, service_config)
            
            # Call OpenRouter API
            response = self.openrouter_client.generate_completion(
                model=service_config.model,
                prompt=prompt,
                max_tokens=service_config.max_tokens,
                temperature=service_config.temperature,
                data=formatted_data
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return LLMServiceResult(
                service_name=service_name,
                result=response.get('content', ''),
                confidence=response.get('confidence', 0.0),
                reasoning=response.get('reasoning', ''),
                execution_time=execution_time,
                tokens_used=response.get('tokens_used', 0),
                success=True
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return LLMServiceResult(
                service_name=service_name,
                result=None,
                confidence=0.0,
                reasoning="",
                execution_time=execution_time,
                tokens_used=0,
                success=False,
                error_message=str(e)
            )
    
    def _format_data_for_llm(self, data: Dict[str, Any], service_config: LLMServiceConfig) -> str:
        """Format data for LLM consumption"""
        # Convert data to JSON string for LLM processing
        formatted_data = json.dumps(data, indent=2, default=str)
        return formatted_data
    
    def _combine_service_results(self, results: Dict[str, LLMServiceResult], task_type: str) -> Dict[str, Any]:
        """Combine results from multiple services"""
        combined = {
            "task_type": task_type,
            "services_executed": list(results.keys()),
            "results": {},
            "summary": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Extract individual results
        for service_name, result in results.items():
            if result.success:
                combined["results"][service_name] = {
                    "result": result.result,
                    "confidence": result.confidence,
                    "reasoning": result.reasoning,
                    "execution_time": result.execution_time,
                    "tokens_used": result.tokens_used
                }
            else:
                combined["results"][service_name] = {
                    "error": result.error_message,
                    "success": False
                }
        
        # Create summary
        successful_services = [name for name, result in results.items() if result.success]
        combined["summary"] = {
            "total_services": len(results),
            "successful_services": len(successful_services),
            "success_rate": len(successful_services) / len(results) if results else 0,
            "total_execution_time": sum(result.execution_time for result in results.values()),
            "total_tokens_used": sum(result.tokens_used for result in results.values())
        }
        
        return combined
    
    def monitor_llm_performance(self) -> Dict[str, Any]:
        """Monitor performance of all LLM services"""
        return self.performance_monitor.get_performance_report()
    
    def auto_optimize_services(self) -> Dict[str, Any]:
        """Automatically optimize LLM services based on performance"""
        optimization_report = {}
        
        for service_name, service_config in self.llm_services.items():
            performance_data = self.performance_monitor.get_service_performance(service_name)
            
            if performance_data:
                # Analyze performance and suggest optimizations
                optimizations = self._analyze_service_performance(service_name, performance_data)
                
                if optimizations:
                    # Apply optimizations
                    self.adjust_llm_service(service_name, optimizations)
                    optimization_report[service_name] = optimizations
        
        return optimization_report
    
    def _analyze_service_performance(self, service_name: str, performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze service performance and suggest optimizations"""
        optimizations = {}
        
        # Analyze execution time
        avg_execution_time = performance_data.get('avg_execution_time', 0)
        if avg_execution_time > 5.0:  # If average execution time > 5 seconds
            optimizations['max_tokens'] = min(service_config.max_tokens * 0.8, 800)
            optimizations['temperature'] = min(service_config.temperature * 0.9, 0.6)
        
        # Analyze success rate
        success_rate = performance_data.get('success_rate', 1.0)
        if success_rate < 0.8:  # If success rate < 80%
            optimizations['temperature'] = max(service_config.temperature * 1.1, 0.8)
        
        return optimizations
    
    def _validate_service_config(self, service_config: LLMServiceConfig) -> bool:
        """Validate service configuration"""
        required_fields = ['service_name', 'model', 'capabilities', 'prompts']
        
        for field in required_fields:
            if not hasattr(service_config, field) or not getattr(service_config, field):
                logger.error(f"Missing required field: {field}")
                return False
        
        # Validate model format
        if not isinstance(service_config.model, str) or not service_config.model:
            logger.error("Invalid model specification")
            return False
        
        # Validate capabilities
        if not isinstance(service_config.capabilities, list) or not service_config.capabilities:
            logger.error("Invalid capabilities specification")
            return False
        
        return True
    
    def load_configuration(self, config_file: str):
        """Load configuration from file"""
        try:
            import yaml
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            # Load services from configuration
            services = config.get('services', {})
            for service_name, service_config in services.items():
                self.register_llm_service(service_name, service_config)
            
            logger.info(f"Loaded configuration from {config_file}")
            
        except Exception as e:
            logger.error(f"Failed to load configuration from {config_file}: {e}")
    
    def save_configuration(self, config_file: str):
        """Save current configuration to file"""
        try:
            import yaml
            config = {
                'services': {}
            }
            
            for service_name, service_config in self.llm_services.items():
                config['services'][service_name] = {
                    'service_name': service_config.service_name,
                    'model': service_config.model,
                    'capabilities': service_config.capabilities,
                    'prompts': service_config.prompts,
                    'max_tokens': service_config.max_tokens,
                    'temperature': service_config.temperature,
                    'enabled': service_config.enabled,
                    'priority': service_config.priority,
                    'dependencies': service_config.dependencies or []
                }
            
            with open(config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            
            logger.info(f"Saved configuration to {config_file}")
            
        except Exception as e:
            logger.error(f"Failed to save configuration to {config_file}: {e}")
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get status of all services"""
        status = {
            'total_services': len(self.llm_services),
            'enabled_services': len([s for s in self.llm_services.values() if s.enabled]),
            'services': {}
        }
        
        for service_name, service_config in self.llm_services.items():
            performance_data = self.performance_monitor.get_service_performance(service_name)
            
            status['services'][service_name] = {
                'enabled': service_config.enabled,
                'model': service_config.model,
                'capabilities': service_config.capabilities,
                'priority': service_config.priority,
                'performance': performance_data
            }
        
        return status


class LLMPerformanceMonitor:
    """Monitors performance of LLM services"""
    
    def __init__(self):
        self.performance_data: Dict[str, List[Dict]] = {}
        self.max_records_per_service = 1000
    
    def record_service_call(self, service_name: str, result: LLMServiceResult):
        """Record a service call result"""
        if service_name not in self.performance_data:
            self.performance_data[service_name] = []
        
        record = {
            'timestamp': datetime.now(timezone.utc),
            'success': result.success,
            'execution_time': result.execution_time,
            'tokens_used': result.tokens_used,
            'confidence': result.confidence
        }
        
        self.performance_data[service_name].append(record)
        
        # Keep only recent records
        if len(self.performance_data[service_name]) > self.max_records_per_service:
            self.performance_data[service_name] = self.performance_data[service_name][-self.max_records_per_service:]
    
    def get_service_performance(self, service_name: str) -> Dict[str, Any]:
        """Get performance metrics for a service"""
        if service_name not in self.performance_data:
            return {}
        
        records = self.performance_data[service_name]
        if not records:
            return {}
        
        successful_records = [r for r in records if r['success']]
        
        return {
            'total_calls': len(records),
            'successful_calls': len(successful_records),
            'success_rate': len(successful_records) / len(records) if records else 0,
            'avg_execution_time': sum(r['execution_time'] for r in successful_records) / len(successful_records) if successful_records else 0,
            'avg_tokens_used': sum(r['tokens_used'] for r in successful_records) / len(successful_records) if successful_records else 0,
            'avg_confidence': sum(r['confidence'] for r in successful_records) / len(successful_records) if successful_records else 0,
            'last_call': records[-1]['timestamp'].isoformat() if records else None
        }
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get performance report for all services"""
        report = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'services': {}
        }
        
        for service_name in self.performance_data.keys():
            report['services'][service_name] = self.get_service_performance(service_name)
        
        return report
