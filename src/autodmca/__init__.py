"""
AutoDMCA - Automated DMCA Takedown Processing System

A comprehensive system for generating compliant DMCA notices, identifying hosting providers,
sending takedown requests, and tracking status with creator anonymity protection.
"""

__version__ = "0.1.0"
__author__ = "AutoDMCA Team"

from .models.takedown import TakedownRequest, TakedownStatus
from .services.dmca_service import DMCAService
from .services.whois_service import WHOISService
from .services.email_service import EmailService
from .services.search_delisting_service import SearchDelistingService

__all__ = [
    "TakedownRequest",
    "TakedownStatus", 
    "DMCAService",
    "WHOISService",
    "EmailService",
    "SearchDelistingService",
]