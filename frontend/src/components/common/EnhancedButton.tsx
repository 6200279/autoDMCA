import React, { forwardRef } from 'react';
import { Button, ButtonProps } from 'primereact/button';
import { classNames } from 'primereact/utils';

export interface EnhancedButtonProps extends Omit<ButtonProps, 'variant' | 'size'> {
  variant?: 'primary' | 'secondary' | 'success' | 'warning' | 'danger' | 'info' | 'ghost' | 'outline';
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  elevation?: '1' | '2' | '3';
  loading?: boolean;
  loadingIcon?: string;
  loadingText?: string;
  fullWidth?: boolean;
}

export const EnhancedButton = forwardRef<HTMLButtonElement, EnhancedButtonProps>(({
  variant = 'primary',
  size = 'md',
  elevation,
  loading = false,
  loadingIcon = 'pi pi-spinner pi-spin',
  loadingText,
  fullWidth = false,
  className,
  children,
  disabled,
  ...props
}, ref) => {
  const getButtonClasses = () => {
    const classes = [];

    // Base enhanced button class
    classes.push('enhanced-button');

    // Variant classes
    switch (variant) {
      case 'primary':
        classes.push('enhanced-button-primary');
        break;
      case 'secondary':
        classes.push('enhanced-button-secondary');
        break;
      case 'success':
        classes.push('enhanced-button-success');
        break;
      case 'warning':
        classes.push('enhanced-button-warning');
        break;
      case 'danger':
        classes.push('enhanced-button-danger');
        break;
      case 'info':
        classes.push('enhanced-button-info');
        break;
      case 'ghost':
        classes.push('enhanced-button-ghost');
        break;
      case 'outline':
        classes.push('enhanced-button-outline');
        break;
    }

    // Size classes
    switch (size) {
      case 'xs':
        classes.push('enhanced-button-xs');
        break;
      case 'sm':
        classes.push('enhanced-button-sm');
        break;
      case 'md':
        classes.push('enhanced-button-md');
        break;
      case 'lg':
        classes.push('enhanced-button-lg');
        break;
      case 'xl':
        classes.push('enhanced-button-xl');
        break;
    }

    // Elevation classes
    if (elevation) {
      classes.push(`enhanced-button-elevation-${elevation}`);
    }

    // Full width
    if (fullWidth) {
      classes.push('enhanced-button-full-width');
    }

    // Loading state
    if (loading) {
      classes.push('enhanced-button-loading');
    }

    return classes.join(' ');
  };

  return (
    <Button
      ref={ref}
      {...props}
      className={classNames(getButtonClasses(), className)}
      disabled={disabled || loading}
      icon={loading ? loadingIcon : props.icon}
      label={loading && loadingText ? loadingText : props.label}
    >
      {children}
    </Button>
  );
});

EnhancedButton.displayName = 'EnhancedButton';