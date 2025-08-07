"""
Response Handler Service

Handles incoming responses to DMCA takedown notices, processes confirmations,
counter-notices, and updates takedown request statuses accordingly.
"""

import asyncio
import email
import logging
import re
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
import imaplib
import poplib
from email.parser import Parser

from ..models.takedown import TakedownRequest, TakedownStatus
from ..models.hosting import DMCAAgent
from ..services.email_service import EmailService
from ..templates.template_renderer import TemplateRenderer
from ..utils.cache import CacheManager
from ..utils.validators import EmailValidator

logger = logging.getLogger(__name__)


class ResponseType:
    """Types of responses to DMCA notices."""
    
    ACKNOWLEDGMENT = "acknowledgment"
    TAKEDOWN_COMPLETE = "takedown_complete"
    COUNTER_NOTICE = "counter_notice"
    REJECTION = "rejection"
    REQUEST_MORE_INFO = "request_more_info"
    AUTO_REPLY = "auto_reply"
    BOUNCE = "bounce"
    UNKNOWN = "unknown"


class ResponseHandler:
    """
    Service for handling responses to DMCA takedown notices.
    """
    
    def __init__(
        self,
        email_service: EmailService,
        cache_manager: Optional[CacheManager] = None,
        imap_config: Optional[Dict[str, Any]] = None,
        pop3_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize response handler.
        
        Args:
            email_service: Email service for sending follow-ups
            cache_manager: Cache for storing response data
            imap_config: IMAP configuration for checking responses
            pop3_config: POP3 configuration for checking responses
        """
        self.email_service = email_service
        self.cache_manager = cache_manager or CacheManager()
        self.imap_config = imap_config or {}
        self.pop3_config = pop3_config or {}
        
        self.template_renderer = TemplateRenderer()
        self.email_validator = EmailValidator()
        
        # Response pattern matching
        self.response_patterns = self._initialize_response_patterns()
        
        # Counter-notice detection patterns
        self.counter_notice_patterns = [
            r'counter[\-\s]?notice',
            r'counter[\-\s]?notification',
            r'section\s+512\(g\)',
            r'good\s+faith\s+belief.*not\s+removed',
            r'material\s+was\s+removed.*mistake',
            r'pursuant\s+to.*512\(g\)'
        ]
    
    def _initialize_response_patterns(self) -> Dict[str, List[str]]:
        """Initialize patterns for detecting different types of responses."""
        return {
            ResponseType.ACKNOWLEDGMENT: [
                r'thank\s+you\s+for.*notice',
                r'received\s+your.*dmca',
                r'we\s+have\s+received',
                r'your\s+complaint.*received',
                r'reference\s+number.*assigned'
            ],
            
            ResponseType.TAKEDOWN_COMPLETE: [
                r'content.*removed',
                r'material.*taken\s+down',
                r'page.*disabled',
                r'access.*disabled',
                r'removed\s+the.*content',
                r'takedown.*completed?',
                r'successfully\s+removed',
                r'no\s+longer\s+available'
            ],
            
            ResponseType.REJECTION: [
                r'cannot\s+remove',
                r'not\s+infringing',
                r'fair\s+use',
                r'legitimate\s+use',
                r'dispute.*claim',
                r'reject.*request',
                r'unable\s+to\s+comply',
                r'not\s+found\s+to\s+be'
            ],
            
            ResponseType.REQUEST_MORE_INFO: [
                r'need.*more\s+information',
                r'additional.*details\s+required',
                r'please\s+provide',
                r'clarify.*request',
                r'incomplete.*notice',
                r'missing.*information'
            ],
            
            ResponseType.AUTO_REPLY: [
                r'out\s+of\s+office',
                r'auto[\-\s]?reply',
                r'automatic\s+response',
                r'vacation\s+message',
                r'away\s+message',
                r'do\s+not\s+reply'
            ],
            
            ResponseType.BOUNCE: [
                r'undelivered\s+mail',
                r'delivery\s+failure',
                r'message.*bounced',
                r'permanent\s+failure',
                r'mailbox\s+full',
                r'user\s+unknown'
            ]
        }
    
    async def process_email_response(
        self,
        email_content: str,
        sender_email: str,
        subject: str,
        message_id: Optional[str] = None,
        in_reply_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process an incoming email response to a DMCA notice.
        
        Args:
            email_content: Content of the email response
            sender_email: Email address of sender
            subject: Email subject line
            message_id: Message ID of the response
            in_reply_to: Message ID this is replying to
        
        Returns:
            Dict with processing results
        """
        try:
            # Find related takedown request
            takedown_request = await self._find_related_takedown_request(
                sender_email, subject, in_reply_to
            )
            
            if not takedown_request:
                logger.warning(f"Could not find related takedown request for email from {sender_email}")
                return {
                    'success': False,
                    'reason': 'No matching takedown request found',
                    'sender': sender_email,
                    'subject': subject
                }
            
            # Classify the response type
            response_classification = self._classify_response(email_content, subject)
            
            # Process based on response type
            processing_result = await self._process_response_by_type(
                takedown_request,
                response_classification,
                email_content,
                sender_email,
                subject
            )
            
            # Update takedown request
            await self._update_takedown_request(
                takedown_request,
                response_classification,
                processing_result,
                email_content,
                sender_email
            )
            
            # Store response for tracking
            await self._store_response_data(
                takedown_request.id,
                response_classification,
                email_content,
                sender_email,
                subject,
                message_id
            )
            
            return {
                'success': True,
                'takedown_request_id': str(takedown_request.id),
                'response_type': response_classification['type'],
                'confidence': response_classification['confidence'],
                'action_taken': processing_result.get('action'),
                'next_steps': processing_result.get('next_steps', [])
            }
            
        except Exception as e:
            logger.error(f"Failed to process email response: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'sender': sender_email,
                'subject': subject
            }
    
    async def _find_related_takedown_request(
        self,
        sender_email: str,
        subject: str,
        in_reply_to: Optional[str]
    ) -> Optional[TakedownRequest]:
        """Find the takedown request this response is related to."""
        try:
            # Try to find by in_reply_to message ID first
            if in_reply_to:
                cache_key = f"email_to_request:{in_reply_to}"
                request_id = await self.cache_manager.get(cache_key)
                if request_id:
                    # Would normally fetch from database
                    # For now, return None as we don't have database access
                    pass
            
            # Try to find by sender email and subject patterns
            # Extract any reference numbers or IDs from subject
            ref_patterns = [
                r'ref[#:\s]*([a-zA-Z0-9\-]+)',
                r'case[#:\s]*([a-zA-Z0-9\-]+)',
                r'ticket[#:\s]*([a-zA-Z0-9\-]+)',
                r'id[#:\s]*([a-zA-Z0-9\-]+)'
            ]
            
            for pattern in ref_patterns:
                match = re.search(pattern, subject, re.IGNORECASE)
                if match:
                    ref_id = match.group(1)
                    # Try to find request by reference
                    cache_key = f"ref_to_request:{ref_id}"
                    request_id = await self.cache_manager.get(cache_key)
                    if request_id:
                        # Would fetch from database
                        break
            
            # Fallback: try to find by sender domain matching hosting provider
            # This would require database access to implement properly
            
            return None  # Placeholder - would return actual request from database
            
        except Exception as e:
            logger.error(f"Error finding related takedown request: {str(e)}")
            return None
    
    def _classify_response(self, email_content: str, subject: str) -> Dict[str, Any]:
        """
        Classify the type of response received.
        
        Args:
            email_content: Email content to analyze
            subject: Email subject line
        
        Returns:
            Dict with classification results
        """
        try:
            classification = {
                'type': ResponseType.UNKNOWN,
                'confidence': 0.0,
                'indicators': [],
                'counter_notice': False
            }
            
            # Combine subject and content for analysis
            text_to_analyze = f"{subject} {email_content}".lower()
            
            # Check for counter-notice first (highest priority)
            counter_notice_score = 0
            for pattern in self.counter_notice_patterns:
                matches = len(re.findall(pattern, text_to_analyze, re.IGNORECASE))
                if matches > 0:
                    counter_notice_score += matches * 2
                    classification['indicators'].append(f'Counter-notice pattern: {pattern}')
            
            if counter_notice_score >= 3:
                classification['type'] = ResponseType.COUNTER_NOTICE
                classification['confidence'] = min(0.9, counter_notice_score * 0.2)
                classification['counter_notice'] = True
                return classification
            
            # Check other response types
            best_match = {'type': ResponseType.UNKNOWN, 'score': 0}
            
            for response_type, patterns in self.response_patterns.items():
                score = 0
                type_indicators = []
                
                for pattern in patterns:
                    matches = len(re.findall(pattern, text_to_analyze, re.IGNORECASE))
                    if matches > 0:
                        score += matches
                        type_indicators.append(f'{response_type} pattern: {pattern}')
                
                if score > best_match['score']:
                    best_match = {
                        'type': response_type,
                        'score': score,
                        'indicators': type_indicators
                    }
            
            if best_match['score'] > 0:
                classification['type'] = best_match['type']
                classification['confidence'] = min(0.95, best_match['score'] * 0.3)
                classification['indicators'] = best_match['indicators']
            
            # Special handling for obvious automated responses
            if any(term in text_to_analyze for term in ['automated', 'robot', 'noreply', 'donotreply']):
                if classification['type'] == ResponseType.UNKNOWN:
                    classification['type'] = ResponseType.AUTO_REPLY
                    classification['confidence'] = 0.8
                    classification['indicators'].append('Automated response detected')
            
            return classification
            
        except Exception as e:
            logger.error(f"Response classification failed: {str(e)}")
            return {
                'type': ResponseType.UNKNOWN,
                'confidence': 0.0,
                'indicators': [f'Classification error: {str(e)}'],
                'counter_notice': False
            }
    
    async def _process_response_by_type(
        self,
        takedown_request: TakedownRequest,
        classification: Dict[str, Any],
        email_content: str,
        sender_email: str,
        subject: str
    ) -> Dict[str, Any]:
        """Process response based on its classified type."""
        try:
            response_type = classification['type']
            processing_result = {
                'action': 'none',
                'next_steps': [],
                'status_update': None
            }
            
            if response_type == ResponseType.ACKNOWLEDGMENT:
                processing_result.update({
                    'action': 'acknowledged',
                    'status_update': TakedownStatus.UNDER_REVIEW,
                    'next_steps': ['Wait for takedown completion', 'Monitor for follow-up if needed']
                })
            
            elif response_type == ResponseType.TAKEDOWN_COMPLETE:
                processing_result.update({
                    'action': 'content_removed',
                    'status_update': TakedownStatus.CONTENT_REMOVED,
                    'next_steps': ['Verify content removal', 'Mark request as completed']
                })
                
                # Schedule verification of removal
                await self._schedule_removal_verification(takedown_request)
            
            elif response_type == ResponseType.COUNTER_NOTICE:
                processing_result.update({
                    'action': 'counter_notice_received',
                    'status_update': TakedownStatus.ESCALATED,
                    'next_steps': [
                        'Review counter-notice for validity',
                        'Notify original complainant',
                        'Consider legal action if appropriate'
                    ]
                })
                
                # Handle counter-notice process
                await self._handle_counter_notice(
                    takedown_request, email_content, sender_email
                )
            
            elif response_type == ResponseType.REJECTION:
                processing_result.update({
                    'action': 'request_rejected',
                    'status_update': TakedownStatus.ESCALATED,
                    'next_steps': [
                        'Review rejection reasoning',
                        'Consider sending additional evidence',
                        'Evaluate escalation options'
                    ]
                })
            
            elif response_type == ResponseType.REQUEST_MORE_INFO:
                processing_result.update({
                    'action': 'more_info_requested',
                    'status_update': TakedownStatus.FOLLOWUP_REQUIRED,
                    'next_steps': [
                        'Review information request',
                        'Prepare supplemental documentation',
                        'Send additional information'
                    ]
                })
            
            elif response_type == ResponseType.AUTO_REPLY:
                processing_result.update({
                    'action': 'auto_reply_received',
                    'next_steps': ['Wait for human response', 'Schedule follow-up if no response']
                })
                
                # Don't update status for auto-replies
            
            elif response_type == ResponseType.BOUNCE:
                processing_result.update({
                    'action': 'email_bounced',
                    'status_update': TakedownStatus.FAILED,
                    'next_steps': [
                        'Find alternative contact information',
                        'Try different email address',
                        'Consider alternative notification methods'
                    ]
                })
            
            return processing_result
            
        except Exception as e:
            logger.error(f"Response processing failed: {str(e)}")
            return {
                'action': 'processing_error',
                'error': str(e),
                'next_steps': ['Manual review required']
            }
    
    async def _update_takedown_request(
        self,
        takedown_request: TakedownRequest,
        classification: Dict[str, Any],
        processing_result: Dict[str, Any],
        email_content: str,
        sender_email: str
    ) -> None:
        """Update takedown request based on response processing."""
        try:
            # Update response information
            takedown_request.response_received_at = datetime.utcnow()
            takedown_request.response_content = email_content
            takedown_request.response_email = sender_email
            
            # Update status if specified
            if processing_result.get('status_update'):
                takedown_request.update_status(
                    processing_result['status_update'],
                    {
                        'response_type': classification['type'],
                        'response_confidence': classification['confidence'],
                        'processing_action': processing_result['action']
                    }
                )
            
            # Handle counter-notice flag
            if classification.get('counter_notice'):
                takedown_request.counter_notice_received = True
            
            # Update completion status for successful takedowns
            if processing_result['action'] == 'content_removed':
                takedown_request.content_removed = True
                takedown_request.completed_at = datetime.utcnow()
            
            logger.info(f"Updated takedown request {takedown_request.id} based on response")
            
        except Exception as e:
            logger.error(f"Failed to update takedown request: {str(e)}")
    
    async def _store_response_data(
        self,
        request_id: UUID,
        classification: Dict[str, Any],
        email_content: str,
        sender_email: str,
        subject: str,
        message_id: Optional[str]
    ) -> None:
        """Store response data for tracking and analysis."""
        try:
            response_data = {
                'request_id': str(request_id),
                'sender_email': sender_email,
                'subject': subject,
                'content': email_content,
                'message_id': message_id,
                'classification': classification,
                'received_at': datetime.utcnow().isoformat(),
                'processed': True
            }
            
            cache_key = f"response:{request_id}:{datetime.utcnow().timestamp()}"
            await self.cache_manager.set(
                cache_key,
                response_data,
                ttl=timedelta(days=90)  # Keep responses for 90 days
            )
            
            logger.info(f"Stored response data for request {request_id}")
            
        except Exception as e:
            logger.error(f"Failed to store response data: {str(e)}")
    
    async def _handle_counter_notice(
        self,
        takedown_request: TakedownRequest,
        counter_notice_content: str,
        sender_email: str
    ) -> None:
        """Handle counter-notice processing."""
        try:
            # Extract key information from counter-notice
            counter_notice_info = self._parse_counter_notice(counter_notice_content)
            
            # Store counter-notice details
            counter_notice_data = {
                'request_id': str(takedown_request.id),
                'sender_email': sender_email,
                'content': counter_notice_content,
                'parsed_info': counter_notice_info,
                'received_at': datetime.utcnow().isoformat(),
                'status': 'pending_review'
            }
            
            cache_key = f"counter_notice:{takedown_request.id}"
            await self.cache_manager.set(
                cache_key,
                counter_notice_data,
                ttl=timedelta(days=365)  # Keep counter-notices for a year
            )
            
            # Generate notification to original complainant
            await self._notify_complainant_of_counter_notice(
                takedown_request, counter_notice_info
            )
            
            logger.info(f"Processed counter-notice for request {takedown_request.id}")
            
        except Exception as e:
            logger.error(f"Counter-notice handling failed: {str(e)}")
    
    def _parse_counter_notice(self, content: str) -> Dict[str, Any]:
        """Parse counter-notice to extract key information."""
        try:
            parsed_info = {
                'has_required_elements': False,
                'subscriber_info': {},
                'material_identification': '',
                'good_faith_statement': False,
                'penalty_statement': False,
                'jurisdiction_consent': False,
                'signature': ''
            }
            
            content_lower = content.lower()
            
            # Check for required elements under DMCA 512(g)
            if 'good faith' in content_lower and 'mistake' in content_lower:
                parsed_info['good_faith_statement'] = True
            
            if 'penalty of perjury' in content_lower:
                parsed_info['penalty_statement'] = True
            
            if 'jurisdiction' in content_lower and 'consent' in content_lower:
                parsed_info['jurisdiction_consent'] = True
            
            # Extract subscriber information (name, address, phone)
            # This would be more sophisticated in production
            email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', content)
            if email_match:
                parsed_info['subscriber_info']['email'] = email_match.group()
            
            phone_match = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', content)
            if phone_match:
                parsed_info['subscriber_info']['phone'] = phone_match.group()
            
            # Check if all required elements are present
            parsed_info['has_required_elements'] = (
                parsed_info['good_faith_statement'] and
                parsed_info['penalty_statement'] and
                bool(parsed_info['subscriber_info'])
            )
            
            return parsed_info
            
        except Exception as e:
            logger.error(f"Counter-notice parsing failed: {str(e)}")
            return {'parsing_error': str(e)}
    
    async def _notify_complainant_of_counter_notice(
        self,
        takedown_request: TakedownRequest,
        counter_notice_info: Dict[str, Any]
    ) -> None:
        """Notify the original complainant about the counter-notice."""
        try:
            # Generate counter-notice notification email
            notification_data = {
                'takedown_request': takedown_request,
                'counter_notice_received': True,
                'counter_notice_summary': counter_notice_info,
                'next_steps': [
                    'Review the counter-notice carefully',
                    'You have 10-14 business days to file a court action',
                    'If no action is filed, content may be restored'
                ]
            }
            
            # This would send an email to the original complainant
            # Implementation depends on your email service configuration
            
            logger.info(f"Counter-notice notification prepared for request {takedown_request.id}")
            
        except Exception as e:
            logger.error(f"Failed to notify complainant of counter-notice: {str(e)}")
    
    async def _schedule_removal_verification(self, takedown_request: TakedownRequest) -> None:
        """Schedule verification that content was actually removed."""
        try:
            verification_data = {
                'request_id': str(takedown_request.id),
                'infringing_url': str(takedown_request.infringement_data.infringing_url),
                'scheduled_for': (datetime.utcnow() + timedelta(hours=24)).isoformat(),
                'verification_type': 'content_removal'
            }
            
            cache_key = f"verification_schedule:{takedown_request.id}"
            await self.cache_manager.set(
                cache_key,
                verification_data,
                ttl=timedelta(days=7)
            )
            
            logger.info(f"Scheduled removal verification for request {takedown_request.id}")
            
        except Exception as e:
            logger.error(f"Failed to schedule removal verification: {str(e)}")
    
    async def check_for_new_responses(self) -> List[Dict[str, Any]]:
        """
        Check email inbox for new responses to DMCA notices.
        
        Returns:
            List of new responses found
        """
        try:
            new_responses = []
            
            # Check IMAP mailbox if configured
            if self.imap_config:
                imap_responses = await self._check_imap_responses()
                new_responses.extend(imap_responses)
            
            # Check POP3 mailbox if configured
            if self.pop3_config:
                pop3_responses = await self._check_pop3_responses()
                new_responses.extend(pop3_responses)
            
            return new_responses
            
        except Exception as e:
            logger.error(f"Failed to check for new responses: {str(e)}")
            return []
    
    async def _check_imap_responses(self) -> List[Dict[str, Any]]:
        """Check IMAP mailbox for new responses."""
        # This would implement IMAP checking
        # Placeholder implementation
        return []
    
    async def _check_pop3_responses(self) -> List[Dict[str, Any]]:
        """Check POP3 mailbox for new responses."""
        # This would implement POP3 checking
        # Placeholder implementation
        return []
    
    async def get_response_statistics(self) -> Dict[str, Any]:
        """Get statistics about processed responses."""
        try:
            # This would query stored response data
            # Placeholder implementation
            return {
                'total_responses': 0,
                'by_type': {},
                'average_response_time': 0,
                'counter_notices': 0,
                'successful_takedowns': 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get response statistics: {str(e)}")
            return {'error': str(e)}