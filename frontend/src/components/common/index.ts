// Layout Components and Types Export
export { Layout } from './Layout';
export { default as LayoutDemo } from './LayoutDemo';
export { default as ProtectedRoute } from './ProtectedRoute';
export { default as ErrorBoundary } from './ErrorBoundary';

// Enhanced UI Components
export { EnhancedButton } from './EnhancedButton';
export { EnhancedCard } from './EnhancedCard';
export { EnhancedLoading } from './EnhancedLoading';
export { SecurityBadge, TrustIndicatorBar, SecurityShield, DataProtectionNotice } from './TrustIndicators';
export { EmptyState, NoData, LoadingState, ErrorState } from './EmptyStates';
export { EnhancedChart, QuickStats } from './EnhancedChart';
export type { EnhancedButtonProps } from './EnhancedButton';
export type { EnhancedCardProps } from './EnhancedCard';
export type { EnhancedLoadingProps } from './EnhancedLoading';
export type { SecurityBadgeProps, TrustIndicatorBarProps, SecurityShieldProps, DataProtectionNoticeProps } from './TrustIndicators';
export type { EmptyStateProps, NoDataProps, LoadingStateProps, ErrorStateProps } from './EmptyStates';
export type { EnhancedChartProps, QuickStatsProps } from './EnhancedChart';

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