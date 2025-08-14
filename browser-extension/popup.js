/**
 * Browser Extension Popup Script
 * Handles user interactions and API communication
 */

class ContentProtectionExtension {
  constructor() {
    this.apiBaseUrl = 'http://localhost:8000/api/v1';
    this.currentUrl = '';
    this.authToken = '';
    this.userProfiles = [];
    
    this.init();
  }
  
  async init() {
    await this.loadAuthToken();
    await this.loadCurrentUrl();
    await this.loadUserProfiles();
    this.setupEventListeners();
    this.updateUI();
  }
  
  async loadAuthToken() {
    try {
      const result = await chrome.storage.local.get(['authToken']);
      this.authToken = result.authToken || '';
    } catch (error) {
      console.error('Error loading auth token:', error);
    }
  }
  
  async loadCurrentUrl() {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      this.currentUrl = tab.url;
      document.getElementById('current-url').textContent = this.currentUrl;
    } catch (error) {
      console.error('Error loading current URL:', error);
      document.getElementById('current-url').textContent = 'Unable to detect URL';
    }
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
  }
  
  updateUI() {
    const mainActions = document.getElementById('main-actions');
    const statusMessage = document.getElementById('status-message');
    
    if (!this.authToken) {
      statusMessage.textContent = 'Please log in to use Content Protection features';
      statusMessage.className = 'status error';
      statusMessage.classList.remove('hidden');
      
      // Disable buttons that require authentication
      document.getElementById('report-infringement').disabled = true;
      document.getElementById('scan-page').disabled = true;
    } else {
      statusMessage.classList.add('hidden');
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
      return;
    }
    
    this.showStatus('Scanning page for matches...', 'loading');
    
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
          profile_id: profileId
        })
      });
      
      if (response.ok) {
        const result = await response.json();
        
        if (result.matches_found > 0) {
          this.showStatus(`Found ${result.matches_found} potential matches`, 'error');
        } else {
          this.showStatus('No matches found on this page', 'success');
        }
      } else {
        this.showStatus('Scan failed. Please try again.', 'error');
      }
    } catch (error) {
      console.error('Scan error:', error);
      this.showStatus('Scan error. Check your connection.', 'error');
    }
  }
  
  async collectImages() {
    this.showStatus('Collecting images from page...', 'loading');
    
    try {
      // Inject content script to collect images
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      
      const results = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        function: this.extractImages
      });
      
      const images = results[0].result;
      
      if (images.length > 0) {
        // Store images for later use
        await chrome.storage.local.set({ collectedImages: images });
        this.showStatus(`Collected ${images.length} images`, 'success');
      } else {
        this.showStatus('No images found on this page', 'error');
      }
    } catch (error) {
      console.error('Image collection error:', error);
      this.showStatus('Failed to collect images', 'error');
    }
  }
  
  extractImages() {
    // This function runs in the page context
    const images = [];
    const imgElements = document.querySelectorAll('img');
    
    imgElements.forEach((img, index) => {
      if (img.src && img.src.startsWith('http')) {
        images.push({
          url: img.src,
          alt: img.alt || '',
          width: img.naturalWidth || img.width,
          height: img.naturalHeight || img.height,
          index: index
        });
      }
    });
    
    return images;
  }
  
  openDashboard() {
    chrome.tabs.create({
      url: 'http://localhost:3000/dashboard'
    });
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
          priority: true
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
        this.showStatus('Failed to submit report', 'error');
      }
    } catch (error) {
      console.error('Report submission error:', error);
      this.showStatus('Network error. Please try again.', 'error');
    }
  }
  
  showStatus(message, type) {
    const statusEl = document.getElementById('status-message');
    statusEl.textContent = message;
    statusEl.className = `status ${type}`;
    statusEl.classList.remove('hidden');
    
    // Auto-hide success messages
    if (type === 'success') {
      setTimeout(() => {
        statusEl.classList.add('hidden');
      }, 3000);
    }
  }
}

// Initialize extension when popup opens
document.addEventListener('DOMContentLoaded', () => {
  new ContentProtectionExtension();
});