import React, { useState, useEffect } from 'react';
import { classNames } from 'primereact/utils';
import { NavigationItem } from '../../types/layout';
import FeatureStatusBadge from './FeatureStatusBadge';
import { SecurityBadge } from './TrustIndicators';

interface EnhancedSidebarMenuProps {
  items: NavigationItem[];
  onNavigate: (path: string) => void;
  isActiveRoute: (path: string) => boolean;
  className?: string;
}

const EnhancedSidebarMenu: React.FC<EnhancedSidebarMenuProps> = ({
  items,
  onNavigate,
  isActiveRoute,
  className = ''
}) => {
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());
  const [animatingItems, setAnimatingItems] = useState<Set<string>>(new Set());

  // Auto-expand parent if child is active
  useEffect(() => {
    const newExpanded = new Set<string>();
    
    const checkActiveChildren = (menuItems: NavigationItem[], parentPath?: string) => {
      menuItems.forEach(item => {
        if (item.children) {
          const hasActiveChild = item.children.some(child => isActiveRoute(child.path));
          if (hasActiveChild || isActiveRoute(item.path)) {
            newExpanded.add(item.path);
            if (parentPath) {
              newExpanded.add(parentPath);
            }
          }
          checkActiveChildren(item.children, item.path);
        }
      });
    };

    checkActiveChildren(items);
    setExpandedItems(newExpanded);
  }, [items, isActiveRoute]);

  const toggleExpanded = async (path: string) => {
    // Add animation class
    setAnimatingItems(prev => new Set(prev).add(path));
    
    // Toggle expansion after a brief delay for smooth animation
    setTimeout(() => {
      setExpandedItems(prev => {
        const newExpanded = new Set(prev);
        if (newExpanded.has(path)) {
          newExpanded.delete(path);
        } else {
          newExpanded.add(path);
        }
        return newExpanded;
      });
      
      // Remove animation class
      setTimeout(() => {
        setAnimatingItems(prev => {
          const newAnimating = new Set(prev);
          newAnimating.delete(path);
          return newAnimating;
        });
      }, 300);
    }, 50);
  };

  const getSecurityIcon = (item: NavigationItem): string => {
    // Map navigation items to security-themed icons
    const iconMap: Record<string, string> = {
      '/dashboard': '🏠',
      '/protection': '🛡️',
      '/protection/profiles': '👤',
      '/protection/infringements': '⚠️',
      '/protection/takedowns': '⚖️',
      '/protection/submissions': '📤',
      '/protection/templates': '📋',
      '/protection/search-delisting': '🔍',
      '/protection/social-media': '📱',
      '/protection/ai-matching': '🤖',
      '/protection/watermarking': '💧',
      '/protection/browser-extension': '🧩',
      '/reports': '📊',
      '/billing': '💳',
      '/settings': '⚙️',
      '/admin': '👥'
    };

    return iconMap[item.path] || item.icon || '📄';
  };

  const renderMenuItem = (item: NavigationItem, level: number = 0) => {
    const isActive = isActiveRoute(item.path);
    const hasChildren = item.children && item.children.length > 0;
    const isExpanded = expandedItems.has(item.path);
    const isAnimating = animatingItems.has(item.path);
    
    const menuItemClasses = classNames(
      'enhanced-sidebar-menu-item',
      `sidebar-level-${level}`,
      {
        'menu-item-active': isActive,
        'menu-item-expandable': hasChildren,
        'menu-item-expanded': isExpanded,
        'menu-item-disabled': item.status === 'disabled',
        'menu-item-animating': isAnimating
      }
    );

    const linkClasses = classNames(
      'enhanced-sidebar-menu-link',
      'interactive-hover',
      'smooth-colors',
      'focus-ring',
      {
        'menu-link-active': isActive,
        'menu-link-has-children': hasChildren
      }
    );

    return (
      <div key={item.path} className={menuItemClasses}>
        <div
          className={linkClasses}
          onClick={() => {
            if (item.status === 'disabled') return;
            if (hasChildren) {
              toggleExpanded(item.path);
            } else {
              onNavigate(item.path);
            }
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              if (item.status === 'disabled') return;
              if (hasChildren) {
                toggleExpanded(item.path);
              } else {
                onNavigate(item.path);
              }
            }
          }}
          role="button"
          tabIndex={item.status === 'disabled' ? -1 : 0}
          aria-expanded={hasChildren ? isExpanded : undefined}
          aria-disabled={item.status === 'disabled'}
          title={item.description || item.label}
        >
          <div className="menu-link-content">
            <div className="menu-icon">
              {getSecurityIcon(item)}
            </div>
            
            <div className="menu-text">
              <span className="menu-label">{item.label}</span>
              {item.description && level === 0 && (
                <span className="menu-description">{item.description}</span>
              )}
            </div>
          </div>

          <div className="menu-indicators">
            {/* Feature Status Badge */}
            {item.status && item.status !== 'functional' && (
              <FeatureStatusBadge 
                status={item.status as any} 
                size="xs"
                expectedDate={item.expectedDate}
              />
            )}
            
            {/* Security Badge for certain items */}
            {(item.path === '/protection' || item.path === '/protection/profiles') && (
              <SecurityBadge type="ssl" size="sm" showText={false} />
            )}
            
            {/* Expand/Collapse Indicator */}
            {hasChildren && (
              <div className={classNames('menu-expand-indicator', {
                'expanded': isExpanded
              })}>
                <i className="pi pi-chevron-right"></i>
              </div>
            )}
          </div>
        </div>

        {/* Children Menu */}
        {hasChildren && (
          <div className={classNames('enhanced-sidebar-submenu', {
            'submenu-expanded': isExpanded,
            'submenu-collapsed': !isExpanded
          })}>
            <div className="submenu-content">
              {item.children!.map(child => renderMenuItem(child, level + 1))}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <nav className={classNames('enhanced-sidebar-menu', 'stagger-children', className)}>
      {items.map(item => renderMenuItem(item))}
    </nav>
  );
};

export default EnhancedSidebarMenu;