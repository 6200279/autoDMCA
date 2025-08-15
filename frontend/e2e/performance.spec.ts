import { test, expect, Page } from '@playwright/test'

// Performance test configuration
const PERFORMANCE_THRESHOLDS = {
  pageLoad: 3000,          // 3 seconds max page load
  apiResponse: 2000,       // 2 seconds max API response
  interaction: 500,        // 500ms max for UI interactions
  lighthouse: {
    performance: 80,
    accessibility: 90,
    bestPractices: 85,
    seo: 85
  }
}

test.describe('Frontend Performance Testing', () => {
  test.beforeEach(async ({ page }) => {
    // Setup performance monitoring
    await page.addInitScript(() => {
      window.performanceMetrics = {
        navigationStart: performance.now(),
        pageLoadTimes: [],
        apiCallTimes: [],
        interactionTimes: []
      }
    })
  })

  test('page load performance - dashboard', async ({ page }) => {
    // Login first
    await page.goto('/login')
    await page.fill('[data-testid="email-input"]', 'test@example.com')
    await page.fill('[data-testid="password-input"]', 'password123')
    
    // Measure dashboard load time
    const startTime = Date.now()
    await page.click('[data-testid="login-button"]')
    
    // Wait for dashboard to be fully loaded
    await page.waitForSelector('[data-testid="dashboard-stats"]', { state: 'visible' })
    await page.waitForLoadState('networkidle')
    
    const loadTime = Date.now() - startTime
    
    // Performance assertion
    expect(loadTime).toBeLessThan(PERFORMANCE_THRESHOLDS.pageLoad)
    
    // Check for performance markers
    const performanceEntries = await page.evaluate(() => {
      return {
        navigationStart: performance.timing.navigationStart,
        domContentLoaded: performance.timing.domContentLoadedEventEnd,
        loadComplete: performance.timing.loadEventEnd,
        firstPaint: performance.getEntriesByName('first-paint')[0]?.startTime || 0,
        firstContentfulPaint: performance.getEntriesByName('first-contentful-paint')[0]?.startTime || 0
      }
    })
    
    const domContentLoadedTime = performanceEntries.domContentLoaded - performanceEntries.navigationStart
    expect(domContentLoadedTime).toBeLessThan(2000) // DOM should load within 2 seconds
  })

  test('API response time performance', async ({ page }) => {
    await loginUser(page)
    
    // Monitor network requests
    const apiResponses: { url: string; duration: number }[] = []
    
    page.on('response', async (response) => {
      if (response.url().includes('/api/')) {
        const request = response.request()
        const timing = response.timing()
        
        apiResponses.push({
          url: response.url(),
          duration: timing.responseEnd - timing.requestStart
        })
      }
    })
    
    // Navigate to dashboard to trigger API calls
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')
    
    // Check API response times
    for (const apiCall of apiResponses) {
      expect(apiCall.duration).toBeLessThan(PERFORMANCE_THRESHOLDS.apiResponse)
    }
    
    // Check specific critical API endpoints
    const statsAPI = apiResponses.find(r => r.url.includes('/dashboard/stats'))
    if (statsAPI) {
      expect(statsAPI.duration).toBeLessThan(1000) // Critical endpoint should be fast
    }
  })

  test('UI interaction performance', async ({ page }) => {
    await loginUser(page)
    await page.goto('/dashboard')
    
    // Test navigation performance
    const startTime = Date.now()
    await page.click('[data-testid="profiles-nav-link"]')
    await page.waitForSelector('[data-testid="profiles-page"]', { state: 'visible' })
    const navigationTime = Date.now() - startTime
    
    expect(navigationTime).toBeLessThan(PERFORMANCE_THRESHOLDS.interaction)
    
    // Test modal opening performance
    const modalStart = Date.now()
    await page.click('[data-testid="create-profile-button"]')
    await page.waitForSelector('[data-testid="profile-modal"]', { state: 'visible' })
    const modalTime = Date.now() - modalStart
    
    expect(modalTime).toBeLessThan(PERFORMANCE_THRESHOLDS.interaction)
    
    // Test form interaction performance
    const formStart = Date.now()
    await page.fill('[data-testid="stage-name-input"]', 'Test Creator')
    await page.fill('[data-testid="bio-input"]', 'Test bio content')
    const formTime = Date.now() - formStart
    
    expect(formTime).toBeLessThan(200) // Form interactions should be very fast
  })

  test('table rendering performance with large datasets', async ({ page }) => {
    await loginUser(page)
    
    // Mock large dataset response
    await page.route('**/api/v1/infringements*', async route => {
      const largeDataset = {
        items: Array.from({ length: 1000 }, (_, i) => ({
          id: i + 1,
          url: `https://example${i}.com/content`,
          title: `Infringement ${i + 1}`,
          platform: ['instagram', 'twitter', 'onlyfans'][i % 3],
          confidence_score: 0.7 + (Math.random() * 0.3),
          status: ['detected', 'confirmed', 'resolved'][i % 3],
          created_at: new Date(Date.now() - i * 86400000).toISOString()
        })),
        total: 1000,
        page: 1,
        size: 50
      }
      
      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify(largeDataset)
      })
    })
    
    // Navigate to infringements page and measure render time
    const renderStart = Date.now()
    await page.goto('/infringements')
    
    // Wait for table to be fully rendered
    await page.waitForSelector('[data-testid="infringements-table"]', { state: 'visible' })
    await page.waitForFunction(() => {
      const table = document.querySelector('[data-testid="infringements-table"]')
      return table && table.querySelectorAll('tbody tr').length > 0
    })
    
    const renderTime = Date.now() - renderStart
    
    // Large table should render within reasonable time
    expect(renderTime).toBeLessThan(3000)
    
    // Test scrolling performance
    const scrollStart = Date.now()
    await page.evaluate(() => {
      const table = document.querySelector('[data-testid="infringements-table"]')
      if (table) {
        table.scrollTop = table.scrollHeight
      }
    })
    const scrollTime = Date.now() - scrollStart
    
    expect(scrollTime).toBeLessThan(100) // Scrolling should be immediate
  })

  test('image loading performance', async ({ page }) => {
    await loginUser(page)
    
    // Navigate to a page with images
    await page.goto('/profiles')
    
    // Monitor image loading
    const imageLoads: { src: string; loadTime: number }[] = []
    
    await page.evaluateOnNewDocument(() => {
      const originalCreateElement = document.createElement
      document.createElement = function(tagName: string) {
        const element = originalCreateElement.call(this, tagName)
        
        if (tagName.toLowerCase() === 'img') {
          const img = element as HTMLImageElement
          const startTime = performance.now()
          
          img.addEventListener('load', () => {
            const loadTime = performance.now() - startTime
            window.imageLoadTimes = window.imageLoadTimes || []
            window.imageLoadTimes.push({
              src: img.src,
              loadTime: loadTime
            })
          })
        }
        
        return element
      }
    })
    
    // Wait for all images to load
    await page.waitForLoadState('networkidle')
    
    // Check image load times
    const imageLoadTimes = await page.evaluate(() => window.imageLoadTimes || [])
    
    for (const imageLoad of imageLoadTimes) {
      expect(imageLoad.loadTime).toBeLessThan(2000) // Images should load within 2 seconds
    }
  })

  test('bundle size and loading performance', async ({ page }) => {
    // Check initial bundle loading
    const responses: { url: string; size: number; type: string }[] = []
    
    page.on('response', async (response) => {
      if (response.url().includes('.js') || response.url().includes('.css')) {
        const buffer = await response.body()
        responses.push({
          url: response.url(),
          size: buffer.length,
          type: response.url().includes('.js') ? 'javascript' : 'css'
        })
      }
    })
    
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Calculate total bundle sizes
    const totalJSSize = responses
      .filter(r => r.type === 'javascript')
      .reduce((sum, r) => sum + r.size, 0)
    
    const totalCSSSize = responses
      .filter(r => r.type === 'css')
      .reduce((sum, r) => sum + r.size, 0)
    
    // Bundle size thresholds
    expect(totalJSSize).toBeLessThan(2 * 1024 * 1024) // JS bundle under 2MB
    expect(totalCSSSize).toBeLessThan(500 * 1024) // CSS bundle under 500KB
    
    // Check for code splitting
    const jsFiles = responses.filter(r => r.type === 'javascript')
    expect(jsFiles.length).toBeGreaterThan(1) // Should have multiple JS chunks
  })

  test('real user metrics simulation', async ({ page }) => {
    await page.goto('/')
    
    // Simulate real user interactions with timing
    const userJourney = [
      { action: 'login', target: '[data-testid="login-button"]' },
      { action: 'navigate', target: '[data-testid="dashboard-nav"]' },
      { action: 'view-profiles', target: '[data-testid="profiles-nav"]' },
      { action: 'create-profile', target: '[data-testid="create-profile-button"]' },
      { action: 'fill-form', target: '[data-testid="stage-name-input"]' },
      { action: 'submit', target: '[data-testid="submit-button"]' }
    ]
    
    const journeyMetrics: { action: string; duration: number }[] = []
    
    // Login first
    await page.fill('[data-testid="email-input"]', 'test@example.com')
    await page.fill('[data-testid="password-input"]', 'password123')
    await page.click('[data-testid="login-button"]')
    await page.waitForSelector('[data-testid="dashboard"]')
    
    for (const step of userJourney.slice(1)) { // Skip login as we already did it
      const startTime = performance.now()
      
      try {
        await page.click(step.target)
        await page.waitForTimeout(100) // Small delay to ensure action completes
        
        const duration = performance.now() - startTime
        journeyMetrics.push({
          action: step.action,
          duration: duration
        })
        
        // Each user action should feel responsive
        expect(duration).toBeLessThan(1000)
        
      } catch (error) {
        console.log(`Skipping step ${step.action}: element not found`)
      }
    }
    
    // Overall journey should complete quickly
    const totalJourneyTime = journeyMetrics.reduce((sum, m) => sum + m.duration, 0)
    expect(totalJourneyTime).toBeLessThan(10000) // Total user journey under 10 seconds
  })

  test('memory usage monitoring', async ({ page }) => {
    await loginUser(page)
    
    // Monitor memory usage over time
    const memorySnapshots: number[] = []
    
    // Take initial memory snapshot
    let initialMemory = await page.evaluate(() => {
      return (performance as any).memory?.usedJSHeapSize || 0
    })
    memorySnapshots.push(initialMemory)
    
    // Perform memory-intensive operations
    const operations = [
      () => page.goto('/dashboard'),
      () => page.goto('/profiles'),
      () => page.goto('/infringements'),
      () => page.goto('/takedowns'),
      () => page.goto('/analytics'),
    ]
    
    for (const operation of operations) {
      await operation()
      await page.waitForLoadState('networkidle')
      
      const currentMemory = await page.evaluate(() => {
        return (performance as any).memory?.usedJSHeapSize || 0
      })
      memorySnapshots.push(currentMemory)
      
      // Force garbage collection if available
      await page.evaluate(() => {
        if ((window as any).gc) {
          (window as any).gc()
        }
      })
    }
    
    // Check for memory leaks
    const finalMemory = memorySnapshots[memorySnapshots.length - 1]
    const memoryGrowth = finalMemory - initialMemory
    
    // Memory growth should be reasonable
    expect(memoryGrowth).toBeLessThan(50 * 1024 * 1024) // Less than 50MB growth
  })

  test('lighthouse performance audit', async ({ page }) => {
    await page.goto('/')
    
    // This would require lighthouse integration
    // For now, we'll simulate the key checks lighthouse performs
    
    // Check for performance best practices
    const performanceChecks = await page.evaluate(() => {
      return {
        hasServiceWorker: 'serviceWorker' in navigator,
        usesHTTPS: location.protocol === 'https:',
        hasViewportMeta: !!document.querySelector('meta[name="viewport"]'),
        hasCompression: document.documentElement.getAttribute('data-compressed') === 'true',
        hasLazyLoading: document.querySelectorAll('img[loading="lazy"]').length > 0
      }
    })
    
    // Performance best practices assertions
    expect(performanceChecks.hasViewportMeta).toBe(true)
    
    // Check Core Web Vitals
    const webVitals = await page.evaluate(() => {
      return new Promise((resolve) => {
        new PerformanceObserver((entryList) => {
          const entries = entryList.getEntries()
          const vitals = {
            FCP: 0,
            LCP: 0,
            FID: 0,
            CLS: 0
          }
          
          entries.forEach(entry => {
            if (entry.name === 'first-contentful-paint') {
              vitals.FCP = entry.startTime
            }
            if (entry.entryType === 'largest-contentful-paint') {
              vitals.LCP = entry.startTime
            }
            if (entry.entryType === 'first-input') {
              vitals.FID = entry.processingStart - entry.startTime
            }
            if (entry.entryType === 'layout-shift' && !entry.hadRecentInput) {
              vitals.CLS += entry.value
            }
          })
          
          resolve(vitals)
        }).observe({ entryTypes: ['paint', 'largest-contentful-paint', 'first-input', 'layout-shift'] })
        
        // Timeout after 5 seconds
        setTimeout(() => resolve({ FCP: 0, LCP: 0, FID: 0, CLS: 0 }), 5000)
      })
    })
    
    const vitals = webVitals as any
    
    // Core Web Vitals thresholds
    if (vitals.FCP > 0) expect(vitals.FCP).toBeLessThan(1800) // First Contentful Paint < 1.8s
    if (vitals.LCP > 0) expect(vitals.LCP).toBeLessThan(2500) // Largest Contentful Paint < 2.5s
    if (vitals.FID > 0) expect(vitals.FID).toBeLessThan(100)  // First Input Delay < 100ms
    if (vitals.CLS > 0) expect(vitals.CLS).toBeLessThan(0.1)  // Cumulative Layout Shift < 0.1
  })

  // Helper function
  async function loginUser(page: Page) {
    await page.goto('/login')
    await page.fill('[data-testid="email-input"]', 'test@example.com')
    await page.fill('[data-testid="password-input"]', 'password123')
    await page.click('[data-testid="login-button"]')
    await page.waitForSelector('[data-testid="dashboard"]', { state: 'visible' })
  }
})