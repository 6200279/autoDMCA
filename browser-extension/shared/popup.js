/**
 * Browser Extension Popup Script
 * Handles user interactions and API communication
 * Compatible with both Chrome and Firefox
 */

// Cross-browser compatibility
const browserAPI = (typeof browser !== 'undefined') ? browser : chrome;

class ContentProtectionExtension {
  constructor() {
    this.apiBaseUrl = 'http://localhost:8000/api/v1';
    this.currentUrl = '';
    this.currentTab = null;
    this.authToken = '';
    this.userProfiles = [];
    this.pageStats = {
      imageCount: 0,
      videoCount: 0,
      linkCount: 0,
      contentType: 'unknown',
      platform: 'unknown'
    };
    
    this.init();
  }
  
  async init() {
    await this.loadAuthToken();
    await this.loadCurrentUrl();
    await this.loadPageStats();
    await this.loadUserProfiles();
    this.setupEventListeners();
    this.updateUI();
  }
  
  async loadAuthToken() {
    try {
      const result = await browserAPI.storage.local.get(['authToken']);
      this.authToken = result.authToken || '';
    } catch (error) {
      console.error('Error loading auth token:', error);
    }
  }
  
  async loadCurrentUrl() {
    try {
      const [tab] = await browserAPI.tabs.query({ active: true, currentWindow: true });
      this.currentTab = tab;
      this.currentUrl = tab.url;
      document.getElementById('current-url').textContent = this.currentUrl;
      
      // Update platform badge
      const platform = this.detectPlatformFromUrl(this.currentUrl);
      document.getElementById('platform-badge').textContent = platform.toUpperCase();
    } catch (error) {
      console.error('Error loading current URL:', error);
      document.getElementById('current-url').textContent = 'Unable to detect URL';
    }
  }
  
  async loadPageStats() {
    try {
      if (!this.currentTab) return;
      
      // Try to get page info from content script
      const response = await browserAPI.tabs.sendMessage(this.currentTab.id, {
        action: 'get-page-info'
      });
      
      if (response) {
        this.pageStats = {
          imageCount: response.imageCount || 0,
          videoCount: response.videoCount || 0,
          linkCount: response.linkCount || 0,
          contentType: response.contentType || 'unknown',
          platform: response.platform || 'unknown'
        };
        
        this.updatePageStats();
      }
    } catch (error) {
      console.log('Could not load page stats:', error);
      // Fallback to basic detection
      this.pageStats.platform = this.detectPlatformFromUrl(this.currentUrl);
    }
  }
  
  updatePageStats() {
    document.getElementById('image-count').textContent = this.pageStats.imageCount;
    document.getElementById('video-count').textContent = this.pageStats.videoCount;
    document.getElementById('link-count').textContent = this.pageStats.linkCount;
    
    // Show stats if there's meaningful content
    if (this.pageStats.imageCount > 0 || this.pageStats.videoCount > 0) {
      document.getElementById('page-stats').classList.remove('hidden');
    }
  }
  
  detectPlatformFromUrl(url) {
    const hostname = url.toLowerCase();
    
    if (hostname.includes('reddit.com')) return 'reddit';
    if (hostname.includes('twitter.com') || hostname.includes('x.com')) return 'twitter';
    if (hostname.includes('instagram.com')) return 'instagram';
    if (hostname.includes('facebook.com')) return 'facebook';
    if (hostname.includes('tiktok.com')) return 'tiktok';
    if (hostname.includes('telegram')) return 'telegram';
    if (hostname.includes('discord')) return 'discord';
    if (hostname.includes('onlyfans.com')) return 'onlyfans';
    if (hostname.includes('fansly.com')) return 'fansly';
    if (hostname.includes('manyvids.com')) return 'manyvids';
    if (hostname.includes('pornhub.com')) return 'pornhub';
    
    return 'web';
  }
  
  async loadUserProfiles() {
    if (!this.authToken) {
      return;
    }
    
    try {
      const response = await fetch(`${this.apiBaseUrl}/profiles`, {
        headers: {
          'Authorization': `Bearer ${this.authToken}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        this.userProfiles = data.profiles || [];
        this.populateProfileSelect();
      }
    } catch (error) {
      console.error('Error loading profiles:', error);
    }
  }
  
  populateProfileSelect() {
    const select = document.getElementById('profile-select');
    select.innerHTML = '<option value="">Select profile...</option>';
    
    this.userProfiles.forEach(profile => {
      const option = document.createElement('option');
      option.value = profile.id;
      option.textContent = `${profile.username} (${profile.platform})`;
      select.appendChild(option);
    });
  }
  
  setupEventListeners() {
    // Report infringement
    document.getElementById('report-infringement').addEventListener('click', () => {
      this.showReportForm();
    });
    
    // Scan page
    document.getElementById('scan-page').addEventListener('click', () => {
      this.scanCurrentPage();
    });
    
    // Collect images
    document.getElementById('collect-images').addEventListener('click', () => {
      this.collectImages();
    });
    
    // View dashboard
    document.getElementById('view-dashboard').addEventListener('click', () => {
      this.openDashboard();
    });
    
    // Submit report
    document.getElementById('submit-report').addEventListener('click', () => {
      this.submitReport();
    });
    
    // Cancel report
    document.getElementById('cancel-report').addEventListener('click', () => {
      this.hideReportForm();
    });
    
    // Login button
    document.getElementById('login-button').addEventListener('click', () => {
      this.openDashboard();
    });
    
    // Footer links
    document.getElementById('help-link').addEventListener('click', (e) => {
      e.preventDefault();
      browserAPI.tabs.create({ url: 'http://localhost:3000/help' });
    });
    
    document.getElementById('settings-link').addEventListener('click', (e) => {
      e.preventDefault();
      browserAPI.tabs.create({ url: 'http://localhost:3000/settings' });
    });
    
    document.getElementById('feedback-link').addEventListener('click', (e) => {
      e.preventDefault();
      browserAPI.tabs.create({ url: 'http://localhost:3000/feedback' });
    });
  }
  
  updateUI() {
    const mainActions = document.getElementById('main-actions');
    const authPrompt = document.getElementById('auth-prompt');
    const statusMessage = document.getElementById('status-message');
    
    if (!this.authToken) {
      authPrompt.classList.remove('hidden');
      mainActions.classList.add('hidden');
      
      statusMessage.textContent = 'Authentication required to access Content Protection features';
      statusMessage.className = 'status info';
      statusMessage.classList.remove('hidden');
    } else {
      authPrompt.classList.add('hidden');
      mainActions.classList.remove('hidden');
      statusMessage.classList.add('hidden');
      
      // Update button states based on page content
      this.updateButtonStates();
    }
  }
  
  updateButtonStates() {
    const scanBtn = document.getElementById('scan-page');
    const collectBtn = document.getElementById('collect-images');
    
    // Enable/disable buttons based on page content
    if (this.pageStats.imageCount === 0) {
      collectBtn.disabled = true;
      collectBtn.style.opacity = '0.5';
    }
    
    // Special handling for known platforms
    if (this.pageStats.platform === 'onlyfans') {
      scanBtn.querySelector('.desc').textContent = 'Scan OnlyFans page for leaks';
    } else if (['reddit', 'twitter', 'instagram'].includes(this.pageStats.platform)) {
      scanBtn.querySelector('.desc').textContent = 'Scan social media for your content';
    }
  }
  
  showReportForm() {
    if (!this.authToken) {
      this.showStatus('Please log in first', 'error');
      return;
    }
    
    document.getElementById('main-actions').classList.add('hidden');
    document.getElementById('report-form').classList.remove('hidden');
    
    // Pre-fill the infringing URL with current page
    document.getElementById('infringement-url').value = this.currentUrl;
  }
  
  hideReportForm() {
    document.getElementById('main-actions').classList.remove('hidden');
    document.getElementById('report-form').classList.add('hidden');
  }
  
  async scanCurrentPage() {
    if (!this.authToken) {
      this.showStatus('Please log in first', 'error');
      return;
    }
    
    if (this.userProfiles.length === 0) {
      this.showStatus('No profiles found. Please create a profile first.', 'error');
      setTimeout(() => {
        this.openDashboard();
      }, 2000);
      return;
    }
    
    this.showStatus('Scanning page for matches...', 'loading');
    
    // Update button to show scanning state
    const scanBtn = document.getElementById('scan-page');
    const originalText = scanBtn.querySelector('.text').innerHTML;
    scanBtn.querySelector('.text').innerHTML = '<div class="desc">Analyzing content...</div>';
    scanBtn.disabled = true;
    
    try {
      // Use the first profile for scanning
      const profileId = this.userProfiles[0].id;
      
      const response = await fetch(`${this.apiBaseUrl}/scanning/scan/url`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          url: this.currentUrl,
          profile_id: profileId,
          context: 'popup_scan',
          page_title: this.currentTab?.title,
          platform: this.pageStats.platform
        })
      });
      
      if (response.ok) {
        const result = await response.json();
        
        if (result.matches_found && result.matches_found > 0) {
          this.showStatus(`Found ${result.matches_found} potential matches! Click to view details.`, 'error');
          setTimeout(() => {
            this.openDashboard();
          }, 3000);
        } else {
          this.showStatus('No matches found on this page', 'success');
        }
      } else {
        this.showStatus('Scan failed. Please try again.', 'error');
      }
    } catch (error) {
      console.error('Scan error:', error);
      this.showStatus('Scan error. Check your connection.', 'error');
    } finally {
      // Restore button state
      scanBtn.querySelector('.text').innerHTML = originalText;
      scanBtn.disabled = false;
    }
  }
  
  async collectImages() {
    if (!this.authToken) {
      this.showStatus('Please log in first', 'error');
      return;
    }
    
    this.showStatus('Collecting images from page...', 'loading');
    
    try {
      // Send message to content script to collect images
      const response = await browserAPI.tabs.sendMessage(this.currentTab.id, {
        action: 'collect-images'
      });
      
      if (response && response.length > 0) {
        // Store images for later use
        await browserAPI.storage.local.set({ 
          collectedImages: response,
          collectedFrom: this.currentUrl,
          collectedAt: Date.now()
        });
        
        this.showStatus(`Collected ${response.length} images`, 'success');
      } else {
        this.showStatus('No images found on this page', 'error');
      }
    } catch (error) {
      console.error('Image collection error:', error);
      this.showStatus('Failed to collect images', 'error');
    }
  }
  
  openDashboard() {
    browserAPI.tabs.create({
      url: 'http://localhost:3000/dashboard'
    });
    window.close();
  }
  
  async submitReport() {
    if (!this.authToken) {
      this.showStatus('Please log in first', 'error');
      return;
    }
    
    const profileId = document.getElementById('profile-select').value;
    const infringementUrl = document.getElementById('infringement-url').value;
    const originalUrl = document.getElementById('original-url').value;
    const description = document.getElementById('description').value;
    
    if (!profileId || !infringementUrl) {
      this.showStatus('Please fill in required fields', 'error');
      return;
    }
    
    this.showStatus('Submitting report...', 'loading');
    
    // Update submit button
    const submitBtn = document.getElementById('submit-report');
    submitBtn.disabled = true;
    submitBtn.querySelector('.text').textContent = 'Submitting...';
    
    try {
      const response = await fetch(`${this.apiBaseUrl}/scanning/scan/url`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          url: infringementUrl,
          profile_id: parseInt(profileId),
          original_url: originalUrl,
          description: description,
          priority: true,
          context: 'manual_report_popup',
          reported_from: this.currentUrl
        })
      });
      
      if (response.ok) {
        this.showStatus('Report submitted successfully!', 'success');
        
        // Clear form
        document.getElementById('infringement-url').value = '';
        document.getElementById('original-url').value = '';
        document.getElementById('description').value = '';
        
        // Hide form after delay
        setTimeout(() => {
          this.hideReportForm();
        }, 2000);
      } else {
        const errorData = await response.json().catch(() => ({}));
        this.showStatus(errorData.detail || 'Failed to submit report', 'error');
      }
    } catch (error) {
      console.error('Report submission error:', error);
      this.showStatus('Network error. Please try again.', 'error');
    } finally {
      // Restore submit button
      submitBtn.disabled = false;
      submitBtn.querySelector('.text').textContent = 'Submit Report';
    }
  }
  
  showStatus(message, type) {
    const statusEl = document.getElementById('status-message');
    statusEl.innerHTML = type === 'loading' ? 
      `<span class="loading-spinner"></span>${message}` : 
      message;
    statusEl.className = `status ${type}`;
    statusEl.classList.remove('hidden');
    
    // Auto-hide success and info messages
    if (['success', 'info'].includes(type)) {
      setTimeout(() => {
        statusEl.classList.add('hidden');
      }, 4000);
    }
  }
}

// Initialize extension when popup opens
document.addEventListener('DOMContentLoaded', () => {
  new ContentProtectionExtension();
});

// Handle extension shortcut from content script
if (browserAPI.runtime.onMessage) {
  browserAPI.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'open-popup') {
      // Popup is already open, just focus
      window.focus();
    }
  });
}