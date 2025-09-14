"""
Service Registry - Manages LLM service discovery and dependencies
Makes all services discoverable and manageable
"""

import logging
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

@dataclass
class ServiceCapability:
    """Represents a service capability"""
    name: str
    description: str
    input_types: List[str]
    output_types: List[str]
    confidence_threshold: float = 0.7

@dataclass
class ServiceDependency:
    """Represents a service dependency"""
    service_name: str
    dependency_type: str  # 'required', 'optional', 'preferred'
    description: str

class ServiceRegistry:
    """
    Registry for all LLM services - makes them discoverable and manageable
    """
    
    def __init__(self):
        self.services: Dict[str, Any] = {}
        self.capabilities: Dict[str, List[ServiceCapability]] = {}
        self.dependencies: Dict[str, List[ServiceDependency]] = {}
        self.service_metadata: Dict[str, Dict[str, Any]] = {}
        
        logger.info("ServiceRegistry initialized")
    
    def register(self, service_name: str, service_instance: Any) -> bool:
        """
        Register a new service
        
        Args:
            service_name: Name of the service
            service_instance: Service instance or configuration
            
        Returns:
            bool: True if registration successful
        """
        try:
            # Store service instance
            self.services[service_name] = service_instance
            
            # Extract capabilities from service instance
            capabilities = self._extract_capabilities(service_instance)
            self.capabilities[service_name] = capabilities
            
            # Extract dependencies from service instance
            dependencies = self._extract_dependencies(service_instance)
            self.dependencies[service_name] = dependencies
            
            # Store metadata
            self.service_metadata[service_name] = {
                'registered_at': datetime.now(timezone.utc),
                'last_updated': datetime.now(timezone.utc),
                'status': 'active',
                'capability_count': len(capabilities),
                'dependency_count': len(dependencies)
            }
            
            logger.info(f"Successfully registered service: {service_name} with {len(capabilities)} capabilities")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register service {service_name}: {e}")
            return False
    
    def unregister(self, service_name: str) -> bool:
        """
        Unregister a service
        
        Args:
            service_name: Name of the service to unregister
            
        Returns:
            bool: True if unregistration successful
        """
        try:
            if service_name not in self.services:
                logger.warning(f"Service {service_name} not found for unregistration")
                return False
            
            # Check for dependent services
            dependent_services = self.get_dependent_services(service_name)
            if dependent_services:
                logger.warning(f"Cannot unregister {service_name}: {dependent_services} depend on it")
                return False
            
            # Remove from all registries
            del self.services[service_name]
            del self.capabilities[service_name]
            del self.dependencies[service_name]
            del self.service_metadata[service_name]
            
            logger.info(f"Successfully unregistered service: {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister service {service_name}: {e}")
            return False
    
    def update(self, service_name: str, service_instance: Any) -> bool:
        """
        Update an existing service
        
        Args:
            service_name: Name of the service to update
            service_instance: Updated service instance or configuration
            
        Returns:
            bool: True if update successful
        """
        try:
            if service_name not in self.services:
                logger.error(f"Service {service_name} not found for update")
                return False
            
            # Update service instance
            self.services[service_name] = service_instance
            
            # Update capabilities
            capabilities = self._extract_capabilities(service_instance)
            self.capabilities[service_name] = capabilities
            
            # Update dependencies
            dependencies = self._extract_dependencies(service_instance)
            self.dependencies[service_name] = dependencies
            
            # Update metadata
            self.service_metadata[service_name]['last_updated'] = datetime.now(timezone.utc)
            self.service_metadata[service_name]['capability_count'] = len(capabilities)
            self.service_metadata[service_name]['dependency_count'] = len(dependencies)
            
            logger.info(f"Successfully updated service: {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update service {service_name}: {e}")
            return False
    
    def discover_services(self, capability: str) -> List[str]:
        """
        Find services that can handle a specific capability
        
        Args:
            capability: Capability to search for
            
        Returns:
            List of service names that can handle the capability
        """
        try:
            capable_services = []
            
            for service_name, service_capabilities in self.capabilities.items():
                for cap in service_capabilities:
                    if capability.lower() in cap.name.lower() or capability.lower() in cap.description.lower():
                        capable_services.append(service_name)
                        break
            
            logger.debug(f"Found {len(capable_services)} services for capability '{capability}': {capable_services}")
            return capable_services
            
        except Exception as e:
            logger.error(f"Failed to discover services for capability '{capability}': {e}")
            return []
    
    def get_service_dependencies(self, service_name: str) -> List[ServiceDependency]:
        """
        Get dependencies for a service
        
        Args:
            service_name: Name of the service
            
        Returns:
            List of service dependencies
        """
        return self.dependencies.get(service_name, [])
    
    def get_dependent_services(self, service_name: str) -> List[str]:
        """
        Get services that depend on the specified service
        
        Args:
            service_name: Name of the service
            
        Returns:
            List of service names that depend on the specified service
        """
        dependent_services = []
        
        for dep_service_name, dependencies in self.dependencies.items():
            for dependency in dependencies:
                if dependency.service_name == service_name:
                    dependent_services.append(dep_service_name)
                    break
        
        return dependent_services
    
    def get_service_capabilities(self, service_name: str) -> List[ServiceCapability]:
        """
        Get capabilities for a service
        
        Args:
            service_name: Name of the service
            
        Returns:
            List of service capabilities
        """
        return self.capabilities.get(service_name, [])
    
    def get_service_info(self, service_name: str) -> Dict[str, Any]:
        """
        Get comprehensive information about a service
        
        Args:
            service_name: Name of the service
            
        Returns:
            Dictionary containing service information
        """
        if service_name not in self.services:
            return {}
        
        return {
            'service_name': service_name,
            'capabilities': [cap.__dict__ for cap in self.capabilities.get(service_name, [])],
            'dependencies': [dep.__dict__ for dep in self.dependencies.get(service_name, [])],
            'metadata': self.service_metadata.get(service_name, {}),
            'status': 'active' if service_name in self.services else 'inactive'
        }
    
    def list_all_services(self) -> List[str]:
        """
        List all registered services
        
        Returns:
            List of all service names
        """
        return list(self.services.keys())
    
    def get_services_by_capability(self, capability: str) -> Dict[str, List[ServiceCapability]]:
        """
        Get all services that have a specific capability
        
        Args:
            capability: Capability to search for
            
        Returns:
            Dictionary mapping service names to their matching capabilities
        """
        matching_services = {}
        
        for service_name, capabilities in self.capabilities.items():
            matching_capabilities = []
            for cap in capabilities:
                if capability.lower() in cap.name.lower() or capability.lower() in cap.description.lower():
                    matching_capabilities.append(cap)
            
            if matching_capabilities:
                matching_services[service_name] = matching_capabilities
        
        return matching_services
    
    def validate_service_dependencies(self, service_name: str) -> Dict[str, Any]:
        """
        Validate that all dependencies for a service are satisfied
        
        Args:
            service_name: Name of the service to validate
            
        Returns:
            Dictionary containing validation results
        """
        validation_result = {
            'service_name': service_name,
            'valid': True,
            'missing_dependencies': [],
            'satisfied_dependencies': [],
            'warnings': []
        }
        
        if service_name not in self.dependencies:
            validation_result['valid'] = True
            return validation_result
        
        dependencies = self.dependencies[service_name]
        
        for dependency in dependencies:
            if dependency.service_name in self.services:
                validation_result['satisfied_dependencies'].append(dependency.service_name)
            else:
                if dependency.dependency_type == 'required':
                    validation_result['missing_dependencies'].append(dependency.service_name)
                    validation_result['valid'] = False
                elif dependency.dependency_type == 'optional':
                    validation_result['warnings'].append(f"Optional dependency {dependency.service_name} not available")
                elif dependency.dependency_type == 'preferred':
                    validation_result['warnings'].append(f"Preferred dependency {dependency.service_name} not available")
        
        return validation_result
    
    def get_registry_status(self) -> Dict[str, Any]:
        """
        Get overall registry status
        
        Returns:
            Dictionary containing registry status information
        """
        total_services = len(self.services)
        active_services = len([s for s in self.service_metadata.values() if s['status'] == 'active'])
        
        total_capabilities = sum(len(caps) for caps in self.capabilities.values())
        total_dependencies = sum(len(deps) for deps in self.dependencies.values())
        
        return {
            'total_services': total_services,
            'active_services': active_services,
            'total_capabilities': total_capabilities,
            'total_dependencies': total_dependencies,
            'services': list(self.services.keys()),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def _extract_capabilities(self, service_instance: Any) -> List[ServiceCapability]:
        """Extract capabilities from service instance"""
        capabilities = []
        
        try:
            # If service_instance has capabilities attribute
            if hasattr(service_instance, 'capabilities'):
                for cap_name in service_instance.capabilities:
                    capability = ServiceCapability(
                        name=cap_name,
                        description=f"Capability: {cap_name}",
                        input_types=["any"],
                        output_types=["any"]
                    )
                    capabilities.append(capability)
            
            # If service_instance is a dict with capabilities
            elif isinstance(service_instance, dict) and 'capabilities' in service_instance:
                for cap_name in service_instance['capabilities']:
                    capability = ServiceCapability(
                        name=cap_name,
                        description=f"Capability: {cap_name}",
                        input_types=["any"],
                        output_types=["any"]
                    )
                    capabilities.append(capability)
            
            # Default capability based on service name
            else:
                service_name = getattr(service_instance, 'service_name', 'unknown')
                capability = ServiceCapability(
                    name=service_name,
                    description=f"Service: {service_name}",
                    input_types=["any"],
                    output_types=["any"]
                )
                capabilities.append(capability)
                
        except Exception as e:
            logger.warning(f"Failed to extract capabilities from service instance: {e}")
            # Add default capability
            capability = ServiceCapability(
                name="default",
                description="Default capability",
                input_types=["any"],
                output_types=["any"]
            )
            capabilities.append(capability)
        
        return capabilities
    
    def _extract_dependencies(self, service_instance: Any) -> List[ServiceDependency]:
        """Extract dependencies from service instance"""
        dependencies = []
        
        try:
            # If service_instance has dependencies attribute
            if hasattr(service_instance, 'dependencies') and service_instance.dependencies:
                for dep_name in service_instance.dependencies:
                    dependency = ServiceDependency(
                        service_name=dep_name,
                        dependency_type="required",
                        description=f"Dependency on {dep_name}"
                    )
                    dependencies.append(dependency)
            
            # If service_instance is a dict with dependencies
            elif isinstance(service_instance, dict) and 'dependencies' in service_instance:
                for dep_name in service_instance['dependencies']:
                    dependency = ServiceDependency(
                        service_name=dep_name,
                        dependency_type="required",
                        description=f"Dependency on {dep_name}"
                    )
                    dependencies.append(dependency)
                    
        except Exception as e:
            logger.warning(f"Failed to extract dependencies from service instance: {e}")
        
        return dependencies

