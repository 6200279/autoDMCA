import React, { forwardRef } from 'react';
import { Card, CardProps } from 'primereact/card';
import { classNames } from 'primereact/utils';

export interface EnhancedCardProps extends Omit<CardProps, 'className'> {
  variant?: 'default' | 'elevated' | 'outlined' | 'filled';
  elevation?: '1' | '2' | '3';
  interactive?: boolean;
  padding?: 'none' | 'sm' | 'md' | 'lg' | 'xl';
  rounded?: 'none' | 'sm' | 'md' | 'lg' | 'xl' | '2xl';
  status?: 'default' | 'success' | 'warning' | 'danger' | 'info';
  className?: string;
  headerActions?: React.ReactNode;
  footerActions?: React.ReactNode;
}

export const EnhancedCard = forwardRef<HTMLDivElement, EnhancedCardProps>(({
  variant = 'default',
  elevation,
  interactive = false,
  padding = 'md',
  rounded = 'lg',
  status = 'default',
  className,
  title,
  subTitle,
  header,
  footer,
  headerActions,
  footerActions,
  children,
  ...props
}, ref) => {
  const getCardClasses = () => {
    const classes = [];

    // Base enhanced card class
    classes.push('enhanced-card');

    // Variant classes
    switch (variant) {
      case 'elevated':
        classes.push('enhanced-card-elevated');
        break;
      case 'outlined':
        classes.push('enhanced-card-outlined');
        break;
      case 'filled':
        classes.push('enhanced-card-filled');
        break;
      default:
        classes.push('enhanced-card-default');
        break;
    }

    // Elevation classes
    if (elevation) {
      classes.push(`enhanced-card-elevation-${elevation}`);
    }

    // Interactive state
    if (interactive) {
      classes.push('enhanced-card-interactive');
    }

    // Padding classes
    switch (padding) {
      case 'none':
        classes.push('enhanced-card-padding-none');
        break;
      case 'sm':
        classes.push('enhanced-card-padding-sm');
        break;
      case 'md':
        classes.push('enhanced-card-padding-md');
        break;
      case 'lg':
        classes.push('enhanced-card-padding-lg');
        break;
      case 'xl':
        classes.push('enhanced-card-padding-xl');
        break;
    }

    // Rounded classes
    switch (rounded) {
      case 'none':
        classes.push('enhanced-card-rounded-none');
        break;
      case 'sm':
        classes.push('enhanced-card-rounded-sm');
        break;
      case 'md':
        classes.push('enhanced-card-rounded-md');
        break;
      case 'lg':
        classes.push('enhanced-card-rounded-lg');
        break;
      case 'xl':
        classes.push('enhanced-card-rounded-xl');
        break;
      case '2xl':
        classes.push('enhanced-card-rounded-2xl');
        break;
    }

    // Status classes
    if (status !== 'default') {
      classes.push(`enhanced-card-status-${status}`);
    }

    return classes.join(' ');
  };

  const renderHeader = () => {
    if (!title && !subTitle && !header && !headerActions) return null;

    if (header && !headerActions) return header;

    return (
      <div className="enhanced-card-header">
        {header && <div className="enhanced-card-header-content">{header}</div>}
        {(title || subTitle) && (
          <div className="enhanced-card-header-text">
            {title && <h3 className="enhanced-card-title">{title}</h3>}
            {subTitle && <p className="enhanced-card-subtitle">{subTitle}</p>}
          </div>
        )}
        {headerActions && (
          <div className="enhanced-card-header-actions">
            {headerActions}
          </div>
        )}
      </div>
    );
  };

  const renderFooter = () => {
    if (!footer && !footerActions) return null;

    return (
      <div className="enhanced-card-footer">
        {footer && <div className="enhanced-card-footer-content">{footer}</div>}
        {footerActions && (
          <div className="enhanced-card-footer-actions">
            {footerActions}
          </div>
        )}
      </div>
    );
  };

  return (
    <Card
      ref={ref}
      {...props}
      className={classNames(getCardClasses(), className)}
      header={renderHeader()}
      footer={renderFooter()}
    >
      <div className="enhanced-card-content">
        {children}
      </div>
    </Card>
  );
});

EnhancedCard.displayName = 'EnhancedCard';