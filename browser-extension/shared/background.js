/**
 * Background Script for Content Protection Extension
 * Handles context menus, notifications, and background tasks
 * Compatible with Chrome Manifest V3
 */

class BackgroundService {
  constructor() {
    this.apiBaseUrl = 'http://localhost:8000/api/v1';
    this.init();
  }
  
  init() {
    this.setupContextMenus();
    this.setupEventListeners();
  }
  
  setupContextMenus() {
    // Create context menu items
    chrome.runtime.onInstalled.addListener(() => {
      // Report image context menu
      chrome.contextMenus.create({
        id: 'report-image',
        title: 'Report as Infringement',
        contexts: ['image']
      });
      
      // Report link context menu
      chrome.contextMenus.create({
        id: 'report-link',
        title: 'Report Link as Infringement',
        contexts: ['link']
      });
      
      // Report page context menu
      chrome.contextMenus.create({
        id: 'report-page',
        title: 'Report Page as Infringement',
        contexts: ['page']
      });
      
      // Scan page context menu
      chrome.contextMenus.create({
        id: 'scan-page',
        title: 'Scan for My Content',
        contexts: ['page']
      });
      
      // Separator
      chrome.contextMenus.create({
        id: 'separator',
        type: 'separator',
        contexts: ['image', 'link', 'page']
      });
      
      // Quick scan context menu
      chrome.contextMenus.create({
        id: 'quick-scan',
        title: 'Quick Content Scan',
        contexts: ['page']
      });
    });
    
    // Handle context menu clicks
    chrome.contextMenus.onClicked.addListener((info, tab) => {
      this.handleContextMenuClick(info, tab);
    });
  }
  
  setupEventListeners() {
    // Handle messages from content scripts and popup
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
      this.handleMessage(request, sender, sendResponse);
      return true; // Keep message channel open for async responses
    });
    
    // Handle extension icon click
    chrome.action.onClicked.addListener((tab) => {
      // Open popup (default behavior)
    });
    
    // Handle browser notifications
    if (chrome.notifications) {
      chrome.notifications.onClicked.addListener((notificationId) => {
        this.handleNotificationClick(notificationId);
      });
    }
  }
  
  async handleContextMenuClick(info, tab) {
    const authToken = await this.getAuthToken();
    
    if (!authToken) {
      this.showNotification(
        'authentication-required',
        'Authentication Required',
        'Please log in to use Content Protection features',
        'basic'
      );
      return;
    }
    
    switch (info.menuItemId) {
      case 'report-image':
        await this.reportImage(info, tab);
        break;
        
      case 'report-link':
        await this.reportLink(info, tab);
        break;
        
      case 'report-page':
        await this.reportPage(info, tab);
        break;
        
      case 'scan-page':
        await this.scanPage(tab);
        break;
        
      case 'quick-scan':
        await this.quickScan(tab);
        break;
    }
  }
  
  async handleMessage(request, sender, sendResponse) {
    try {
      switch (request.action) {
        case 'get-auth-token':
          const token = await this.getAuthToken();
          sendResponse({ authToken: token });
          break;
          
        case 'set-auth-token':
          await this.setAuthToken(request.token);
          sendResponse({ success: true });
          break;
          
        case 'scan-content':
          const result = await this.scanContent(request.data);
          sendResponse(result);
          break;
          
        case 'submit-report':
          const reportResult = await this.submitReport(request.data);
          sendResponse(reportResult);
          break;
          
        case 'report-image':
          const imageResult = await this.reportImageFromContent(request.data);
          sendResponse(imageResult);
          break;
          
        case 'report-page':
          const pageResult = await this.reportPageFromContent(request.data);
          sendResponse(pageResult);
          break;
          
        case 'quick-scan':
          const scanResult = await this.quickScanFromContent(request.data);
          sendResponse(scanResult);
          break;
          
        case 'collect-images':
          const collectResult = await this.collectImagesFromContent(request.data);
          sendResponse(collectResult);
          break;
          
        default:
          sendResponse({ error: 'Unknown action' });
      }
    } catch (error) {
      console.error('Message handling error:', error);
      sendResponse({ error: error.message });
    }
  }
  
  async reportImage(info, tab) {
    const imageUrl = info.srcUrl;
    
    this.showNotification(
      'report-submitted',
      'Image Report Submitted',
      `Reporting image: ${this.truncateUrl(imageUrl)}`,
      'basic'
    );
    
    try {
      const profiles = await this.getUserProfiles();
      
      if (profiles.length === 0) {
        this.showNotification(
          'no-profiles',
          'No Profiles Found',
          'Please create a profile before reporting content',
          'basic'
        );
        return;
      }
      
      // Use first profile for quick reporting
      const profileId = profiles[0].id;
      
      const response = await fetch(`${this.apiBaseUrl}/scanning/scan/url`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${await this.getAuthToken()}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          url: imageUrl,
          profile_id: profileId,
          priority: true,
          context: 'context_menu_report',
          page_url: tab.url,
          content_type: 'image'
        })
      });
      
      if (response.ok) {
        this.showNotification(
          'report-success',
          'Report Submitted',
          'Image has been submitted for analysis',
          'basic'
        );
      } else {
        throw new Error(`API request failed with status ${response.status}`);
      }
    } catch (error) {
      console.error('Report image error:', error);
      this.showNotification(
        'report-error',
        'Report Failed',
        'Failed to submit image report. Please try again.',
        'basic'
      );
    }
  }
  
  async reportLink(info, tab) {
    const linkUrl = info.linkUrl;
    
    try {
      const profiles = await this.getUserProfiles();
      
      if (profiles.length === 0) {
        this.showNotification(
          'no-profiles',
          'No Profiles Found',
          'Please create a profile before reporting content',
          'basic'
        );
        return;
      }
      
      const profileId = profiles[0].id;
      
      const response = await fetch(`${this.apiBaseUrl}/scanning/scan/url`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${await this.getAuthToken()}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          url: linkUrl,
          profile_id: profileId,
          priority: true,
          context: 'context_menu_report',
          page_url: tab.url,
          content_type: 'link'
        })
      });
      
      if (response.ok) {
        this.showNotification(
          'report-success',
          'Link Report Submitted',
          `Link has been submitted for analysis`,
          'basic'
        );
      } else {
        throw new Error(`API request failed with status ${response.status}`);
      }
    } catch (error) {
      console.error('Report link error:', error);
      this.showNotification(
        'report-error',
        'Report Failed',
        'Failed to submit link report. Please try again.',
        'basic'
      );
    }
  }
  
  async reportPage(info, tab) {
    const pageUrl = tab.url;
    
    try {
      const profiles = await this.getUserProfiles();
      
      if (profiles.length === 0) {
        this.showNotification(
          'no-profiles',
          'No Profiles Found',
          'Please create a profile before reporting content',
          'basic'
        );
        return;
      }
      
      const profileId = profiles[0].id;
      
      const response = await fetch(`${this.apiBaseUrl}/scanning/scan/url`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${await this.getAuthToken()}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          url: pageUrl,
          profile_id: profileId,
          priority: true,
          context: 'context_menu_report',
          content_type: 'page',
          page_title: tab.title
        })
      });
      
      if (response.ok) {
        this.showNotification(
          'report-success',
          'Page Report Submitted',
          `Page has been submitted for analysis`,
          'basic'
        );
      } else {
        throw new Error(`API request failed with status ${response.status}`);
      }
    } catch (error) {
      console.error('Report page error:', error);
      this.showNotification(
        'report-error',
        'Report Failed',
        'Failed to submit page report. Please try again.',
        'basic'
      );
    }
  }
  
  async scanPage(tab) {
    this.showNotification(
      'scan-started',
      'Scan Started',
      'Scanning page for your content...',
      'basic'
    );
    
    try {
      const profiles = await this.getUserProfiles();
      
      if (profiles.length === 0) {
        this.showNotification(
          'no-profiles',
          'No Profiles Found',
          'Please create a profile before scanning content',
          'basic'
        );
        return;
      }
      
      const profileId = profiles[0].id;
      
      const response = await fetch(`${this.apiBaseUrl}/scanning/scan/url`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${await this.getAuthToken()}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          url: tab.url,
          profile_id: profileId,
          context: 'context_menu_scan',
          page_title: tab.title
        })
      });
      
      if (response.ok) {
        const result = await response.json();
        
        if (result.matches_found && result.matches_found > 0) {
          this.showNotification(
            'matches-found',
            'Matches Found!',
            `Found ${result.matches_found} potential matches on this page`,
            'basic'
          );
        } else {
          this.showNotification(
            'no-matches',
            'Scan Complete',
            'No matches found on this page',
            'basic'
          );
        }
      } else {
        throw new Error(`API request failed with status ${response.status}`);
      }
    } catch (error) {
      console.error('Scan page error:', error);
      this.showNotification(
        'scan-error',
        'Scan Failed',
        'Failed to scan page. Please try again.',
        'basic'
      );
    }
  }
  
  async quickScan(tab) {
    this.showNotification(
      'quick-scan-started',
      'Quick Scan Started',
      'Performing quick content scan...',
      'basic'
    );
    
    try {
      // Send message to content script to collect basic page info
      const response = await chrome.tabs.sendMessage(tab.id, {
        action: 'get-page-info'
      });
      
      if (response && response.imageCount > 0) {
        this.showNotification(
          'quick-scan-complete',
          'Quick Scan Complete',
          `Found ${response.imageCount} images to analyze`,
          'basic'
        );
      } else {
        this.showNotification(
          'quick-scan-complete',
          'Quick Scan Complete',
          'No significant content detected',
          'basic'
        );
      }
    } catch (error) {
      console.error('Quick scan error:', error);
      this.showNotification(
        'quick-scan-error',
        'Quick Scan Failed',
        'Failed to perform quick scan',
        'basic'
      );
    }
  }
  
  async reportImageFromContent(data) {
    try {
      const profiles = await this.getUserProfiles();
      
      if (profiles.length === 0) {
        return { error: 'No profiles found' };
      }
      
      const profileId = profiles[0].id;
      
      const response = await fetch(`${this.apiBaseUrl}/scanning/scan/url`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${await this.getAuthToken()}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          url: data.url,
          profile_id: profileId,
          priority: true,
          context: 'content_script_report',
          page_url: data.pageUrl,
          content_type: 'image',
          metadata: data.context
        })
      });
      
      if (response.ok) {
        return { success: true };
      } else {
        throw new Error(`API request failed with status ${response.status}`);
      }
    } catch (error) {
      console.error('Report image from content error:', error);
      return { error: error.message };
    }
  }
  
  async reportPageFromContent(data) {
    try {
      const profiles = await this.getUserProfiles();
      
      if (profiles.length === 0) {
        return { error: 'No profiles found' };
      }
      
      const profileId = profiles[0].id;
      
      const response = await fetch(`${this.apiBaseUrl}/scanning/scan/url`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${await this.getAuthToken()}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          url: data.url,
          profile_id: profileId,
          priority: true,
          context: 'content_script_report',
          content_type: 'page',
          metadata: data.pageInfo
        })
      });
      
      if (response.ok) {
        return { success: true };
      } else {
        throw new Error(`API request failed with status ${response.status}`);
      }
    } catch (error) {
      console.error('Report page from content error:', error);
      return { error: error.message };
    }
  }
  
  async quickScanFromContent(data) {
    try {
      return {
        success: true,
        matches: Math.floor(Math.random() * 3) // Simulated for quick response
      };
    } catch (error) {
      console.error('Quick scan from content error:', error);
      return { error: error.message };
    }
  }
  
  async collectImagesFromContent(data) {
    try {
      // Store collected images for later processing
      await chrome.storage.local.set({
        collectedImages: data.images,
        collectedTimestamp: Date.now(),
        collectedFrom: data.pageInfo.url
      });
      
      return { success: true, count: data.images.length };
    } catch (error) {
      console.error('Collect images from content error:', error);
      return { error: error.message };
    }
  }
  
  async getAuthToken() {
    try {
      const result = await chrome.storage.local.get(['authToken']);
      return result.authToken || '';
    } catch (error) {
      console.error('Error getting auth token:', error);
      return '';
    }
  }
  
  async setAuthToken(token) {
    try {
      await chrome.storage.local.set({ authToken: token });
    } catch (error) {
      console.error('Error setting auth token:', error);
    }
  }
  
  async getUserProfiles() {
    try {
      const authToken = await this.getAuthToken();
      
      if (!authToken) {
        return [];
      }
      
      const response = await fetch(`${this.apiBaseUrl}/profiles`, {
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        return data.profiles || [];
      } else {
        return [];
      }
    } catch (error) {
      console.error('Error getting user profiles:', error);
      return [];
    }
  }
  
  showNotification(id, title, message, type) {
    if (chrome.notifications) {
      chrome.notifications.create(id, {
        type: type,
        iconUrl: chrome.runtime.getURL('../icons/icon-48.png'),
        title: title,
        message: message
      });
    }
  }
  
  handleNotificationClick(notificationId) {
    switch (notificationId) {
      case 'matches-found':
      case 'report-success':
      case 'scan-complete':
        // Open dashboard
        chrome.tabs.create({
          url: 'http://localhost:3000/dashboard'
        });
        break;
        
      case 'authentication-required':
      case 'no-profiles':
        // Open login/settings page
        chrome.tabs.create({
          url: 'http://localhost:3000/login'
        });
        break;
    }
    
    // Clear the notification
    if (chrome.notifications) {
      chrome.notifications.clear(notificationId);
    }
  }
  
  truncateUrl(url) {
    if (url.length > 50) {
      return url.substring(0, 47) + '...';
    }
    return url;
  }
}

// Initialize background service
new BackgroundService();