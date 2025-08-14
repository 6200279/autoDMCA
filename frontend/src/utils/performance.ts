// Performance monitoring utilities

interface PerformanceMetrics {
  loadTime: number;
  domContentLoaded: number;
  firstContentfulPaint?: number;
  largestContentfulPaint?: number;
  firstInputDelay?: number;
  cumulativeLayoutShift?: number;
}

class PerformanceMonitor {
  private metrics: PerformanceMetrics = {
    loadTime: 0,
    domContentLoaded: 0
  };

  constructor() {
    this.measureBasicMetrics();
    this.measureWebVitals();
  }

  private measureBasicMetrics(): void {
    // Measure page load time
    window.addEventListener('load', () => {
      const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
      this.metrics.loadTime = navigation.loadEventEnd - navigation.loadEventStart;
      this.metrics.domContentLoaded = navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart;
      
      if (process.env.NODE_ENV === 'development') {
        console.log('Performance Metrics:', this.metrics);
      }
    });
  }

  private measureWebVitals(): void {
    // First Contentful Paint (FCP)
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (entry.name === 'first-contentful-paint') {
          this.metrics.firstContentfulPaint = entry.startTime;
        }
      }
    }).observe({ entryTypes: ['paint'] });

    // Largest Contentful Paint (LCP)
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        this.metrics.largestContentfulPaint = entry.startTime;
      }
    }).observe({ entryTypes: ['largest-contentful-paint'] });

    // First Input Delay (FID)
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        this.metrics.firstInputDelay = entry.processingStart - entry.startTime;
      }
    }).observe({ entryTypes: ['first-input'] });

    // Cumulative Layout Shift (CLS)
    let clsValue = 0;
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (!entry.hadRecentInput) {
          clsValue += entry.value;
        }
      }
      this.metrics.cumulativeLayoutShift = clsValue;
    }).observe({ entryTypes: ['layout-shift'] });
  }

  public getMetrics(): PerformanceMetrics {
    return { ...this.metrics };
  }

  public logChunkLoadTime(chunkName: string): void {
    const entries = performance.getEntriesByType('resource') as PerformanceResourceTiming[];
    const chunkEntry = entries.find(entry => entry.name.includes(chunkName));
    
    if (chunkEntry && process.env.NODE_ENV === 'development') {
      console.log(`Chunk "${chunkName}" loaded in ${chunkEntry.responseEnd - chunkEntry.startTime}ms`);
    }
  }

  public measureRouteTransition(routeName: string): () => void {
    const start = performance.now();
    
    return () => {
      const end = performance.now();
      if (process.env.NODE_ENV === 'development') {
        console.log(`Route "${routeName}" transition took ${end - start}ms`);
      }
    };
  }
}

// Singleton instance
export const performanceMonitor = new PerformanceMonitor();

// Bundle size reporter
export const reportBundleSize = (): void => {
  if ('getEntriesByType' in performance) {
    const resources = performance.getEntriesByType('resource') as PerformanceResourceTiming[];
    const jsResources = resources.filter(resource => 
      resource.name.includes('.js') && 
      (resource.name.includes('/assets/') || resource.name.includes('/js/'))
    );

    let totalSize = 0;
    const bundleInfo: Array<{ name: string; size: number }> = [];

    jsResources.forEach(resource => {
      const size = resource.transferSize || 0;
      totalSize += size;
      
      const filename = resource.name.split('/').pop() || 'unknown';
      bundleInfo.push({
        name: filename,
        size: size
      });
    });

    if (process.env.NODE_ENV === 'development') {
      console.group('Bundle Analysis');
      console.log(`Total JS bundle size: ${(totalSize / 1024).toFixed(2)} KB`);
      console.log('Individual chunks:', bundleInfo.sort((a, b) => b.size - a.size));
      console.groupEnd();
    }
  }
};

// Memory usage monitoring
export const monitorMemoryUsage = (): void => {
  if ('memory' in performance) {
    const memory = (performance as any).memory;
    
    if (process.env.NODE_ENV === 'development') {
      console.log('Memory usage:', {
        used: `${(memory.usedJSHeapSize / 1024 / 1024).toFixed(2)} MB`,
        total: `${(memory.totalJSHeapSize / 1024 / 1024).toFixed(2)} MB`,
        limit: `${(memory.jsHeapSizeLimit / 1024 / 1024).toFixed(2)} MB`
      });
    }
  }
};

// Export performance utilities
export default {
  monitor: performanceMonitor,
  reportBundleSize,
  monitorMemoryUsage
};