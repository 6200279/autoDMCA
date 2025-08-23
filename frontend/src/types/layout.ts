// Layout-specific TypeScript interfaces and types

export interface NavigationItem {
  /** Display label for the navigation item */
  label: string;
  /** PrimeIcons icon class name */
  icon: string;
  /** Route path for navigation */
  path: string;
  /** Optional badge count to display */
  badge?: number;
  /** Child navigation items for submenus */
  children?: NavigationItem[];
  /** Whether this item is only visible to admin users */
  adminOnly?: boolean;
  /** Whether this item is currently active */
  active?: boolean;
  /** Additional CSS classes */
  className?: string;
  /** Tooltip text */
  tooltip?: string;
  /** Feature development status */
  status?: 'functional' | 'partial' | 'coming-soon' | 'disabled';
  /** Expected release date for non-functional features */
  expectedDate?: string;
  /** Feature description for tooltips */
  description?: string;
}

export interface BreadcrumbItem {
  /** Display label for the breadcrumb */
  label: string;
  /** Optional URL for navigation */
  url?: string;
  /** Optional icon class */
  icon?: string;
  /** Command to execute on click */
  command?: () => void;
}

export interface NotificationItem {
  /** Unique identifier */
  id: number;
  /** Notification title */
  title: string;
  /** Notification message */
  message: string;
  /** Notification type for styling and icons */
  type: 'info' | 'warning' | 'error' | 'success';
  /** Timestamp when notification was created */
  timestamp: Date;
  /** Whether the notification has been read */
  read: boolean;
  /** Optional action to perform on click */
  action?: () => void;
  /** Optional URL to navigate to */
  actionUrl?: string;
  /** Priority level for sorting */
  priority?: 'low' | 'medium' | 'high';
  /** Optional category for grouping */
  category?: string;
}

export interface LayoutProps {
  /** Child components to render */
  children?: React.ReactNode;
  /** Whether to show the sidebar navigation */
  showSidebar?: boolean;
  /** Whether to show the breadcrumb navigation */
  showBreadcrumb?: boolean;
  /** Optional page title to display */
  pageTitle?: string;
  /** Optional page subtitle */
  pageSubtitle?: string;
  /** Custom breadcrumb items */
  customBreadcrumbs?: BreadcrumbItem[];
  /** Additional CSS classes */
  className?: string;
  /** Whether the layout should have full height */
  fullHeight?: boolean;
  /** Custom navigation items */
  customNavigationItems?: NavigationItem[];
  /** Whether to show the user menu */
  showUserMenu?: boolean;
  /** Whether to show notifications */
  showNotifications?: boolean;
  /** Whether to show the theme toggle */
  showThemeToggle?: boolean;
  /** Custom footer content */
  footerContent?: React.ReactNode;
}

export interface ThemeConfig {
  /** Current theme mode */
  mode: 'light' | 'dark' | 'auto';
  /** Primary color */
  primaryColor?: string;
  /** Surface colors */
  surfaceColors?: {
    ground: string;
    card: string;
    border: string;
    hover: string;
  };
  /** Text colors */
  textColors?: {
    primary: string;
    secondary: string;
    muted: string;
  };
}

export interface UserMenuConfig {
  /** Whether to show the profile link */
  showProfile?: boolean;
  /** Whether to show settings */
  showSettings?: boolean;
  /** Whether to show help/support */
  showHelp?: boolean;
  /** Custom menu items */
  customItems?: NavigationItem[];
  /** Avatar size */
  avatarSize?: 'small' | 'normal' | 'large';
  /** Avatar shape */
  avatarShape?: 'circle' | 'square';
}

export interface NotificationConfig {
  /** Maximum number of notifications to display */
  maxNotifications?: number;
  /** Auto-refresh interval in seconds */
  refreshInterval?: number;
  /** Whether to group notifications */
  groupByCategory?: boolean;
  /** Whether to play sound on new notifications */
  playSound?: boolean;
  /** Position of the notification panel */
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left';
}

export interface SidebarConfig {
  /** Default collapsed state on mobile */
  collapsedOnMobile?: boolean;
  /** Default collapsed state on desktop */
  collapsedOnDesktop?: boolean;
  /** Whether to show icons only when collapsed */
  iconsOnly?: boolean;
  /** Sidebar width when expanded */
  expandedWidth?: number;
  /** Sidebar width when collapsed */
  collapsedWidth?: number;
  /** Position of the sidebar */
  position?: 'left' | 'right';
}

export interface LayoutState {
  /** Current sidebar visibility */
  sidebarVisible: boolean;
  /** Current theme */
  currentTheme: 'light' | 'dark';
  /** Active navigation path */
  activeRoute: string;
  /** Unread notification count */
  unreadNotifications: number;
  /** Whether the layout is in mobile mode */
  isMobile: boolean;
  /** Loading state */
  isLoading: boolean;
}

export interface LayoutContextValue extends LayoutState {
  /** Toggle sidebar visibility */
  toggleSidebar: () => void;
  /** Set sidebar visibility */
  setSidebarVisible: (visible: boolean) => void;
  /** Toggle theme */
  toggleTheme: () => void;
  /** Set active route */
  setActiveRoute: (route: string) => void;
  /** Add notification */
  addNotification: (notification: Omit<NotificationItem, 'id' | 'timestamp'>) => void;
  /** Mark notification as read */
  markNotificationAsRead: (id: number) => void;
  /** Mark all notifications as read */
  markAllNotificationsAsRead: () => void;
  /** Clear all notifications */
  clearAllNotifications: () => void;
}

// Utility types for props
export type ResponsiveSize = 'sm' | 'md' | 'lg' | 'xl';
export type Severity = 'info' | 'success' | 'warn' | 'error';
export type Position = 'top' | 'bottom' | 'left' | 'right' | 'center';

// Route configuration
export interface RouteConfig {
  path: string;
  breadcrumbs: BreadcrumbItem[];
  title?: string;
  subtitle?: string;
  requiredRoles?: string[];
  showSidebar?: boolean;
  showBreadcrumb?: boolean;
}

// Analytics and tracking
export interface LayoutAnalytics {
  /** Track navigation events */
  trackNavigation?: (path: string, source: 'sidebar' | 'breadcrumb' | 'direct') => void;
  /** Track theme changes */
  trackThemeChange?: (theme: 'light' | 'dark') => void;
  /** Track notification interactions */
  trackNotificationClick?: (notificationId: number, action: string) => void;
}

// All types are already exported as named exports above