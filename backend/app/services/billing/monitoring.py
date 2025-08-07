"""
Monitoring and alerting system for billing operations.
"""

import logging
import time
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict, deque
import asyncio

from app.core.config import settings

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MetricType(Enum):
    """Types of metrics to monitor."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class Alert:
    """Alert definition."""
    name: str
    severity: AlertSeverity
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.utcnow())
    resolved: bool = False


@dataclass
class Metric:
    """Metric definition."""
    name: str
    type: MetricType
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.utcnow())


class BillingMonitor:
    """Comprehensive monitoring for billing operations."""
    
    def __init__(self):
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.alerts: list[Alert] = []
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = defaultdict(float)
        self.timers: Dict[str, list[float]] = defaultdict(list)
        
        # Alert thresholds
        self.thresholds = {
            'payment_failure_rate': 0.05,  # 5%
            'webhook_failure_rate': 0.02,  # 2%
            'subscription_churn_rate': 0.10,  # 10%
            'api_error_rate': 0.01,  # 1%
            'response_time_p95': 2.0,  # 2 seconds
            'stripe_api_errors': 10,  # per hour
        }
        
        # Time windows for calculations
        self.time_windows = {
            'short': timedelta(minutes=5),
            'medium': timedelta(hours=1),
            'long': timedelta(hours=24)
        }
    
    def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a metric value."""
        metric = Metric(
            name=name,
            type=metric_type,
            value=value,
            labels=labels or {}
        )
        
        self.metrics[name].append(metric)
        
        # Update aggregated metrics
        if metric_type == MetricType.COUNTER:
            self.counters[name] += value
        elif metric_type == MetricType.GAUGE:
            self.gauges[name] = value
        elif metric_type == MetricType.TIMER:
            self.timers[name].append(value)
            # Keep only recent values
            if len(self.timers[name]) > 1000:
                self.timers[name] = self.timers[name][-1000:]
        
        # Check for alerts
        self._check_alerts(name, value, metric_type)
    
    def increment_counter(self, name: str, value: float = 1, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric."""
        self.record_metric(name, value, MetricType.COUNTER, labels)
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge metric."""
        self.record_metric(name, value, MetricType.GAUGE, labels)
    
    def record_timer(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record a timer metric."""
        self.record_metric(name, value, MetricType.TIMER, labels)
    
    def get_metric_stats(self, name: str, window: str = 'medium') -> Dict[str, Any]:
        """Get statistics for a metric over a time window."""
        if name not in self.metrics:
            return {}
        
        window_delta = self.time_windows.get(window, self.time_windows['medium'])
        cutoff_time = datetime.utcnow() - window_delta
        
        # Filter metrics within time window
        recent_metrics = [
            m for m in self.metrics[name] 
            if m.timestamp >= cutoff_time
        ]
        
        if not recent_metrics:
            return {}
        
        values = [m.value for m in recent_metrics]
        
        return {
            'count': len(values),
            'sum': sum(values),
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'p95': self._percentile(values, 95),
            'p99': self._percentile(values, 99),
            'window': window,
            'start_time': cutoff_time.isoformat(),
            'end_time': datetime.utcnow().isoformat()
        }
    
    def _percentile(self, values: list[float], percentile: float) -> float:
        """Calculate percentile of values."""
        if not values:
            return 0
        
        sorted_values = sorted(values)
        index = int((percentile / 100) * len(sorted_values))
        index = min(index, len(sorted_values) - 1)
        return sorted_values[index]
    
    def _check_alerts(self, metric_name: str, value: float, metric_type: MetricType) -> None:
        """Check if metric triggers any alerts."""
        
        # Payment failure rate
        if metric_name == 'payment_failed':
            self._check_payment_failure_rate()
        
        # Webhook failure rate
        elif metric_name == 'webhook_failed':
            self._check_webhook_failure_rate()
        
        # API response time
        elif metric_name == 'api_response_time':
            self._check_response_time(value)
        
        # Stripe API errors
        elif metric_name == 'stripe_api_error':
            self._check_stripe_api_errors()
        
        # Subscription events
        elif metric_name in ['subscription_created', 'subscription_cancelled']:
            self._check_subscription_health()
    
    def _check_payment_failure_rate(self) -> None:
        """Check payment failure rate and alert if necessary."""
        failed_stats = self.get_metric_stats('payment_failed', 'medium')
        succeeded_stats = self.get_metric_stats('payment_succeeded', 'medium')
        
        if not failed_stats or not succeeded_stats:
            return
        
        total_payments = failed_stats['sum'] + succeeded_stats['sum']
        if total_payments < 10:  # Not enough data
            return
        
        failure_rate = failed_stats['sum'] / total_payments
        
        if failure_rate > self.thresholds['payment_failure_rate']:
            self._create_alert(
                name="High Payment Failure Rate",
                severity=AlertSeverity.HIGH if failure_rate > 0.1 else AlertSeverity.MEDIUM,
                message=f"Payment failure rate is {failure_rate:.2%}",
                details={
                    'failure_rate': failure_rate,
                    'failed_payments': failed_stats['sum'],
                    'total_payments': total_payments,
                    'threshold': self.thresholds['payment_failure_rate']
                }
            )
    
    def _check_webhook_failure_rate(self) -> None:
        """Check webhook failure rate and alert if necessary."""
        failed_stats = self.get_metric_stats('webhook_failed', 'medium')
        processed_stats = self.get_metric_stats('webhook_processed', 'medium')
        
        if not failed_stats or not processed_stats:
            return
        
        total_webhooks = failed_stats['sum'] + processed_stats['sum']
        if total_webhooks < 5:  # Not enough data
            return
        
        failure_rate = failed_stats['sum'] / total_webhooks
        
        if failure_rate > self.thresholds['webhook_failure_rate']:
            self._create_alert(
                name="High Webhook Failure Rate",
                severity=AlertSeverity.HIGH,
                message=f"Webhook failure rate is {failure_rate:.2%}",
                details={
                    'failure_rate': failure_rate,
                    'failed_webhooks': failed_stats['sum'],
                    'total_webhooks': total_webhooks,
                    'threshold': self.thresholds['webhook_failure_rate']
                }
            )
    
    def _check_response_time(self, value: float) -> None:
        """Check API response time and alert if necessary."""
        if value > 10.0:  # Individual request too slow
            self._create_alert(
                name="Slow API Response",
                severity=AlertSeverity.MEDIUM,
                message=f"API response took {value:.2f} seconds",
                details={'response_time': value}
            )
        
        # Check P95 response time
        stats = self.get_metric_stats('api_response_time', 'short')
        if stats and stats['p95'] > self.thresholds['response_time_p95']:
            self._create_alert(
                name="High API Response Time",
                severity=AlertSeverity.MEDIUM,
                message=f"P95 response time is {stats['p95']:.2f}s",
                details={
                    'p95_response_time': stats['p95'],
                    'threshold': self.thresholds['response_time_p95'],
                    'stats': stats
                }
            )
    
    def _check_stripe_api_errors(self) -> None:
        """Check Stripe API error rate and alert if necessary."""
        stats = self.get_metric_stats('stripe_api_error', 'medium')
        
        if stats and stats['sum'] > self.thresholds['stripe_api_errors']:
            self._create_alert(
                name="High Stripe API Error Rate",
                severity=AlertSeverity.HIGH,
                message=f"{stats['sum']} Stripe API errors in the last hour",
                details={
                    'error_count': stats['sum'],
                    'threshold': self.thresholds['stripe_api_errors'],
                    'stats': stats
                }
            )
    
    def _check_subscription_health(self) -> None:
        """Check subscription health metrics."""
        created_stats = self.get_metric_stats('subscription_created', 'long')
        cancelled_stats = self.get_metric_stats('subscription_cancelled', 'long')
        
        if not created_stats or not cancelled_stats:
            return
        
        if created_stats['sum'] == 0:
            return
        
        churn_rate = cancelled_stats['sum'] / created_stats['sum']
        
        if churn_rate > self.thresholds['subscription_churn_rate']:
            self._create_alert(
                name="High Subscription Churn Rate",
                severity=AlertSeverity.MEDIUM,
                message=f"Daily churn rate is {churn_rate:.2%}",
                details={
                    'churn_rate': churn_rate,
                    'cancelled': cancelled_stats['sum'],
                    'created': created_stats['sum'],
                    'threshold': self.thresholds['subscription_churn_rate']
                }
            )
    
    def _create_alert(
        self,
        name: str,
        severity: AlertSeverity,
        message: str,
        details: Dict[str, Any]
    ) -> None:
        """Create and log an alert."""
        alert = Alert(
            name=name,
            severity=severity,
            message=message,
            details=details
        )
        
        self.alerts.append(alert)
        
        # Log the alert
        log_level = {
            AlertSeverity.LOW: logging.INFO,
            AlertSeverity.MEDIUM: logging.WARNING,
            AlertSeverity.HIGH: logging.ERROR,
            AlertSeverity.CRITICAL: logging.CRITICAL
        }.get(severity, logging.WARNING)
        
        logger.log(
            log_level,
            f"ALERT [{severity.value.upper()}] {name}: {message}",
            extra={
                'alert_name': name,
                'alert_severity': severity.value,
                'alert_details': details,
                'monitor': 'billing'
            }
        )
        
        # Send external notifications for high/critical alerts
        if severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]:
            self._send_external_alert(alert)
    
    def _send_external_alert(self, alert: Alert) -> None:
        """Send alert to external monitoring systems."""
        # In production, this would integrate with:
        # - Slack/Discord webhooks
        # - PagerDuty
        # - Email notifications
        # - SMS alerts
        
        logger.critical(
            f"EXTERNAL ALERT TRIGGERED: {alert.name}",
            extra={
                'alert': alert.__dict__,
                'external_notification': True
            }
        )
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall system health status."""
        recent_alerts = [
            a for a in self.alerts 
            if not a.resolved and (datetime.utcnow() - a.timestamp) < timedelta(hours=1)
        ]
        
        critical_alerts = [a for a in recent_alerts if a.severity == AlertSeverity.CRITICAL]
        high_alerts = [a for a in recent_alerts if a.severity == AlertSeverity.HIGH]
        
        if critical_alerts:
            status = "critical"
        elif high_alerts:
            status = "degraded"
        elif recent_alerts:
            status = "warning"
        else:
            status = "healthy"
        
        return {
            'status': status,
            'alerts': {
                'total': len(recent_alerts),
                'critical': len(critical_alerts),
                'high': len(high_alerts),
                'medium': len([a for a in recent_alerts if a.severity == AlertSeverity.MEDIUM]),
                'low': len([a for a in recent_alerts if a.severity == AlertSeverity.LOW])
            },
            'metrics': {
                'counters': dict(self.counters),
                'gauges': dict(self.gauges),
                'active_timers': len(self.timers)
            },
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Get metrics for monitoring dashboard."""
        return {
            'payment_metrics': {
                'success_rate': self._calculate_success_rate('payment'),
                'total_volume': self.get_metric_stats('payment_amount', 'long'),
                'avg_response_time': self.get_metric_stats('payment_response_time', 'medium')
            },
            'subscription_metrics': {
                'active_subscriptions': self.gauges.get('active_subscriptions', 0),
                'new_subscriptions': self.get_metric_stats('subscription_created', 'long'),
                'churn_rate': self._calculate_churn_rate()
            },
            'api_metrics': {
                'request_rate': self.get_metric_stats('api_request', 'medium'),
                'error_rate': self._calculate_success_rate('api'),
                'response_time': self.get_metric_stats('api_response_time', 'medium')
            },
            'webhook_metrics': {
                'processed': self.get_metric_stats('webhook_processed', 'medium'),
                'failed': self.get_metric_stats('webhook_failed', 'medium'),
                'success_rate': self._calculate_success_rate('webhook')
            }
        }
    
    def _calculate_success_rate(self, prefix: str) -> float:
        """Calculate success rate for operations."""
        success_stats = self.get_metric_stats(f'{prefix}_succeeded', 'medium')
        failed_stats = self.get_metric_stats(f'{prefix}_failed', 'medium')
        
        if not success_stats or not failed_stats:
            return 0.0
        
        total = success_stats['sum'] + failed_stats['sum']
        return (success_stats['sum'] / total) if total > 0 else 0.0
    
    def _calculate_churn_rate(self) -> float:
        """Calculate subscription churn rate."""
        created_stats = self.get_metric_stats('subscription_created', 'long')
        cancelled_stats = self.get_metric_stats('subscription_cancelled', 'long')
        
        if not created_stats or not cancelled_stats or created_stats['sum'] == 0:
            return 0.0
        
        return cancelled_stats['sum'] / created_stats['sum']


class PerformanceTimer:
    """Context manager for timing operations."""
    
    def __init__(self, monitor: BillingMonitor, metric_name: str, labels: Optional[Dict[str, str]] = None):
        self.monitor = monitor
        self.metric_name = metric_name
        self.labels = labels or {}
        self.start_time: Optional[float] = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration = time.time() - self.start_time
            self.monitor.record_timer(self.metric_name, duration, self.labels)


# Global monitor instance
billing_monitor = BillingMonitor()


# Convenience functions
def record_payment_success(amount: float, currency: str = 'USD', payment_method: str = 'card'):
    """Record a successful payment."""
    billing_monitor.increment_counter('payment_succeeded', labels={'payment_method': payment_method})
    billing_monitor.increment_counter('payment_amount', amount, labels={'currency': currency})


def record_payment_failure(reason: str, payment_method: str = 'card'):
    """Record a failed payment."""
    billing_monitor.increment_counter('payment_failed', labels={'reason': reason, 'payment_method': payment_method})


def record_subscription_event(event_type: str, plan: str):
    """Record a subscription event."""
    billing_monitor.increment_counter(f'subscription_{event_type}', labels={'plan': plan})


def record_webhook_event(event_type: str, processed: bool):
    """Record a webhook processing event."""
    if processed:
        billing_monitor.increment_counter('webhook_processed', labels={'event_type': event_type})
    else:
        billing_monitor.increment_counter('webhook_failed', labels={'event_type': event_type})


def record_api_request(endpoint: str, status_code: int, response_time: float):
    """Record an API request."""
    billing_monitor.increment_counter('api_request', labels={'endpoint': endpoint, 'status': str(status_code)})
    billing_monitor.record_timer('api_response_time', response_time, labels={'endpoint': endpoint})
    
    if status_code >= 400:
        billing_monitor.increment_counter('api_error', labels={'endpoint': endpoint, 'status': str(status_code)})


def time_operation(operation_name: str, labels: Optional[Dict[str, str]] = None) -> PerformanceTimer:
    """Create a timer for an operation."""
    return PerformanceTimer(billing_monitor, f'{operation_name}_duration', labels)