import React from 'react';
import { classNames } from 'primereact/utils';

export interface SecurityBadgeProps {
  type?: 'ssl' | 'encrypted' | 'verified' | 'professional' | 'gdpr' | 'dmca';
  size?: 'sm' | 'md' | 'lg';
  showText?: boolean;
  className?: string;
}

export const SecurityBadge: React.FC<SecurityBadgeProps> = ({
  type = 'ssl',
  size = 'md',
  showText = true,
  className
}) => {
  const getBadgeConfig = () => {
    switch (type) {
      case 'ssl':
        return {
          icon: '🔒',
          text: 'SSL Secured',
          color: 'success'
        };
      case 'encrypted':
        return {
          icon: '🔐',
          text: 'End-to-End Encrypted',
          color: 'info'
        };
      case 'verified':
        return {
          icon: '✅',
          text: 'Verified Platform',
          color: 'success'
        };
      case 'professional':
        return {
          icon: '🏆',
          text: 'Professional Grade',
          color: 'warning'
        };
      case 'gdpr':
        return {
          icon: '🇪🇺',
          text: 'GDPR Compliant',
          color: 'info'
        };
      case 'dmca':
        return {
          icon: '⚖️',
          text: 'DMCA Protected',
          color: 'primary'
        };
      default:
        return {
          icon: '🔒',
          text: 'Secure',
          color: 'success'
        };
    }
  };

  const config = getBadgeConfig();

  return (
    <div className={classNames(
      'security-badge',
      `security-badge-${size}`,
      `security-badge-${config.color}`,
      className
    )}>
      <span className="security-badge-icon">{config.icon}</span>
      {showText && <span className="security-badge-text">{config.text}</span>}
    </div>
  );
};

export interface TrustIndicatorBarProps {
  indicators?: SecurityBadgeProps['type'][];
  size?: 'sm' | 'md' | 'lg';
  layout?: 'horizontal' | 'vertical';
  className?: string;
}

export const TrustIndicatorBar: React.FC<TrustIndicatorBarProps> = ({
  indicators = ['ssl', 'verified', 'gdpr'],
  size = 'sm',
  layout = 'horizontal',
  className
}) => {
  return (
    <div className={classNames(
      'trust-indicator-bar',
      `trust-indicator-bar-${layout}`,
      `trust-indicator-bar-${size}`,
      className
    )}>
      {indicators.map((type, index) => (
        <SecurityBadge
          key={`${type}-${index}`}
          type={type}
          size={size}
          showText={layout === 'vertical'}
        />
      ))}
    </div>
  );
};

export interface SecurityShieldProps {
  level?: 'basic' | 'premium' | 'enterprise';
  animated?: boolean;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

export const SecurityShield: React.FC<SecurityShieldProps> = ({
  level = 'premium',
  animated = true,
  size = 'md',
  className
}) => {
  const getShieldConfig = () => {
    switch (level) {
      case 'basic':
        return {
          color: 'var(--autodmca-info-500)',
          rings: 1,
          title: 'Basic Protection'
        };
      case 'premium':
        return {
          color: 'var(--autodmca-primary-500)',
          rings: 2,
          title: 'Premium Protection'
        };
      case 'enterprise':
        return {
          color: 'var(--autodmca-secondary-500)',
          rings: 3,
          title: 'Enterprise Security'
        };
      default:
        return {
          color: 'var(--autodmca-primary-500)',
          rings: 2,
          title: 'Premium Protection'
        };
    }
  };

  const config = getShieldConfig();

  return (
    <div className={classNames(
      'security-shield',
      `security-shield-${size}`,
      `security-shield-${level}`,
      { 'security-shield-animated': animated },
      className
    )}>
      <div className="security-shield-icon">
        🛡️
      </div>
      {Array.from({ length: config.rings }, (_, i) => (
        <div 
          key={i}
          className={`security-shield-ring security-shield-ring-${i + 1}`}
          style={{ 
            borderColor: config.color,
            animationDelay: `${i * 0.5}s`
          }}
        />
      ))}
      <div className="security-shield-label">{config.title}</div>
    </div>
  );
};

export interface DataProtectionNoticeProps {
  compact?: boolean;
  className?: string;
}

export const DataProtectionNotice: React.FC<DataProtectionNoticeProps> = ({
  compact = false,
  className
}) => {
  if (compact) {
    return (
      <div className={classNames('data-protection-notice-compact', className)}>
        <SecurityBadge type="encrypted" size="sm" showText={false} />
        <span className="text-xs text-muted">Your data is encrypted and secure</span>
      </div>
    );
  }

  return (
    <div className={classNames('data-protection-notice', className)}>
      <div className="data-protection-header">
        <SecurityShield level="enterprise" size="sm" animated={false} />
        <h4 className="font-semibold text-primary">Enterprise-Grade Security</h4>
      </div>
      <div className="data-protection-features">
        <div className="protection-feature">
          <SecurityBadge type="encrypted" size="sm" />
          <span>256-bit AES encryption</span>
        </div>
        <div className="protection-feature">
          <SecurityBadge type="gdpr" size="sm" />
          <span>GDPR & CCPA compliant</span>
        </div>
        <div className="protection-feature">
          <SecurityBadge type="ssl" size="sm" />
          <span>SSL/TLS secured connections</span>
        </div>
      </div>
    </div>
  );
};