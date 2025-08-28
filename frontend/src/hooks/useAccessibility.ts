import { useRef, useCallback, useEffect } from 'react';

/**
 * Enhanced accessibility hook for managing screen reader announcements,
 * focus management, and keyboard shortcuts
 */
export interface UseAccessibilityOptions {
  announcements?: boolean;
  keyboardShortcuts?: boolean;
  focusManagement?: boolean;
  highContrast?: boolean;
}

export interface AccessibilityHook {
  announce: (message: string, priority?: 'polite' | 'assertive') => void;
  manageFocus: {
    trap: (element: HTMLElement) => () => void;
    restore: () => void;
    saveFocus: () => void;
    moveTo: (element: HTMLElement | null) => void;
  };
  keyboard: {
    registerShortcut: (key: string, handler: () => void, description: string) => () => void;
    getShortcuts: () => Array<{ key: string; description: string }>;
  };
  screen: {
    isScreenReader: boolean;
    prefersReducedMotion: boolean;
    prefersHighContrast: boolean;
  };
}

export const useAccessibility = (options: UseAccessibilityOptions = {}): AccessibilityHook => {
  const {
    announcements = true,
    keyboardShortcuts = true,
    focusManagement = true,
    highContrast = true
  } = options;

  // Live region for announcements
  const liveRegionRef = useRef<HTMLDivElement | null>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const keyboardShortcutsRef = useRef<Map<string, { handler: () => void; description: string }>>(new Map());
  
  // Initialize live regions
  useEffect(() => {
    if (!announcements) return;

    // Create polite live region
    const politeRegion = document.getElementById('polite-announcements') || 
      document.createElement('div');
    politeRegion.id = 'polite-announcements';
    politeRegion.setAttribute('aria-live', 'polite');
    politeRegion.setAttribute('aria-atomic', 'true');
    politeRegion.className = 'sr-only';
    
    // Create assertive live region
    const assertiveRegion = document.getElementById('assertive-announcements') || 
      document.createElement('div');
    assertiveRegion.id = 'assertive-announcements';
    assertiveRegion.setAttribute('aria-live', 'assertive');
    assertiveRegion.setAttribute('aria-atomic', 'true');
    assertiveRegion.className = 'sr-only';

    if (!document.getElementById('polite-announcements')) {
      document.body.appendChild(politeRegion);
    }
    if (!document.getElementById('assertive-announcements')) {
      document.body.appendChild(assertiveRegion);
    }

    liveRegionRef.current = politeRegion;

    return () => {
      // Cleanup on unmount
      politeRegion.remove();
      assertiveRegion.remove();
    };
  }, [announcements]);

  // Screen reader and preference detection
  const screen = {
    isScreenReader: window.navigator.userAgent.includes('NVDA') || 
                   window.navigator.userAgent.includes('JAWS') || 
                   window.speechSynthesis || 
                   !!window.navigator.userAgent.match(/HeadlessChrome/),
    prefersReducedMotion: window.matchMedia('(prefers-reduced-motion: reduce)').matches,
    prefersHighContrast: window.matchMedia('(prefers-contrast: high)').matches ||
                        window.matchMedia('(-ms-high-contrast: active)').matches
  };

  // Announce messages to screen readers
  const announce = useCallback((message: string, priority: 'polite' | 'assertive' = 'polite') => {
    if (!announcements) return;
    
    const targetId = priority === 'assertive' ? 'assertive-announcements' : 'polite-announcements';
    const region = document.getElementById(targetId);
    
    if (region) {
      // Clear previous announcement
      region.textContent = '';
      
      // Add new announcement with slight delay to ensure it's read
      setTimeout(() => {
        region.textContent = message;
      }, 10);
    }
  }, [announcements]);

  // Focus management utilities
  const manageFocus = {
    trap: useCallback((element: HTMLElement) => {
      if (!focusManagement) return () => {};

      const focusableSelector = 
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';
      const focusableElements = element.querySelectorAll<HTMLElement>(focusableSelector);
      const firstFocusable = focusableElements[0];
      const lastFocusable = focusableElements[focusableElements.length - 1];

      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === 'Tab') {
          if (e.shiftKey) {
            if (document.activeElement === firstFocusable) {
              e.preventDefault();
              lastFocusable?.focus();
            }
          } else {
            if (document.activeElement === lastFocusable) {
              e.preventDefault();
              firstFocusable?.focus();
            }
          }
        }
        
        if (e.key === 'Escape') {
          // Allow escape to break out of trap
          manageFocus.restore();
        }
      };

      element.addEventListener('keydown', handleKeyDown);
      
      // Focus first element
      firstFocusable?.focus();

      return () => {
        element.removeEventListener('keydown', handleKeyDown);
      };
    }, [focusManagement]),

    saveFocus: useCallback(() => {
      if (focusManagement) {
        previousFocusRef.current = document.activeElement as HTMLElement;
      }
    }, [focusManagement]),

    restore: useCallback(() => {
      if (focusManagement && previousFocusRef.current) {
        previousFocusRef.current.focus();
        previousFocusRef.current = null;
      }
    }, [focusManagement]),

    moveTo: useCallback((element: HTMLElement | null) => {
      if (focusManagement && element) {
        element.focus();
        element.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    }, [focusManagement])
  };

  // Keyboard shortcuts management
  const keyboard = {
    registerShortcut: useCallback((key: string, handler: () => void, description: string) => {
      if (!keyboardShortcuts) return () => {};

      const shortcutHandler = (e: KeyboardEvent) => {
        const normalizedKey = key.toLowerCase();
        const eventKey = `${e.ctrlKey ? 'ctrl+' : ''}${e.altKey ? 'alt+' : ''}${e.shiftKey ? 'shift+' : ''}${e.key.toLowerCase()}`;
        
        if (eventKey === normalizedKey) {
          e.preventDefault();
          handler();
        }
      };

      keyboardShortcutsRef.current.set(key, { handler, description });
      document.addEventListener('keydown', shortcutHandler);

      return () => {
        keyboardShortcutsRef.current.delete(key);
        document.removeEventListener('keydown', shortcutHandler);
      };
    }, [keyboardShortcuts]),

    getShortcuts: useCallback(() => {
      return Array.from(keyboardShortcutsRef.current.entries()).map(([key, { description }]) => ({
        key,
        description
      }));
    }, [])
  };

  // Add high contrast support
  useEffect(() => {
    if (!highContrast) return;

    const handleContrastChange = (e: MediaQueryListEvent) => {
      document.documentElement.classList.toggle('high-contrast', e.matches);
    };

    const contrastQuery = window.matchMedia('(prefers-contrast: high)');
    contrastQuery.addEventListener('change', handleContrastChange);
    
    // Set initial state
    if (contrastQuery.matches) {
      document.documentElement.classList.add('high-contrast');
    }

    return () => {
      contrastQuery.removeEventListener('change', handleContrastChange);
    };
  }, [highContrast]);

  return {
    announce,
    manageFocus,
    keyboard,
    screen
  };
};

export default useAccessibility;