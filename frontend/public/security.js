/**
 * Early Security Initialization Script
 * 
 * This script runs before React loads to implement early security measures
 * and protect against certain types of attacks.
 */

(function() {
  'use strict';
  
  // Security configuration
  const SECURITY_CONFIG = {
    // Enable strict mode for all scripts
    strictMode: true,
    
    // Console protection in production
    disableConsoleInProduction: true,
    
    // DevTools detection
    enableDevToolsDetection: true,
    
    // Frame busting protection
    enableFrameBusting: true,
    
    // Clickjacking protection
    enableClickjackingProtection: true
  };
  
  /**
   * Console Protection
   * Disable console in production to prevent information leakage
   */
  function protectConsole() {
    if (SECURITY_CONFIG.disableConsoleInProduction && 
        window.location.hostname !== 'localhost' && 
        !window.location.hostname.startsWith('127.0.0.1')) {
      
      const noop = function() {};
      const consoleProps = ['log', 'warn', 'error', 'info', 'debug', 'trace', 'dir', 'group', 'groupEnd', 'time', 'timeEnd', 'profile', 'profileEnd', 'dirxml', 'assert', 'count', 'markTimeline', 'timeStamp', 'clear'];
      
      consoleProps.forEach(function(prop) {
        if (console[prop]) {
          console[prop] = noop;
        }
      });
    }
  }
  
  /**
   * DevTools Detection
   * Detect if browser DevTools are open
   */
  function detectDevTools() {
    if (!SECURITY_CONFIG.enableDevToolsDetection) return;
    
    let devtools = {
      open: false,
      orientation: null
    };
    
    const threshold = 160;
    
    setInterval(function() {
      if (window.outerHeight - window.innerHeight > threshold || 
          window.outerWidth - window.innerWidth > threshold) {
        
        if (!devtools.open) {
          devtools.open = true;
          devtools.orientation = (window.outerHeight - window.innerHeight > threshold) ? 'vertical' : 'horizontal';
          
          // Log security event
          logSecurityEvent('devtools_detected', {
            orientation: devtools.orientation,
            windowSize: {
              outer: { width: window.outerWidth, height: window.outerHeight },
              inner: { width: window.innerWidth, height: window.innerHeight }
            }
          });
          
          // Optional: Take action when DevTools are detected
          // window.location.reload();
        }
      } else {
        devtools.open = false;
      }
    }, 500);
    
    // Keyboard shortcut detection
    document.addEventListener('keydown', function(e) {
      // F12
      if (e.keyCode === 123) {
        logSecurityEvent('f12_pressed', { timestamp: Date.now() });
        e.preventDefault();
        return false;
      }
      
      // Ctrl+Shift+I, Ctrl+Shift+C, Ctrl+Shift+J
      if (e.ctrlKey && e.shiftKey && (e.keyCode === 73 || e.keyCode === 67 || e.keyCode === 74)) {
        logSecurityEvent('devtools_shortcut_pressed', { keyCode: e.keyCode });
        e.preventDefault();
        return false;
      }
      
      // Ctrl+U (View Source)
      if (e.ctrlKey && e.keyCode === 85) {
        logSecurityEvent('view_source_pressed', { timestamp: Date.now() });
        e.preventDefault();
        return false;
      }
    });
  }
  
  /**
   * Frame Busting Protection
   * Prevent the page from being loaded in a frame/iframe
   */
  function enableFrameBusting() {
    if (!SECURITY_CONFIG.enableFrameBusting) return;
    
    try {
      if (window.top !== window.self) {
        // Page is being loaded in a frame
        logSecurityEvent('framejacking_attempt', {
          topOrigin: window.top.location.origin,
          selfOrigin: window.self.location.origin
        });
        
        // Break out of the frame
        window.top.location = window.self.location;
      }
    } catch (e) {
      // Cross-origin frame detected
      logSecurityEvent('cross_origin_frame_detected', { error: e.message });
      
      // Force redirect to break out of frame
      document.write('<script>window.top.location="' + window.location + '";<\/script>');
      document.close();
    }
  }
  
  /**
   * Clickjacking Protection
   * Additional protection against clickjacking attacks
   */
  function enableClickjackingProtection() {
    if (!SECURITY_CONFIG.enableClickjackingProtection) return;
    
    // Create invisible overlay to detect clicks outside the frame
    const overlay = document.createElement('div');
    overlay.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: transparent;
      z-index: -1;
      pointer-events: none;
    `;
    
    overlay.addEventListener('click', function() {
      logSecurityEvent('clickjacking_attempt', { timestamp: Date.now() });
    });
    
    document.addEventListener('DOMContentLoaded', function() {
      document.body.appendChild(overlay);
    });
  }
  
  /**
   * Right-Click Protection
   * Disable right-click context menu (optional)
   */
  function disableRightClick() {
    document.addEventListener('contextmenu', function(e) {
      logSecurityEvent('right_click_disabled', { 
        element: e.target.tagName,
        x: e.clientX,
        y: e.clientY 
      });
      e.preventDefault();
      return false;
    });
  }
  
  /**
   * Text Selection Protection
   * Disable text selection (optional)
   */
  function disableTextSelection() {
    document.addEventListener('selectstart', function(e) {
      logSecurityEvent('text_selection_disabled', { 
        element: e.target.tagName 
      });
      e.preventDefault();
      return false;
    });
    
    document.addEventListener('dragstart', function(e) {
      logSecurityEvent('drag_disabled', { 
        element: e.target.tagName 
      });
      e.preventDefault();
      return false;
    });
  }
  
  /**
   * Security Event Logging
   */
  function logSecurityEvent(eventType, details) {
    const event = {
      timestamp: new Date().toISOString(),
      eventType: eventType,
      details: details,
      userAgent: navigator.userAgent,
      url: window.location.href,
      referrer: document.referrer
    };
    
    // Store in session storage for later transmission
    try {
      const events = JSON.parse(sessionStorage.getItem('security_events') || '[]');
      events.push(event);
      
      // Keep only last 100 events
      if (events.length > 100) {
        events.splice(0, events.length - 100);
      }
      
      sessionStorage.setItem('security_events', JSON.stringify(events));
    } catch (e) {
      console.error('Failed to log security event:', e);
    }
    
    // Try to send immediately if API is available
    if (window.fetch) {
      fetch('/api/v1/security/events', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(event)
      }).catch(function() {
        // Ignore errors - events are stored in sessionStorage as backup
      });
    }
  }
  
  /**
   * DOM Clobbering Protection
   */
  function preventDOMClobbering() {
    // Freeze important global objects
    if (Object.freeze && Object.seal) {
      try {
        Object.freeze(window.location);
        Object.freeze(document.location);
        Object.seal(window);
        Object.seal(document);
      } catch (e) {
        // Some browsers may not allow this
      }
    }
  }
  
  /**
   * Initialize Security Measures
   */
  function initializeSecurity() {
    // Log initialization
    logSecurityEvent('security_early_init', {
      userAgent: navigator.userAgent,
      cookieEnabled: navigator.cookieEnabled,
      onLine: navigator.onLine,
      language: navigator.language,
      platform: navigator.platform,
      screenResolution: screen.width + 'x' + screen.height
    });
    
    // Enable security measures
    protectConsole();
    detectDevTools();
    enableFrameBusting();
    enableClickjackingProtection();
    preventDOMClobbering();
    
    // Optional protections (uncomment if needed)
    // disableRightClick();
    // disableTextSelection();
    
    // CSP violation reporting
    document.addEventListener('securitypolicyviolation', function(e) {
      logSecurityEvent('csp_violation', {
        blockedURI: e.blockedURI,
        documentURI: e.documentURI,
        originalPolicy: e.originalPolicy,
        violatedDirective: e.violatedDirective,
        lineNumber: e.lineNumber,
        sourceFile: e.sourceFile
      });
    });
    
    // Monitor for suspicious activity
    let clickCount = 0;
    let lastClickTime = 0;
    
    document.addEventListener('click', function() {
      const now = Date.now();
      if (now - lastClickTime < 100) { // Clicks less than 100ms apart
        clickCount++;
        if (clickCount > 10) {
          logSecurityEvent('suspicious_clicking', {
            clickCount: clickCount,
            timeWindow: now - lastClickTime
          });
          clickCount = 0;
        }
      } else {
        clickCount = 0;
      }
      lastClickTime = now;
    });
  }
  
  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeSecurity);
  } else {
    initializeSecurity();
  }
  
  // Expose security API for React app
  window.SecurityAPI = {
    logEvent: logSecurityEvent,
    getStoredEvents: function() {
      try {
        return JSON.parse(sessionStorage.getItem('security_events') || '[]');
      } catch (e) {
        return [];
      }
    },
    clearStoredEvents: function() {
      sessionStorage.removeItem('security_events');
    }
  };
  
})();