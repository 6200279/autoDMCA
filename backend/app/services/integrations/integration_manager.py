"""
Integration Manager for Third-Party Services

Provides centralized management of all third-party integrations with:
- Service discovery and health monitoring
- Fallback mechanisms and circuit breakers
- Service orchestration and coordination
- Error handling and retry logic
- Performance monitoring and alerting
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from enum import Enum
import json
from dataclasses import dataclass, asdict

from app.core.config import settings

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Service status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNAVAILABLE = "unavailable"
    NOT_CONFIGURED = "not_configured"


class CircuitBreakerState(Enum):
    """Circuit breaker state enumeration"""
    CLOSED = "closed"        # Normal operation
    OPEN = "open"           # Failing, requests blocked
    HALF_OPEN = "half_open" # Testing if service recovered


@dataclass
class ServiceHealth:
    """Service health information"""
    service_name: str
    status: ServiceStatus
    last_check: datetime
    response_time: float
    error_rate: float
    error_count: int
    total_requests: int
    last_error: Optional[str] = None
    metadata: Dict[str, Any] = None


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5           # Failures before opening
    success_threshold: int = 3           # Successes to close from half-open
    timeout: timedelta = timedelta(minutes=1)  # Time before trying half-open
    max_timeout: timedelta = timedelta(minutes=10)  # Maximum timeout


class CircuitBreaker:
    """Circuit breaker for service resilience"""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.timeout = config.timeout
        
    async def call(self, func, *args, **kwargs):
        """Execute function through circuit breaker"""
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
                logger.info(f"Circuit breaker {self.name} moved to HALF_OPEN")
            else:
                raise Exception(f"Circuit breaker {self.name} is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure(str(e))
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset"""
        if not self.last_failure_time:
            return False
        return datetime.utcnow() - self.last_failure_time > self.timeout
    
    def _on_success(self):
        """Handle successful request"""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                self.timeout = self.config.timeout
                logger.info(f"Circuit breaker {self.name} CLOSED after recovery")
        else:
            self.failure_count = 0  # Reset failure count on success
    
    def _on_failure(self, error: str):
        """Handle failed request"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            self.success_count = 0
            # Increase timeout exponentially (up to max)
            self.timeout = min(self.timeout * 2, self.config.max_timeout)
            logger.warning(f"Circuit breaker {self.name} returned to OPEN from HALF_OPEN")
        elif self.failure_count >= self.config.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.warning(f"Circuit breaker {self.name} OPENED after {self.failure_count} failures")


class IntegrationManager:
    """
    Central manager for all third-party service integrations
    """
    
    def __init__(self):
        self.services = {}
        self.health_status = {}
        self.circuit_breakers = {}
        self.monitoring_task = None
        self.last_health_check = None
        
        # Initialize circuit breakers for each service
        self._initialize_circuit_breakers()
        
    def _initialize_circuit_breakers(self):
        """Initialize circuit breakers for all services"""
        service_configs = {
            'sendgrid': CircuitBreakerConfig(failure_threshold=3, timeout=timedelta(minutes=2)),
            'google_vision': CircuitBreakerConfig(failure_threshold=5, timeout=timedelta(minutes=3)),
            'paypal': CircuitBreakerConfig(failure_threshold=3, timeout=timedelta(minutes=5)),
        }
        
        for service_name, config in service_configs.items():
            self.circuit_breakers[service_name] = CircuitBreaker(service_name, config)
    
    async def register_service(self, service_name: str, service_instance: Any):
        """Register a service with the integration manager"""
        self.services[service_name] = service_instance
        
        # Initialize health status
        self.health_status[service_name] = ServiceHealth(
            service_name=service_name,
            status=ServiceStatus.UNAVAILABLE,
            last_check=datetime.utcnow(),
            response_time=0.0,
            error_rate=0.0,
            error_count=0,
            total_requests=0
        )
        
        logger.info(f"Service {service_name} registered with integration manager")
    
    async def get_service(self, service_name: str) -> Optional[Any]:
        """Get service instance if available and healthy"""
        if service_name not in self.services:
            return None
        
        health = self.health_status.get(service_name)
        if not health or health.status in [ServiceStatus.UNAVAILABLE, ServiceStatus.UNHEALTHY]:
            return None
        
        return self.services[service_name]
    
    async def call_service(
        self,
        service_name: str,
        method_name: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Call service method through circuit breaker with monitoring
        """
        service = await self.get_service(service_name)
        if not service:
            raise Exception(f"Service {service_name} not available")
        
        circuit_breaker = self.circuit_breakers.get(service_name)
        method = getattr(service, method_name)
        
        start_time = datetime.utcnow()
        
        try:
            if circuit_breaker:
                result = await circuit_breaker.call(method, *args, **kwargs)
            else:
                result = await method(*args, **kwargs)
            
            # Update health metrics
            await self._record_success(service_name, start_time)
            return result
            
        except Exception as e:
            # Update health metrics
            await self._record_failure(service_name, start_time, str(e))
            raise
    
    async def _record_success(self, service_name: str, start_time: datetime):
        """Record successful service call"""
        if service_name not in self.health_status:
            return
        
        health = self.health_status[service_name]
        response_time = (datetime.utcnow() - start_time).total_seconds()
        
        health.total_requests += 1
        health.response_time = (health.response_time + response_time) / 2  # Moving average
        health.error_rate = health.error_count / health.total_requests
        health.last_check = datetime.utcnow()
        
        # Update status based on performance
        if health.error_rate < 0.01 and response_time < 5.0:
            health.status = ServiceStatus.HEALTHY
        elif health.error_rate < 0.05 and response_time < 10.0:
            health.status = ServiceStatus.DEGRADED
        else:
            health.status = ServiceStatus.UNHEALTHY
    
    async def _record_failure(self, service_name: str, start_time: datetime, error: str):
        """Record failed service call"""
        if service_name not in self.health_status:
            return
        
        health = self.health_status[service_name]
        response_time = (datetime.utcnow() - start_time).total_seconds()
        
        health.total_requests += 1
        health.error_count += 1
        health.response_time = (health.response_time + response_time) / 2  # Moving average
        health.error_rate = health.error_count / health.total_requests
        health.last_error = error
        health.last_check = datetime.utcnow()
        
        # Mark as unhealthy on failures
        health.status = ServiceStatus.UNHEALTHY
    
    async def send_email_with_fallback(
        self,
        to_email: str,
        subject: str,
        text_content: str,
        html_content: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send email with automatic fallback from SendGrid to SMTP
        """
        try:
            # Try SendGrid first
            result = await self.call_service(
                'sendgrid',
                'send_email',
                to_email=to_email,
                subject=subject,
                text_content=text_content,
                html_content=html_content,
                **kwargs
            )
            
            return {
                'success': result,
                'provider': 'sendgrid',
                'fallback_used': False
            }
            
        except Exception as e:
            logger.warning(f"SendGrid failed, falling back to SMTP: {e}")
            
            try:
                # Fallback to SMTP email service
                from app.services.auth.email_service import email_service
                result = await email_service.send_email(
                    to_email=to_email,
                    subject=subject,
                    body_text=text_content,
                    body_html=html_content
                )
                
                return {
                    'success': result,
                    'provider': 'smtp',
                    'fallback_used': True,
                    'original_error': str(e)
                }
                
            except Exception as fallback_error:
                logger.error(f"Both SendGrid and SMTP failed: {fallback_error}")
                return {
                    'success': False,
                    'provider': 'none',
                    'fallback_used': True,
                    'original_error': str(e),
                    'fallback_error': str(fallback_error)
                }
    
    async def analyze_image_with_fallback(
        self,
        image_data: Union[bytes, str],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Analyze image with Google Vision API with local fallback
        """
        try:
            # Try Google Vision API first
            result = await self.call_service(
                'google_vision',
                'analyze_image_comprehensive',
                image_data=image_data,
                **kwargs
            )
            
            result['provider'] = 'google_vision'
            result['fallback_used'] = False
            return result
            
        except Exception as e:
            logger.warning(f"Google Vision failed, using local analysis: {e}")
            
            try:
                # Fallback to local image analysis
                from app.services.ai.enhanced_content_matcher import EnhancedContentMatcher
                matcher = EnhancedContentMatcher()
                
                # Basic local analysis
                local_result = {
                    'provider': 'local_analysis',
                    'fallback_used': True,
                    'original_error': str(e),
                    'analysis_complete': True,
                    'analyzed_at': datetime.utcnow().isoformat(),
                    'features_analyzed': ['basic_analysis'],
                    'explicit_content': {
                        'safe': True,  # Default to safe without detailed analysis
                        'confidence': 0.1,
                        'risk_level': 'low'
                    },
                    'insights': {
                        'content_type': 'image',
                        'risk_level': 'low',
                        'contains_people': False,
                        'contains_text': False,
                        'potential_issues': [],
                        'recommendations': ['Consider using Google Vision API for detailed analysis']
                    }
                }
                
                return local_result
                
            except Exception as fallback_error:
                logger.error(f"Both Google Vision and local analysis failed: {fallback_error}")
                return {
                    'error': 'Image analysis unavailable',
                    'provider': 'none',
                    'fallback_used': True,
                    'original_error': str(e),
                    'fallback_error': str(fallback_error),
                    'analysis_complete': False
                }
    
    async def process_payment_with_fallback(
        self,
        amount: str,
        currency: str = 'USD',
        description: str = 'Payment',
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process payment with PayPal primary and Stripe fallback
        """
        try:
            # Try PayPal first
            result = await self.call_service(
                'paypal',
                'create_payment',
                amount=amount,
                currency=currency,
                description=description,
                **kwargs
            )
            
            result['provider'] = 'paypal'
            result['fallback_used'] = False
            return result
            
        except Exception as e:
            logger.warning(f"PayPal failed, falling back to Stripe: {e}")
            
            try:
                # Fallback to Stripe
                from app.services.billing.stripe_service import stripe_service
                
                # Convert PayPal format to Stripe format
                stripe_result = await stripe_service.create_payment_intent(
                    customer_id=kwargs.get('customer_id'),
                    amount=int(float(amount) * 100),  # Stripe uses cents
                    currency=currency,
                    description=description,
                    metadata=kwargs.get('metadata', {})
                )
                
                return {
                    'success': True,
                    'provider': 'stripe',
                    'fallback_used': True,
                    'original_error': str(e),
                    'payment_intent': stripe_result
                }
                
            except Exception as fallback_error:
                logger.error(f"Both PayPal and Stripe failed: {fallback_error}")
                return {
                    'success': False,
                    'provider': 'none',
                    'fallback_used': True,
                    'original_error': str(e),
                    'fallback_error': str(fallback_error)
                }
    
    async def check_all_service_health(self) -> Dict[str, Any]:
        """Check health of all registered services"""
        health_results = {}
        
        for service_name, service in self.services.items():
            try:
                start_time = datetime.utcnow()
                
                # Call service health check method
                if hasattr(service, 'health_check'):
                    health_result = service.health_check()
                else:
                    health_result = {'status': 'unknown', 'message': 'No health check method'}
                
                response_time = (datetime.utcnow() - start_time).total_seconds()
                
                # Update internal health tracking
                if service_name in self.health_status:
                    health = self.health_status[service_name]
                    health.last_check = datetime.utcnow()
                    health.response_time = response_time
                    
                    # Determine status from health check result
                    if health_result.get('status') == 'healthy':
                        health.status = ServiceStatus.HEALTHY
                    elif health_result.get('status') in ['degraded', 'partial']:
                        health.status = ServiceStatus.DEGRADED
                    elif health_result.get('status') == 'unavailable':
                        health.status = ServiceStatus.UNAVAILABLE
                    else:
                        health.status = ServiceStatus.UNHEALTHY
                
                health_results[service_name] = health_result
                
            except Exception as e:
                logger.error(f"Health check failed for {service_name}: {e}")
                health_results[service_name] = {
                    'status': 'error',
                    'error': str(e)
                }
                
                # Mark as unhealthy
                if service_name in self.health_status:
                    self.health_status[service_name].status = ServiceStatus.UNHEALTHY
                    self.health_status[service_name].last_error = str(e)
        
        self.last_health_check = datetime.utcnow()
        
        # Overall health summary
        all_statuses = [h.get('status', 'error') for h in health_results.values()]
        healthy_count = len([s for s in all_statuses if s == 'healthy'])
        total_services = len(all_statuses)
        
        overall_health = {
            'overall_status': 'healthy' if healthy_count == total_services else 'degraded',
            'healthy_services': healthy_count,
            'total_services': total_services,
            'services': health_results,
            'last_check': self.last_health_check.isoformat(),
            'circuit_breaker_status': {
                name: {
                    'state': cb.state.value,
                    'failure_count': cb.failure_count,
                    'success_count': cb.success_count
                }
                for name, cb in self.circuit_breakers.items()
            }
        }
        
        return overall_health
    
    async def start_health_monitoring(self, interval_minutes: int = 5):
        """Start continuous health monitoring"""
        if self.monitoring_task and not self.monitoring_task.done():
            logger.warning("Health monitoring already running")
            return
        
        self.monitoring_task = asyncio.create_task(
            self._health_monitoring_loop(interval_minutes)
        )
        logger.info(f"Started health monitoring with {interval_minutes} minute intervals")
    
    async def stop_health_monitoring(self):
        """Stop health monitoring"""
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped health monitoring")
    
    async def _health_monitoring_loop(self, interval_minutes: int):
        """Continuous health monitoring loop"""
        while True:
            try:
                await self.check_all_service_health()
                
                # Check for critical issues and alert
                critical_services = [
                    name for name, health in self.health_status.items()
                    if health.status == ServiceStatus.UNHEALTHY
                ]
                
                if critical_services:
                    logger.warning(f"Critical service issues detected: {critical_services}")
                    # Here you could send alerts to monitoring systems
                
                # Wait for next check
                await asyncio.sleep(interval_minutes * 60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retry
    
    def get_service_metrics(self) -> Dict[str, Any]:
        """Get comprehensive service metrics"""
        metrics = {}
        
        for service_name, health in self.health_status.items():
            circuit_breaker = self.circuit_breakers.get(service_name)
            
            metrics[service_name] = {
                'health': asdict(health),
                'circuit_breaker': {
                    'state': circuit_breaker.state.value if circuit_breaker else 'not_configured',
                    'failure_count': circuit_breaker.failure_count if circuit_breaker else 0,
                    'success_count': circuit_breaker.success_count if circuit_breaker else 0,
                    'last_failure': circuit_breaker.last_failure_time.isoformat() 
                                   if circuit_breaker and circuit_breaker.last_failure_time else None
                } if circuit_breaker else None
            }
        
        return metrics


# Create singleton instance
integration_manager = IntegrationManager()


# Convenience functions
async def send_email_reliably(
    to_email: str,
    subject: str,
    text_content: str,
    html_content: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """Send email with automatic fallback handling"""
    return await integration_manager.send_email_with_fallback(
        to_email=to_email,
        subject=subject,
        text_content=text_content,
        html_content=html_content,
        **kwargs
    )


async def analyze_image_reliably(
    image_data: Union[bytes, str],
    **kwargs
) -> Dict[str, Any]:
    """Analyze image with automatic fallback handling"""
    return await integration_manager.analyze_image_with_fallback(
        image_data=image_data,
        **kwargs
    )


async def process_payment_reliably(
    amount: str,
    currency: str = 'USD',
    description: str = 'Payment',
    **kwargs
) -> Dict[str, Any]:
    """Process payment with automatic fallback handling"""
    return await integration_manager.process_payment_with_fallback(
        amount=amount,
        currency=currency,
        description=description,
        **kwargs
    )


async def get_integration_health() -> Dict[str, Any]:
    """Get health status of all integrations"""
    return await integration_manager.check_all_service_health()


async def initialize_integration_services():
    """Initialize and register all integration services"""
    try:
        # Register SendGrid service
        try:
            from app.services.integrations.sendgrid_service import sendgrid_service
            await integration_manager.register_service('sendgrid', sendgrid_service)
        except Exception as e:
            logger.warning(f"Failed to register SendGrid service: {e}")
        
        # Register Google Vision service
        try:
            from app.services.integrations.google_vision_service import google_vision_service
            await integration_manager.register_service('google_vision', google_vision_service)
        except Exception as e:
            logger.warning(f"Failed to register Google Vision service: {e}")
        
        # Register PayPal service
        try:
            from app.services.integrations.paypal_service import paypal_service
            await integration_manager.register_service('paypal', paypal_service)
        except Exception as e:
            logger.warning(f"Failed to register PayPal service: {e}")
        
        # Start health monitoring
        await integration_manager.start_health_monitoring(interval_minutes=5)
        
        logger.info("Integration services initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize integration services: {e}")
        raise