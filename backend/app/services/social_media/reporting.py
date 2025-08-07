"""
Automated reporting system for social media platforms.
"""

import asyncio
import uuid
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import base64
from pathlib import Path

import aiohttp
import aiofiles
import structlog
from jinja2 import Template

from app.db.models.social_media import (
    SocialMediaPlatform, SocialMediaImpersonation, SocialMediaReport, 
    ReportStatus, ImpersonationType
)
from .config import SocialMediaSettings, MonitoringConfig
from .api_clients import ProfileData
from .fake_detection import FakeAccountScore


logger = structlog.get_logger(__name__)


@dataclass
class ReportTemplate:
    """Template for platform-specific reports."""
    platform: SocialMediaPlatform
    report_type: str
    subject_template: str
    body_template: str
    required_fields: List[str]
    optional_fields: List[str]
    max_attachments: int = 10
    attachment_size_limit_mb: int = 10


@dataclass
class ReportEvidence:
    """Evidence to include in reports."""
    evidence_type: str  # screenshot, profile_comparison, similarity_analysis
    file_path: Optional[str] = None
    file_data: Optional[bytes] = None
    description: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ReportSubmission:
    """Represents a report submission to a platform."""
    report_id: str
    platform: SocialMediaPlatform
    report_type: str
    target_username: str
    target_url: str
    reporter_info: Dict[str, str]
    report_content: Dict[str, str]
    evidence: List[ReportEvidence]
    status: ReportStatus = ReportStatus.PENDING
    platform_response: Optional[Dict[str, Any]] = None
    submission_timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if not self.submission_timestamp:
            self.submission_timestamp = datetime.now()


class PlatformReporter:
    """Base class for platform-specific reporting."""
    
    def __init__(self, platform: SocialMediaPlatform, settings: SocialMediaSettings):
        self.platform = platform
        self.settings = settings
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = logger.bind(platform=platform.value)
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def submit_report(self, submission: ReportSubmission) -> Dict[str, Any]:
        """Submit report to platform. Override in subclasses."""
        raise NotImplementedError("Must be implemented by platform-specific subclass")
    
    async def check_report_status(self, platform_report_id: str) -> Dict[str, Any]:
        """Check status of submitted report. Override in subclasses."""
        raise NotImplementedError("Must be implemented by platform-specific subclass")


class InstagramReporter(PlatformReporter):
    """Instagram-specific reporting implementation."""
    
    async def submit_report(self, submission: ReportSubmission) -> Dict[str, Any]:
        """Submit report to Instagram."""
        self.logger.info("Submitting Instagram report", target=submission.target_username)
        
        # Instagram uses web forms - we'll simulate the process
        # In production, this would use Instagram's actual reporting API/forms
        
        report_data = {
            "report_type": submission.report_type,
            "reported_content": submission.target_url,
            "reason": submission.report_content.get("reason", ""),
            "description": submission.report_content.get("description", ""),
            "evidence_count": len(submission.evidence)
        }
        
        # Simulate API call
        await asyncio.sleep(2)  # Simulate network delay
        
        # Mock response
        platform_report_id = f"IG_{uuid.uuid4().hex[:8]}"
        
        return {
            "success": True,
            "platform_report_id": platform_report_id,
            "status": "submitted",
            "message": "Report submitted successfully to Instagram",
            "estimated_review_time": "24-48 hours"
        }
    
    async def check_report_status(self, platform_report_id: str) -> Dict[str, Any]:
        """Check Instagram report status."""
        # Mock status check
        return {
            "platform_report_id": platform_report_id,
            "status": "under_review",
            "last_updated": datetime.now().isoformat(),
            "estimated_completion": "1-2 days"
        }


class TwitterReporter(PlatformReporter):
    """Twitter/X-specific reporting implementation."""
    
    async def submit_report(self, submission: ReportSubmission) -> Dict[str, Any]:
        """Submit report to Twitter/X."""
        self.logger.info("Submitting Twitter report", target=submission.target_username)
        
        # Twitter has specific API endpoints for reporting
        # This is a simplified implementation
        
        headers = {
            "Authorization": f"Bearer {self.settings.twitter_bearer_token}",
            "Content-Type": "application/json"
        }
        
        report_payload = {
            "target": submission.target_url,
            "type": submission.report_type,
            "reason": submission.report_content.get("reason", ""),
            "description": submission.report_content.get("description", "")
        }
        
        try:
            # Mock API endpoint - replace with actual Twitter reporting endpoint
            mock_endpoint = "https://api.twitter.com/2/reports"
            
            # For now, simulate the call
            await asyncio.sleep(1.5)
            
            platform_report_id = f"TW_{uuid.uuid4().hex[:8]}"
            
            return {
                "success": True,
                "platform_report_id": platform_report_id,
                "status": "submitted",
                "message": "Report submitted to Twitter",
                "reference_number": platform_report_id
            }
            
        except Exception as e:
            self.logger.error("Twitter report submission failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to submit report to Twitter"
            }
    
    async def check_report_status(self, platform_report_id: str) -> Dict[str, Any]:
        """Check Twitter report status."""
        return {
            "platform_report_id": platform_report_id,
            "status": "acknowledged",
            "last_updated": datetime.now().isoformat()
        }


class FacebookReporter(PlatformReporter):
    """Facebook-specific reporting implementation."""
    
    async def submit_report(self, submission: ReportSubmission) -> Dict[str, Any]:
        """Submit report to Facebook."""
        self.logger.info("Submitting Facebook report", target=submission.target_username)
        
        # Facebook reporting would use their specific forms/APIs
        await asyncio.sleep(2.5)  # Simulate longer processing
        
        platform_report_id = f"FB_{uuid.uuid4().hex[:8]}"
        
        return {
            "success": True,
            "platform_report_id": platform_report_id,
            "status": "submitted",
            "message": "Report submitted to Facebook",
            "case_number": platform_report_id
        }
    
    async def check_report_status(self, platform_report_id: str) -> Dict[str, Any]:
        """Check Facebook report status."""
        return {
            "platform_report_id": platform_report_id,
            "status": "under_review",
            "last_updated": datetime.now().isoformat()
        }


class TikTokReporter(PlatformReporter):
    """TikTok-specific reporting implementation."""
    
    async def submit_report(self, submission: ReportSubmission) -> Dict[str, Any]:
        """Submit report to TikTok."""
        self.logger.info("Submitting TikTok report", target=submission.target_username)
        
        await asyncio.sleep(3)  # Simulate processing
        
        platform_report_id = f"TT_{uuid.uuid4().hex[:8]}"
        
        return {
            "success": True,
            "platform_report_id": platform_report_id,
            "status": "submitted",
            "message": "Report submitted to TikTok"
        }
    
    async def check_report_status(self, platform_report_id: str) -> Dict[str, Any]:
        """Check TikTok report status."""
        return {
            "platform_report_id": platform_report_id,
            "status": "submitted",
            "last_updated": datetime.now().isoformat()
        }


class RedditReporter(PlatformReporter):
    """Reddit-specific reporting implementation."""
    
    async def submit_report(self, submission: ReportSubmission) -> Dict[str, Any]:
        """Submit report to Reddit."""
        self.logger.info("Submitting Reddit report", target=submission.target_username)
        
        # Reddit has modmail and admin reporting systems
        await asyncio.sleep(1)
        
        platform_report_id = f"RD_{uuid.uuid4().hex[:8]}"
        
        return {
            "success": True,
            "platform_report_id": platform_report_id,
            "status": "submitted",
            "message": "Report submitted to Reddit administrators"
        }
    
    async def check_report_status(self, platform_report_id: str) -> Dict[str, Any]:
        """Check Reddit report status."""
        return {
            "platform_report_id": platform_report_id,
            "status": "submitted",
            "last_updated": datetime.now().isoformat()
        }


class ReportTemplateManager:
    """Manages report templates for different platforms and report types."""
    
    def __init__(self, config: MonitoringConfig):
        self.config = config
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, Dict[str, ReportTemplate]]:
        """Load report templates for each platform and report type."""
        templates = {}
        
        # Instagram templates
        templates[SocialMediaPlatform.INSTAGRAM] = {
            "impersonation": ReportTemplate(
                platform=SocialMediaPlatform.INSTAGRAM,
                report_type="impersonation",
                subject_template="Impersonation Report - {{ target_username }}",
                body_template="""
I am reporting an Instagram account that is impersonating me.

Impersonating Account: {{ target_url }}
Username: {{ target_username }}

My Legitimate Account: {{ original_url }}
Username: {{ original_username }}

The reported account is:
- Using my profile picture without permission
- Copying my bio and personal information  
- Attempting to deceive my followers and the public
- {{ additional_details }}

I have attached evidence showing the similarities between the accounts.

Please remove this impersonating account immediately.

Thank you,
{{ reporter_name }}
{{ contact_email }}
                """.strip(),
                required_fields=["target_username", "target_url", "original_username", "original_url", "reporter_name", "contact_email"],
                optional_fields=["additional_details"],
                max_attachments=5
            ),
            "copyright": ReportTemplate(
                platform=SocialMediaPlatform.INSTAGRAM,
                report_type="copyright",
                subject_template="Copyright Infringement - {{ target_username }}",
                body_template="""
I am the copyright owner of content being used without permission.

Infringing Account: {{ target_url }}
Infringing Content: {{ infringing_content_urls }}

I own the copyright to this content and have not authorized its use.
Please remove the infringing content immediately.

{{ additional_details }}

Regards,
{{ reporter_name }}
{{ contact_email }}
                """.strip(),
                required_fields=["target_username", "target_url", "reporter_name", "contact_email"],
                optional_fields=["infringing_content_urls", "additional_details"]
            )
        }
        
        # Twitter templates
        templates[SocialMediaPlatform.TWITTER] = {
            "impersonation": ReportTemplate(
                platform=SocialMediaPlatform.TWITTER,
                report_type="impersonation",
                subject_template="Impersonation Report",
                body_template="""
Reporting impersonation on Twitter/X.

Impersonating Account: {{ target_url }}
This account is pretending to be me and using my content without permission.

My Legitimate Account: {{ original_url }}

Evidence of impersonation attached.

{{ reporter_name }}
                """.strip(),
                required_fields=["target_username", "target_url", "original_url", "reporter_name"],
                optional_fields=[]
            )
        }
        
        # Facebook templates
        templates[SocialMediaPlatform.FACEBOOK] = {
            "impersonation": ReportTemplate(
                platform=SocialMediaPlatform.FACEBOOK,
                report_type="impersonation",
                subject_template="Facebook Impersonation Report",
                body_template="""
I am reporting a Facebook account that is impersonating me.

Fake Account: {{ target_url }}
My Real Account: {{ original_url }}

The fake account is using my photos and information to deceive people.

{{ additional_details }}

Please remove this account.

{{ reporter_name }}
{{ contact_email }}
                """.strip(),
                required_fields=["target_url", "original_url", "reporter_name", "contact_email"],
                optional_fields=["additional_details"]
            )
        }
        
        # Add templates for other platforms...
        
        return templates
    
    def get_template(self, platform: SocialMediaPlatform, report_type: str) -> Optional[ReportTemplate]:
        """Get template for specific platform and report type."""
        return self.templates.get(platform, {}).get(report_type)
    
    def render_report(self, template: ReportTemplate, context: Dict[str, Any]) -> Dict[str, str]:
        """Render report using template and context."""
        try:
            subject_tmpl = Template(template.subject_template)
            body_tmpl = Template(template.body_template)
            
            subject = subject_tmpl.render(**context)
            body = body_tmpl.render(**context)
            
            return {
                "subject": subject.strip(),
                "body": body.strip()
            }
        except Exception as e:
            logger.error("Template rendering failed", error=str(e), template=template.report_type)
            raise


class EvidenceManager:
    """Manages evidence collection and preparation for reports."""
    
    def __init__(self, settings: SocialMediaSettings):
        self.settings = settings
        self.evidence_path = Path(settings.screenshot_storage_path)
        self.evidence_path.mkdir(parents=True, exist_ok=True)
    
    async def capture_profile_screenshot(self, profile_url: str, filename: Optional[str] = None) -> Optional[str]:
        """Capture screenshot of profile page."""
        if not filename:
            filename = f"profile_{uuid.uuid4().hex[:8]}.png"
        
        filepath = self.evidence_path / filename
        
        # This would use Selenium or similar to capture screenshots
        # For now, we'll simulate the process
        await asyncio.sleep(1)
        
        # Create mock screenshot file
        mock_screenshot = b"mock screenshot data"
        try:
            async with aiofiles.open(filepath, 'wb') as f:
                await f.write(mock_screenshot)
            return str(filepath)
        except Exception as e:
            logger.error("Failed to save screenshot", error=str(e), filename=filename)
            return None
    
    async def create_comparison_image(self, original_profile: ProfileData, fake_profile: ProfileData) -> Optional[str]:
        """Create side-by-side comparison image."""
        filename = f"comparison_{uuid.uuid4().hex[:8]}.png"
        filepath = self.evidence_path / filename
        
        # This would create actual comparison images
        # For now, simulate the process
        await asyncio.sleep(2)
        
        mock_comparison = b"mock comparison image data"
        try:
            async with aiofiles.open(filepath, 'wb') as f:
                await f.write(mock_comparison)
            return str(filepath)
        except Exception as e:
            logger.error("Failed to create comparison image", error=str(e))
            return None
    
    async def prepare_evidence_package(self, impersonation: Dict[str, Any]) -> List[ReportEvidence]:
        """Prepare comprehensive evidence package."""
        evidence = []
        
        # Profile screenshot
        if impersonation.get("fake_url"):
            screenshot_path = await self.capture_profile_screenshot(impersonation["fake_url"])
            if screenshot_path:
                evidence.append(ReportEvidence(
                    evidence_type="screenshot",
                    file_path=screenshot_path,
                    description="Screenshot of impersonating profile",
                    metadata={"url": impersonation["fake_url"]}
                ))
        
        # Profile comparison
        if impersonation.get("original_profile") and impersonation.get("fake_profile"):
            comparison_path = await self.create_comparison_image(
                impersonation["original_profile"],
                impersonation["fake_profile"]
            )
            if comparison_path:
                evidence.append(ReportEvidence(
                    evidence_type="profile_comparison",
                    file_path=comparison_path,
                    description="Side-by-side comparison of profiles",
                    metadata={"similarity_score": impersonation.get("similarity_score", 0)}
                ))
        
        # Similarity analysis report
        if impersonation.get("analysis_results"):
            analysis_text = json.dumps(impersonation["analysis_results"], indent=2)
            evidence.append(ReportEvidence(
                evidence_type="similarity_analysis",
                file_data=analysis_text.encode('utf-8'),
                description="Detailed similarity analysis report",
                metadata={"format": "json"}
            ))
        
        return evidence


class AutomatedReportingService:
    """Main automated reporting service."""
    
    def __init__(self, config: MonitoringConfig):
        self.config = config
        self.settings = config.settings
        self.template_manager = ReportTemplateManager(config)
        self.evidence_manager = EvidenceManager(config.settings)
        self.reporters = self._initialize_reporters()
        
    def _initialize_reporters(self) -> Dict[SocialMediaPlatform, PlatformReporter]:
        """Initialize platform-specific reporters."""
        return {
            SocialMediaPlatform.INSTAGRAM: InstagramReporter(SocialMediaPlatform.INSTAGRAM, self.settings),
            SocialMediaPlatform.TWITTER: TwitterReporter(SocialMediaPlatform.TWITTER, self.settings),
            SocialMediaPlatform.FACEBOOK: FacebookReporter(SocialMediaPlatform.FACEBOOK, self.settings),
            SocialMediaPlatform.TIKTOK: TikTokReporter(SocialMediaPlatform.TIKTOK, self.settings),
            SocialMediaPlatform.REDDIT: RedditReporter(SocialMediaPlatform.REDDIT, self.settings)
        }
    
    async def create_report(
        self,
        impersonation_data: Dict[str, Any],
        report_type: str = "impersonation",
        auto_submit: bool = False
    ) -> ReportSubmission:
        """Create a report for an impersonation."""
        
        platform = SocialMediaPlatform(impersonation_data["platform"])
        template = self.template_manager.get_template(platform, report_type)
        
        if not template:
            raise ValueError(f"No template found for {platform.value} {report_type}")
        
        # Prepare context for template rendering
        context = {
            "target_username": impersonation_data.get("fake_username", ""),
            "target_url": impersonation_data.get("fake_url", ""),
            "original_username": impersonation_data.get("original_username", ""),
            "original_url": impersonation_data.get("original_url", ""),
            "reporter_name": impersonation_data.get("reporter_name", ""),
            "contact_email": impersonation_data.get("contact_email", ""),
            "additional_details": impersonation_data.get("additional_details", ""),
            "similarity_score": impersonation_data.get("similarity_score", 0)
        }
        
        # Render report content
        report_content = self.template_manager.render_report(template, context)
        
        # Prepare evidence
        evidence = await self.evidence_manager.prepare_evidence_package(impersonation_data)
        
        # Create report submission
        submission = ReportSubmission(
            report_id=str(uuid.uuid4()),
            platform=platform,
            report_type=report_type,
            target_username=context["target_username"],
            target_url=context["target_url"],
            reporter_info={
                "name": context["reporter_name"],
                "email": context["contact_email"]
            },
            report_content=report_content,
            evidence=evidence
        )
        
        # Auto-submit if requested and confidence is high enough
        if auto_submit and self._should_auto_submit(impersonation_data):
            submission = await self.submit_report(submission)
        
        return submission
    
    def _should_auto_submit(self, impersonation_data: Dict[str, Any]) -> bool:
        """Determine if report should be auto-submitted."""
        # Only auto-submit high-confidence cases
        confidence_score = impersonation_data.get("confidence_score", 0)
        similarity_score = impersonation_data.get("similarity_score", 0)
        
        # Auto-submit if very high confidence and similarity
        return (confidence_score >= self.settings.auto_report_confidence_threshold and 
                similarity_score >= 0.9 and 
                self.settings.auto_reporting_enabled)
    
    async def submit_report(self, submission: ReportSubmission) -> ReportSubmission:
        """Submit report to the appropriate platform."""
        reporter = self.reporters.get(submission.platform)
        if not reporter:
            raise ValueError(f"No reporter available for platform: {submission.platform}")
        
        try:
            async with reporter as r:
                result = await r.submit_report(submission)
                
                if result.get("success"):
                    submission.status = ReportStatus.SUBMITTED
                    submission.platform_response = result
                    logger.info(
                        "Report submitted successfully",
                        platform=submission.platform.value,
                        report_id=submission.report_id,
                        platform_report_id=result.get("platform_report_id")
                    )
                else:
                    submission.status = ReportStatus.PENDING
                    submission.platform_response = result
                    logger.error(
                        "Report submission failed",
                        platform=submission.platform.value,
                        report_id=submission.report_id,
                        error=result.get("error", "Unknown error")
                    )
                
        except Exception as e:
            logger.error(
                "Report submission error",
                platform=submission.platform.value,
                report_id=submission.report_id,
                error=str(e)
            )
            submission.status = ReportStatus.PENDING
            submission.platform_response = {"error": str(e)}
        
        return submission
    
    async def check_report_status(self, submission: ReportSubmission) -> ReportSubmission:
        """Check status of submitted report."""
        if not submission.platform_response or not submission.platform_response.get("platform_report_id"):
            return submission
        
        reporter = self.reporters.get(submission.platform)
        if not reporter:
            return submission
        
        try:
            async with reporter as r:
                status_result = await r.check_report_status(
                    submission.platform_response["platform_report_id"]
                )
                
                # Update submission status based on platform response
                platform_status = status_result.get("status", "").lower()
                
                status_mapping = {
                    "submitted": ReportStatus.SUBMITTED,
                    "acknowledged": ReportStatus.ACKNOWLEDGED,
                    "under_review": ReportStatus.UNDER_REVIEW,
                    "accepted": ReportStatus.ACCEPTED,
                    "rejected": ReportStatus.REJECTED
                }
                
                new_status = status_mapping.get(platform_status)
                if new_status:
                    submission.status = new_status
                
                # Update platform response with status check result
                submission.platform_response.update(status_result)
                
        except Exception as e:
            logger.error(
                "Status check error",
                report_id=submission.report_id,
                error=str(e)
            )
        
        return submission
    
    async def batch_create_reports(
        self,
        impersonations: List[Dict[str, Any]],
        report_type: str = "impersonation"
    ) -> List[ReportSubmission]:
        """Create multiple reports in batch."""
        submissions = []
        
        for impersonation in impersonations:
            try:
                submission = await self.create_report(impersonation, report_type)
                submissions.append(submission)
            except Exception as e:
                logger.error(
                    "Failed to create report",
                    impersonation=impersonation.get("fake_username", "unknown"),
                    error=str(e)
                )
        
        return submissions
    
    async def process_high_priority_reports(self, submissions: List[ReportSubmission]) -> None:
        """Process high-priority reports with expedited submission."""
        # Sort by priority (confidence score if available)
        high_priority = [
            s for s in submissions 
            if s.status == ReportStatus.PENDING and 
               self._is_high_priority(s)
        ]
        
        for submission in high_priority:
            try:
                await self.submit_report(submission)
                # Add small delay between submissions to avoid overwhelming platforms
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(
                    "High priority report submission failed",
                    report_id=submission.report_id,
                    error=str(e)
                )
    
    def _is_high_priority(self, submission: ReportSubmission) -> bool:
        """Determine if submission is high priority."""
        # This could be based on various factors like similarity score,
        # fake account score, verified status, follower count, etc.
        return True  # For now, treat all as high priority
    
    def generate_reporting_summary(self, submissions: List[ReportSubmission]) -> Dict[str, Any]:
        """Generate summary of reporting activity."""
        if not submissions:
            return {
                "total_reports": 0,
                "status_distribution": {},
                "platform_distribution": {},
                "success_rate": 0
            }
        
        status_counts = {}
        platform_counts = {}
        successful_submissions = 0
        
        for submission in submissions:
            # Count by status
            status_counts[submission.status.value] = status_counts.get(submission.status.value, 0) + 1
            
            # Count by platform
            platform_counts[submission.platform.value] = platform_counts.get(submission.platform.value, 0) + 1
            
            # Count successful submissions
            if submission.status in [ReportStatus.SUBMITTED, ReportStatus.ACKNOWLEDGED, ReportStatus.ACCEPTED]:
                successful_submissions += 1
        
        success_rate = (successful_submissions / len(submissions)) * 100 if submissions else 0
        
        return {
            "total_reports": len(submissions),
            "status_distribution": status_counts,
            "platform_distribution": platform_counts,
            "success_rate": success_rate,
            "successful_submissions": successful_submissions,
            "pending_submissions": status_counts.get("pending", 0)
        }