"""
Dashboard Services Package

This package contains services related to dashboard functionality:
- Real-time dashboard data aggregation
- Analytics and metrics calculations
- User activity tracking
- Business intelligence services
"""

from .dashboard_service import DashboardService, dashboard_service

__all__ = [
    'DashboardService',
    'dashboard_service'
]