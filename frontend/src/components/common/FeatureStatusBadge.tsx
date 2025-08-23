import React from 'react';
import { Tag } from 'primereact/tag';
import { Tooltip } from 'primereact/tooltip';

interface FeatureStatusBadgeProps {
  status?: 'functional' | 'partial' | 'coming-soon' | 'disabled';
  expectedDate?: string;
  description?: string;
  className?: string;
  size?: 'small' | 'normal';
}

const FeatureStatusBadge: React.FC<FeatureStatusBadgeProps> = ({
  status = 'functional',
  expectedDate,
  description,
  className = '',
  size = 'small'
}) => {
  if (status === 'functional') {
    return null; // No badge needed for fully functional features
  }

  const getStatusConfig = () => {
    switch (status) {
      case 'partial':
        return {
          value: 'BETA',
          severity: 'warning' as const,
          icon: 'pi pi-exclamation-circle',
          tooltip: `${description || 'Partially functional feature'} - Some functionality may be limited.`
        };
      case 'coming-soon':
        return {
          value: expectedDate ? `SOON` : 'SOON',
          severity: 'info' as const,
          icon: 'pi pi-clock',
          tooltip: `${description || 'Feature in development'}${expectedDate ? ` - Expected: ${expectedDate}` : ''}`
        };
      case 'disabled':
        return {
          value: 'OFF',
          severity: 'danger' as const,
          icon: 'pi pi-ban',
          tooltip: description || 'Feature temporarily disabled'
        };
      default:
        return {
          value: 'NEW',
          severity: 'success' as const,
          icon: 'pi pi-star',
          tooltip: description || 'New feature'
        };
    }
  };

  const config = getStatusConfig();
  const badgeId = `status-badge-${Math.random().toString(36).substr(2, 9)}`;

  return (
    <>
      <Tag
        id={badgeId}
        value={config.value}
        severity={config.severity}
        icon={config.icon}
        className={`
          feature-status-badge 
          ${size === 'small' ? 'p-tag-sm' : ''} 
          ${className}
        `}
        style={{
          fontSize: size === 'small' ? '0.65rem' : '0.75rem',
          padding: size === 'small' ? '0.15rem 0.35rem' : '0.25rem 0.5rem',
          marginLeft: '0.5rem',
          verticalAlign: 'middle'
        }}
      />
      <Tooltip target={`#${badgeId}`} content={config.tooltip} position="top" />
    </>
  );
};

export default FeatureStatusBadge;