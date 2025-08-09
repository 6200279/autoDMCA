import React, { useRef, useEffect } from 'react';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';
import { Menubar } from 'primereact/menubar';
import { Sidebar } from 'primereact/sidebar';
import { Button } from 'primereact/button';
import { Avatar } from 'primereact/avatar';
import { Badge } from 'primereact/badge';
import { Menu } from 'primereact/menu';
import { BreadCrumb } from 'primereact/breadcrumb';
import { OverlayPanel } from 'primereact/overlaypanel';
import { Divider } from 'primereact/divider';
import { Toast } from 'primereact/toast';
import { InputSwitch } from 'primereact/inputswitch';
import { MenuItem } from 'primereact/menuitem';
import { useAuth } from '../../contexts/AuthContext';
import { useLayout, useLayoutTheme, useLayoutSidebar, useLayoutNotifications } from '../../contexts/LayoutContext';
import { NavigationItem, BreadcrumbItem, LayoutProps, NotificationItem } from '../../types/layout';
import './Layout.css';

// Re-export types for convenience (they're now imported from types/layout.ts)
export type { NavigationItem, BreadcrumbItem, LayoutProps, NotificationItem };

// Navigation menu structure for AutoDMCA
const navigationItems: NavigationItem[] = [
  {
    label: 'Dashboard',
    icon: 'pi pi-home',
    path: '/dashboard'
  },
  {
    label: 'Content Protection',
    icon: 'pi pi-shield',
    path: '/protection',
    children: [
      {
        label: 'Profiles',
        icon: 'pi pi-user',
        path: '/protection/profiles'
      },
      {
        label: 'Infringements',
        icon: 'pi pi-exclamation-triangle',
        path: '/protection/infringements'
      },
      {
        label: 'Takedown Requests',
        icon: 'pi pi-file',
        path: '/protection/takedowns'
      },
      {
        label: 'Submissions',
        icon: 'pi pi-upload',
        path: '/protection/submissions'
      },
      {
        label: 'DMCA Templates',
        icon: 'pi pi-book',
        path: '/protection/templates'
      },
      {
        label: 'Search Engine Delisting',
        icon: 'pi pi-search-minus',
        path: '/protection/search-delisting'
      }
    ]
  },
  {
    label: 'Analytics & Reports',
    icon: 'pi pi-chart-bar',
    path: '/reports'
  },
  {
    label: 'Billing & Account',
    icon: 'pi pi-credit-card',
    path: '/billing'
  },
  {
    label: 'Settings',
    icon: 'pi pi-cog',
    path: '/settings'
  },
  {
    label: 'Admin Panel',
    icon: 'pi pi-users',
    path: '/admin',
    adminOnly: true
  }
];

// Route to breadcrumb mapping
const routeBreadcrumbMap: Record<string, BreadcrumbItem[]> = {
  '/dashboard': [{ label: 'Dashboard', icon: 'pi pi-home' }],
  '/protection/profiles': [
    { label: 'Content Protection', url: '/protection' },
    { label: 'Profiles', icon: 'pi pi-user' }
  ],
  '/protection/infringements': [
    { label: 'Content Protection', url: '/protection' },
    { label: 'Infringements', icon: 'pi pi-exclamation-triangle' }
  ],
  '/protection/takedowns': [
    { label: 'Content Protection', url: '/protection' },
    { label: 'Takedown Requests', icon: 'pi pi-file' }
  ],
  '/protection/submissions': [
    { label: 'Content Protection', url: '/protection' },
    { label: 'Submissions', icon: 'pi pi-upload' }
  ],
  '/protection/templates': [
    { label: 'Content Protection', url: '/protection' },
    { label: 'DMCA Templates', icon: 'pi pi-book' }
  ],
  '/protection/search-delisting': [
    { label: 'Content Protection', url: '/protection' },
    { label: 'Search Engine Delisting', icon: 'pi pi-search-minus' }
  ],
  '/reports': [{ label: 'Analytics & Reports', icon: 'pi pi-chart-bar' }],
  '/billing': [{ label: 'Billing & Account', icon: 'pi pi-credit-card' }],
  '/settings': [{ label: 'Settings', icon: 'pi pi-cog' }],
  '/admin': [{ label: 'Admin Panel', icon: 'pi pi-users' }]
};

export const Layout: React.FC<LayoutProps> = ({ 
  children, 
  showSidebar = true, 
  showBreadcrumb = true, 
  pageTitle 
}) => {
  const { user, logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const toast = useRef<Toast>(null);
  
  // Layout state from context
  const { setActiveRoute } = useLayout();
  const { toggleTheme, isDarkTheme } = useLayoutTheme();
  const { sidebarVisible, setSidebarVisible, toggleSidebar } = useLayoutSidebar();
  const { 
    unreadNotifications, 
    markNotificationAsRead, 
    markAllNotificationsAsRead 
  } = useLayoutNotifications();

  // Refs for overlay panels
  const userMenuRef = useRef<OverlayPanel>(null);
  const notificationMenuRef = useRef<OverlayPanel>(null);

  // Sample notifications data (in a real app, this would come from an API or global state)
  const notifications: NotificationItem[] = [
    {
      id: 1,
      title: 'New Infringement Detected',
      message: 'Found 3 new infringements for profile "Model ABC"',
      type: 'warning',
      timestamp: new Date(Date.now() - 1000 * 60 * 30), // 30 minutes ago
      read: false
    },
    {
      id: 2,
      title: 'Takedown Request Successful',
      message: 'Content removed from example.com',
      type: 'success',
      timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2), // 2 hours ago
      read: false
    }
  ];

  // Update active route when location changes
  useEffect(() => {
    setActiveRoute(location.pathname);
  }, [location.pathname, setActiveRoute]);

  // Navigation helpers
  const handleNavigation = (path: string) => {
    navigate(path);
    if (sidebarVisible) {
      setSidebarVisible(false);
    }
  };

  const isActiveRoute = (path: string): boolean => {
    if (path === '/dashboard' && location.pathname === '/') return true;
    return location.pathname.startsWith(path);
  };

  // Get current breadcrumbs
  const getCurrentBreadcrumbs = (): BreadcrumbItem[] => {
    const currentPath = location.pathname;
    return routeBreadcrumbMap[currentPath] || [
      { label: 'Dashboard', url: '/dashboard' },
      { label: 'Page' }
    ];
  };

  // Filter navigation items based on user permissions
  const getFilteredNavigationItems = (): NavigationItem[] => {
    return navigationItems.filter(item => {
      if (item.adminOnly && (!user || !user.is_superuser)) {
        return false;
      }
      return true;
    });
  };

  // Generate sidebar menu items
  const generateSidebarItems = (items: NavigationItem[]): MenuItem[] => {
    return items.map(item => ({
      label: item.label,
      icon: item.icon,
      badge: item.badge,
      className: isActiveRoute(item.path) ? 'active-menu-item' : '',
      command: () => handleNavigation(item.path),
      items: item.children ? generateSidebarItems(item.children) : undefined
    }));
  };

  // User menu items
  const userMenuItems: MenuItem[] = [
    {
      label: 'Profile',
      icon: 'pi pi-user',
      command: () => handleNavigation('/profile')
    },
    {
      label: 'Account Settings',
      icon: 'pi pi-cog',
      command: () => handleNavigation('/settings/account')
    },
    {
      separator: true
    },
    {
      label: 'Help & Support',
      icon: 'pi pi-question-circle',
      command: () => handleNavigation('/support')
    },
    {
      separator: true
    },
    {
      label: 'Sign Out',
      icon: 'pi pi-sign-out',
      command: () => handleLogout()
    }
  ];

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/auth/login');
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  // Notification handlers (using context methods)
  const handleNotificationClick = (id: number) => {
    markNotificationAsRead(id);
  };

  const handleMarkAllAsRead = () => {
    markAllNotificationsAsRead();
  };

  // Top navigation bar items
  const topNavItems: MenuItem[] = [
    {
      label: 'AutoDMCA',
      icon: 'pi pi-shield',
      className: 'navbar-brand',
      command: () => handleNavigation('/dashboard')
    }
  ];

  const topNavEndItems = (
    <div className="flex align-items-center gap-3">
      {/* Theme Toggle with InputSwitch */}
      <div className="theme-toggle-container">
        <i className="pi pi-sun"></i>
        <InputSwitch
          checked={isDarkTheme}
          onChange={toggleTheme}
          tooltip={`Switch to ${isDarkTheme ? 'light' : 'dark'} theme`}
          tooltipOptions={{ position: 'bottom' }}
        />
        <i className="pi pi-moon"></i>
      </div>

      {/* Notifications */}
      <Button
        icon="pi pi-bell"
        rounded
        text
        aria-label="Notifications"
        onClick={(e) => notificationMenuRef.current?.toggle(e)}
        className="p-overlay-badge"
      >
        {unreadNotifications > 0 && (
          <Badge value={unreadNotifications} severity="danger" />
        )}
      </Button>

      <OverlayPanel ref={notificationMenuRef} className="notification-panel">
        <div className="p-3" style={{ minWidth: '350px' }}>
          <div className="flex justify-content-between align-items-center mb-3">
            <h6 className="m-0">Notifications</h6>
            {unreadNotifications > 0 && (
              <Button
                label="Mark all read"
                link
                size="small"
                onClick={handleMarkAllAsRead}
              />
            )}
          </div>
          <Divider className="my-2" />
          <div className="max-h-20rem overflow-auto">
            {notifications.length === 0 ? (
              <p className="text-center text-color-secondary m-4">
                No notifications
              </p>
            ) : (
              notifications.map(notification => (
                <div
                  key={notification.id}
                  className={`notification-item p-2 border-round cursor-pointer ${
                    !notification.read ? 'notification-unread' : ''
                  }`}
                  onClick={() => handleNotificationClick(notification.id)}
                >
                  <div className="flex justify-content-between align-items-start">
                    <div className="flex-1">
                      <h6 className="m-0 mb-1 font-medium">
                        {notification.title}
                      </h6>
                      <p className="m-0 text-sm text-color-secondary">
                        {notification.message}
                      </p>
                      <small className="text-color-secondary">
                        {notification.timestamp.toLocaleTimeString()}
                      </small>
                    </div>
                    <i className={`notification-icon pi ${
                      notification.type === 'warning' ? 'pi-exclamation-triangle text-orange-500' :
                      notification.type === 'error' ? 'pi-times-circle text-red-500' :
                      notification.type === 'success' ? 'pi-check-circle text-green-500' :
                      'pi-info-circle text-blue-500'
                    }`} />
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </OverlayPanel>

      {/* User Menu */}
      <Button
        className="user-avatar-button"
        onClick={(e) => userMenuRef.current?.toggle(e)}
        aria-label="User menu"
        unstyled
      >
        <Avatar
          image={user?.avatar_url}
          label={user?.full_name?.charAt(0) || 'U'}
          size="normal"
          shape="circle"
          className="user-avatar"
        />
      </Button>

      <OverlayPanel ref={userMenuRef} className="user-menu-panel">
        <div className="p-3" style={{ minWidth: '250px' }}>
          <div className="flex align-items-center mb-3">
            <Avatar
              image={user?.avatar_url}
              label={user?.full_name?.charAt(0) || 'U'}
              size="large"
              shape="circle"
              className="mr-3"
            />
            <div>
              <div className="font-medium">{user?.full_name || 'User'}</div>
              <div className="text-sm text-color-secondary">
                {user?.email}
              </div>
              {user?.company && (
                <div className="text-sm text-color-secondary">
                  {user.company}
                </div>
              )}
            </div>
          </div>
          <Divider className="my-2" />
          <Menu model={userMenuItems} popup={false} />
        </div>
      </OverlayPanel>

      {/* Mobile Menu Toggle */}
      {showSidebar && (
        <Button
          icon="pi pi-bars"
          rounded
          text
          aria-label="Toggle sidebar"
          onClick={toggleSidebar}
          className="md:hidden"
        />
      )}
    </div>
  );

  if (!isAuthenticated) {
    return <Outlet />;
  }

  return (
    <div className="layout-wrapper">
      <Toast ref={toast} />
      
      {/* Top Navigation Bar */}
      <Menubar
        model={topNavItems}
        end={topNavEndItems}
        className="layout-topbar border-none"
      />

      {/* Mobile Sidebar */}
      {showSidebar && (
        <Sidebar
          visible={sidebarVisible}
          onHide={() => setSidebarVisible(false)}
          className="layout-sidebar-mobile"
          modal
        >
          <div className="layout-sidebar-content">
            <div className="sidebar-header p-3">
              <h5 className="m-0">AutoDMCA</h5>
              <p className="text-color-secondary m-0">Content Protection</p>
            </div>
            <Divider className="my-2" />
            <Menu
              model={generateSidebarItems(getFilteredNavigationItems())}
              className="sidebar-menu"
            />
          </div>
        </Sidebar>
      )}

      {/* Desktop Sidebar */}
      {showSidebar && (
        <div className="layout-sidebar-desktop hidden md:block">
          <div className="layout-sidebar-content">
            <div className="sidebar-header p-3">
              <h5 className="m-0">AutoDMCA</h5>
              <p className="text-color-secondary m-0">Content Protection</p>
            </div>
            <Divider className="my-2" />
            <Menu
              model={generateSidebarItems(getFilteredNavigationItems())}
              className="sidebar-menu"
            />
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className={`layout-content ${showSidebar ? 'with-sidebar' : ''}`}>
        {/* Breadcrumb */}
        {showBreadcrumb && (
          <div className="layout-breadcrumb p-3">
            <BreadCrumb
              model={getCurrentBreadcrumbs()}
              home={{ icon: 'pi pi-home', url: '/dashboard' }}
              className="breadcrumb-custom"
            />
            {pageTitle && (
              <h4 className="mt-2 mb-0">{pageTitle}</h4>
            )}
          </div>
        )}

        {/* Page Content */}
        <div className="layout-main-content p-3">
          {children || <Outlet />}
        </div>

        {/* Footer */}
        <footer className="layout-footer p-3 mt-6">
          <div className="flex justify-content-between align-items-center">
            <div>
              <span className="text-color-secondary">
                © 2024 AutoDMCA. All rights reserved.
              </span>
            </div>
            <div className="flex gap-3">
              <a href="/privacy" className="text-color-secondary no-underline">
                Privacy Policy
              </a>
              <a href="/terms" className="text-color-secondary no-underline">
                Terms of Service
              </a>
              <a href="/support" className="text-color-secondary no-underline">
                Support
              </a>
              <span className="text-color-secondary">v1.0.0</span>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
};

export default Layout;