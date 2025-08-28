"""
Service Container and Dependency Injection System

This module provides a centralized service container for managing dependencies,
service lifecycle, and dependency injection throughout the AutoDMCA application.

The container handles:
- Service registration and resolution
- Singleton and transient service lifecycles
- Circular dependency detection
- Service health monitoring
- Configuration management
"""

import logging
from typing import Any, Dict, Type, TypeVar, Callable, Optional, Union, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import inspect
import asyncio
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ServiceLifetime(Enum):
    """Service lifetime management options."""
    SINGLETON = "singleton"    # One instance for the entire application
    SCOPED = "scoped"         # One instance per scope (e.g., per request)
    TRANSIENT = "transient"   # New instance every time


class ServiceStatus(Enum):
    """Service health status."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    STOPPING = "stopping"
    STOPPED = "stopped"


@dataclass
class ServiceDescriptor:
    """Describes a service registration in the container."""
    service_type: Type
    implementation: Union[Type, Callable]
    lifetime: ServiceLifetime
    dependencies: List[Type] = field(default_factory=list)
    instance: Optional[Any] = None
    factory: Optional[Callable] = None
    initialized: bool = False
    status: ServiceStatus = ServiceStatus.STOPPED
    created_at: Optional[datetime] = None
    last_accessed: Optional[datetime] = None
    access_count: int = 0
    health_check: Optional[Callable] = None


class ServiceContainer:
    """
    Central service container for dependency injection and service lifecycle management.
    
    Features:
    - Service registration with different lifetimes
    - Automatic dependency resolution
    - Circular dependency detection
    - Health monitoring
    - Async service initialization
    """
    
    def __init__(self):
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._scoped_instances: Dict[str, Dict[Type, Any]] = {}
        self._initialization_lock = asyncio.Lock()
        self._startup_hooks: List[Callable] = []
        self._shutdown_hooks: List[Callable] = []
        self._health_checks: Dict[Type, Callable] = {}
        
    def register_singleton(self, service_type: Type[T], implementation: Union[Type[T], T, Callable[[], T]]) -> 'ServiceContainer':
        """Register a singleton service."""
        return self.register(service_type, implementation, ServiceLifetime.SINGLETON)
    
    def register_scoped(self, service_type: Type[T], implementation: Union[Type[T], Callable[[], T]]) -> 'ServiceContainer':
        """Register a scoped service.""" 
        return self.register(service_type, implementation, ServiceLifetime.SCOPED)
    
    def register_transient(self, service_type: Type[T], implementation: Union[Type[T], Callable[[], T]]) -> 'ServiceContainer':
        """Register a transient service."""
        return self.register(service_type, implementation, ServiceLifetime.TRANSIENT)
    
    def register(self, service_type: Type[T], implementation: Union[Type[T], T, Callable[[], T]], 
                 lifetime: ServiceLifetime) -> 'ServiceContainer':
        """
        Register a service with the container.
        
        Args:
            service_type: The service interface or base type
            implementation: The concrete implementation, instance, or factory function
            lifetime: Service lifetime management
        
        Returns:
            Self for method chaining
        """
        if service_type in self._services:
            logger.warning(f"Service {service_type.__name__} is already registered. Overwriting.")
        
        # Analyze dependencies
        dependencies = self._analyze_dependencies(implementation)
        
        # If implementation is already an instance, store it directly
        instance = None
        factory = None
        if not inspect.isclass(implementation) and not callable(implementation):
            instance = implementation
        elif callable(implementation) and not inspect.isclass(implementation):
            factory = implementation
        
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation,
            lifetime=lifetime,
            dependencies=dependencies,
            instance=instance,
            factory=factory,
            created_at=datetime.utcnow() if instance else None
        )
        
        self._services[service_type] = descriptor
        
        logger.info(f"Registered service {service_type.__name__} as {lifetime.value}")
        return self
    
    def register_factory(self, service_type: Type[T], factory: Callable[[], T], 
                        lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT) -> 'ServiceContainer':
        """Register a factory function for creating service instances."""
        return self.register(service_type, factory, lifetime)
    
    def register_instance(self, service_type: Type[T], instance: T) -> 'ServiceContainer':
        """Register a specific instance as a singleton."""
        return self.register(service_type, instance, ServiceLifetime.SINGLETON)
    
    async def get(self, service_type: Type[T], scope_id: Optional[str] = None) -> T:
        """
        Resolve and return a service instance.
        
        Args:
            service_type: The service type to resolve
            scope_id: Optional scope identifier for scoped services
            
        Returns:
            Service instance
        """
        if service_type not in self._services:
            raise ValueError(f"Service {service_type.__name__} is not registered")
        
        descriptor = self._services[service_type]
        descriptor.last_accessed = datetime.utcnow()
        descriptor.access_count += 1
        
        # Return existing singleton instance
        if descriptor.lifetime == ServiceLifetime.SINGLETON and descriptor.instance is not None:
            return descriptor.instance
        
        # Return existing scoped instance
        if descriptor.lifetime == ServiceLifetime.SCOPED and scope_id:
            if scope_id in self._scoped_instances and service_type in self._scoped_instances[scope_id]:
                return self._scoped_instances[scope_id][service_type]
        
        # Create new instance
        async with self._initialization_lock:
            instance = await self._create_instance(descriptor, scope_id)
            
            # Store singleton instance
            if descriptor.lifetime == ServiceLifetime.SINGLETON:
                descriptor.instance = instance
                descriptor.initialized = True
                descriptor.status = ServiceStatus.HEALTHY
            
            # Store scoped instance
            elif descriptor.lifetime == ServiceLifetime.SCOPED and scope_id:
                if scope_id not in self._scoped_instances:
                    self._scoped_instances[scope_id] = {}
                self._scoped_instances[scope_id][service_type] = instance
            
            return instance
    
    async def get_required(self, service_type: Type[T], scope_id: Optional[str] = None) -> T:
        """Get a required service, raising an exception if not found."""
        try:
            return await self.get(service_type, scope_id)
        except ValueError:
            raise RuntimeError(f"Required service {service_type.__name__} is not available")
    
    def try_get(self, service_type: Type[T], scope_id: Optional[str] = None) -> Optional[T]:
        """Try to get a service, returning None if not available."""
        try:
            return asyncio.create_task(self.get(service_type, scope_id))
        except (ValueError, RuntimeError):
            return None
    
    async def _create_instance(self, descriptor: ServiceDescriptor, scope_id: Optional[str] = None) -> Any:
        """Create a new service instance with dependency injection."""
        descriptor.status = ServiceStatus.STARTING
        
        try:
            # Use factory function if available
            if descriptor.factory:
                if asyncio.iscoroutinefunction(descriptor.factory):
                    instance = await descriptor.factory()
                else:
                    instance = descriptor.factory()
                logger.debug(f"Created {descriptor.service_type.__name__} instance via factory")
                return instance
            
            # Use existing instance
            if descriptor.instance is not None:
                return descriptor.instance
            
            # Create instance via constructor injection
            implementation = descriptor.implementation
            if inspect.isclass(implementation):
                # Resolve constructor dependencies
                dependencies = await self._resolve_dependencies(descriptor.dependencies, scope_id)
                
                # Create instance with dependencies
                if asyncio.iscoroutinefunction(implementation.__init__):
                    instance = implementation(**dependencies)
                    if hasattr(instance, '__ainit__'):
                        await instance.__ainit__()
                else:
                    instance = implementation(**dependencies)
                
                logger.debug(f"Created {descriptor.service_type.__name__} instance with {len(dependencies)} dependencies")
                return instance
            
            raise ValueError(f"Cannot create instance of {descriptor.service_type.__name__}")
            
        except Exception as e:
            descriptor.status = ServiceStatus.UNHEALTHY
            logger.error(f"Failed to create {descriptor.service_type.__name__}: {e}")
            raise
    
    async def _resolve_dependencies(self, dependencies: List[Type], scope_id: Optional[str] = None) -> Dict[str, Any]:
        """Resolve all dependencies for a service."""
        resolved = {}
        
        for dep_type in dependencies:
            try:
                # Check for circular dependencies
                if self._has_circular_dependency(dep_type, set()):
                    logger.warning(f"Potential circular dependency detected for {dep_type.__name__}")
                
                dependency_instance = await self.get(dep_type, scope_id)
                
                # Use parameter name as key (convert type name to snake_case)
                param_name = self._type_to_param_name(dep_type)
                resolved[param_name] = dependency_instance
                
            except Exception as e:
                logger.error(f"Failed to resolve dependency {dep_type.__name__}: {e}")
                # Continue with other dependencies
        
        return resolved
    
    def _analyze_dependencies(self, implementation: Union[Type, Callable]) -> List[Type]:
        """Analyze constructor parameters to determine dependencies."""
        dependencies = []
        
        if inspect.isclass(implementation):
            # Analyze constructor signature
            sig = inspect.signature(implementation.__init__)
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                    
                if param.annotation and param.annotation != inspect.Parameter.empty:
                    # Check if annotation is a registered service type
                    if param.annotation in self._services or hasattr(param.annotation, '__origin__'):
                        dependencies.append(param.annotation)
        
        return dependencies
    
    def _has_circular_dependency(self, service_type: Type, visited: set) -> bool:
        """Check for circular dependencies."""
        if service_type in visited:
            return True
        
        if service_type not in self._services:
            return False
        
        visited.add(service_type)
        
        descriptor = self._services[service_type]
        for dep in descriptor.dependencies:
            if self._has_circular_dependency(dep, visited.copy()):
                return True
        
        return False
    
    def _type_to_param_name(self, type_obj: Type) -> str:
        """Convert a type name to parameter name convention."""
        name = type_obj.__name__
        # Convert CamelCase to snake_case
        result = ''.join(['_' + c.lower() if c.isupper() and i > 0 else c.lower() 
                         for i, c in enumerate(name)])
        return result
    
    @asynccontextmanager
    async def scope(self, scope_id: str):
        """Create a service scope for scoped service instances."""
        logger.debug(f"Starting service scope: {scope_id}")
        try:
            yield scope_id
        finally:
            # Cleanup scoped instances
            if scope_id in self._scoped_instances:
                scoped_services = self._scoped_instances.pop(scope_id)
                
                # Call cleanup methods on scoped services
                for service_instance in scoped_services.values():
                    if hasattr(service_instance, '__aexit__'):
                        try:
                            await service_instance.__aexit__(None, None, None)
                        except Exception as e:
                            logger.error(f"Error during scoped service cleanup: {e}")
                    elif hasattr(service_instance, 'close'):
                        try:
                            if asyncio.iscoroutinefunction(service_instance.close):
                                await service_instance.close()
                            else:
                                service_instance.close()
                        except Exception as e:
                            logger.error(f"Error during scoped service cleanup: {e}")
                
                logger.debug(f"Cleaned up service scope: {scope_id} ({len(scoped_services)} services)")
    
    async def start_services(self):
        """Start all registered services and run startup hooks."""
        logger.info("Starting service container...")
        
        # Initialize singleton services
        for service_type, descriptor in self._services.items():
            if descriptor.lifetime == ServiceLifetime.SINGLETON:
                try:
                    await self.get(service_type)
                    logger.info(f"Started singleton service: {service_type.__name__}")
                except Exception as e:
                    logger.error(f"Failed to start service {service_type.__name__}: {e}")
        
        # Run startup hooks
        for hook in self._startup_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook()
                else:
                    hook()
                logger.debug("Executed startup hook")
            except Exception as e:
                logger.error(f"Startup hook failed: {e}")
        
        logger.info("Service container started successfully")
    
    async def stop_services(self):
        """Stop all services and run shutdown hooks."""
        logger.info("Stopping service container...")
        
        # Run shutdown hooks
        for hook in self._shutdown_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook()
                else:
                    hook()
                logger.debug("Executed shutdown hook")
            except Exception as e:
                logger.error(f"Shutdown hook failed: {e}")
        
        # Stop singleton services
        for service_type, descriptor in self._services.items():
            if descriptor.instance is not None:
                try:
                    if hasattr(descriptor.instance, '__aexit__'):
                        await descriptor.instance.__aexit__(None, None, None)
                    elif hasattr(descriptor.instance, 'close'):
                        if asyncio.iscoroutinefunction(descriptor.instance.close):
                            await descriptor.instance.close()
                        else:
                            descriptor.instance.close()
                    
                    descriptor.status = ServiceStatus.STOPPED
                    logger.info(f"Stopped service: {service_type.__name__}")
                except Exception as e:
                    logger.error(f"Error stopping service {service_type.__name__}: {e}")
        
        # Clear all scoped instances
        for scope_id in list(self._scoped_instances.keys()):
            try:
                async with self.scope(scope_id):
                    pass  # Cleanup happens in context manager exit
            except Exception as e:
                logger.error(f"Error cleaning up scope {scope_id}: {e}")
        
        logger.info("Service container stopped")
    
    def add_startup_hook(self, hook: Callable):
        """Add a function to run during service container startup."""
        self._startup_hooks.append(hook)
    
    def add_shutdown_hook(self, hook: Callable):
        """Add a function to run during service container shutdown."""
        self._shutdown_hooks.append(hook)
    
    def add_health_check(self, service_type: Type, health_check: Callable):
        """Add a health check function for a service."""
        self._health_checks[service_type] = health_check
    
    async def check_health(self) -> Dict[str, Any]:
        """Run health checks on all registered services."""
        health_status = {
            "overall_healthy": True,
            "services": {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        for service_type, descriptor in self._services.items():
            service_health = {
                "status": descriptor.status.value,
                "access_count": descriptor.access_count,
                "last_accessed": descriptor.last_accessed.isoformat() if descriptor.last_accessed else None,
                "healthy": True
            }
            
            # Run custom health check if available
            if service_type in self._health_checks:
                try:
                    health_check = self._health_checks[service_type]
                    if asyncio.iscoroutinefunction(health_check):
                        check_result = await health_check()
                    else:
                        check_result = health_check()
                    
                    service_health["healthy"] = check_result
                    if not check_result:
                        health_status["overall_healthy"] = False
                        
                except Exception as e:
                    logger.error(f"Health check failed for {service_type.__name__}: {e}")
                    service_health["healthy"] = False
                    service_health["error"] = str(e)
                    health_status["overall_healthy"] = False
            
            health_status["services"][service_type.__name__] = service_health
        
        return health_status
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get information about all registered services."""
        return {
            service_type.__name__: {
                "lifetime": descriptor.lifetime.value,
                "status": descriptor.status.value,
                "initialized": descriptor.initialized,
                "access_count": descriptor.access_count,
                "dependencies": [dep.__name__ for dep in descriptor.dependencies],
                "created_at": descriptor.created_at.isoformat() if descriptor.created_at else None,
                "last_accessed": descriptor.last_accessed.isoformat() if descriptor.last_accessed else None
            }
            for service_type, descriptor in self._services.items()
        }


# Global service container instance
container = ServiceContainer()


# Dependency injection decorators for convenience
def inject(service_type: Type[T]) -> T:
    """Dependency injection decorator for function parameters."""
    def decorator(func):
        # This would be implemented to automatically inject dependencies
        # For now, it's a placeholder that documents the intent
        return func
    return decorator


def service(lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT):
    """Class decorator to automatically register a service."""
    def decorator(cls):
        container.register(cls, cls, lifetime)
        return cls
    return decorator


# Export the container and key utilities
__all__ = [
    'ServiceContainer',
    'ServiceLifetime', 
    'ServiceStatus',
    'container',
    'inject',
    'service'
]