// Route Preloading Utility

interface PreloadedRoute {
  path: string;
  component: () => Promise<any>;
  preloaded: boolean;
}

class RoutePreloader {
  private routes: Map<string, PreloadedRoute> = new Map();
  private preloadInProgress = new Set<string>();

  constructor() {
    // Register all lazy-loaded routes
    this.registerRoute('/protection/profiles', () => import('../pages/Profiles'));
    this.registerRoute('/protection/infringements', () => import('../pages/Infringements'));
    this.registerRoute('/protection/takedowns', () => import('../pages/TakedownRequests'));
    this.registerRoute('/protection/submissions', () => import('../pages/Submissions'));
    this.registerRoute('/reports', () => import('../pages/Reports'));
    this.registerRoute('/protection/social-media', () => import('../pages/SocialMediaProtection'));
    this.registerRoute('/protection/ai-matching', () => import('../pages/AIContentMatching'));
    this.registerRoute('/settings', () => import('../pages/Settings'));
    this.registerRoute('/billing', () => import('../pages/Billing'));
    this.registerRoute('/admin', () => import('../pages/AdminPanel'));
    this.registerRoute('/protection/templates', () => import('../pages/DMCATemplates'));
    this.registerRoute('/protection/search-delisting', () => import('../pages/SearchEngineDelisting'));
    this.registerRoute('/protection/watermarking', () => import('../pages/ContentWatermarking'));
    this.registerRoute('/protection/browser-extension', () => import('../pages/BrowserExtension'));
  }

  private registerRoute(path: string, importFn: () => Promise<any>) {
    this.routes.set(path, {
      path,
      component: importFn,
      preloaded: false
    });
  }

  async preloadRoute(path: string): Promise<void> {
    const route = this.routes.get(path);
    
    if (!route || route.preloaded || this.preloadInProgress.has(path)) {
      return;
    }

    this.preloadInProgress.add(path);

    try {
      await route.component();
      route.preloaded = true;
      console.log(`Route preloaded: ${path}`);
    } catch (error) {
      console.error(`Failed to preload route ${path}:`, error);
    } finally {
      this.preloadInProgress.delete(path);
    }
  }

  async preloadCriticalRoutes(): Promise<void> {
    // Preload most commonly accessed routes
    const criticalRoutes = [
      '/protection/profiles',
      '/protection/infringements',
      '/reports',
      '/settings'
    ];

    // Use requestIdleCallback to preload during idle time
    if ('requestIdleCallback' in window) {
      window.requestIdleCallback(() => {
        criticalRoutes.forEach(route => this.preloadRoute(route));
      });
    } else {
      // Fallback: preload after a short delay
      setTimeout(() => {
        criticalRoutes.forEach(route => this.preloadRoute(route));
      }, 1000);
    }
  }

  preloadOnHover(path: string): void {
    // Preload route when user hovers over navigation link
    this.preloadRoute(path);
  }

  getPreloadStatus(): { [key: string]: boolean } {
    const status: { [key: string]: boolean } = {};
    this.routes.forEach((route, path) => {
      status[path] = route.preloaded;
    });
    return status;
  }
}

// Singleton instance
export const routePreloader = new RoutePreloader();

// Hook for navigation components
export const useRoutePreloader = () => {
  return {
    preloadRoute: (path: string) => routePreloader.preloadRoute(path),
    preloadOnHover: (path: string) => routePreloader.preloadOnHover(path),
    getStatus: () => routePreloader.getPreloadStatus()
  };
};

export default routePreloader;