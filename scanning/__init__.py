"""
Content Scanning Engine for AutoDMCA Platform

A comprehensive scanning engine that monitors the internet for copyright infringement
using multiple search strategies, AI-powered content matching, and automated DMCA processing.
"""

from .scanner import ContentScanner
from .processors import (
    FaceRecognitionProcessor,
    ImageHashProcessor, 
    ContentMatcher
)
from .crawlers import (
    SearchEngineAPI,
    WebCrawler,
    PiracySiteCrawler
)
from .queue import DMCAQueue
from .scheduler import ScanScheduler
from .config import ScannerConfig

__version__ = "1.0.0"
__all__ = [
    "ContentScanner",
    "FaceRecognitionProcessor",
    "ImageHashProcessor",
    "ContentMatcher", 
    "SearchEngineAPI",
    "WebCrawler",
    "PiracySiteCrawler",
    "DMCAQueue",
    "ScanScheduler",
    "ScannerConfig"
]