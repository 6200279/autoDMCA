/**
 * Shared Utilities for Content Protection Extension
 * Cross-browser compatibility helpers and common functions
 */

// Cross-browser API wrapper
window.ContentProtectionUtils = {
  // Browser API compatibility
  getBrowserAPI() {
    return (typeof browser !== 'undefined') ? browser : chrome;
  },

  // Storage utilities
  async getStorageItem(key) {
    try {
      const browserAPI = this.getBrowserAPI();
      const result = await browserAPI.storage.local.get([key]);
      return result[key];
    } catch (error) {
      console.error(`Error getting storage item ${key}:`, error);
      return null;
    }
  },

  async setStorageItem(key, value) {
    try {
      const browserAPI = this.getBrowserAPI();
      await browserAPI.storage.local.set({ [key]: value });
      return true;
    } catch (error) {
      console.error(`Error setting storage item ${key}:`, error);
      return false;
    }
  },

  async removeStorageItem(key) {
    try {
      const browserAPI = this.getBrowserAPI();
      await browserAPI.storage.local.remove([key]);
      return true;
    } catch (error) {
      console.error(`Error removing storage item ${key}:`, error);
      return false;
    }
  },

  // Message passing utilities
  async sendMessage(message) {
    try {
      const browserAPI = this.getBrowserAPI();
      return await browserAPI.runtime.sendMessage(message);
    } catch (error) {
      console.error('Error sending message:', error);
      return { error: error.message };
    }
  },

  async sendTabMessage(tabId, message) {
    try {
      const browserAPI = this.getBrowserAPI();
      return await browserAPI.tabs.sendMessage(tabId, message);
    } catch (error) {
      console.error('Error sending tab message:', error);
      return { error: error.message };
    }
  },

  // Tab utilities
  async getCurrentTab() {
    try {
      const browserAPI = this.getBrowserAPI();
      const [tab] = await browserAPI.tabs.query({ active: true, currentWindow: true });
      return tab;
    } catch (error) {
      console.error('Error getting current tab:', error);
      return null;
    }
  },

  async createTab(url) {
    try {
      const browserAPI = this.getBrowserAPI();
      return await browserAPI.tabs.create({ url });
    } catch (error) {
      console.error('Error creating tab:', error);
      return null;
    }
  },

  // Notification utilities
  showNotification(id, title, message, type = 'basic') {
    try {
      const browserAPI = this.getBrowserAPI();
      
      if (browserAPI.notifications) {
        browserAPI.notifications.create(id, {
          type: type,
          iconUrl: this.getExtensionIcon(48),
          title: title,
          message: message
        });
      }
    } catch (error) {
      console.error('Error showing notification:', error);
    }
  },

  // Extension utilities
  getExtensionIcon(size = 48) {
    const browserAPI = this.getBrowserAPI();
    return browserAPI.runtime.getURL(`../icons/icon-${size}.png`);
  },

  getExtensionURL(path) {
    const browserAPI = this.getBrowserAPI();
    return browserAPI.runtime.getURL(path);
  },

  // URL utilities
  isValidURL(string) {
    try {
      new URL(string);
      return true;
    } catch (_) {
      return false;
    }
  },

  getDomainFromURL(url) {
    try {
      return new URL(url).hostname.toLowerCase();
    } catch (_) {
      return '';
    }
  },

  // Platform detection
  detectPlatform(url) {
    const hostname = this.getDomainFromURL(url);
    
    const platforms = {
      'reddit.com': 'reddit',
      'twitter.com': 'twitter',
      'x.com': 'twitter',
      'instagram.com': 'instagram',
      'facebook.com': 'facebook',
      'tiktok.com': 'tiktok',
      'onlyfans.com': 'onlyfans',
      'fansly.com': 'fansly',
      'manyvids.com': 'manyvids',
      'justforfans.com': 'justforfans',
      'chaturbate.com': 'chaturbate',
      'pornhub.com': 'pornhub',
      't.me': 'telegram',
      'web.telegram.org': 'telegram',
      'discord.com': 'discord',
      'discordapp.com': 'discord'
    };
    
    for (const [domain, platform] of Object.entries(platforms)) {
      if (hostname.includes(domain)) {
        return platform;
      }
    }
    
    return 'unknown';
  },

  // Content type detection
  detectContentType(url, title = '', content = '') {
    const platform = this.detectPlatform(url);
    
    // Platform-specific content types
    if (['onlyfans', 'fansly', 'manyvids', 'justforfans'].includes(platform)) {
      return 'adult_platform';
    }
    
    if (['reddit', 'twitter', 'instagram', 'facebook', 'tiktok'].includes(platform)) {
      return 'social_media';
    }
    
    // Content-based detection
    const combinedText = `${url} ${title} ${content}`.toLowerCase();
    
    if (/\b(nsfw|adult|xxx|porn|nude|naked|sex|explicit)\b/.test(combinedText)) {
      return 'adult_content';
    }
    
    if (/\b(leak|leaked|onlyfans|of|premium|exclusive|pirated)\b/.test(combinedText)) {
      return 'potential_leak';
    }
    
    if (/\b(image|photo|picture|gallery|album)\b/.test(combinedText)) {
      return 'image_content';
    }
    
    if (/\b(video|stream|movie|clip)\b/.test(combinedText)) {
      return 'video_content';
    }
    
    return 'general';
  },

  // Validation utilities
  validateReportData(data) {
    const errors = [];
    
    if (!data.url || !this.isValidURL(data.url)) {
      errors.push('Invalid URL provided');
    }
    
    if (!data.profile_id || typeof data.profile_id !== 'number') {
      errors.push('Valid profile ID is required');
    }
    
    if (data.original_url && !this.isValidURL(data.original_url)) {
      errors.push('Invalid original URL provided');
    }
    
    return {
      isValid: errors.length === 0,
      errors: errors
    };
  },

  // Rate limiting utilities
  rateLimiters: new Map(),

  async checkRateLimit(key, maxRequests = 10, windowMs = 60000) {
    const now = Date.now();
    const windowStart = now - windowMs;
    
    if (!this.rateLimiters.has(key)) {
      this.rateLimiters.set(key, []);
    }
    
    const requests = this.rateLimiters.get(key);
    
    // Remove old requests outside the window
    const validRequests = requests.filter(time => time > windowStart);
    this.rateLimiters.set(key, validRequests);
    
    // Check if we're under the limit
    if (validRequests.length < maxRequests) {
      validRequests.push(now);
      return { allowed: true, remaining: maxRequests - validRequests.length };
    }
    
    return { 
      allowed: false, 
      remaining: 0,
      resetTime: Math.min(...validRequests) + windowMs
    };
  },

  // Error handling utilities
  handleError(error, context = 'Unknown') {
    const errorInfo = {
      message: error.message || 'Unknown error',
      context: context,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location?.href || 'Extension context'
    };
    
    console.error(`[ContentProtection] ${context}:`, error);
    
    // Store error for debugging (with size limit)
    this.logError(errorInfo);
    
    return errorInfo;
  },

  async logError(errorInfo) {
    try {
      const errors = await this.getStorageItem('errorLog') || [];
      errors.push(errorInfo);
      
      // Keep only last 50 errors
      if (errors.length > 50) {
        errors.splice(0, errors.length - 50);
      }
      
      await this.setStorageItem('errorLog', errors);
    } catch (e) {
      console.error('Failed to log error:', e);
    }
  },

  // Performance utilities
  performanceMarkers: new Map(),

  startTimer(label) {
    this.performanceMarkers.set(label, performance.now());
  },

  endTimer(label) {
    const startTime = this.performanceMarkers.get(label);
    if (startTime) {
      const duration = performance.now() - startTime;
      this.performanceMarkers.delete(label);
      return duration;
    }
    return null;
  },

  // Formatting utilities
  formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
  },

  formatTimeAgo(timestamp) {
    const now = Date.now();
    const diff = now - timestamp;
    
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    
    if (days > 0) return `${days} day${days > 1 ? 's' : ''} ago`;
    if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    if (minutes > 0) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    return `${seconds} second${seconds > 1 ? 's' : ''} ago`;
  },

  truncateText(text, maxLength = 50) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength - 3) + '...';
  },

  // Security utilities
  sanitizeInput(input) {
    if (typeof input !== 'string') return input;
    
    return input
      .replace(/[<>]/g, '') // Remove potential HTML tags
      .replace(/javascript:/gi, '') // Remove javascript: protocol
      .replace(/data:/gi, '') // Remove data: protocol
      .trim();
  },

  // Analytics utilities
  async trackEvent(eventName, properties = {}) {
    try {
      const eventData = {
        event: eventName,
        properties: {
          ...properties,
          timestamp: Date.now(),
          extension_version: '1.0.0',
          user_agent: navigator.userAgent
        }
      };
      
      // Store locally for now (could be sent to analytics service)
      const events = await this.getStorageItem('analyticsEvents') || [];
      events.push(eventData);
      
      // Keep only last 1000 events
      if (events.length > 1000) {
        events.splice(0, events.length - 1000);
      }
      
      await this.setStorageItem('analyticsEvents', events);
    } catch (error) {
      console.warn('Failed to track event:', error);
    }
  },

  // Debug utilities
  isDebugMode() {
    return process.env.NODE_ENV === 'development' || 
           window.location.search.includes('debug=true');
  },

  debugLog(message, ...args) {
    if (this.isDebugMode()) {
      console.log(`[ContentProtection Debug] ${message}`, ...args);
    }
  },

  // Migration utilities
  async migrateStorageIfNeeded() {
    try {
      const version = await this.getStorageItem('extensionVersion');
      const currentVersion = '1.0.0';
      
      if (!version) {
        // First install
        await this.setStorageItem('extensionVersion', currentVersion);
        await this.setStorageItem('installDate', Date.now());
        this.debugLog('Extension installed for first time');
      } else if (version !== currentVersion) {
        // Version upgrade
        await this.setStorageItem('extensionVersion', currentVersion);
        await this.setStorageItem('lastUpgradeDate', Date.now());
        this.debugLog(`Extension upgraded from ${version} to ${currentVersion}`);
      }
    } catch (error) {
      console.error('Migration failed:', error);
    }
  }
};

// Initialize utilities
if (typeof window !== 'undefined') {
  window.ContentProtectionUtils.migrateStorageIfNeeded();
}

// Export for Node.js environments (testing)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = window.ContentProtectionUtils;
}