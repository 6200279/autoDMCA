# AutoDMCA Layout Component

A comprehensive, responsive layout component built with PrimeReact for the AutoDMCA content protection platform.

## Features

### 🎨 **Professional UI/UX Design**
- Clean, modern interface with AutoDMCA branding
- Dark/light theme support with toggle
- Mobile-first responsive design
- Accessibility features (ARIA labels, keyboard navigation)

### 🧭 **Navigation System**
- Collapsible sidebar with hierarchical menu structure
- Top navigation bar with user menu and notifications
- Breadcrumb navigation with route awareness
- Active route highlighting
- Mobile-optimized hamburger menu

### 🔔 **Real-time Notifications**
- Notification bell with unread count badge
- Support for different notification types (info, warning, error, success)
- Mark as read functionality
- Overlay panel with scrollable list

### 👤 **User Management**
- User avatar with dropdown menu
- Profile access, settings, and logout functionality
- Admin panel access for superusers
- User information display

### 📱 **Responsive Design**
- Mobile-first approach
- Collapsible sidebar for mobile devices
- Adaptive layout for different screen sizes
- Touch-friendly interface elements

## Quick Start

### 1. Installation
The Layout component uses the following dependencies:
```json
{
  "primereact": "^10.6.6",
  "primeicons": "^7.0.0", 
  "primeflex": "^3.3.1",
  "react-router-dom": "^6.21.0"
}
```

### 2. Basic Setup
```tsx
import React from 'react';
import { BrowserRouter } from 'react-router-dom';
import { Layout, LayoutProvider } from './components/common';
import { AuthProvider } from './contexts/AuthContext';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <LayoutProvider>
          <Layout>
            {/* Your application content */}
          </Layout>
        </LayoutProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
```

### 3. Using Layout Hooks
```tsx
import { useLayoutTheme, useLayoutNotifications } from './contexts/LayoutContext';

function MyComponent() {
  const { toggleTheme, isDarkTheme } = useLayoutTheme();
  const { addSuccessNotification } = useLayoutNotifications();

  const handleSuccess = () => {
    addSuccessNotification('Success!', 'Operation completed successfully');
  };

  return (
    <div>
      <button onClick={toggleTheme}>
        Switch to {isDarkTheme ? 'Light' : 'Dark'} Theme
      </button>
      <button onClick={handleSuccess}>
        Show Success Notification
      </button>
    </div>
  );
}
```

## Component API

### Layout Props
```tsx
interface LayoutProps {
  children?: React.ReactNode;           // Page content
  showSidebar?: boolean;               // Show/hide sidebar (default: true)
  showBreadcrumb?: boolean;            // Show/hide breadcrumbs (default: true)
  pageTitle?: string;                  // Optional page title
  pageSubtitle?: string;               // Optional page subtitle
  customBreadcrumbs?: BreadcrumbItem[]; // Custom breadcrumb items
  className?: string;                  // Additional CSS classes
  fullHeight?: boolean;                // Full height layout
}
```

### Navigation Structure
The layout includes a predefined navigation structure for AutoDMCA:

```tsx
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
      { label: 'Profiles', icon: 'pi pi-user', path: '/protection/profiles' },
      { label: 'Infringements', icon: 'pi pi-exclamation-triangle', path: '/protection/infringements' },
      { label: 'Takedown Requests', icon: 'pi pi-file', path: '/protection/takedowns' },
      { label: 'Submissions', icon: 'pi pi-upload', path: '/protection/submissions' }
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
    adminOnly: true  // Only visible to admin users
  }
];
```

## Context Hooks

### useLayoutTheme()
```tsx
const {
  currentTheme,        // 'light' | 'dark'
  toggleTheme,         // () => void
  isDarkTheme,         // boolean
  isLightTheme,        // boolean
  setLightTheme,       // () => void
  setDarkTheme         // () => void
} = useLayoutTheme();
```

### useLayoutSidebar()
```tsx
const {
  sidebarVisible,      // boolean
  setSidebarVisible,   // (visible: boolean) => void
  toggleSidebar,       // () => void
  isMobile,           // boolean
  showSidebar,        // () => void
  hideSidebar         // () => void
} = useLayoutSidebar();
```

### useLayoutNotifications()
```tsx
const {
  unreadNotifications,        // number
  addNotification,           // (notification) => void
  markNotificationAsRead,    // (id: number) => void
  markAllNotificationsAsRead, // () => void
  clearAllNotifications,     // () => void
  
  // Convenience methods
  addSuccessNotification,    // (title, message) => void
  addWarningNotification,    // (title, message) => void
  addErrorNotification,      // (title, message) => void
  addInfoNotification        // (title, message) => void
} = useLayoutNotifications();
```

## Styling & Theming

### CSS Classes
The Layout component uses CSS custom properties for theming:

```css
:root {
  --primary-color: #3b82f6;
  --surface-ground: #f8fafc;
  --surface-card: #ffffff;
  --surface-border: #e5e7eb;
  --text-color: #1f2937;
}

.dark-theme {
  --surface-ground: #0f172a;
  --surface-card: #1e293b;
  --surface-border: #334155;
  --text-color: #f1f5f9;
}
```

### Custom Styling
Add custom styles by targeting specific CSS classes:

```css
/* Custom sidebar styling */
.layout-sidebar-desktop {
  background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
}

/* Custom notification styling */
.notification-panel .notification-item.notification-unread {
  border-left: 4px solid var(--primary-color);
  background: rgba(var(--primary-color-rgb), 0.1);
}
```

## Accessibility

The Layout component includes several accessibility features:

### Keyboard Navigation
- All interactive elements are keyboard accessible
- Proper tab order throughout the interface
- Escape key closes overlays and modals

### Screen Reader Support
- ARIA labels on all interactive elements
- Semantic HTML structure
- Proper heading hierarchy
- Live regions for notifications

### High Contrast & Reduced Motion
```css
/* High contrast mode support */
@media (prefers-contrast: high) {
  .layout-wrapper {
    border: 2px solid var(--text-color);
  }
}

/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
  .layout-wrapper * {
    transition: none !important;
    animation: none !important;
  }
}
```

## Integration Examples

### With React Router
```tsx
import { Routes, Route } from 'react-router-dom';
import { Layout } from './components/common';

function AppRoutes() {
  return (
    <Layout>
      <Routes>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/protection/profiles" element={<Profiles />} />
        <Route path="/billing" element={<Billing />} />
        {/* More routes */}
      </Routes>
    </Layout>
  );
}
```

### With Page-Specific Settings
```tsx
function ProfilesPage() {
  return (
    <Layout 
      pageTitle="Protected Profiles"
      showBreadcrumb={true}
      customBreadcrumbs={[
        { label: 'Content Protection', url: '/protection' },
        { label: 'Profiles', icon: 'pi pi-user' }
      ]}
    >
      <ProfilesContent />
    </Layout>
  );
}
```

## Performance Considerations

### Code Splitting
The Layout component supports lazy loading of child components:

```tsx
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Profiles = lazy(() => import('./pages/Profiles'));

function App() {
  return (
    <Layout>
      <Suspense fallback={<div>Loading...</div>}>
        <Routes>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/profiles" element={<Profiles />} />
        </Routes>
      </Suspense>
    </Layout>
  );
}
```

### Memory Management
- Context state is optimized to prevent unnecessary re-renders
- Event listeners are properly cleaned up
- Local storage is used for theme persistence

## Browser Support

- **Modern browsers**: Full feature support
- **IE11**: Basic layout with graceful degradation
- **Mobile browsers**: Optimized touch interfaces
- **Screen readers**: Full accessibility support

## Troubleshooting

### Common Issues

1. **Sidebar not showing on mobile**
   - Ensure `showSidebar` prop is not set to `false`
   - Check that `LayoutProvider` is wrapping your app

2. **Theme not persisting**
   - Verify localStorage is available
   - Check browser permissions for local storage

3. **Notifications not appearing**
   - Ensure `LayoutProvider` is properly configured
   - Check browser notification permissions

4. **Active route not highlighting**
   - Verify router is properly configured
   - Check that route paths match navigation items

### Debug Mode
Enable debug mode by adding to localStorage:
```js
localStorage.setItem('autodmca-debug', 'true');
```

This will log layout state changes and context updates to the console.