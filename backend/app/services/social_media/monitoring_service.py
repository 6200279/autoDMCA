"""
Main social media monitoring service that orchestrates all monitoring activities.
"""

import asyncio
import uuid
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict
import json

import structlog
from sqlalchemy.orm import Session

from app.db.models.social_media import (
    SocialMediaPlatform, SocialMediaAccount, SocialMediaImpersonation,
    MonitoringSession, MonitoringStatus, ImpersonationType, AccountStatus
)
from app.db.models.profile import ProtectedProfile
from app.db.session import get_db

from .config import MonitoringConfig, SocialMediaSettings
from .api_clients import ProfileData, create_api_client
from .scrapers import create_scraper
from .username_monitor import UsernameMonitor, UsernameMatch
from .face_matcher import ProfileImageAnalyzer, FaceMatch
from .fake_detection import FakeAccountDetector, FakeAccountScore
from .reporting import AutomatedReportingService, ReportSubmission
from ..auth.rate_limiter import MultiServiceRateLimiter, RateLimitConfig


logger = structlog.get_logger(__name__)


@dataclass
class MonitoringJob:
    """Represents a monitoring job for a specific profile."""
    job_id: str
    profile_id: int
    platforms: List[SocialMediaPlatform]
    monitoring_type: str  # username, face_recognition, content_theft, comprehensive
    priority: str = "medium"  # low, medium, high, urgent
    created_at: datetime = None
    scheduled_at: Optional[datetime] = None
    status: MonitoringStatus = MonitoringStatus.PENDING
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now()


@dataclass
class MonitoringResult:
    """Results from a monitoring job."""
    job_id: str
    profile_id: int
    platform: SocialMediaPlatform
    accounts_found: List[ProfileData]
    impersonations_detected: List[Dict[str, Any]]
    fake_accounts: List[Dict[str, Any]]
    reports_created: List[ReportSubmission]
    execution_time: float
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SocialMediaMonitoringService:
    """Comprehensive social media monitoring service."""
    
    def __init__(self, config: MonitoringConfig):
        self.config = config
        self.settings = config.settings
        self.username_monitor = UsernameMonitor(config)
        self.face_matcher = ProfileImageAnalyzer(config.settings)
        self.fake_detector = FakeAccountDetector(config.settings)
        self.reporting_service = AutomatedReportingService(config)
        
        # Initialize rate limiter for all platforms
        self.rate_limiter = self._setup_rate_limiter()
        
        # Job queues
        self.pending_jobs: List[MonitoringJob] = []
        self.active_jobs: Set[str] = set()
        self.completed_jobs: Dict[str, MonitoringResult] = {}
        
        # Statistics
        self.stats = {
            "jobs_completed": 0,
            "impersonations_found": 0,
            "reports_submitted": 0,
            "platforms_monitored": set(),
            "last_activity": datetime.now()
        }
        
        self.logger = logger.bind(service="social_media_monitoring")
    
    def _setup_rate_limiter(self) -> MultiServiceRateLimiter:
        """Setup rate limiters for all platforms."""
        service_configs = {}
        
        for platform, platform_config in self.config.platform_configs.items():
            service_configs[platform.value] = RateLimitConfig(
                max_calls=platform_config.requests_per_minute,
                time_window=60,
                burst_limit=platform_config.burst_limit if hasattr(platform_config, 'burst_limit') else None,
                backoff_factor=1.5
            )
        
        return MultiServiceRateLimiter(service_configs)
    
    async def start_monitoring(self, profile_id: int, platforms: List[SocialMediaPlatform], 
                              monitoring_type: str = "comprehensive") -> str:
        """Start monitoring for a specific profile."""
        job_id = str(uuid.uuid4())
        
        job = MonitoringJob(
            job_id=job_id,
            profile_id=profile_id,
            platforms=platforms,
            monitoring_type=monitoring_type,
            priority="medium"
        )
        
        self.pending_jobs.append(job)
        
        self.logger.info(
            "Monitoring job queued",
            job_id=job_id,
            profile_id=profile_id,
            platforms=[p.value for p in platforms],
            monitoring_type=monitoring_type
        )
        
        return job_id
    
    async def monitor_profile(self, profile_id: int, platforms: List[SocialMediaPlatform]) -> Dict[str, MonitoringResult]:
        """Monitor a specific profile across multiple platforms."""
        results = {}
        
        # Get profile data from database
        async with get_db() as db:
            profile = db.query(ProtectedProfile).filter(ProtectedProfile.id == profile_id).first()
            if not profile:
                raise ValueError(f"Profile {profile_id} not found")
        
        # Create monitoring session record
        session_id = await self._create_monitoring_session(profile_id, platforms)
        
        for platform in platforms:
            self.logger.info("Starting platform monitoring", platform=platform.value, profile_id=profile_id)
            
            start_time = datetime.now()
            try:
                result = await self._monitor_platform(profile, platform, session_id)
                result.execution_time = (datetime.now() - start_time).total_seconds()
                results[platform.value] = result
                
                self.stats["platforms_monitored"].add(platform.value)
                
            except Exception as e:
                self.logger.error(
                    "Platform monitoring failed",
                    platform=platform.value,
                    profile_id=profile_id,
                    error=str(e)
                )
                
                results[platform.value] = MonitoringResult(
                    job_id=session_id,
                    profile_id=profile_id,
                    platform=platform,
                    accounts_found=[],
                    impersonations_detected=[],
                    fake_accounts=[],
                    reports_created=[],
                    execution_time=(datetime.now() - start_time).total_seconds(),
                    success=False,
                    error_message=str(e)
                )
        
        # Update monitoring session
        await self._update_monitoring_session(session_id, results)
        
        # Update statistics
        self.stats["jobs_completed"] += 1
        self.stats["last_activity"] = datetime.now()
        
        return results
    
    async def _monitor_platform(self, profile: ProtectedProfile, platform: SocialMediaPlatform, session_id: str) -> MonitoringResult:
        """Monitor a specific platform for impersonations."""
        accounts_found = []
        impersonations_detected = []
        fake_accounts = []
        reports_created = []
        
        try:
            # Step 1: Username monitoring
            username_matches = await self._perform_username_monitoring(profile, platform)
            
            # Step 2: Profile discovery via APIs and scraping
            discovered_profiles = await self._discover_profiles(profile, platform)
            accounts_found.extend(discovered_profiles)
            
            # Step 3: Face recognition analysis (if reference images available)
            if profile.face_encodings and profile.reference_images:
                face_matches = await self._perform_face_recognition(profile, discovered_profiles, platform)
                for match in face_matches:
                    if match['similarity_score'] >= self.settings.face_recognition_tolerance:
                        impersonations_detected.append(match)
            
            # Step 4: Username-based impersonation detection
            for username_match in username_matches:
                if username_match.profile_data:
                    impersonation = await self._analyze_potential_impersonation(
                        profile, username_match.profile_data, platform, "username_similarity"
                    )
                    if impersonation:
                        impersonations_detected.append(impersonation)
            
            # Step 5: Fake account detection
            if discovered_profiles:
                fake_analysis = await self.fake_detector.batch_analyze_accounts(discovered_profiles, platform)
                for username, fake_score in fake_analysis.items():
                    if fake_score.risk_category in ["likely_fake", "definitely_fake"]:
                        fake_account = {
                            "username": username,
                            "platform": platform.value,
                            "fake_score": fake_score.overall_score,
                            "risk_category": fake_score.risk_category,
                            "confidence": fake_score.confidence_level,
                            "reasons": fake_score.reasons
                        }
                        fake_accounts.append(fake_account)
            
            # Step 6: Automated reporting (for high-confidence cases)
            if self.settings.auto_reporting_enabled:
                high_confidence_cases = [
                    imp for imp in impersonations_detected 
                    if imp.get('confidence_score', 0) >= self.settings.auto_report_confidence_threshold
                ]
                
                for impersonation in high_confidence_cases:
                    try:
                        report = await self.reporting_service.create_report(
                            impersonation, auto_submit=True
                        )
                        reports_created.append(report)
                        self.stats["reports_submitted"] += 1
                    except Exception as e:
                        self.logger.error("Failed to create report", error=str(e))
            
            # Step 7: Store results in database
            await self._store_monitoring_results(profile.id, platform, impersonations_detected, fake_accounts)
            
            self.stats["impersonations_found"] += len(impersonations_detected)
            
            return MonitoringResult(
                job_id=session_id,
                profile_id=profile.id,
                platform=platform,
                accounts_found=accounts_found,
                impersonations_detected=impersonations_detected,
                fake_accounts=fake_accounts,
                reports_created=reports_created,
                execution_time=0,  # Will be set by caller
                success=True,
                metadata={
                    "username_matches": len(username_matches),
                    "profiles_analyzed": len(discovered_profiles),
                    "high_confidence_impersonations": len([i for i in impersonations_detected if i.get('confidence_score', 0) > 0.8])
                }
            )
            
        except Exception as e:
            self.logger.error("Platform monitoring error", platform=platform.value, error=str(e))
            raise
    
    async def _perform_username_monitoring(self, profile: ProtectedProfile, platform: SocialMediaPlatform) -> List[UsernameMatch]:
        """Perform username-based monitoring."""
        search_terms = profile.search_keywords or []
        
        # Extract primary username from profile name or first search term
        primary_username = None
        if search_terms:
            primary_username = search_terms[0]
        
        if not primary_username:
            return []
        
        # Apply rate limiting
        await self.rate_limiter.acquire(platform.value)
        
        try:
            results = await self.username_monitor.monitor_username(
                primary_username,
                [platform],
                stage_name=profile.stage_name
            )
            return results.get(platform, [])
            
        except Exception as e:
            self.logger.warning("Username monitoring failed", platform=platform.value, error=str(e))
            return []
    
    async def _discover_profiles(self, profile: ProtectedProfile, platform: SocialMediaPlatform) -> List[ProfileData]:
        """Discover profiles through API and scraping."""
        discovered = []
        platform_config = self.config.get_platform_config(platform)
        
        if not platform_config:
            return discovered
        
        # Apply rate limiting
        await self.rate_limiter.acquire(platform.value)
        
        try:
            # Try API-based discovery first
            async with create_api_client(platform, platform_config, self.settings) as api_client:
                # Search for variations of the username
                search_terms = self.config.get_search_terms(profile.name, profile.stage_name)
                
                for search_term in search_terms[:5]:  # Limit searches to avoid rate limiting
                    try:
                        search_result = await api_client.search_profiles(search_term, limit=10)
                        discovered.extend(search_result.profiles)
                    except Exception as e:
                        self.logger.debug("API search failed", search_term=search_term, error=str(e))
                        continue
            
            # Fallback to scraping if API results are limited
            if len(discovered) < 5:
                scraper = create_scraper(platform, platform_config, self.settings)
                
                # Scrape high-priority username variations
                username_variations = self.config.get_username_variations(profile.name)[:10]
                
                for variation in username_variations:
                    try:
                        scraped_profile = await scraper.scrape_profile(variation)
                        if scraped_profile:
                            discovered.append(scraped_profile)
                    except Exception as e:
                        self.logger.debug("Scraping failed", username=variation, error=str(e))
                        continue
        
        except Exception as e:
            self.logger.warning("Profile discovery failed", platform=platform.value, error=str(e))
        
        # Remove duplicates
        seen_usernames = set()
        unique_profiles = []
        for prof in discovered:
            if prof.username not in seen_usernames:
                unique_profiles.append(prof)
                seen_usernames.add(prof.username)
        
        return unique_profiles
    
    async def _perform_face_recognition(self, profile: ProtectedProfile, discovered_profiles: List[ProfileData], platform: SocialMediaPlatform) -> List[Dict[str, Any]]:
        """Perform face recognition analysis."""
        if not profile.face_encodings or not profile.reference_images:
            return []
        
        matches = []
        
        try:
            # Analyze profiles against reference face encodings
            analysis_results = await self.face_matcher.batch_analyze_candidates(
                ProfileData(
                    username=profile.name,
                    profile_image_url=profile.reference_images[0] if profile.reference_images else None
                ),
                discovered_profiles,
                reference_face_encodings=profile.face_encodings
            )
            
            for username, analysis in analysis_results.items():
                if analysis['overall_similarity'] >= 0.75:  # High similarity threshold
                    match = {
                        'username': username,
                        'platform': platform.value,
                        'similarity_score': analysis['overall_similarity'],
                        'confidence_score': 0.9 if analysis['confidence_level'] == 'high' else 0.7,
                        'detection_method': 'face_recognition',
                        'impersonation_type': ImpersonationType.PROFILE_COPY.value,
                        'analysis_details': analysis
                    }
                    matches.append(match)
        
        except Exception as e:
            self.logger.error("Face recognition analysis failed", error=str(e))
        
        return matches
    
    async def _analyze_potential_impersonation(self, original_profile: ProtectedProfile, candidate_profile: ProfileData, 
                                             platform: SocialMediaPlatform, detection_method: str) -> Optional[Dict[str, Any]]:
        """Analyze if a candidate profile is an impersonation."""
        
        # Calculate various similarity metrics
        username_similarity = self._calculate_username_similarity(original_profile.name, candidate_profile.username)
        
        # Bio similarity (if both have bios)
        bio_similarity = 0.0
        if original_profile.description and candidate_profile.bio:
            from difflib import SequenceMatcher
            bio_similarity = SequenceMatcher(None, original_profile.description.lower(), 
                                           candidate_profile.bio.lower()).ratio()
        
        # Determine if this constitutes impersonation
        confidence_score = max(username_similarity, bio_similarity)
        
        if confidence_score >= 0.7:  # Threshold for considering it impersonation
            impersonation_type = ImpersonationType.PROFILE_COPY
            if username_similarity > 0.8:
                impersonation_type = ImpersonationType.USERNAME_SQUATTING
            
            return {
                'original_username': original_profile.name,
                'fake_username': candidate_profile.username,
                'fake_url': candidate_profile.url,
                'platform': platform.value,
                'similarity_score': confidence_score,
                'confidence_score': confidence_score,
                'detection_method': detection_method,
                'impersonation_type': impersonation_type.value,
                'fake_profile': candidate_profile,
                'analysis_timestamp': datetime.now().isoformat(),
                'additional_details': f"Username similarity: {username_similarity:.2f}, Bio similarity: {bio_similarity:.2f}"
            }
        
        return None
    
    def _calculate_username_similarity(self, original: str, candidate: str) -> float:
        """Calculate similarity between usernames."""
        from difflib import SequenceMatcher
        return SequenceMatcher(None, original.lower(), candidate.lower()).ratio()
    
    async def _create_monitoring_session(self, profile_id: int, platforms: List[SocialMediaPlatform]) -> str:
        """Create a monitoring session record in the database."""
        session_id = str(uuid.uuid4())
        
        # This would create a MonitoringSession record in the database
        # For now, we'll just return the session ID
        
        return session_id
    
    async def _update_monitoring_session(self, session_id: str, results: Dict[str, MonitoringResult]) -> None:
        """Update monitoring session with results."""
        # This would update the MonitoringSession record with results
        pass
    
    async def _store_monitoring_results(self, profile_id: int, platform: SocialMediaPlatform, 
                                      impersonations: List[Dict[str, Any]], fake_accounts: List[Dict[str, Any]]) -> None:
        """Store monitoring results in the database."""
        # This would create SocialMediaImpersonation records
        # For now, we'll just log the results
        
        self.logger.info(
            "Storing monitoring results",
            profile_id=profile_id,
            platform=platform.value,
            impersonations_count=len(impersonations),
            fake_accounts_count=len(fake_accounts)
        )
    
    async def process_monitoring_queue(self) -> None:
        """Process pending monitoring jobs."""
        while self.pending_jobs:
            job = self.pending_jobs.pop(0)
            
            if job.job_id in self.active_jobs:
                continue  # Skip if already processing
            
            self.active_jobs.add(job.job_id)
            
            try:
                self.logger.info("Processing monitoring job", job_id=job.job_id)
                
                results = await self.monitor_profile(job.profile_id, job.platforms)
                
                # Store results
                for platform_name, result in results.items():
                    self.completed_jobs[f"{job.job_id}_{platform_name}"] = result
                
                self.logger.info("Monitoring job completed", job_id=job.job_id)
                
            except Exception as e:
                self.logger.error("Monitoring job failed", job_id=job.job_id, error=str(e))
                
            finally:
                self.active_jobs.remove(job.job_id)
    
    async def continuous_monitoring(self, check_interval_minutes: int = 60) -> None:
        """Run continuous monitoring loop."""
        self.logger.info("Starting continuous monitoring", check_interval=check_interval_minutes)
        
        while True:
            try:
                # Process pending jobs
                if self.pending_jobs:
                    await self.process_monitoring_queue()
                
                # Sleep until next check
                await asyncio.sleep(check_interval_minutes * 60)
                
            except KeyboardInterrupt:
                self.logger.info("Continuous monitoring stopped by user")
                break
            except Exception as e:
                self.logger.error("Continuous monitoring error", error=str(e))
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    def get_monitoring_statistics(self) -> Dict[str, Any]:
        """Get monitoring service statistics."""
        return {
            **self.stats,
            "pending_jobs": len(self.pending_jobs),
            "active_jobs": len(self.active_jobs),
            "completed_jobs": len(self.completed_jobs),
            "platforms_monitored": list(self.stats["platforms_monitored"]),
            "uptime_hours": (datetime.now() - self.stats["last_activity"]).total_seconds() / 3600
        }
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get status of a specific monitoring job."""
        # Check if job is pending
        for job in self.pending_jobs:
            if job.job_id == job_id:
                return {
                    "job_id": job_id,
                    "status": "pending",
                    "created_at": job.created_at.isoformat(),
                    "priority": job.priority,
                    "platforms": [p.value for p in job.platforms]
                }
        
        # Check if job is active
        if job_id in self.active_jobs:
            return {
                "job_id": job_id,
                "status": "active",
                "message": "Currently processing"
            }
        
        # Check completed jobs
        completed_results = {k: v for k, v in self.completed_jobs.items() if k.startswith(job_id)}
        if completed_results:
            return {
                "job_id": job_id,
                "status": "completed",
                "results": {
                    k.split('_', 1)[1]: {
                        "success": v.success,
                        "accounts_found": len(v.accounts_found),
                        "impersonations_detected": len(v.impersonations_detected),
                        "fake_accounts": len(v.fake_accounts),
                        "reports_created": len(v.reports_created),
                        "execution_time": v.execution_time,
                        "error_message": v.error_message
                    }
                    for k, v in completed_results.items()
                }
            }
        
        return {
            "job_id": job_id,
            "status": "not_found",
            "message": "Job not found"
        }
    
    async def emergency_monitoring(self, profile_id: int, platforms: List[SocialMediaPlatform]) -> Dict[str, MonitoringResult]:
        """Perform emergency monitoring with high priority."""
        self.logger.warning("Emergency monitoring initiated", profile_id=profile_id)
        
        # Skip queue and process immediately
        results = await self.monitor_profile(profile_id, platforms)
        
        # Auto-report all findings regardless of confidence
        for platform_name, result in results.items():
            if result.impersonations_detected:
                for impersonation in result.impersonations_detected:
                    try:
                        report = await self.reporting_service.create_report(
                            impersonation, auto_submit=True
                        )
                        result.reports_created.append(report)
                    except Exception as e:
                        self.logger.error("Emergency report creation failed", error=str(e))
        
        return results