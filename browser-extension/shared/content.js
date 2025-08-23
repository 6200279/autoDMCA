/**
 * Content Script for Content Protection Extension
 * Handles page-level interactions and content detection
 * Compatible with both Chrome and Firefox
 */

// Cross-browser compatibility
const browserAPI = (typeof browser !== 'undefined') ? browser : chrome;

class ContentProtectionContent {
  constructor() {
    this.highlightedElements = [];
    this.isScanning = false;
    this.selectedImages = [];
    this.init();
  }
  
  init() {
    this.setupEventListeners();
    this.detectImages();
    
    // Listen for messages from background script (cross-browser compatible)
    browserAPI.runtime.onMessage.addListener((request, sender, sendResponse) => {
      this.handleMessage(request, sender, sendResponse);
      return true; // Keep message channel open
    });
  }
  
  setupEventListeners() {
    // Right-click context menu enhancement
    document.addEventListener('contextmenu', (e) => {
      this.handleContextMenu(e);
    });
    
    // Image hover effects for better UX
    document.addEventListener('mouseover', (e) => {
      if (e.target.tagName === 'IMG') {
        this.highlightImage(e.target);
      }
    });
    
    document.addEventListener('mouseout', (e) => {
      if (e.target.tagName === 'IMG') {
        this.removeImageHighlight(e.target);
      }
    });
    
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      this.handleKeyboard(e);
    });
  }
  
  handleContextMenu(event) {
    // Store context information for background script
    const contextInfo = {
      element: event.target.tagName,
      src: event.target.src || '',
      href: event.target.href || '',
      alt: event.target.alt || '',
      url: window.location.href,
      timestamp: Date.now()
    };
    
    // Store in session storage for background script access
    try {
      sessionStorage.setItem('cp-context', JSON.stringify(contextInfo));
    } catch (error) {
      console.log('Could not store context info:', error);
    }
  }
  
  handleKeyboard(event) {
    // Ctrl+Shift+P - Quick scan
    if (event.ctrlKey && event.shiftKey && event.key === 'P') {
      event.preventDefault();
      this.triggerQuickScan();
    }
    
    // Ctrl+Shift+R - Report current page
    if (event.ctrlKey && event.shiftKey && event.key === 'R') {
      event.preventDefault();
      this.reportCurrentPage();
    }
    
    // Ctrl+Shift+I - Collect images
    if (event.ctrlKey && event.shiftKey && event.key === 'I') {
      event.preventDefault();
      this.collectAllImages();
    }
  }
  
  handleMessage(request, sender, sendResponse) {
    switch (request.action) {
      case 'scan-page':
        this.scanPage().then(sendResponse);
        break;
        
      case 'collect-images':
        this.collectImages().then(sendResponse);
        break;
        
      case 'highlight-content':
        this.highlightContent(request.data).then(sendResponse);
        break;
        
      case 'get-page-info':
        sendResponse(this.getPageInfo());
        break;
        
      case 'detect-content-type':
        sendResponse(this.detectContentType());
        break;
        
      default:
        sendResponse({ error: 'Unknown action' });
    }
  }
  
  async scanPage() {
    if (this.isScanning) {
      return { error: 'Scan already in progress' };
    }
    
    this.isScanning = true;
    this.showNotification('Scanning page for content...', 'info');
    
    try {
      // Add visual scanning indicators
      const images = document.querySelectorAll('img');
      images.forEach(img => img.classList.add('cp-scanning'));
      
      const pageInfo = this.getPageInfo();
      const images_data = await this.collectImages();
      
      // Simulate scan delay for visual feedback
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Remove scanning indicators
      images.forEach(img => img.classList.remove('cp-scanning'));
      
      this.isScanning = false;
      
      return {
        success: true,
        pageInfo,
        images: images_data,
        timestamp: Date.now()
      };
      
    } catch (error) {
      this.isScanning = false;
      return { error: error.message };
    }
  }
  
  async collectImages() {
    const images = [];
    const imgElements = document.querySelectorAll('img');
    
    imgElements.forEach((img, index) => {
      if (img.src && img.src.startsWith('http') && img.naturalWidth > 100 && img.naturalHeight > 100) {
        // Create container for quick actions
        const container = this.createImageContainer(img);
        
        images.push({
          url: img.src,
          alt: img.alt || '',
          title: img.title || '',
          width: img.naturalWidth || img.width,
          height: img.naturalHeight || img.height,
          index: index,
          selector: this.getElementSelector(img),
          context: this.getImageContext(img)
        });
      }
    });
    
    this.showNotification(`Collected ${images.length} images`, 'success');
    return images;
  }
  
  createImageContainer(img) {
    if (img.parentElement.classList.contains('cp-image-container')) {
      return img.parentElement;
    }
    
    const container = document.createElement('div');
    container.className = 'cp-image-container';
    container.style.position = 'relative';
    container.style.display = 'inline-block';
    
    img.parentNode.insertBefore(container, img);
    container.appendChild(img);
    
    const quickAction = document.createElement('button');
    quickAction.className = 'cp-quick-action';
    quickAction.textContent = '🚨';
    quickAction.title = 'Report this image';
    quickAction.onclick = (e) => {
      e.preventDefault();
      e.stopPropagation();
      this.reportImage(img);
    };
    
    container.appendChild(quickAction);
    return container;
  }
  
  highlightImage(img) {
    if (!img.classList.contains('cp-scanning')) {
      img.classList.add('cp-highlight');
    }
  }
  
  removeImageHighlight(img) {
    img.classList.remove('cp-highlight');
  }
  
  highlightContent(data) {
    // Remove existing highlights
    this.clearHighlights();
    
    if (data.elements) {
      data.elements.forEach(selector => {
        const elements = document.querySelectorAll(selector);
        elements.forEach(el => {
          el.classList.add('cp-selected');
          this.highlightedElements.push(el);
        });
      });
    }
    
    return { highlighted: this.highlightedElements.length };
  }
  
  clearHighlights() {
    this.highlightedElements.forEach(el => {
      el.classList.remove('cp-selected', 'cp-highlight');
    });
    this.highlightedElements = [];
  }
  
  getPageInfo() {
    return {
      url: window.location.href,
      title: document.title,
      domain: window.location.hostname,
      imageCount: document.querySelectorAll('img').length,
      videoCount: document.querySelectorAll('video').length,
      linkCount: document.querySelectorAll('a').length,
      contentType: this.detectContentType(),
      timestamp: Date.now(),
      userAgent: navigator.userAgent,
      language: navigator.language,
      platform: this.detectPlatform()
    };
  }
  
  detectContentType() {
    const url = window.location.href.toLowerCase();
    const title = document.title.toLowerCase();
    const content = document.body.textContent.toLowerCase();
    
    // Detect common adult content platforms
    const platforms = {
      onlyfans: /onlyfans\.com|of\.com/,
      fansly: /fansly\.com/,
      justforfans: /justforfans\.com/,
      manyvids: /manyvids\.com/,
      chaturbate: /chaturbate\.com/,
      pornhub: /pornhub\.com/,
      reddit: /reddit\.com/,
      twitter: /twitter\.com|x\.com/,
      instagram: /instagram\.com/,
      telegram: /t\.me|telegram/,
      discord: /discord/
    };
    
    for (const [platform, pattern] of Object.entries(platforms)) {
      if (pattern.test(url) || pattern.test(title)) {
        return platform;
      }
    }
    
    // Detect content type by keywords
    if (/\b(nsfw|adult|xxx|porn|nude|naked|sex)\b/.test(content)) {
      return 'adult_content';
    }
    
    if (/\b(leak|leaked|onlyfans|of|premium|exclusive)\b/.test(content)) {
      return 'potential_leak';
    }
    
    return 'general';
  }
  
  detectPlatform() {
    const hostname = window.location.hostname.toLowerCase();
    
    if (hostname.includes('reddit.com')) return 'reddit';
    if (hostname.includes('twitter.com') || hostname.includes('x.com')) return 'twitter';
    if (hostname.includes('instagram.com')) return 'instagram';
    if (hostname.includes('facebook.com')) return 'facebook';
    if (hostname.includes('tiktok.com')) return 'tiktok';
    if (hostname.includes('telegram')) return 'telegram';
    if (hostname.includes('discord')) return 'discord';
    if (hostname.includes('onlyfans.com')) return 'onlyfans';
    
    return 'unknown';
  }
  
  getElementSelector(element) {
    if (element.id) {
      return `#${element.id}`;
    }
    
    if (element.className) {
      const classes = element.className.split(' ').filter(c => c && !c.startsWith('cp-'));
      if (classes.length > 0) {
        return `${element.tagName.toLowerCase()}.${classes.join('.')}`;
      }
    }
    
    // Generate path-based selector
    const path = [];
    let current = element;
    
    while (current && current.tagName) {
      let selector = current.tagName.toLowerCase();
      
      if (current.id) {
        selector += `#${current.id}`;
        path.unshift(selector);
        break;
      }
      
      const siblings = current.parentElement ? 
        Array.from(current.parentElement.children).filter(e => e.tagName === current.tagName) : 
        [];
      
      if (siblings.length > 1) {
        const index = siblings.indexOf(current) + 1;
        selector += `:nth-child(${index})`;
      }
      
      path.unshift(selector);
      current = current.parentElement;
      
      if (path.length > 5) break; // Limit depth
    }
    
    return path.join(' > ');
  }
  
  getImageContext(img) {
    const context = {
      alt: img.alt || '',
      title: img.title || '',
      parentText: '',
      surroundingLinks: []
    };
    
    // Get parent element text
    if (img.parentElement) {
      context.parentText = img.parentElement.textContent?.slice(0, 200) || '';
    }
    
    // Get surrounding links
    const links = img.parentElement?.querySelectorAll('a') || [];
    Array.from(links).forEach(link => {
      if (link.href && link.textContent) {
        context.surroundingLinks.push({
          href: link.href,
          text: link.textContent.slice(0, 50)
        });
      }
    });
    
    return context;
  }
  
  async reportImage(img) {
    this.showNotification('Reporting image...', 'info');
    
    try {
      // Send message to background script to handle the report
      const response = await browserAPI.runtime.sendMessage({
        action: 'report-image',
        data: {
          url: img.src,
          pageUrl: window.location.href,
          context: this.getImageContext(img),
          selector: this.getElementSelector(img)
        }
      });
      
      if (response.success) {
        img.classList.add('cp-selected');
        this.showNotification('Image reported successfully!', 'success');
      } else {
        this.showNotification('Failed to report image', 'error');
      }
    } catch (error) {
      console.error('Report image error:', error);
      this.showNotification('Error reporting image', 'error');
    }
  }
  
  async triggerQuickScan() {
    this.showNotification('Starting quick scan...', 'info');
    
    try {
      const response = await browserAPI.runtime.sendMessage({
        action: 'quick-scan',
        data: {
          url: window.location.href,
          pageInfo: this.getPageInfo()
        }
      });
      
      if (response.success) {
        this.showNotification(`Quick scan complete: ${response.matches || 0} matches`, 'success');
      } else {
        this.showNotification('Quick scan failed', 'error');
      }
    } catch (error) {
      console.error('Quick scan error:', error);
      this.showNotification('Quick scan error', 'error');
    }
  }
  
  async reportCurrentPage() {
    this.showNotification('Reporting current page...', 'info');
    
    try {
      const response = await browserAPI.runtime.sendMessage({
        action: 'report-page',
        data: {
          url: window.location.href,
          pageInfo: this.getPageInfo()
        }
      });
      
      if (response.success) {
        this.showNotification('Page reported successfully!', 'success');
      } else {
        this.showNotification('Failed to report page', 'error');
      }
    } catch (error) {
      console.error('Report page error:', error);
      this.showNotification('Error reporting page', 'error');
    }
  }
  
  async collectAllImages() {
    this.showNotification('Collecting all images...', 'info');
    
    try {
      const images = await this.collectImages();
      
      const response = await browserAPI.runtime.sendMessage({
        action: 'collect-images',
        data: {
          images,
          pageInfo: this.getPageInfo()
        }
      });
      
      if (response.success) {
        this.showNotification(`Collected ${images.length} images`, 'success');
      } else {
        this.showNotification('Failed to collect images', 'error');
      }
    } catch (error) {
      console.error('Collect images error:', error);
      this.showNotification('Error collecting images', 'error');
    }
  }
  
  detectImages() {
    // Auto-detect images on page load
    const images = document.querySelectorAll('img');
    
    if (images.length > 0) {
      setTimeout(() => {
        images.forEach(img => {
          if (img.naturalWidth > 200 && img.naturalHeight > 200) {
            this.createImageContainer(img);
          }
        });
      }, 1000);
    }
  }
  
  showNotification(message, type = 'info') {
    // Remove existing notifications
    const existing = document.querySelectorAll('.cp-notification');
    existing.forEach(n => n.remove());
    
    const notification = document.createElement('div');
    notification.className = `cp-notification ${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
      if (notification.parentElement) {
        notification.remove();
      }
    }, 3000);
  }
}

// Initialize content script
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    new ContentProtectionContent();
  });
} else {
  new ContentProtectionContent();
}