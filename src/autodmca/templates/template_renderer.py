"""
Template rendering system for DMCA notices with Jinja2.

Provides secure template rendering with proper escaping and validation
for generating legally compliant DMCA takedown notices.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape, Template
from jinja2.exceptions import TemplateError, TemplateSyntaxError

from ..models.takedown import TakedownRequest, CreatorProfile
from ..models.hosting import DMCAAgent, ContactInfo
from .dmca_notice import DMCANoticeTemplate, DMCAFollowupTemplate, get_subject_line


class TemplateRenderer:
    """
    Secure template renderer for DMCA notices with validation and escaping.
    """
    
    def __init__(self, template_dir: Optional[Path] = None):
        """
        Initialize the template renderer.
        
        Args:
            template_dir: Optional directory containing custom templates
        """
        self.template_dir = template_dir
        
        # Configure Jinja2 environment with security measures
        if template_dir and template_dir.exists():
            self.env = Environment(
                loader=FileSystemLoader(str(template_dir)),
                autoescape=select_autoescape(['html', 'xml']),
                trim_blocks=True,
                lstrip_blocks=True
            )
        else:
            self.env = Environment(
                autoescape=select_autoescape(['html', 'xml']),
                trim_blocks=True,
                lstrip_blocks=True
            )
        
        # Add custom filters
        self.env.filters['format_date'] = self._format_date
        self.env.filters['format_address'] = self._format_address
        self.env.filters['sanitize_text'] = self._sanitize_text
        self.env.filters['truncate_url'] = self._truncate_url
    
    def render_dmca_notice(
        self,
        takedown_request: TakedownRequest,
        agent_contact: Optional[DMCAAgent] = None,
        template_type: str = "standard"
    ) -> Dict[str, str]:
        """
        Render a DMCA takedown notice.
        
        Args:
            takedown_request: The takedown request data
            agent_contact: DMCA agent contact information
            template_type: Type of template (standard, followup, final)
        
        Returns:
            Dict with 'subject' and 'body' keys containing rendered notice
        """
        # Get the appropriate template
        if template_type == "followup":
            template_content = DMCANoticeTemplate.get_followup_notice()
            subject_type = f"followup_{takedown_request.followup_count}"
        elif template_type == "final":
            template_content = DMCANoticeTemplate.get_final_notice()
            subject_type = "final"
        else:
            template_content = DMCANoticeTemplate.get_standard_notice()
            subject_type = "initial"
        
        # Prepare template variables
        variables = self._prepare_template_variables(takedown_request, agent_contact)
        
        # Validate template variables
        errors = DMCANoticeTemplate.validate_template_variables(template_content, variables)
        if errors:
            raise ValueError(f"Template validation failed: {errors}")
        
        # Render the template
        try:
            template = Template(template_content)
            body = template.render(**variables)
            
            # Generate subject line
            subject = get_subject_line(
                subject_type,
                title=takedown_request.infringement_data.original_work_title[:50]
            )
            
            return {
                'subject': subject,
                'body': body,
                'template_type': template_type
            }
            
        except TemplateError as e:
            raise ValueError(f"Template rendering failed: {str(e)}")
    
    def render_search_delisting_request(
        self,
        takedown_requests: List[TakedownRequest],
        agent_contact: Optional[DMCAAgent] = None
    ) -> Dict[str, str]:
        """
        Render a search engine delisting request for multiple URLs.
        
        Args:
            takedown_requests: List of takedown requests to delist
            agent_contact: DMCA agent contact information
        
        Returns:
            Dict with 'subject' and 'body' keys containing rendered request
        """
        if not takedown_requests:
            raise ValueError("At least one takedown request is required")
        
        # Use the first request as the primary work
        primary_request = takedown_requests[0]
        
        # Collect all infringing URLs
        infringing_urls = [req.infringement_data.infringing_url for req in takedown_requests]
        
        # Prepare template variables
        variables = self._prepare_template_variables(primary_request, agent_contact)
        variables.update({
            'infringing_urls': infringing_urls,
            'url_count': len(infringing_urls)
        })
        
        # Get delisting template
        template_content = DMCANoticeTemplate.get_search_delisting_template()
        
        try:
            template = Template(template_content)
            body = template.render(**variables)
            
            subject = get_subject_line(
                'search_delisting',
                title=primary_request.infringement_data.original_work_title[:50]
            )
            
            return {
                'subject': subject,
                'body': body,
                'template_type': 'search_delisting',
                'url_count': len(infringing_urls)
            }
            
        except TemplateError as e:
            raise ValueError(f"Search delisting template rendering failed: {str(e)}")
    
    def render_custom_template(
        self,
        template_name: str,
        variables: Dict[str, Any]
    ) -> str:
        """
        Render a custom template by name.
        
        Args:
            template_name: Name of template file
            variables: Template variables
        
        Returns:
            Rendered template content
        """
        if not self.template_dir:
            raise ValueError("Template directory not configured")
        
        try:
            template = self.env.get_template(template_name)
            return template.render(**variables)
        except TemplateError as e:
            raise ValueError(f"Custom template rendering failed: {str(e)}")
    
    def _prepare_template_variables(
        self,
        takedown_request: TakedownRequest,
        agent_contact: Optional[DMCAAgent] = None
    ) -> Dict[str, Any]:
        """
        Prepare template variables from takedown request data.
        
        Args:
            takedown_request: The takedown request
            agent_contact: Optional DMCA agent contact
        
        Returns:
            Dictionary of template variables
        """
        creator = takedown_request.creator_profile
        infringement = takedown_request.infringement_data
        
        # Base variables
        variables = {
            # Creator information
            'creator_name': creator.public_name,
            'creator_business_name': creator.business_name,
            'creator_email': str(creator.email),
            'creator_phone': creator.phone,
            'creator_address': self._format_creator_address(creator),
            
            # Work information  
            'original_work_title': infringement.original_work_title,
            'original_work_description': infringement.original_work_description,
            'original_work_urls': [str(url) for url in infringement.original_work_urls],
            'copyright_registration': infringement.copyright_registration_number,
            'creation_date': self._format_date(infringement.creation_date) if infringement.creation_date else None,
            'publication_date': self._format_date(infringement.publication_date) if infringement.publication_date else None,
            
            # Infringement information
            'infringing_url': str(infringement.infringing_url),
            'infringement_description': infringement.description,
            'screenshot_url': str(infringement.screenshot_url) if infringement.screenshot_url else None,
            
            # Timestamps
            'current_date': self._format_date(datetime.utcnow()),
            'original_notice_date': self._format_date(takedown_request.notice_sent_at) if takedown_request.notice_sent_at else None,
            'followup_number': takedown_request.followup_count,
            
            # Deadlines
            'response_deadline_days': 7,  # Standard 7-day response window
            'final_deadline_days': 5,    # Final notice deadline
            
            # Anonymity and agent settings
            'use_anonymity': creator.use_anonymity,
            'agent_representation': creator.agent_representation,
            'agent_contact': agent_contact,
            
            # Signature
            'signature_name': agent_contact.name if (creator.use_anonymity and agent_contact) else creator.public_name,
        }
        
        # Add followup-specific variables
        if takedown_request.followup_count > 0:
            followup_dates = []
            # This would be populated from actual followup history in a real implementation
            variables['followup_dates'] = followup_dates
        
        return variables
    
    def _format_creator_address(self, creator: CreatorProfile) -> str:
        """Format creator address for template use."""
        parts = [creator.address_line1]
        
        if creator.address_line2:
            parts.append(creator.address_line2)
        
        parts.append(f"{creator.city}, {creator.state_province} {creator.postal_code}")
        parts.append(creator.country)
        
        return "\n".join(parts)
    
    def _format_date(self, date: Optional[datetime]) -> Optional[str]:
        """Format datetime for templates."""
        if not date:
            return None
        return date.strftime("%B %d, %Y")
    
    def _format_address(self, address_parts: List[str]) -> str:
        """Format address components."""
        return "\n".join(filter(None, address_parts))
    
    def _sanitize_text(self, text: str) -> str:
        """Sanitize text content for templates."""
        if not text:
            return ""
        
        # Remove potentially dangerous content
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<[^>]+>', '', text)  # Remove HTML tags
        text = re.sub(r'[^\w\s\-.,;:!?()[\]{}"\'/\\]', '', text)  # Allow only safe characters
        
        return text.strip()
    
    def _truncate_url(self, url: str, max_length: int = 100) -> str:
        """Truncate URL for display purposes."""
        if len(url) <= max_length:
            return url
        return url[:max_length-3] + "..."
    
    def validate_rendered_notice(self, rendered_notice: Dict[str, str]) -> List[str]:
        """
        Validate a rendered DMCA notice for legal compliance.
        
        Args:
            rendered_notice: Dict with 'subject' and 'body' keys
        
        Returns:
            List of validation warnings/errors
        """
        warnings = []
        body = rendered_notice.get('body', '')
        
        # Check for required DMCA elements
        required_phrases = [
            'Digital Millennium Copyright Act',
            'good faith belief',
            'under penalty of perjury',
            'authorized to act',
            'infringing',
            'copyrighted'
        ]
        
        for phrase in required_phrases:
            if phrase.lower() not in body.lower():
                warnings.append(f"Missing required phrase: '{phrase}'")
        
        # Check for contact information
        if '@' not in body:
            warnings.append("No email address found in notice")
        
        # Check for URL presence
        if 'http' not in body:
            warnings.append("No URLs found in notice")
        
        # Check minimum length (DMCA notices should be substantive)
        if len(body) < 500:
            warnings.append("Notice may be too short for effective DMCA compliance")
        
        # Check for signature
        if 'Date:' not in body:
            warnings.append("Missing signature date")
        
        return warnings