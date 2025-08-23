"""
Piracy Site Scanner for Platforms Module
Wrapper for the main PiracySiteScanner to fit the platforms interface
"""
import asyncio
from typing import List, Dict, Any, Optional
import logging

from .base_scanner import BaseScanner, ScanResult
from ..piracy_sites import PiracySiteScanner as MainPiracyScanner

logger = logging.getLogger(__name__)


class PiracySiteScanner(BaseScanner):
    """
    Platform-compatible wrapper for the main PiracySiteScanner
    """
    
    def __init__(self, region: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(region=region, rate_limit=10, **kwargs)
        self.piracy_scanner = MainPiracyScanner(region=region, **kwargs)
    
    async def get_platform_name(self) -> str:
        return "piracy_sites_platform"
    
    async def search(
        self,
        query: str,
        limit: int = 50,
        include_metadata: bool = True,
        **kwargs
    ) -> List[ScanResult]:
        """
        Search piracy sites using the main scanner
        """
        try:
            return await self.piracy_scanner.search(
                query=query,
                limit=limit,
                include_metadata=include_metadata,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Piracy platform scanner error: {e}")
            return []
    
    async def health_check(self) -> bool:
        """Check if piracy scanner is healthy"""
        try:
            return await self.piracy_scanner.health_check()
        except Exception as e:
            logger.error(f"Piracy platform scanner health check failed: {e}")
            return False