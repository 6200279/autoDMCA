"""Analytics worker tasks for AutoDMCA platform."""

from .report_generator import generate_daily_reports

__all__ = [
    "generate_daily_reports"
]