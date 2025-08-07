"""
Validation utilities for the AutoDMCA system.

Provides comprehensive validation for emails, URLs, and other input data
with security considerations.
"""

import re
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from datetime import datetime
import socket

logger = logging.getLogger(__name__)


class EmailValidator:
    """
    Comprehensive email validation utility.
    """
    
    def __init__(self):
        """Initialize email validator with patterns."""
        # RFC 5322 compliant email regex (simplified for practical use)
        self.email_pattern = re.compile(
            r'^[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
        )
        
        # Common disposable email domains to flag
        self.disposable_domains = {
            '10minutemail.com', 'tempmail.org', 'guerrillamail.com',
            'mailinator.com', 'throwaway.email', '7timer.com'
        }
        
        # Common email provider domains for validation
        self.common_domains = {
            'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
            'aol.com', 'icloud.com', 'protonmail.com', 'fastmail.com'
        }
    
    def validate(self, email: str) -> Dict[str, Any]:
        """
        Comprehensive email validation.
        
        Args:
            email: Email address to validate
        
        Returns:
            Dict with validation results
        """
        try:
            validation_result = {
                'is_valid': False,
                'email': email.strip().lower() if email else '',
                'warnings': [],
                'errors': [],
                'domain_info': {},
                'recommendations': []
            }
            
            if not email:
                validation_result['errors'].append('Email is required')
                return validation_result
            
            email = email.strip().lower()
            validation_result['email'] = email
            
            # Basic format validation
            if not self.email_pattern.match(email):
                validation_result['errors'].append('Invalid email format')
                return validation_result
            
            # Length validation
            if len(email) > 320:  # RFC 5321 limit
                validation_result['errors'].append('Email is too long (max 320 characters)')
                return validation_result
            
            # Split local and domain parts
            try:
                local_part, domain_part = email.rsplit('@', 1)
            except ValueError:
                validation_result['errors'].append('Invalid email format')
                return validation_result
            
            # Validate local part
            local_validation = self._validate_local_part(local_part)
            validation_result['warnings'].extend(local_validation['warnings'])
            validation_result['errors'].extend(local_validation['errors'])
            
            # Validate domain part
            domain_validation = self._validate_domain_part(domain_part)
            validation_result['warnings'].extend(domain_validation['warnings'])
            validation_result['errors'].extend(domain_validation['errors'])
            validation_result['domain_info'] = domain_validation['domain_info']
            
            # Check for disposable email
            if domain_part in self.disposable_domains:
                validation_result['warnings'].append('Email appears to be from a disposable email service')
                validation_result['recommendations'].append('Consider using a permanent email address')
            
            # Overall validation
            validation_result['is_valid'] = len(validation_result['errors']) == 0
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Email validation failed: {str(e)}")
            return {
                'is_valid': False,
                'email': email if email else '',
                'errors': [f'Validation error: {str(e)}'],
                'warnings': [],
                'domain_info': {},
                'recommendations': []
            }
    
    def _validate_local_part(self, local_part: str) -> Dict[str, Any]:
        """Validate the local part (before @) of email address."""
        result = {
            'warnings': [],
            'errors': []
        }
        
        if not local_part:
            result['errors'].append('Local part cannot be empty')
            return result
        
        if len(local_part) > 64:  # RFC 5321 limit
            result['errors'].append('Local part is too long (max 64 characters)')
        
        # Check for consecutive dots
        if '..' in local_part:
            result['errors'].append('Local part cannot contain consecutive dots')
        
        # Check for starting/ending with dot
        if local_part.startswith('.') or local_part.endswith('.'):
            result['errors'].append('Local part cannot start or end with a dot')
        
        # Check for common issues
        if local_part.startswith('+'):
            result['warnings'].append('Email uses plus addressing (may not be supported by all systems)')
        
        return result
    
    def _validate_domain_part(self, domain_part: str) -> Dict[str, Any]:
        """Validate the domain part (after @) of email address."""
        result = {
            'warnings': [],
            'errors': [],
            'domain_info': {
                'domain': domain_part,
                'is_common_provider': domain_part in self.common_domains,
                'is_disposable': domain_part in self.disposable_domains,
                'has_mx_record': False
            }
        }
        
        if not domain_part:
            result['errors'].append('Domain part cannot be empty')
            return result
        
        if len(domain_part) > 253:  # RFC 5321 limit
            result['errors'].append('Domain part is too long (max 253 characters)')
            return result
        
        # Basic domain format validation
        domain_pattern = re.compile(r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$')
        if not domain_pattern.match(domain_part):
            result['errors'].append('Invalid domain format')
            return result
        
        # Check for MX record (simplified check)
        try:
            socket.getaddrinfo(domain_part, None)
            result['domain_info']['has_mx_record'] = True
        except socket.gaierror:
            result['warnings'].append('Domain does not appear to have valid DNS records')
            result['domain_info']['has_mx_record'] = False
        
        # Check TLD length
        if '.' in domain_part:
            tld = domain_part.split('.')[-1]
            if len(tld) < 2:
                result['errors'].append('Invalid top-level domain')
            elif len(tld) > 6:
                result['warnings'].append('Unusually long top-level domain')
        
        return result
    
    def is_business_email(self, email: str) -> bool:
        """Check if email appears to be a business email."""
        try:
            if not email or '@' not in email:
                return False
            
            domain = email.split('@')[1].lower()
            
            # Not a business email if it's a common consumer provider
            if domain in self.common_domains:
                return False
            
            # Not a business email if it's disposable
            if domain in self.disposable_domains:
                return False
            
            # Likely business email if it has multiple subdomains or professional TLD
            parts = domain.split('.')
            if len(parts) >= 3:  # e.g., mail.company.com
                return True
            
            # Check for professional TLDs
            professional_tlds = {'.com', '.org', '.net', '.edu', '.gov', '.mil', '.law'}
            if any(domain.endswith(tld) for tld in professional_tlds):
                return True
            
            return True  # Default to business if not obviously personal
            
        except Exception:
            return False


class URLValidator:
    """
    Comprehensive URL validation utility.
    """
    
    def __init__(self):
        """Initialize URL validator."""
        # Common URL schemes
        self.valid_schemes = {'http', 'https', 'ftp', 'ftps'}
        
        # Suspicious TLDs that might indicate malicious content
        self.suspicious_tlds = {'.tk', '.ml', '.cf', '.ga', '.bit', '.onion'}
        
        # Common file extensions for different content types
        self.content_extensions = {
            'image': {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'},
            'video': {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv'},
            'audio': {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a'},
            'document': {'.pdf', '.doc', '.docx', '.txt', '.rtf'},
            'archive': {'.zip', '.rar', '.7z', '.tar', '.gz'}
        }
    
    def validate(self, url: str) -> Dict[str, Any]:
        """
        Comprehensive URL validation.
        
        Args:
            url: URL to validate
        
        Returns:
            Dict with validation results
        """
        try:
            validation_result = {
                'is_valid': False,
                'url': url.strip() if url else '',
                'parsed': {},
                'warnings': [],
                'errors': [],
                'security_flags': [],
                'content_type_hints': []
            }
            
            if not url:
                validation_result['errors'].append('URL is required')
                return validation_result
            
            url = url.strip()
            validation_result['url'] = url
            
            # Basic format validation
            try:
                parsed = urlparse(url)
                validation_result['parsed'] = {
                    'scheme': parsed.scheme,
                    'netloc': parsed.netloc,
                    'path': parsed.path,
                    'params': parsed.params,
                    'query': parsed.query,
                    'fragment': parsed.fragment
                }
            except Exception as e:
                validation_result['errors'].append(f'URL parsing failed: {str(e)}')
                return validation_result
            
            # Validate scheme
            if not parsed.scheme:
                validation_result['errors'].append('URL must include a scheme (http://, https://)')
            elif parsed.scheme.lower() not in self.valid_schemes:
                validation_result['warnings'].append(f'Unusual URL scheme: {parsed.scheme}')
            
            # Validate netloc (domain)
            if not parsed.netloc:
                validation_result['errors'].append('URL must include a domain')
            else:
                domain_validation = self._validate_domain(parsed.netloc)
                validation_result['warnings'].extend(domain_validation['warnings'])
                validation_result['errors'].extend(domain_validation['errors'])
                validation_result['security_flags'].extend(domain_validation['security_flags'])
            
            # Check URL length
            if len(url) > 2048:  # Common browser limit
                validation_result['warnings'].append('URL is very long (may not work in all browsers)')
            
            # Detect content type from path
            if parsed.path:
                content_hints = self._detect_content_type(parsed.path)
                validation_result['content_type_hints'] = content_hints
            
            # Security checks
            security_checks = self._perform_security_checks(url, parsed)
            validation_result['security_flags'].extend(security_checks)
            
            # Overall validation
            validation_result['is_valid'] = len(validation_result['errors']) == 0
            
            return validation_result
            
        except Exception as e:
            logger.error(f"URL validation failed: {str(e)}")
            return {
                'is_valid': False,
                'url': url if url else '',
                'parsed': {},
                'errors': [f'Validation error: {str(e)}'],
                'warnings': [],
                'security_flags': [],
                'content_type_hints': []
            }
    
    def _validate_domain(self, netloc: str) -> Dict[str, Any]:
        """Validate domain part of URL."""
        result = {
            'warnings': [],
            'errors': [],
            'security_flags': []
        }
        
        # Extract domain (remove port if present)
        domain = netloc.split(':')[0].lower()
        
        if not domain:
            result['errors'].append('Domain cannot be empty')
            return result
        
        # Check for IP addresses
        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', domain):
            result['warnings'].append('URL uses IP address instead of domain name')
            result['security_flags'].append('ip_address_used')
        
        # Check for suspicious TLDs
        for tld in self.suspicious_tlds:
            if domain.endswith(tld):
                result['security_flags'].append('suspicious_tld')
                result['warnings'].append(f'Domain uses suspicious TLD: {tld}')
                break
        
        # Check for very long domains
        if len(domain) > 253:
            result['errors'].append('Domain name is too long')
        
        # Check for subdomain depth (potential typosquatting)
        parts = domain.split('.')
        if len(parts) > 5:
            result['warnings'].append('Domain has many subdomains (check carefully)')
            result['security_flags'].append('deep_subdomain')
        
        # Check for homograph attacks (simplified)
        if any(ord(char) > 127 for char in domain):
            result['warnings'].append('Domain contains non-ASCII characters (check for homograph attacks)')
            result['security_flags'].append('unicode_domain')
        
        return result
    
    def _detect_content_type(self, path: str) -> List[str]:
        """Detect likely content type from URL path."""
        if not path:
            return []
        
        path_lower = path.lower()
        content_hints = []
        
        for content_type, extensions in self.content_extensions.items():
            if any(path_lower.endswith(ext) for ext in extensions):
                content_hints.append(content_type)
        
        # Check for specific patterns
        if '/video/' in path_lower or '/videos/' in path_lower:
            content_hints.append('video')
        elif '/image/' in path_lower or '/images/' in path_lower or '/img/' in path_lower:
            content_hints.append('image')
        elif '/download/' in path_lower or '/dl/' in path_lower:
            content_hints.append('download')
        
        return content_hints
    
    def _perform_security_checks(self, url: str, parsed) -> List[str]:
        """Perform security checks on URL."""
        security_flags = []
        
        url_lower = url.lower()
        
        # Check for URL shorteners
        shortener_domains = {
            'bit.ly', 'tinyurl.com', 't.co', 'goo.gl', 'ow.ly',
            'short.link', 'tiny.cc', 'is.gd', 'buff.ly'
        }
        
        domain = parsed.netloc.split(':')[0].lower()
        if any(domain.endswith(shortener) for shortener in shortener_domains):
            security_flags.append('url_shortener')
        
        # Check for suspicious keywords in URL
        suspicious_keywords = [
            'admin', 'login', 'password', 'secure', 'bank',
            'paypal', 'amazon', 'google', 'microsoft', 'apple'
        ]
        
        for keyword in suspicious_keywords:
            if keyword in url_lower and keyword not in domain:
                security_flags.append('suspicious_keyword')
                break
        
        # Check for excessive redirects (multiple URL parameters)
        if url_lower.count('http') > 1:
            security_flags.append('potential_redirect_chain')
        
        # Check for encoded URLs
        if '%' in url and any(encoded in url_lower for encoded in ['%2f', '%3a', '%2e']):
            security_flags.append('url_encoding_detected')
        
        return security_flags
    
    def is_likely_piracy_site(self, url: str) -> Dict[str, Any]:
        """Check if URL is likely from a known piracy site."""
        try:
            parsed = urlparse(url.lower())
            domain = parsed.netloc.split(':')[0]
            
            # Common patterns in piracy sites
            piracy_patterns = [
                'leak', 'free', 'download', 'stream', 'watch',
                'torrent', 'crack', 'hack', 'rip', 'cam'
            ]
            
            piracy_tlds = ['.tk', '.ml', '.cf', '.ga']
            
            score = 0
            indicators = []
            
            # Check domain for piracy keywords
            for pattern in piracy_patterns:
                if pattern in domain:
                    score += 2
                    indicators.append(f'Domain contains "{pattern}"')
            
            # Check for suspicious TLD
            if any(domain.endswith(tld) for tld in piracy_tlds):
                score += 3
                indicators.append('Uses suspicious TLD')
            
            # Check path for piracy indicators
            path_lower = parsed.path.lower()
            if any(pattern in path_lower for pattern in piracy_patterns):
                score += 1
                indicators.append('Path contains piracy-related terms')
            
            # Determine likelihood
            if score >= 5:
                likelihood = 'high'
            elif score >= 3:
                likelihood = 'medium'
            elif score >= 1:
                likelihood = 'low'
            else:
                likelihood = 'none'
            
            return {
                'likelihood': likelihood,
                'score': score,
                'indicators': indicators,
                'domain': domain
            }
            
        except Exception as e:
            logger.error(f"Piracy site detection failed: {str(e)}")
            return {
                'likelihood': 'unknown',
                'score': 0,
                'indicators': [f'Detection error: {str(e)}'],
                'domain': ''
            }