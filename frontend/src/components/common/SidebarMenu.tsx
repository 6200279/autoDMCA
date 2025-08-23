import React, { useState } from 'react';
import { NavigationItem } from '../../types/layout';
import FeatureStatusBadge from './FeatureStatusBadge';

interface SidebarMenuProps {
  items: NavigationItem[];
  onNavigate: (path: string) => void;
  isActiveRoute: (path: string) => boolean;
  className?: string;
}

const SidebarMenu: React.FC<SidebarMenuProps> = ({
  items,
  onNavigate,
  isActiveRoute,
  className = ''
}) => {
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());

  const toggleExpanded = (path: string) => {
    const newExpanded = new Set(expandedItems);
    if (newExpanded.has(path)) {
      newExpanded.delete(path);
    } else {
      newExpanded.add(path);
    }
    setExpandedItems(newExpanded);
  };

  const renderMenuItem = (item: NavigationItem, level: number = 0) => {
    const isActive = isActiveRoute(item.path);
    const hasChildren = item.children && item.children.length > 0;
    const isExpanded = expandedItems.has(item.path);
    const indentClass = level > 0 ? 'pl-' + (3 + level * 2) : 'pl-3';

    return (
      <div key={item.path} className="sidebar-menu-item">
        <div
          className={`
            flex align-items-center justify-content-between
            p-2 cursor-pointer border-round
            sidebar-menu-link ${indentClass}
            ${isActive ? 'bg-primary text-primary-contrast' : 'hover:bg-surface-hover'}
            ${item.status === 'disabled' ? 'opacity-50 cursor-not-allowed' : ''}
          `}
          onClick={() => {
            if (item.status === 'disabled') return;
            if (hasChildren) {
              toggleExpanded(item.path);
            } else {
              onNavigate(item.path);
            }
          }}
          title={item.description}
        >
          <div className="flex align-items-center flex-1 min-w-0">
            {item.icon && (
              <i className={`${item.icon} mr-2 flex-shrink-0`} />
            )}
            <span className="sidebar-menu-label flex-1 white-space-nowrap overflow-hidden text-overflow-ellipsis">
              {item.label}
            </span>
            <FeatureStatusBadge
              status={item.status}
              expectedDate={item.expectedDate}
              description={item.description}
              size="small"
            />
          </div>
          
          {hasChildren && (
            <i className={`pi ${isExpanded ? 'pi-chevron-down' : 'pi-chevron-right'} ml-2 flex-shrink-0`} />
          )}
          
          {item.badge && (
            <span className="sidebar-menu-badge bg-primary text-primary-contrast border-round ml-2 px-2 text-xs flex-shrink-0">
              {item.badge}
            </span>
          )}
        </div>

        {/* Render children */}
        {hasChildren && isExpanded && (
          <div className="sidebar-submenu">
            {item.children!.map(child => renderMenuItem(child, level + 1))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className={`sidebar-menu ${className}`}>
      {items.map(item => renderMenuItem(item))}
    </div>
  );
};

export default SidebarMenu;