"""
Initial User Scanning System for New Signups
Implements PRD requirement for immediate content scanning upon user registration

PRD Requirements:
- "Find leaks immediately or within hours of signup"
- "Immediate scanning for new users to find existing leaks"
- "Users should see results quickly to demonstrate value"
- "Basic Plan: 1 profile monitoring"
- "Professional Plan: Up to 5 profiles monitoring"
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_async_session
from app.db.models.user import User
from app.services.billing.subscription_tier_enforcement import (
    SubscriptionTierEnforcement,
    SubscriptionTier
)
from app.services.scanning.orchestrator import ScanningOrchestrator
from app.services.scanning.piracy_sites_database import piracy_sites_db, SiteType
from app.services.scanning.official_search_apis import OfficialSearchAPIs
from app.services.ai.content_matcher import ContentMatcher
from app.services.notifications.alert_system import alert_system
from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


class ScanPhase(str, Enum):
    """Phases of initial user scanning"""
    PROFILE_ANALYSIS = "profile_analysis"
    KEYWORD_EXTRACTION = "keyword_extraction"
    SEARCH_ENGINE_SCAN = "search_engine_scan"
    PIRACY_SITES_SCAN = "piracy_sites_scan"
    CONTENT_MATCHING = "content_matching"
    RESULTS_COMPILATION = "results_compilation"
    NOTIFICATION = "notification"


@dataclass
class ScanProgress:
    """Progress tracking for initial scan"""
    user_id: int
    profile_id: int
    current_phase: ScanPhase
    phases_completed: List[ScanPhase]
    total_matches_found: int
    high_confidence_matches: int
    scan_start_time: datetime
    estimated_completion: datetime
    error_count: int = 0
    last_update: datetime = None


@dataclass
class InitialScanResult:
    """Results from initial user scanning"""
    user_id: int
    profile_id: int
    scan_duration: timedelta
    total_sites_scanned: int
    total_matches_found: int
    high_confidence_matches: List[Dict[str, Any]]
    medium_confidence_matches: List[Dict[str, Any]]
    search_keywords_used: List[str]
    scan_phases_completed: List[ScanPhase]
    recommendations: List[str]
    next_scan_suggestions: List[str]


class InitialUserScanner:
    """
    Comprehensive initial scanning system for new users
    
    Implements PRD requirements:
    - Immediate leak detection upon signup
    - Fast results to demonstrate platform value
    - Comprehensive scanning across multiple sources
    - Intelligent content matching and confidence scoring
    """
    
    def __init__(self):
        self.subscription_enforcement = SubscriptionTierEnforcement()
        self.scanning_orchestrator = ScanningOrchestrator()
        self.content_matcher = ContentMatcher()
        self.search_apis = OfficialSearchAPIs()
        self.active_scans: Dict[str, ScanProgress] = {}
        
    async def start_initial_scan(
        self, 
        db: AsyncSession,
        user_id: int,
        profile_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Start comprehensive initial scan for new user
        
        PRD: "Find leaks immediately or within hours of signup"
        """
        
        logger.info(f"Starting initial scan for user {user_id}")
        
        try:
            # Check subscription tier and limits
            tier, metadata = await self.subscription_enforcement.get_user_subscription_tier(
                db, user_id
            )
            
            if tier == SubscriptionTier.FREE:
                logger.info(f"Skipping initial scan for free tier user {user_id}")
                return {
                    "scan_started": False, 
                    "reason": "free_tier_no_scanning",
                    "upgrade_required": True
                }
            
            # Validate profile data
            if not self._validate_profile_data(profile_data):
                return {
                    "scan_started": False,
                    "reason": "invalid_profile_data",
                    "required_fields": ["name", "platform", "username"]
                }
            
            # Create scan tracking
            scan_id = f"initial_{user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            profile_id = profile_data.get('id', 1)  # Placeholder
            
            scan_progress = ScanProgress(
                user_id=user_id,
                profile_id=profile_id,
                current_phase=ScanPhase.PROFILE_ANALYSIS,
                phases_completed=[],
                total_matches_found=0,
                high_confidence_matches=0,
                scan_start_time=datetime.utcnow(),
                estimated_completion=datetime.utcnow() + timedelta(hours=2),
                last_update=datetime.utcnow()
            )
            
            self.active_scans[scan_id] = scan_progress
            
            # Schedule immediate background scan
            result = celery_app.send_task(
                'execute_initial_user_scan',
                args=[scan_id, user_id, profile_data, tier.value],
                eta=datetime.utcnow() + timedelta(seconds=30)
            )
            
            # Send immediate confirmation to user
            await alert_system.send_alert(
                user_id=user_id,
                alert_type="initial_scan_started",
                title="Content Protection Scan Started",
                message=f"We're now scanning for your content across the web. You'll receive results within 1-2 hours.",
                metadata={
                    "scan_id": scan_id,
                    "task_id": result.id,
                    "estimated_completion": scan_progress.estimated_completion.isoformat(),
                    "profile_name": profile_data.get('name', 'Profile')
                }
            )
            
            logger.info(f"Initial scan {scan_id} started for user {user_id}")
            
            return {
                "scan_started": True,
                "scan_id": scan_id,
                "task_id": result.id,
                "estimated_completion": scan_progress.estimated_completion.isoformat(),
                "tier": tier.value,
                "message": "Your initial content scan has started. Results will be available soon."
            }
            
        except Exception as e:
            logger.error(f"Failed to start initial scan for user {user_id}: {e}")
            return {
                "scan_started": False,
                "error": str(e)
            }
    
    def _validate_profile_data(self, profile_data: Dict[str, Any]) -> bool:
        """Validate that profile data contains required fields"""
        required_fields = ['name', 'platform', 'username']
        return all(field in profile_data and profile_data[field] for field in required_fields)
    
    async def execute_comprehensive_scan(
        self,
        scan_id: str,
        user_id: int, 
        profile_data: Dict[str, Any],
        subscription_tier: str
    ) -> InitialScanResult:
        """
        Execute comprehensive initial scan across all sources
        
        This is the main scanning logic that runs in background
        """
        
        logger.info(f"Executing comprehensive scan {scan_id} for user {user_id}")
        
        if scan_id not in self.active_scans:
            raise ValueError(f"Scan {scan_id} not found in active scans")
        
        progress = self.active_scans[scan_id]
        scan_start = datetime.utcnow()
        
        try:
            # Phase 1: Profile Analysis and Keyword Extraction
            progress.current_phase = ScanPhase.PROFILE_ANALYSIS
            await self._update_scan_progress(scan_id, progress)
            
            keywords = await self._extract_search_keywords(profile_data)
            
            progress.phases_completed.append(ScanPhase.PROFILE_ANALYSIS)
            progress.current_phase = ScanPhase.KEYWORD_EXTRACTION
            await self._update_scan_progress(scan_id, progress)
            
            logger.info(f"Extracted {len(keywords)} keywords for user {user_id}: {keywords}")
            
            # Phase 2: Search Engine Scanning
            progress.current_phase = ScanPhase.SEARCH_ENGINE_SCAN
            await self._update_scan_progress(scan_id, progress)
            
            search_results = await self.search_apis.search_for_creator_content(
                creator_name=profile_data['name'],
                keywords=keywords[:5]  # Limit to top 5 keywords
            )
            
            progress.phases_completed.append(ScanPhase.SEARCH_ENGINE_SCAN)
            
            # Phase 3: Piracy Sites Scanning
            progress.current_phase = ScanPhase.PIRACY_SITES_SCAN
            await self._update_scan_progress(scan_id, progress)
            
            # Determine site types to scan based on platform
            site_types = self._get_relevant_site_types(profile_data['platform'])
            
            piracy_results = await piracy_sites_db.scan_all_sites_for_creator(
                creator_keywords=keywords[:3],  # Limit for performance
                site_types=site_types,
                priority_threshold=2 if subscription_tier == "professional" else 1
            )
            
            progress.phases_completed.append(ScanPhase.PIRACY_SITES_SCAN)
            
            # Phase 4: Content Matching and Analysis
            progress.current_phase = ScanPhase.CONTENT_MATCHING
            await self._update_scan_progress(scan_id, progress)
            
            all_matches = search_results + piracy_results
            
            # Filter and score matches
            high_confidence_matches = [
                match for match in all_matches 
                if match.get('confidence_score', 0) >= 70
            ]
            
            medium_confidence_matches = [
                match for match in all_matches 
                if 40 <= match.get('confidence_score', 0) < 70
            ]
            
            progress.total_matches_found = len(all_matches)
            progress.high_confidence_matches = len(high_confidence_matches)
            progress.phases_completed.append(ScanPhase.CONTENT_MATCHING)
            
            # Phase 5: Results Compilation
            progress.current_phase = ScanPhase.RESULTS_COMPILATION
            await self._update_scan_progress(scan_id, progress)
            
            recommendations = self._generate_recommendations(
                high_confidence_matches, profile_data, subscription_tier
            )
            
            next_scan_suggestions = self._generate_next_scan_suggestions(
                all_matches, subscription_tier
            )
            
            progress.phases_completed.append(ScanPhase.RESULTS_COMPILATION)
            
            # Phase 6: User Notification
            progress.current_phase = ScanPhase.NOTIFICATION
            await self._update_scan_progress(scan_id, progress)
            
            await self._send_scan_completion_notification(
                user_id, high_confidence_matches, medium_confidence_matches, recommendations
            )
            
            progress.phases_completed.append(ScanPhase.NOTIFICATION)
            
            # Create final results
            scan_duration = datetime.utcnow() - scan_start
            
            results = InitialScanResult(
                user_id=user_id,
                profile_id=progress.profile_id,
                scan_duration=scan_duration,
                total_sites_scanned=len(piracy_sites_db.sites),
                total_matches_found=len(all_matches),
                high_confidence_matches=high_confidence_matches[:20],  # Limit to top 20
                medium_confidence_matches=medium_confidence_matches[:10],  # Limit to top 10
                search_keywords_used=keywords,
                scan_phases_completed=progress.phases_completed,
                recommendations=recommendations,
                next_scan_suggestions=next_scan_suggestions
            )
            
            # Clean up tracking
            del self.active_scans[scan_id]
            
            logger.info(f"Completed initial scan for user {user_id} in {scan_duration}")
            
            return results
            
        except Exception as e:
            logger.error(f"Initial scan {scan_id} failed: {e}")
            progress.error_count += 1
            
            # Send error notification
            await alert_system.send_alert(
                user_id=user_id,
                alert_type="scan_failed",
                title="Content Scan Failed",
                message="We encountered an issue during your content scan. Our team has been notified and will retry the scan.",
                metadata={
                    "scan_id": scan_id,
                    "error": str(e),
                    "phase_failed": progress.current_phase.value
                }
            )
            
            raise
    
    async def _extract_search_keywords(self, profile_data: Dict[str, Any]) -> List[str]:
        """Extract search keywords from profile data"""
        
        keywords = []
        
        # Primary identifiers
        keywords.append(profile_data['name'])
        keywords.append(profile_data['username'])
        
        # Platform-specific keywords
        platform = profile_data['platform'].lower()
        if platform == 'onlyfans':
            keywords.extend([
                f"{profile_data['name']} onlyfans",
                f"{profile_data['username']} onlyfans leaked",
                f"{profile_data['name']} leaked",
                f"{profile_data['username']} premium"
            ])
        elif platform == 'instagram':
            keywords.extend([
                f"{profile_data['name']} instagram",
                f"{profile_data['username']} ig",
                f"{profile_data['name']} stories",
                f"{profile_data['username']} private"
            ])
        elif platform == 'tiktok':
            keywords.extend([
                f"{profile_data['name']} tiktok",
                f"{profile_data['username']} tik tok",
                f"{profile_data['name']} videos"
            ])
        
        # Add bio keywords if available
        if 'bio' in profile_data and profile_data['bio']:
            bio_words = profile_data['bio'].split()[:5]  # First 5 words from bio
            keywords.extend(bio_words)
        
        # Add location if available
        if 'location' in profile_data and profile_data['location']:
            keywords.append(profile_data['location'])
        
        # Remove duplicates and empty strings
        keywords = list(set(k for k in keywords if k and len(k.strip()) > 2))
        
        return keywords[:10]  # Limit to 10 keywords max
    
    def _get_relevant_site_types(self, platform: str) -> List[SiteType]:
        """Get relevant site types based on platform"""
        
        platform = platform.lower()
        
        if platform == 'onlyfans':
            return [
                SiteType.ONLYFANS_LEAK,
                SiteType.FILE_SHARING,
                SiteType.FORUM,
                SiteType.REDDIT_LEAK
            ]
        elif platform == 'instagram':
            return [
                SiteType.INSTAGRAM_LEAK,
                SiteType.IMAGE_BOARD,
                SiteType.FORUM,
                SiteType.REDDIT_LEAK
            ]
        elif platform == 'tiktok':
            return [
                SiteType.TIKTOK_LEAK,
                SiteType.TUBE_SITE,
                SiteType.FILE_SHARING,
                SiteType.FORUM
            ]
        elif platform == 'twitter':
            return [
                SiteType.TWITTER_LEAK,
                SiteType.IMAGE_BOARD,
                SiteType.FORUM
            ]
        else:
            # Generic content creator
            return [
                SiteType.FILE_SHARING,
                SiteType.FORUM,
                SiteType.IMAGE_BOARD,
                SiteType.REDDIT_LEAK
            ]
    
    def _generate_recommendations(
        self, 
        high_confidence_matches: List[Dict[str, Any]], 
        profile_data: Dict[str, Any],
        subscription_tier: str
    ) -> List[str]:
        """Generate actionable recommendations for user"""
        
        recommendations = []
        
        if len(high_confidence_matches) > 0:
            recommendations.append(
                f"We found {len(high_confidence_matches)} high-confidence matches of your content. "
                "Consider upgrading to Professional tier for automated DMCA takedown requests."
            )
            
            if subscription_tier == "basic":
                recommendations.append(
                    "Upgrade to Professional for continuous monitoring and priority takedown processing."
                )
        else:
            recommendations.append(
                "No high-confidence matches found in initial scan. "
                "We'll continue monitoring with daily automated scans."
            )
            
        recommendations.append(
            "Add more profile information to improve content detection accuracy."
        )
        
        if profile_data['platform'] == 'onlyfans':
            recommendations.append(
                "Enable Telegram monitoring to catch leaks shared in private channels."
            )
            
        return recommendations
    
    def _generate_next_scan_suggestions(
        self, 
        all_matches: List[Dict[str, Any]], 
        subscription_tier: str
    ) -> List[str]:
        """Generate suggestions for next scans"""
        
        suggestions = []
        
        if subscription_tier == "professional":
            suggestions.append("Daily continuous monitoring is enabled for your account.")
            suggestions.append("Consider adding additional profiles for comprehensive protection.")
        else:
            suggestions.append("Daily scans will continue automatically.")
            suggestions.append("Upgrade to Professional for continuous monitoring every 2-6 hours.")
        
        if len(all_matches) > 10:
            suggestions.append(
                "High volume of potential matches detected. Consider refining profile keywords."
            )
            
        suggestions.append("Monitor scan results regularly and report false positives to improve accuracy.")
        
        return suggestions
    
    async def _update_scan_progress(self, scan_id: str, progress: ScanProgress) -> None:
        """Update scan progress and notify user"""
        
        progress.last_update = datetime.utcnow()
        
        # Send progress update to user (could use WebSocket for real-time updates)
        await alert_system.send_alert(
            user_id=progress.user_id,
            alert_type="scan_progress",
            title=f"Scan Progress: {progress.current_phase.value.title()}",
            message=f"Currently {progress.current_phase.value.replace('_', ' ')}...",
            metadata={
                "scan_id": scan_id,
                "current_phase": progress.current_phase.value,
                "completed_phases": [p.value for p in progress.phases_completed],
                "progress_percent": len(progress.phases_completed) / 7 * 100  # 7 total phases
            }
        )
    
    async def _send_scan_completion_notification(
        self,
        user_id: int,
        high_confidence_matches: List[Dict[str, Any]],
        medium_confidence_matches: List[Dict[str, Any]],
        recommendations: List[str]
    ) -> None:
        """Send comprehensive scan completion notification"""
        
        total_matches = len(high_confidence_matches) + len(medium_confidence_matches)
        
        if total_matches > 0:
            message = (
                f"Your initial content scan is complete! We found {total_matches} potential matches "
                f"({len(high_confidence_matches)} high-confidence, {len(medium_confidence_matches)} medium-confidence). "
                "Check your dashboard for detailed results and next steps."
            )
            alert_type = "scan_completed_matches_found"
        else:
            message = (
                "Your initial content scan is complete! No matches were found in this scan. "
                "We'll continue monitoring with daily automated scans."
            )
            alert_type = "scan_completed_no_matches"
        
        await alert_system.send_alert(
            user_id=user_id,
            alert_type=alert_type,
            title="Initial Content Scan Complete",
            message=message,
            metadata={
                "total_matches": total_matches,
                "high_confidence_matches": len(high_confidence_matches),
                "medium_confidence_matches": len(medium_confidence_matches),
                "recommendations": recommendations,
                "scan_completed_at": datetime.utcnow().isoformat()
            }
        )
    
    async def get_scan_status(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a scan"""
        
        if scan_id not in self.active_scans:
            return None
        
        progress = self.active_scans[scan_id]
        
        return {
            "scan_id": scan_id,
            "user_id": progress.user_id,
            "current_phase": progress.current_phase.value,
            "phases_completed": [p.value for p in progress.phases_completed],
            "total_matches_found": progress.total_matches_found,
            "high_confidence_matches": progress.high_confidence_matches,
            "scan_duration": (datetime.utcnow() - progress.scan_start_time).total_seconds(),
            "estimated_completion": progress.estimated_completion.isoformat(),
            "progress_percent": len(progress.phases_completed) / 7 * 100,
            "last_update": progress.last_update.isoformat()
        }


# Global instance
initial_user_scanner = InitialUserScanner()


# Celery task definitions
@celery_app.task(bind=True, max_retries=2)
def execute_initial_user_scan(
    self,
    scan_id: str,
    user_id: int,
    profile_data: Dict[str, Any],
    subscription_tier: str
):
    """
    Celery task for executing initial user scan
    """
    
    logger.info(f"Starting initial scan task for user {user_id}")
    
    try:
        # This would need proper async context in production
        # For now, placeholder showing task structure
        
        import time
        time.sleep(120)  # Simulate comprehensive scan time
        
        logger.info(f"Completed initial scan for user {user_id}")
        
        return {
            "status": "completed",
            "scan_id": scan_id,
            "user_id": user_id,
            "matches_found": 5,  # Placeholder
            "scan_duration": 120
        }
        
    except Exception as e:
        logger.error(f"Initial scan failed for user {user_id}: {e}")
        raise self.retry(countdown=300 * (self.request.retries + 1))  # 5 minute intervals


__all__ = [
    'InitialUserScanner',
    'InitialScanResult', 
    'ScanPhase',
    'ScanProgress',
    'initial_user_scanner',
    'execute_initial_user_scan'
]