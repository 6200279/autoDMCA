"""
Security and Anonymity Protection Utilities

Provides tools for maintaining creator anonymity while ensuring legal compliance
in DMCA takedown notices and communications.
"""

import hashlib
import secrets
import logging
from typing import Dict, Optional, Any, List
from datetime import datetime
import re

from ..models.takedown import CreatorProfile
from ..models.hosting import DMCAAgent, ContactInfo

logger = logging.getLogger(__name__)


class AnonymityHelper:
    """
    Helper class for maintaining creator anonymity in DMCA processes.
    """
    
    def __init__(self, default_agent: DMCAAgent):
        """
        Initialize anonymity helper.
        
        Args:
            default_agent: Default DMCA agent for anonymous representation
        """
        self.default_agent = default_agent
        
        # Common pseudonym patterns for validation
        self.pseudonym_patterns = [
            r'^[A-Z][a-z]+\s[A-Z][a-z]+$',  # First Last
            r'^[A-Z][a-z]+\s[A-Z]\.$',      # First L.
            r'^[A-Z]\.\s[A-Z][a-z]+$',      # F. Last
        ]
    
    def anonymize_creator_profile(
        self,
        creator_profile: CreatorProfile,
        agent: Optional[DMCAAgent] = None
    ) -> Dict[str, Any]:
        """
        Create anonymized contact information for DMCA notices.
        
        Args:
            creator_profile: Original creator profile
            agent: Optional custom DMCA agent (uses default if not provided)
        
        Returns:
            Dict with anonymized contact information
        """
        try:
            selected_agent = agent or self.default_agent
            
            # Use agent information for external communications
            anonymized_contact = {
                'public_name': creator_profile.public_name,  # Keep stage name/pseudonym
                'contact_name': selected_agent.name,
                'contact_email': selected_agent.email,
                'contact_phone': selected_agent.phone,
                'contact_address': selected_agent.get_formatted_address(),
                'business_name': creator_profile.business_name,
                
                # Maintain legal compliance
                'is_authorized_agent': True,
                'agent_organization': selected_agent.organization,
                'agent_title': selected_agent.title,
                
                # Privacy flags
                'anonymity_enabled': True,
                'real_identity_protected': True,
            }
            
            return anonymized_contact
            
        except Exception as e:
            logger.error(f"Anonymization failed: {str(e)}")
            raise ValueError(f"Failed to anonymize creator profile: {str(e)}")
    
    def validate_pseudonym(self, name: str) -> Dict[str, Any]:
        """
        Validate that a name appears to be a proper pseudonym.
        
        Args:
            name: Name to validate
        
        Returns:
            Dict with validation results
        """
        validation_result = {
            'is_valid': False,
            'is_pseudonym': False,
            'warnings': [],
            'recommendations': []
        }
        
        try:
            if not name or len(name.strip()) < 2:
                validation_result['warnings'].append("Name is too short")
                return validation_result
            
            name = name.strip()
            
            # Check for common real name patterns that might expose identity
            real_name_indicators = [
                r'\b(jr|sr|iii|iv)\b',  # Suffixes
                r'\b(dr|prof|mr|mrs|ms)\b',  # Titles
                r'[0-9]',  # Numbers in names are unusual
                r'[@#$%^&*]',  # Special characters
            ]
            
            has_real_name_indicators = any(
                re.search(pattern, name.lower()) 
                for pattern in real_name_indicators
            )
            
            if has_real_name_indicators:
                validation_result['warnings'].append(
                    "Name contains patterns that might indicate real identity"
                )
            
            # Check for pseudonym patterns
            is_pseudonym = any(
                re.match(pattern, name) 
                for pattern in self.pseudonym_patterns
            )
            
            validation_result['is_pseudonym'] = is_pseudonym
            
            # Length checks
            if len(name) > 50:
                validation_result['warnings'].append("Name is unusually long")
            
            # Word count check
            word_count = len(name.split())
            if word_count == 1:
                validation_result['recommendations'].append(
                    "Consider using a first and last name format"
                )
            elif word_count > 3:
                validation_result['warnings'].append(
                    "Name has many parts - consider simplifying"
                )
            
            # Overall validation
            validation_result['is_valid'] = (
                len(validation_result['warnings']) == 0 and
                len(name.split()) >= 1 and
                len(name) <= 50
            )
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Pseudonym validation failed: {str(e)}")
            validation_result['warnings'].append(f"Validation error: {str(e)}")
            return validation_result
    
    def generate_secure_pseudonym(self, seed: Optional[str] = None) -> str:
        """
        Generate a secure pseudonym for anonymous use.
        
        Args:
            seed: Optional seed for consistent generation
        
        Returns:
            Generated pseudonym
        """
        try:
            # Lists of common first and last names for pseudonyms
            first_names = [
                'Alex', 'Jordan', 'Taylor', 'Morgan', 'Casey', 'Riley', 'Avery',
                'Quinn', 'Sage', 'Blake', 'Cameron', 'Drew', 'Emery', 'Finley',
                'Harper', 'Hayden', 'Jamie', 'Kendall', 'Lane', 'Marley'
            ]
            
            last_names = [
                'Anderson', 'Johnson', 'Williams', 'Brown', 'Davis', 'Miller',
                'Wilson', 'Moore', 'Taylor', 'Thomas', 'Jackson', 'White',
                'Harris', 'Martin', 'Thompson', 'Garcia', 'Martinez', 'Robinson',
                'Clark', 'Rodriguez', 'Lewis', 'Lee', 'Walker', 'Hall'
            ]
            
            if seed:
                # Use seed for consistent generation
                hash_obj = hashlib.sha256(seed.encode())
                hash_bytes = hash_obj.digest()
                first_idx = hash_bytes[0] % len(first_names)
                last_idx = hash_bytes[1] % len(last_names)
            else:
                # Random generation
                first_idx = secrets.randbelow(len(first_names))
                last_idx = secrets.randbelow(len(last_names))
            
            pseudonym = f"{first_names[first_idx]} {last_names[last_idx]}"
            
            # Validate the generated pseudonym
            validation = self.validate_pseudonym(pseudonym)
            if not validation['is_valid']:
                logger.warning(f"Generated pseudonym validation issues: {validation['warnings']}")
            
            return pseudonym
            
        except Exception as e:
            logger.error(f"Pseudonym generation failed: {str(e)}")
            return "Anonymous Creator"
    
    def create_anonymous_contact_info(
        self,
        creator_profile: CreatorProfile,
        purpose: str = "dmca_notice"
    ) -> ContactInfo:
        """
        Create anonymous contact information for specific purposes.
        
        Args:
            creator_profile: Original creator profile
            purpose: Purpose of the contact (dmca_notice, legal, etc.)
        
        Returns:
            Anonymous contact information
        """
        try:
            # Use agent address for anonymity
            agent = self.default_agent
            
            anonymous_contact = ContactInfo(
                name=creator_profile.public_name,  # Use pseudonym/stage name
                email=agent.email,  # Use agent email
                phone=agent.phone,   # Use agent phone
                
                # Use agent's address to protect creator location
                address_line1=agent.address_line1,
                address_line2=agent.address_line2,
                city=agent.city,
                state_province=agent.state_province,
                postal_code=agent.postal_code,
                country=agent.country,
                
                # Add purpose-specific URLs if needed
                contact_form_url=None,  # Don't expose creator's forms
                dmca_page_url=None,     # Use agent's DMCA page
            )
            
            return anonymous_contact
            
        except Exception as e:
            logger.error(f"Anonymous contact creation failed: {str(e)}")
            raise ValueError(f"Failed to create anonymous contact: {str(e)}")
    
    def sanitize_personal_info(self, text: str, creator_profile: CreatorProfile) -> str:
        """
        Remove or replace personal information from text content.
        
        Args:
            text: Text content to sanitize
            creator_profile: Creator profile with personal info to protect
        
        Returns:
            Sanitized text
        """
        try:
            if not text:
                return text
            
            sanitized = text
            
            # Personal information to redact
            personal_info = [
                creator_profile.email,
                creator_profile.phone,
                creator_profile.address_line1,
                creator_profile.address_line2,
                creator_profile.city,
                creator_profile.state_province,
                creator_profile.postal_code,
            ]
            
            # Remove personal info
            for info in personal_info:
                if info and info in sanitized:
                    sanitized = sanitized.replace(info, "[REDACTED]")
            
            # Remove email patterns
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            if re.search(email_pattern, sanitized):
                # Only redact if it's not the agent's email
                agent_email = self.default_agent.email
                emails_found = re.findall(email_pattern, sanitized)
                for email in emails_found:
                    if email != agent_email:
                        sanitized = sanitized.replace(email, "[EMAIL REDACTED]")
            
            # Remove phone patterns
            phone_pattern = r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
            if re.search(phone_pattern, sanitized):
                agent_phone = self.default_agent.phone
                phones_found = re.findall(phone_pattern, sanitized)
                for phone in phones_found:
                    if phone != agent_phone:
                        sanitized = re.sub(phone_pattern, "[PHONE REDACTED]", sanitized)
            
            return sanitized
            
        except Exception as e:
            logger.error(f"Text sanitization failed: {str(e)}")
            return text  # Return original if sanitization fails
    
    def assess_privacy_risk(
        self,
        creator_profile: CreatorProfile,
        dmca_content: str
    ) -> Dict[str, Any]:
        """
        Assess privacy risks in DMCA notice content.
        
        Args:
            creator_profile: Creator profile to assess
            dmca_content: DMCA notice content
        
        Returns:
            Dict with risk assessment
        """
        try:
            risk_assessment = {
                'overall_risk': 'low',
                'risks_found': [],
                'recommendations': [],
                'privacy_score': 100  # Start with perfect score
            }
            
            # Check for personal email exposure
            if creator_profile.email in dmca_content:
                risk_assessment['risks_found'].append('Personal email address exposed')
                risk_assessment['recommendations'].append('Use agent email instead')
                risk_assessment['privacy_score'] -= 20
            
            # Check for personal phone exposure
            if creator_profile.phone and creator_profile.phone in dmca_content:
                risk_assessment['risks_found'].append('Personal phone number exposed')
                risk_assessment['recommendations'].append('Use agent phone instead')
                risk_assessment['privacy_score'] -= 15
            
            # Check for address exposure
            address_parts = [
                creator_profile.address_line1,
                creator_profile.city,
                creator_profile.state_province
            ]
            
            for addr_part in address_parts:
                if addr_part and addr_part in dmca_content:
                    risk_assessment['risks_found'].append('Personal address information exposed')
                    risk_assessment['recommendations'].append('Use agent address for all correspondence')
                    risk_assessment['privacy_score'] -= 25
                    break
            
            # Check pseudonym quality
            pseudonym_validation = self.validate_pseudonym(creator_profile.public_name)
            if not pseudonym_validation['is_valid']:
                risk_assessment['risks_found'].append('Pseudonym may not provide adequate protection')
                risk_assessment['recommendations'].extend(pseudonym_validation['recommendations'])
                risk_assessment['privacy_score'] -= 10
            
            # Check for social media username patterns
            for username in creator_profile.protected_usernames:
                if username.lower() in dmca_content.lower():
                    # This is expected, but check if it might reveal real identity
                    if any(char.isdigit() for char in username):
                        risk_assessment['risks_found'].append(
                            'Username contains numbers which might be personal (birth year, etc.)'
                        )
                        risk_assessment['privacy_score'] -= 5
            
            # Determine overall risk level
            if risk_assessment['privacy_score'] >= 80:
                risk_assessment['overall_risk'] = 'low'
            elif risk_assessment['privacy_score'] >= 60:
                risk_assessment['overall_risk'] = 'medium'
            else:
                risk_assessment['overall_risk'] = 'high'
            
            return risk_assessment
            
        except Exception as e:
            logger.error(f"Privacy risk assessment failed: {str(e)}")
            return {
                'overall_risk': 'unknown',
                'error': str(e),
                'privacy_score': 0
            }
    
    def get_anonymity_checklist(self, creator_profile: CreatorProfile) -> Dict[str, Any]:
        """
        Generate anonymity checklist for creator profile.
        
        Args:
            creator_profile: Creator profile to check
        
        Returns:
            Dict with checklist items and status
        """
        try:
            checklist = {
                'items': [],
                'total_score': 0,
                'max_score': 0,
                'compliance_percentage': 0
            }
            
            checklist_items = [
                {
                    'item': 'Using pseudonym/stage name',
                    'required': True,
                    'weight': 3,
                    'check': lambda: bool(creator_profile.public_name) and creator_profile.public_name != creator_profile.email.split('@')[0]
                },
                {
                    'item': 'Anonymity mode enabled',
                    'required': True,
                    'weight': 3,
                    'check': lambda: creator_profile.use_anonymity
                },
                {
                    'item': 'Agent representation enabled',
                    'required': True,
                    'weight': 3,
                    'check': lambda: creator_profile.agent_representation
                },
                {
                    'item': 'Valid pseudonym format',
                    'required': False,
                    'weight': 2,
                    'check': lambda: self.validate_pseudonym(creator_profile.public_name)['is_valid']
                },
                {
                    'item': 'Business name provided (recommended)',
                    'required': False,
                    'weight': 1,
                    'check': lambda: bool(creator_profile.business_name)
                },
            ]
            
            for item in checklist_items:
                passed = item['check']()
                score = item['weight'] if passed else 0
                
                checklist['items'].append({
                    'description': item['item'],
                    'status': 'pass' if passed else 'fail',
                    'required': item['required'],
                    'weight': item['weight'],
                    'score': score
                })
                
                checklist['total_score'] += score
                checklist['max_score'] += item['weight']
            
            # Calculate compliance percentage
            if checklist['max_score'] > 0:
                checklist['compliance_percentage'] = (
                    checklist['total_score'] / checklist['max_score'] * 100
                )
            
            return checklist
            
        except Exception as e:
            logger.error(f"Anonymity checklist generation failed: {str(e)}")
            return {
                'items': [],
                'error': str(e),
                'total_score': 0,
                'max_score': 0,
                'compliance_percentage': 0
            }