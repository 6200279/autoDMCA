// Layout Components and Types Export
export { Layout } from './Layout';
export { default as LayoutDemo } from './LayoutDemo';
export { default as ProtectedRoute } from './ProtectedRoute';
export { default as ErrorBoundary } from './ErrorBoundary';

// Re-export layout types for convenience
export type { 
  NavigationItem, 
  BreadcrumbItem, 
  LayoutProps, 
  NotificationItem,
  ThemeConfig,
  UserMenuConfig,
  NotificationConfig,
  SidebarConfig,
  LayoutState,
  LayoutContextValue,
  RouteConfig,
  LayoutAnalytics
} from '../../types/layout';

// Re-export layout context hooks
export { 
  LayoutProvider,
  useLayout,
  useLayoutNotifications,
  useLayoutSidebar,
  useLayoutTheme
} from '../../contexts/LayoutContext';

// Default export for the main Layout component
export { Layout as default } from './Layout';