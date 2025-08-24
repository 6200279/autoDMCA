/**
 * Frontend Security Utilities for Content Protection Platform
 * 
 * Provides client-side security measures including:
 * - Input validation and sanitization
 * - XSS protection
 * - CSRF protection
 * - Secure storage
 * - Content Security Policy helpers
 */

import DOMPurify from 'dompurify';

// Security configuration
export const SECURITY_CONFIG = {
  // CSP nonce for inline scripts (if needed)
  cspNonce: document.querySelector('meta[name="csp-nonce"]')?.getAttribute('content') || '',
  
  // API endpoints
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  
  // Security headers
  securityHeaders: {
    'X-Requested-With': 'XMLHttpRequest',
    'X-CSRF-Token': '', // Will be populated from meta tag
    'Content-Type': 'application/json'
  }
};

/**
 * Input Validation and Sanitization
 */
export class InputValidator {
  
  // Common validation patterns
  private static readonly PATTERNS = {
    email: /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/,
    password: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{12,}$/,
    url: /^https?:\/\/[^\s/$.?#].[^\s]*$/,
    phone: /^\+?[1-9]\d{1,14}$/,
    alphanumeric: /^[a-zA-Z0-9]+$/,
    safeString: /^[a-zA-Z0-9\s\-_.,'()]+$/
  };
  
  // Dangerous patterns to detect
  private static readonly DANGEROUS_PATTERNS = [
    /<script[^>]*>.*?<\/script>/gi,
    /javascript:/gi,
    /vbscript:/gi,
    /on\w+\s*=/gi,
    /<iframe[^>]*>.*?<\/iframe>/gi,
    /<object[^>]*>.*?<\/object>/gi,
    /<embed[^>]*>/gi,
    /data:text\/html/gi,
    /eval\s*\(/gi,
    /Function\s*\(/gi,
    /setTimeout\s*\(/gi,
    /setInterval\s*\(/gi
  ];
  
  /**
   * Validate email address
   */
  static validateEmail(email: string): boolean {
    if (!email || email.length > 254) return false;
    return this.PATTERNS.email.test(email.trim().toLowerCase());
  }
  
  /**
   * Validate password strength
   */
  static validatePassword(password: string): { valid: boolean; errors: string[] } {
    const errors: string[] = [];
    
    if (!password) {
      errors.push('Password is required');
      return { valid: false, errors };
    }
    
    if (password.length < 12) {
      errors.push('Password must be at least 12 characters long');
    }
    
    if (!/[a-z]/.test(password)) {
      errors.push('Password must contain at least one lowercase letter');
    }
    
    if (!/[A-Z]/.test(password)) {
      errors.push('Password must contain at least one uppercase letter');
    }
    
    if (!/\d/.test(password)) {
      errors.push('Password must contain at least one number');
    }
    
    if (!/[@$!%*?&]/.test(password)) {
      errors.push('Password must contain at least one special character');
    }
    
    // Check for common passwords
    const commonPasswords = ['password', '123456', 'admin', 'letmein', 'welcome123'];
    if (commonPasswords.includes(password.toLowerCase())) {
      errors.push('Password is too common');
    }
    
    return { valid: errors.length === 0, errors };
  }
  
  /**
   * Validate URL
   */
  static validateUrl(url: string): boolean {
    if (!url) return false;
    
    try {
      const parsed = new URL(url);
      // Only allow HTTP/HTTPS
      if (!['http:', 'https:'].includes(parsed.protocol)) {
        return false;
      }
      
      // Prevent localhost/private IPs in production
      if (import.meta.env.PROD) {
        const hostname = parsed.hostname.toLowerCase();
        const privateIPs = ['localhost', '127.0.0.1', '0.0.0.0', '::1'];
        const privateRanges = ['192.168.', '10.', '172.16.', '172.17.', '172.18.', '172.19.', '172.20.', '172.21.', '172.22.', '172.23.', '172.24.', '172.25.', '172.26.', '172.27.', '172.28.', '172.29.', '172.30.', '172.31.'];
        
        if (privateIPs.includes(hostname) || privateRanges.some(range => hostname.startsWith(range))) {
          return false;
        }
      }
      
      return this.PATTERNS.url.test(url);
    } catch {
      return false;
    }
  }
  
  /**
   * Sanitize HTML input
   */
  static sanitizeHtml(html: string): string {
    if (!html) return '';
    
    // Configure DOMPurify for safe HTML
    const cleanHtml = DOMPurify.sanitize(html, {
      ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'br', 'ul', 'ol', 'li'],
      ALLOWED_ATTR: ['href', 'target', 'rel'],
      ALLOW_DATA_ATTR: false,
      ALLOWED_URI_REGEXP: /^https?:\/\/[^\s/$.?#].[^\s]*$/
    });
    
    return cleanHtml;
  }
  
  /**
   * Sanitize plain text input
   */
  static sanitizeText(text: string, maxLength: number = 1000): string {
    if (!text) return '';
    
    // Remove null bytes and control characters
    let sanitized = text.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '');
    
    // Trim and limit length
    sanitized = sanitized.trim().slice(0, maxLength);
    
    return sanitized;
  }
  
  /**
   * Detect potentially malicious content
   */
  static detectMaliciousContent(content: string): boolean {
    if (!content) return false;
    
    return this.DANGEROUS_PATTERNS.some(pattern => pattern.test(content));
  }
  
  /**
   * Validate file upload
   */
  static validateFile(
    file: File,
    allowedTypes: string[] = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
    maxSize: number = 10 * 1024 * 1024 // 10MB
  ): { valid: boolean; errors: string[] } {
    const errors: string[] = [];
    
    if (!file) {
      errors.push('No file selected');
      return { valid: false, errors };
    }
    
    // Check file size
    if (file.size > maxSize) {
      errors.push(`File size must be less than ${Math.round(maxSize / (1024 * 1024))}MB`);
    }
    
    // Check file type
    if (!allowedTypes.includes(file.type)) {
      errors.push(`File type ${file.type} is not allowed`);
    }
    
    // Check filename for suspicious patterns
    const dangerousExtensions = ['.exe', '.bat', '.cmd', '.scr', '.vbs', '.js', '.jar', '.com', '.pif', '.php', '.asp', '.jsp'];
    const filename = file.name.toLowerCase();
    
    if (dangerousExtensions.some(ext => filename.endsWith(ext))) {
      errors.push('Suspicious file extension detected');
    }
    
    // Check for double extensions
    if ((filename.match(/\./g) || []).length > 1) {
      errors.push('Multiple file extensions not allowed');
    }
    
    return { valid: errors.length === 0, errors };
  }
}

/**
 * Secure Storage Utilities
 */
export class SecureStorage {
  
  private static readonly ENCRYPTION_KEY = 'content_protection_';
  
  /**
   * Simple XOR encryption for client-side data
   * Note: This is NOT cryptographically secure, only for obfuscation
   */
  private static simpleEncrypt(text: string, key: string): string {
    let result = '';
    for (let i = 0; i < text.length; i++) {
      result += String.fromCharCode(
        text.charCodeAt(i) ^ key.charCodeAt(i % key.length)
      );
    }
    return btoa(result);
  }
  
  private static simpleDecrypt(encryptedText: string, key: string): string {
    try {
      const text = atob(encryptedText);
      let result = '';
      for (let i = 0; i < text.length; i++) {
        result += String.fromCharCode(
          text.charCodeAt(i) ^ key.charCodeAt(i % key.length)
        );
      }
      return result;
    } catch {
      return '';
    }
  }
  
  /**
   * Securely store data in localStorage
   */
  static setItem(key: string, value: any): void {
    try {
      const jsonValue = JSON.stringify(value);
      const encrypted = this.simpleEncrypt(jsonValue, this.ENCRYPTION_KEY);
      localStorage.setItem(`secure_${key}`, encrypted);
    } catch (error) {
      console.error('Failed to store secure item:', error);
    }
  }
  
  /**
   * Securely retrieve data from localStorage
   */
  static getItem<T>(key: string): T | null {
    try {
      const encrypted = localStorage.getItem(`secure_${key}`);
      if (!encrypted) return null;
      
      const decrypted = this.simpleDecrypt(encrypted, this.ENCRYPTION_KEY);
      return JSON.parse(decrypted);
    } catch (error) {
      console.error('Failed to retrieve secure item:', error);
      return null;
    }
  }
  
  /**
   * Remove item from secure storage
   */
  static removeItem(key: string): void {
    localStorage.removeItem(`secure_${key}`);
  }
  
  /**
   * Clear all secure storage
   */
  static clear(): void {
    const keys = Object.keys(localStorage);
    keys.forEach(key => {
      if (key.startsWith('secure_')) {
        localStorage.removeItem(key);
      }
    });
  }
  
  /**
   * Store JWT token securely
   */
  static setToken(token: string): void {
    this.setItem('auth_token', token);
    
    // Also set expiration time
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      if (payload.exp) {
        this.setItem('token_expires', payload.exp * 1000); // Convert to milliseconds
      }
    } catch {
      // Invalid token format, ignore
    }
  }
  
  /**
   * Get JWT token if not expired
   */
  static getToken(): string | null {
    const token = this.getItem<string>('auth_token');
    const expires = this.getItem<number>('token_expires');
    
    if (!token) return null;
    
    // Check if token is expired
    if (expires && Date.now() > expires) {
      this.removeItem('auth_token');
      this.removeItem('token_expires');
      return null;
    }
    
    return token;
  }
}

/**
 * CSRF Protection Utilities
 */
export class CSRFProtection {
  
  private static csrfToken: string | null = null;
  
  /**
   * Get CSRF token from meta tag
   */
  static getToken(): string | null {
    if (!this.csrfToken) {
      const metaTag = document.querySelector('meta[name="csrf-token"]') as HTMLMetaElement;
      this.csrfToken = metaTag?.content || null;
    }
    return this.csrfToken;
  }
  
  /**
   * Add CSRF token to headers
   */
  static addToHeaders(headers: HeadersInit = {}): HeadersInit {
    const token = this.getToken();
    if (token) {
      return {
        ...headers,
        'X-CSRF-Token': token
      };
    }
    return headers;
  }
  
  /**
   * Refresh CSRF token
   */
  static async refreshToken(): Promise<void> {
    try {
      const response = await fetch('/api/v1/csrf-token', {
        method: 'GET',
        credentials: 'same-origin'
      });
      
      if (response.ok) {
        const data = await response.json();
        this.csrfToken = data.token;
        
        // Update meta tag
        const metaTag = document.querySelector('meta[name="csrf-token"]') as HTMLMetaElement;
        if (metaTag && this.csrfToken) {
          metaTag.content = this.csrfToken;
        }
      }
    } catch (error) {
      console.error('Failed to refresh CSRF token:', error);
    }
  }
}

/**
 * Secure HTTP Client
 */
export class SecureHttpClient {
  
  private static defaultHeaders: HeadersInit = {
    'Content-Type': 'application/json',
    'X-Requested-With': 'XMLHttpRequest'
  };
  
  /**
   * Make secure HTTP request
   */
  static async request(
    url: string,
    options: RequestInit = {}
  ): Promise<Response> {
    
    // Validate URL
    if (!InputValidator.validateUrl(url) && !url.startsWith('/')) {
      throw new Error('Invalid URL');
    }
    
    // Prepare headers
    const headers: HeadersInit = {
      ...this.defaultHeaders,
      ...options.headers
    };
    
    // Add authentication token
    const token = SecureStorage.getToken();
    if (token) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
    }
    
    // Add CSRF protection for unsafe methods
    if (options.method && !['GET', 'HEAD', 'OPTIONS'].includes(options.method.toUpperCase())) {
      CSRFProtection.addToHeaders(headers);
    }
    
    // Make request
    const response = await fetch(url, {
      ...options,
      headers,
      credentials: 'same-origin' // Include cookies for CSRF protection
    });
    
    // Handle authentication errors
    if (response.status === 401) {
      SecureStorage.removeItem('auth_token');
      SecureStorage.removeItem('token_expires');
      // Redirect to login or trigger authentication flow
      window.location.href = '/login';
      throw new Error('Authentication required');
    }
    
    // Handle CSRF errors
    if (response.status === 403) {
      await CSRFProtection.refreshToken();
      throw new Error('CSRF token validation failed');
    }
    
    return response;
  }
  
  /**
   * GET request
   */
  static async get(url: string): Promise<Response> {
    return this.request(url, { method: 'GET' });
  }
  
  /**
   * POST request
   */
  static async post(url: string, data?: any): Promise<Response> {
    return this.request(url, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined
    });
  }
  
  /**
   * PUT request
   */
  static async put(url: string, data?: any): Promise<Response> {
    return this.request(url, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined
    });
  }
  
  /**
   * DELETE request
   */
  static async delete(url: string): Promise<Response> {
    return this.request(url, { method: 'DELETE' });
  }
}

/**
 * Content Security Policy Helpers
 */
export class CSPHelper {
  
  /**
   * Report CSP violations
   */
  static reportViolation(violation: SecurityPolicyViolationEvent): void {
    console.warn('CSP Violation:', violation);
    
    // Send violation report to server (if configured)
    if (import.meta.env.VITE_CSP_REPORT_URI) {
      fetch(import.meta.env.VITE_CSP_REPORT_URI, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/csp-report'
        },
        body: JSON.stringify({
          'csp-report': {
            'blocked-uri': violation.blockedURI,
            'document-uri': violation.documentURI,
            'line-number': violation.lineNumber,
            'original-policy': violation.originalPolicy,
            'referrer': violation.referrer,
            'script-sample': violation.sample,
            'source-file': violation.sourceFile,
            'violated-directive': violation.violatedDirective
          }
        })
      }).catch(error => console.error('Failed to report CSP violation:', error));
    }
  }
  
  /**
   * Initialize CSP reporting
   */
  static initReporting(): void {
    document.addEventListener('securitypolicyviolation', this.reportViolation);
  }
}

/**
 * Security Event Logger
 */
export class SecurityLogger {
  
  /**
   * Log security event
   */
  static logEvent(
    eventType: string,
    details: Record<string, any>,
    severity: 'low' | 'medium' | 'high' | 'critical' = 'medium'
  ): void {
    const event = {
      timestamp: new Date().toISOString(),
      eventType,
      severity,
      details,
      userAgent: navigator.userAgent,
      url: window.location.href
    };
    
    console.warn('Security Event:', event);
    
    // Send to server (if configured)
    if (import.meta.env.VITE_SECURITY_LOG_ENDPOINT) {
      SecureHttpClient.post(import.meta.env.VITE_SECURITY_LOG_ENDPOINT, event)
        .catch(error => console.error('Failed to log security event:', error));
    }
  }
  
  /**
   * Log authentication event
   */
  static logAuthEvent(eventType: 'login' | 'logout' | 'token_refresh' | 'auth_error', details?: Record<string, any>): void {
    this.logEvent(`auth_${eventType}`, details || {}, 'medium');
  }
  
  /**
   * Log input validation failure
   */
  static logValidationFailure(field: string, value: string, error: string): void {
    this.logEvent('input_validation_failure', {
      field,
      valueLength: value.length,
      error,
      hasDangerousContent: InputValidator.detectMaliciousContent(value)
    }, 'high');
  }
}

// Initialize security features
export const initializeSecurity = (): void => {
  // Initialize CSP reporting
  CSPHelper.initReporting();
  
  // Log security initialization
  SecurityLogger.logEvent('security_initialized', {
    userAgent: navigator.userAgent,
    cookieEnabled: navigator.cookieEnabled,
    onLine: navigator.onLine
  }, 'low');
  
  // Set up periodic token refresh
  const refreshToken = () => {
    const token = SecureStorage.getToken();
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        const exp = payload.exp * 1000;
        const now = Date.now();
        
        // Refresh token if it expires within 5 minutes
        if (exp - now < 5 * 60 * 1000) {
          CSRFProtection.refreshToken();
        }
      } catch (error) {
        console.error('Token refresh check failed:', error);
      }
    }
  };
  
  // Check token every minute
  setInterval(refreshToken, 60 * 1000);
};

export default {
  InputValidator,
  SecureStorage,
  CSRFProtection,
  SecureHttpClient,
  CSPHelper,
  SecurityLogger,
  initializeSecurity
};