"""
Integration between social media monitoring and existing DMCA system.
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import json

import structlog
from sqlalchemy.orm import Session

from app.db.models.social_media import (
    SocialMediaPlatform, SocialMediaImpersonation, SocialMediaReport,
    ImpersonationType, ReportStatus
)
from app.db.models.infringement import Infringement, InfringementStatus, InfringementType
from app.db.models.takedown import TakedownRequest
from app.db.models.profile import ProtectedProfile
from app.db.session import get_db

from .monitoring_service import MonitoringResult
from .reporting import ReportSubmission, AutomatedReportingService
from .config import MonitoringConfig
from ..dmca.takedown_processor import DMCATakedownProcessor as DMCAService
# from src.autodmca.services.email_service import EmailService  # Disabled for local testing
# from src.autodmca.templates.template_renderer import TemplateRenderer  # Disabled for local testing


logger = structlog.get_logger(__name__)


@dataclass
class SocialMediaInfringement:
    """Represents a social media infringement that can be processed by DMCA system."""
    platform: str
    fake_username: str
    fake_url: str
    original_username: str
    original_url: str
    impersonation_type: str
    similarity_score: float
    confidence_score: float
    evidence_urls: List[str]
    detection_method: str
    profile_data: Optional[Dict[str, Any]] = None


class SocialMediaDMCABridge:
    """Bridge between social media monitoring and DMCA systems."""
    
    def __init__(self, config: MonitoringConfig, dmca_service: DMCAService):
        self.config = config
        self.dmca_service = dmca_service
        # self.email_service = EmailService()  # Disabled for local testing
        # self.template_renderer = TemplateRenderer()  # Disabled for local testing
        self.email_service = None
        self.template_renderer = None
        self.logger = logger.bind(service="social_media_dmca_bridge")
        
    async def process_monitoring_results(self, profile_id: int, results: Dict[str, MonitoringResult]) -> Dict[str, Any]:
        """Process monitoring results and integrate with DMCA system."""
        
        processing_summary = {
            "profile_id": profile_id,
            "platforms_processed": [],
            "infringements_created": 0,
            "takedown_requests_generated": 0,
            "reports_sent": 0,
            "errors": [],
            "processing_timestamp": datetime.now().isoformat()
        }
        
        async with get_db() as db:
            profile = db.query(ProtectedProfile).filter(ProtectedProfile.id == profile_id).first()
            if not profile:
                processing_summary["errors"].append(f"Profile {profile_id} not found")
                return processing_summary
        
        for platform_name, result in results.items():
            try:
                platform_summary = await self._process_platform_results(profile, platform_name, result, db)
                processing_summary["platforms_processed"].append(platform_summary)
                
                # Aggregate counts
                processing_summary["infringements_created"] += platform_summary["infringements_created"]
                processing_summary["takedown_requests_generated"] += platform_summary["takedown_requests_generated"]
                processing_summary["reports_sent"] += platform_summary["reports_sent"]
                
            except Exception as e:
                error_msg = f"Failed to process {platform_name} results: {str(e)}"
                processing_summary["errors"].append(error_msg)
                self.logger.error("Platform result processing failed", platform=platform_name, error=str(e))
        
        # Send summary notification
        await self._send_processing_summary(profile, processing_summary)
        
        return processing_summary
    
    async def _process_platform_results(self, profile: ProtectedProfile, platform_name: str, 
                                      result: MonitoringResult, db: Session) -> Dict[str, Any]:
        """Process results for a specific platform."""
        
        platform_summary = {
            "platform": platform_name,
            "success": result.success,
            "accounts_found": len(result.accounts_found),
            "impersonations_detected": len(result.impersonations_detected),
            "infringements_created": 0,
            "takedown_requests_generated": 0,
            "reports_sent": 0,
            "processing_errors": []
        }
        
        if not result.success:
            platform_summary["processing_errors"].append(result.error_message or "Unknown error")
            return platform_summary
        
        # Process each detected impersonation
        for impersonation_data in result.impersonations_detected:
            try:
                # Convert to standardized format
                social_media_infringement = self._convert_to_infringement(impersonation_data, platform_name)
                
                # Create infringement record in main system
                infringement = await self._create_infringement_record(
                    profile, social_media_infringement, db
                )
                platform_summary["infringements_created"] += 1
                
                # Determine if DMCA takedown is appropriate
                if self._should_generate_takedown(social_media_infringement):
                    takedown_request = await self._generate_takedown_request(
                        profile, infringement, social_media_infringement, db
                    )
                    if takedown_request:
                        platform_summary["takedown_requests_generated"] += 1
                
                # Handle platform-specific reporting
                if result.reports_created:
                    for report in result.reports_created:
                        await self._link_report_to_infringement(infringement, report, db)
                        platform_summary["reports_sent"] += 1
                
            except Exception as e:
                error_msg = f"Failed to process impersonation {impersonation_data.get('fake_username', 'unknown')}: {str(e)}"
                platform_summary["processing_errors"].append(error_msg)
                self.logger.error("Impersonation processing failed", error=str(e))
        
        return platform_summary
    
    def _convert_to_infringement(self, impersonation_data: Dict[str, Any], platform_name: str) -> SocialMediaInfringement:
        """Convert impersonation data to standardized infringement format."""
        return SocialMediaInfringement(
            platform=platform_name,
            fake_username=impersonation_data.get("fake_username", ""),
            fake_url=impersonation_data.get("fake_url", ""),
            original_username=impersonation_data.get("original_username", ""),
            original_url=impersonation_data.get("original_url", ""),
            impersonation_type=impersonation_data.get("impersonation_type", ImpersonationType.PROFILE_COPY.value),
            similarity_score=impersonation_data.get("similarity_score", 0.0),
            confidence_score=impersonation_data.get("confidence_score", 0.0),
            evidence_urls=impersonation_data.get("evidence_urls", []),
            detection_method=impersonation_data.get("detection_method", "unknown"),
            profile_data=impersonation_data.get("fake_profile")
        )
    
    async def _create_infringement_record(self, profile: ProtectedProfile, 
                                        social_media_infringement: SocialMediaInfringement,
                                        db: Session) -> Infringement:
        """Create infringement record in the main DMCA system."""
        
        # Determine infringement type based on social media impersonation type
        infringement_type_map = {
            ImpersonationType.PROFILE_COPY.value: InfringementType.PROFILE,
            ImpersonationType.CONTENT_THEFT.value: InfringementType.IMAGE,
            ImpersonationType.USERNAME_SQUATTING.value: InfringementType.PROFILE,
            ImpersonationType.CATFISHING.value: InfringementType.PROFILE,
            ImpersonationType.BRAND_IMPERSONATION.value: InfringementType.PROFILE
        }
        
        infringement_type = infringement_type_map.get(
            social_media_infringement.impersonation_type, 
            InfringementType.PROFILE
        )
        
        # Create infringement record
        infringement = Infringement(
            profile_id=profile.id,
            type=infringement_type,
            status=InfringementStatus.PENDING,
            url=social_media_infringement.fake_url,
            domain=self._extract_domain(social_media_infringement.fake_url),
            platform=social_media_infringement.platform,
            title=f"Impersonation on {social_media_infringement.platform}",
            description=f"User '{social_media_infringement.fake_username}' is impersonating '{social_media_infringement.original_username}'",
            confidence_score=social_media_infringement.confidence_score,
            detection_method=social_media_infringement.detection_method,
            match_data={
                "similarity_score": social_media_infringement.similarity_score,
                "impersonation_type": social_media_infringement.impersonation_type,
                "evidence_urls": social_media_infringement.evidence_urls,
                "fake_profile_data": social_media_infringement.profile_data
            },
            priority=self._determine_priority(social_media_infringement),
            detected_at=datetime.now(),
            first_seen=datetime.now(),
            last_seen=datetime.now()
        )
        
        db.add(infringement)
        db.commit()
        db.refresh(infringement)
        
        self.logger.info(
            "Infringement record created",
            infringement_id=infringement.id,
            platform=social_media_infringement.platform,
            fake_username=social_media_infringement.fake_username
        )
        
        return infringement
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
            return parsed.netloc
        except:
            return "unknown"
    
    def _determine_priority(self, infringement: SocialMediaInfringement) -> int:
        """Determine priority level (1-10) for infringement."""
        priority = 5  # Default medium priority
        
        # Increase priority based on confidence
        if infringement.confidence_score >= 0.9:
            priority += 3
        elif infringement.confidence_score >= 0.8:
            priority += 2
        elif infringement.confidence_score >= 0.7:
            priority += 1
        
        # Increase priority for certain impersonation types
        high_priority_types = [
            ImpersonationType.BRAND_IMPERSONATION.value,
            ImpersonationType.CATFISHING.value
        ]
        if infringement.impersonation_type in high_priority_types:
            priority += 2
        
        # Platform-specific adjustments
        high_visibility_platforms = ["instagram", "twitter", "facebook"]
        if infringement.platform.lower() in high_visibility_platforms:
            priority += 1
        
        return min(priority, 10)  # Cap at 10
    
    def _should_generate_takedown(self, infringement: SocialMediaInfringement) -> bool:
        """Determine if a DMCA takedown should be generated."""
        # Generate takedown for high-confidence cases
        if infringement.confidence_score >= 0.8:
            return True
        
        # Generate for specific impersonation types regardless of confidence
        always_takedown_types = [
            ImpersonationType.CONTENT_THEFT.value,
            ImpersonationType.BRAND_IMPERSONATION.value
        ]
        if infringement.impersonation_type in always_takedown_types:
            return True
        
        return False
    
    async def _generate_takedown_request(self, profile: ProtectedProfile, infringement: Infringement,
                                       social_media_infringement: SocialMediaInfringement,
                                       db: Session) -> Optional[TakedownRequest]:
        """Generate DMCA takedown request for social media impersonation."""
        
        try:
            # Prepare takedown request data
            takedown_data = {
                "infringement_id": infringement.id,
                "profile_id": profile.id,
                "platform": social_media_infringement.platform,
                "infringing_url": social_media_infringement.fake_url,
                "original_url": social_media_infringement.original_url,
                "infringement_type": "impersonation",
                "evidence": {
                    "similarity_score": social_media_infringement.similarity_score,
                    "detection_method": social_media_infringement.detection_method,
                    "evidence_urls": social_media_infringement.evidence_urls,
                    "impersonation_details": {
                        "fake_username": social_media_infringement.fake_username,
                        "original_username": social_media_infringement.original_username,
                        "impersonation_type": social_media_infringement.impersonation_type
                    }
                }
            }
            
            # Use DMCA service to generate takedown
            takedown_request = await self.dmca_service.create_social_media_takedown(takedown_data)
            
            if takedown_request:
                # Link takedown to infringement
                infringement.takedown_requests.append(takedown_request)
                infringement.status = InfringementStatus.TAKEDOWN_SENT
                db.commit()
                
                self.logger.info(
                    "DMCA takedown request generated",
                    infringement_id=infringement.id,
                    takedown_id=takedown_request.id
                )
            
            return takedown_request
            
        except Exception as e:
            self.logger.error("Failed to generate takedown request", error=str(e))
            return None
    
    async def _link_report_to_infringement(self, infringement: Infringement, 
                                         report: ReportSubmission, db: Session) -> None:
        """Link platform report to infringement record."""
        
        # Update infringement metadata to include report information
        if not infringement.match_data:
            infringement.match_data = {}
        
        if "platform_reports" not in infringement.match_data:
            infringement.match_data["platform_reports"] = []
        
        report_data = {
            "report_id": report.report_id,
            "platform_report_id": report.platform_response.get("platform_report_id") if report.platform_response else None,
            "status": report.status.value,
            "submitted_at": report.submission_timestamp.isoformat() if report.submission_timestamp else None,
            "report_type": report.report_type
        }
        
        infringement.match_data["platform_reports"].append(report_data)
        db.commit()
        
        self.logger.info(
            "Platform report linked to infringement",
            infringement_id=infringement.id,
            report_id=report.report_id
        )
    
    async def _send_processing_summary(self, profile: ProtectedProfile, summary: Dict[str, Any]) -> None:
        """Send processing summary notification to profile owner."""
        
        try:
            # Prepare email context
            context = {
                "profile_name": profile.name,
                "stage_name": profile.stage_name,
                "total_infringements": summary["infringements_created"],
                "total_takedowns": summary["takedown_requests_generated"],
                "total_reports": summary["reports_sent"],
                "platforms_processed": [p["platform"] for p in summary["platforms_processed"]],
                "processing_timestamp": summary["processing_timestamp"],
                "has_errors": len(summary["errors"]) > 0,
                "errors": summary["errors"]
            }
            
            # Render email template
            subject = f"Social Media Monitoring Summary - {profile.name}"
            
            # Use a simple template for now
            email_body = f"""
Social Media Monitoring Summary for {profile.name}

Processing completed at: {summary['processing_timestamp']}

Results:
- Platforms monitored: {len(summary['platforms_processed'])}
- Infringements detected: {summary['infringements_created']}
- DMCA takedowns generated: {summary['takedown_requests_generated']}
- Platform reports submitted: {summary['reports_sent']}

Platform Details:
"""
            
            for platform_summary in summary["platforms_processed"]:
                email_body += f"""
{platform_summary['platform'].upper()}:
  - Accounts found: {platform_summary['accounts_found']}
  - Impersonations detected: {platform_summary['impersonations_detected']}
  - Infringements created: {platform_summary['infringements_created']}
  - Reports sent: {platform_summary['reports_sent']}
"""
            
            if summary["errors"]:
                email_body += f"\nErrors encountered:\n"
                for error in summary["errors"]:
                    email_body += f"  - {error}\n"
            
            # Send email notification
            await self.email_service.send_email(
                to_email=profile.contact_email,
                subject=subject,
                body=email_body,
                from_name="AutoDMCA Social Media Monitor"
            )
            
            self.logger.info(
                "Processing summary notification sent",
                profile_id=profile.id,
                email=profile.contact_email
            )
            
        except Exception as e:
            self.logger.error("Failed to send processing summary", error=str(e))
    
    async def sync_social_media_reports_status(self) -> Dict[str, Any]:
        """Sync status of social media reports with platform responses."""
        
        sync_summary = {
            "reports_checked": 0,
            "status_updates": 0,
            "errors": [],
            "updated_reports": []
        }
        
        try:
            async with get_db() as db:
                # Get all submitted reports that need status updates
                pending_reports = db.query(SocialMediaReport).filter(
                    SocialMediaReport.status.in_([
                        ReportStatus.SUBMITTED,
                        ReportStatus.ACKNOWLEDGED,
                        ReportStatus.UNDER_REVIEW
                    ])
                ).all()
                
                sync_summary["reports_checked"] = len(pending_reports)
                
                # Check status of each report (this would integrate with actual platform APIs)
                for report in pending_reports:
                    try:
                        # Mock status check - in reality this would call platform APIs
                        await asyncio.sleep(0.1)  # Simulate API call
                        
                        # Randomly update some statuses for demo
                        import random
                        if random.random() < 0.1:  # 10% chance of status update
                            old_status = report.status
                            
                            # Simulate status progression
                            if report.status == ReportStatus.SUBMITTED:
                                report.status = ReportStatus.ACKNOWLEDGED
                            elif report.status == ReportStatus.ACKNOWLEDGED:
                                report.status = ReportStatus.UNDER_REVIEW
                            elif report.status == ReportStatus.UNDER_REVIEW:
                                report.status = random.choice([ReportStatus.ACCEPTED, ReportStatus.REJECTED])
                            
                            report.responded_at = datetime.now()
                            if report.status in [ReportStatus.ACCEPTED, ReportStatus.REJECTED]:
                                report.resolved_at = datetime.now()
                            
                            sync_summary["status_updates"] += 1
                            sync_summary["updated_reports"].append({
                                "report_id": report.id,
                                "platform": report.platform.value,
                                "old_status": old_status.value,
                                "new_status": report.status.value
                            })
                    
                    except Exception as e:
                        error_msg = f"Failed to sync report {report.id}: {str(e)}"
                        sync_summary["errors"].append(error_msg)
                
                db.commit()
                
        except Exception as e:
            sync_summary["errors"].append(f"Database error: {str(e)}")
        
        self.logger.info(
            "Social media report status sync completed",
            reports_checked=sync_summary["reports_checked"],
            status_updates=sync_summary["status_updates"],
            errors_count=len(sync_summary["errors"])
        )
        
        return sync_summary
    
    async def generate_comprehensive_report(self, profile_id: int, 
                                          date_range: Tuple[datetime, datetime]) -> Dict[str, Any]:
        """Generate comprehensive report of social media monitoring and DMCA activities."""
        
        start_date, end_date = date_range
        
        report = {
            "profile_id": profile_id,
            "report_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "summary": {},
            "platform_breakdown": {},
            "infringement_analysis": {},
            "takedown_effectiveness": {},
            "recommendations": []
        }
        
        try:
            async with get_db() as db:
                profile = db.query(ProtectedProfile).filter(ProtectedProfile.id == profile_id).first()
                if not profile:
                    report["error"] = f"Profile {profile_id} not found"
                    return report
                
                # Get infringements from date range
                infringements = db.query(Infringement).filter(
                    Infringement.profile_id == profile_id,
                    Infringement.detected_at >= start_date,
                    Infringement.detected_at <= end_date,
                    Infringement.platform.isnot(None)  # Social media infringements
                ).all()
                
                # Calculate summary statistics
                report["summary"] = {
                    "total_infringements": len(infringements),
                    "platforms_affected": len(set(inf.platform for inf in infringements if inf.platform)),
                    "high_priority_cases": len([inf for inf in infringements if inf.priority >= 7]),
                    "resolved_cases": len([inf for inf in infringements if inf.status == InfringementStatus.RESOLVED]),
                    "pending_cases": len([inf for inf in infringements if inf.status == InfringementStatus.PENDING]),
                    "average_confidence": sum(inf.confidence_score or 0 for inf in infringements) / len(infringements) if infringements else 0
                }
                
                # Platform breakdown
                platform_stats = {}
                for infringement in infringements:
                    platform = infringement.platform or "unknown"
                    if platform not in platform_stats:
                        platform_stats[platform] = {
                            "total_infringements": 0,
                            "resolved": 0,
                            "pending": 0,
                            "average_priority": 0,
                            "takedowns_sent": 0
                        }
                    
                    platform_stats[platform]["total_infringements"] += 1
                    if infringement.status == InfringementStatus.RESOLVED:
                        platform_stats[platform]["resolved"] += 1
                    elif infringement.status == InfringementStatus.PENDING:
                        platform_stats[platform]["pending"] += 1
                    
                    platform_stats[platform]["takedowns_sent"] += len(infringement.takedown_requests)
                
                # Calculate averages
                for platform, stats in platform_stats.items():
                    platform_infringements = [inf for inf in infringements if inf.platform == platform]
                    if platform_infringements:
                        stats["average_priority"] = sum(inf.priority for inf in platform_infringements) / len(platform_infringements)
                        stats["resolution_rate"] = stats["resolved"] / stats["total_infringements"] * 100
                
                report["platform_breakdown"] = platform_stats
                
                # Generate recommendations
                recommendations = []
                
                if report["summary"]["total_infringements"] > 10:
                    recommendations.append("High number of infringements detected. Consider increasing monitoring frequency.")
                
                if report["summary"]["average_confidence"] < 0.7:
                    recommendations.append("Low average confidence scores. Review detection algorithms and thresholds.")
                
                for platform, stats in platform_stats.items():
                    if stats["resolution_rate"] < 50:
                        recommendations.append(f"Low resolution rate for {platform}. Review takedown process.")
                
                if not recommendations:
                    recommendations.append("Monitoring and protection systems are performing well.")
                
                report["recommendations"] = recommendations
                
        except Exception as e:
            report["error"] = f"Failed to generate report: {str(e)}"
            self.logger.error("Failed to generate comprehensive report", error=str(e))
        
        return report