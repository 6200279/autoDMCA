import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useLocation } from 'react-router-dom';
import { LayoutContextValue, LayoutState, NotificationItem } from '../types/layout';

interface LayoutProviderProps {
  children: ReactNode;
}

const LayoutContext = createContext<LayoutContextValue | undefined>(undefined);

export const LayoutProvider: React.FC<LayoutProviderProps> = ({ children }) => {
  const location = useLocation();
  
  // State management
  const [sidebarVisible, setSidebarVisible] = useState(false);
  const [currentTheme, setCurrentTheme] = useState<'light' | 'dark'>('light');
  const [activeRoute, setActiveRoute] = useState(location.pathname);
  const [notifications, setNotifications] = useState<NotificationItem[]>([
    {
      id: 1,
      title: 'New Infringement Detected',
      message: 'Found 3 new infringements for profile "Model ABC"',
      type: 'warning',
      timestamp: new Date(Date.now() - 1000 * 60 * 30), // 30 minutes ago
      read: false,
      priority: 'high',
      category: 'infringement'
    },
    {
      id: 2,
      title: 'Takedown Request Successful',
      message: 'Content removed from example.com',
      type: 'success',
      timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2), // 2 hours ago
      read: false,
      priority: 'medium',
      category: 'takedown'
    },
    {
      id: 3,
      title: 'Monthly Report Available',
      message: 'Your content protection report for this month is ready',
      type: 'info',
      timestamp: new Date(Date.now() - 1000 * 60 * 60 * 24), // 1 day ago
      read: true,
      priority: 'low',
      category: 'report'
    }
  ]);
  const [isMobile, setIsMobile] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Apply theme by updating CSS link and document class
  const applyTheme = (theme: 'light' | 'dark') => {
    // Update document classes
    document.documentElement.classList.remove('light-theme', 'dark-theme');
    document.documentElement.classList.add(`${theme}-theme`);
    
    // Update PrimeReact theme CSS dynamically
    const existingThemeLink = document.getElementById('primereact-theme') as HTMLLinkElement;
    const newThemeUrl = theme === 'dark' 
      ? 'https://unpkg.com/primereact/resources/themes/lara-dark-blue/theme.css'
      : 'https://unpkg.com/primereact/resources/themes/lara-light-blue/theme.css';
    
    if (existingThemeLink) {
      existingThemeLink.href = newThemeUrl;
    } else {
      // Create new theme link if it doesn't exist
      const link = document.createElement('link');
      link.id = 'primereact-theme';
      link.rel = 'stylesheet';
      link.href = newThemeUrl;
      document.head.appendChild(link);
    }
    
    // Add smooth transition class temporarily
    document.documentElement.classList.add('theme-transition');
    setTimeout(() => {
      document.documentElement.classList.remove('theme-transition');
    }, 300);
  };

  // Initialize theme from localStorage or system preference
  useEffect(() => {
    const initializeTheme = () => {
      const savedTheme = localStorage.getItem('autodmca-theme') as 'light' | 'dark' | null;
      
      if (savedTheme) {
        // Use saved preference
        setCurrentTheme(savedTheme);
        applyTheme(savedTheme);
      } else {
        // Auto-detect system preference
        const prefersDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const systemTheme = prefersDarkMode ? 'dark' : 'light';
        setCurrentTheme(systemTheme);
        applyTheme(systemTheme);
        localStorage.setItem('autodmca-theme', systemTheme);
      }
    };

    initializeTheme();

    // Listen for system theme changes
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleSystemThemeChange = (e: MediaQueryListEvent) => {
      if (!localStorage.getItem('autodmca-theme')) {
        const newTheme = e.matches ? 'dark' : 'light';
        setCurrentTheme(newTheme);
        applyTheme(newTheme);
      }
    };

    mediaQuery.addEventListener('change', handleSystemThemeChange);
    return () => mediaQuery.removeEventListener('change', handleSystemThemeChange);
  }, []);

  // Update active route when location changes
  useEffect(() => {
    setActiveRoute(location.pathname);
  }, [location.pathname]);

  // Handle mobile detection
  useEffect(() => {
    const checkIsMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };

    checkIsMobile();
    window.addEventListener('resize', checkIsMobile);

    return () => {
      window.removeEventListener('resize', checkIsMobile);
    };
  }, []);

  // Auto-close sidebar on mobile when route changes
  useEffect(() => {
    if (isMobile) {
      setSidebarVisible(false);
    }
  }, [location.pathname, isMobile]);

  // Methods
  const toggleSidebar = () => {
    setSidebarVisible(prev => !prev);
  };

  const toggleTheme = () => {
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    setCurrentTheme(newTheme);
    applyTheme(newTheme);
    localStorage.setItem('autodmca-theme', newTheme);
  };

  const addNotification = (notification: Omit<NotificationItem, 'id' | 'timestamp'>) => {
    const newNotification: NotificationItem = {
      ...notification,
      id: Date.now(), // Simple ID generation
      timestamp: new Date(),
    };
    
    setNotifications(prev => [newNotification, ...prev]);
    
    // Optional: Play notification sound
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification(notification.title, {
        body: notification.message,
        icon: '/favicon.ico',
      });
    }
  };

  const markNotificationAsRead = (id: number) => {
    setNotifications(prev =>
      prev.map(notification =>
        notification.id === id
          ? { ...notification, read: true }
          : notification
      )
    );
  };

  const markAllNotificationsAsRead = () => {
    setNotifications(prev =>
      prev.map(notification => ({ ...notification, read: true }))
    );
  };

  const clearAllNotifications = () => {
    setNotifications([]);
  };

  // Computed values
  const unreadNotifications = notifications.filter(n => !n.read).length;

  const value: LayoutContextValue = {
    // State
    sidebarVisible,
    currentTheme,
    activeRoute,
    unreadNotifications,
    isMobile,
    isLoading,
    
    // Actions
    toggleSidebar,
    setSidebarVisible,
    toggleTheme,
    setActiveRoute,
    addNotification,
    markNotificationAsRead,
    markAllNotificationsAsRead,
    clearAllNotifications,
  };

  return (
    <LayoutContext.Provider value={value}>
      {children}
    </LayoutContext.Provider>
  );
};

// Hook for using the LayoutContext
export const useLayout = (): LayoutContextValue => {
  const context = useContext(LayoutContext);
  if (context === undefined) {
    throw new Error('useLayout must be used within a LayoutProvider');
  }
  return context;
};

// Enhanced hook with specific features
export const useLayoutNotifications = () => {
  const { 
    addNotification, 
    markNotificationAsRead, 
    markAllNotificationsAsRead, 
    clearAllNotifications,
    unreadNotifications 
  } = useLayout();
  
  return {
    addNotification,
    markNotificationAsRead,
    markAllNotificationsAsRead,
    clearAllNotifications,
    unreadNotifications,
    
    // Convenience methods
    addSuccessNotification: (title: string, message: string) =>
      addNotification({ title, message, type: 'success', read: false }),
      
    addWarningNotification: (title: string, message: string) =>
      addNotification({ title, message, type: 'warning', read: false }),
      
    addErrorNotification: (title: string, message: string) =>
      addNotification({ title, message, type: 'error', read: false }),
      
    addInfoNotification: (title: string, message: string) =>
      addNotification({ title, message, type: 'info', read: false }),
  };
};

// Hook for sidebar control
export const useLayoutSidebar = () => {
  const { sidebarVisible, setSidebarVisible, toggleSidebar, isMobile } = useLayout();
  
  return {
    sidebarVisible,
    setSidebarVisible,
    toggleSidebar,
    isMobile,
    
    // Convenience methods
    showSidebar: () => setSidebarVisible(true),
    hideSidebar: () => setSidebarVisible(false),
  };
};

// Hook for theme control
export const useLayoutTheme = () => {
  const { currentTheme, toggleTheme } = useLayout();
  
  return {
    currentTheme,
    toggleTheme,
    isDarkTheme: currentTheme === 'dark',
    isLightTheme: currentTheme === 'light',
    
    // Convenience methods
    setLightTheme: () => {
      if (currentTheme !== 'light') toggleTheme();
    },
    setDarkTheme: () => {
      if (currentTheme !== 'dark') toggleTheme();
    },
  };
};

export { LayoutContext };
export default LayoutContext;