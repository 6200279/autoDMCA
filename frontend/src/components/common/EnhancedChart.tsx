import React, { useRef, useEffect } from 'react';
import { Chart } from 'primereact/chart';
import { classNames } from 'primereact/utils';
import { EnhancedCard } from './EnhancedCard';
import { EnhancedLoading } from './EnhancedLoading';
import { EmptyState } from './EmptyStates';

export interface EnhancedChartProps {
  type: 'line' | 'bar' | 'doughnut' | 'pie' | 'area' | 'radar';
  data: any;
  options?: any;
  title?: string;
  subtitle?: string;
  loading?: boolean;
  error?: string;
  height?: string;
  responsive?: boolean;
  showCard?: boolean;
  cardVariant?: 'default' | 'elevated' | 'outlined' | 'filled';
  cardElevation?: '1' | '2' | '3';
  theme?: 'light' | 'dark' | 'auto';
  animated?: boolean;
  className?: string;
  onDataPointClick?: (event: any, elements: any[]) => void;
  onLegendClick?: (event: any, legendItem: any) => void;
}

export const EnhancedChart: React.FC<EnhancedChartProps> = ({
  type,
  data,
  options: userOptions = {},
  title,
  subtitle,
  loading = false,
  error,
  height = '300px',
  responsive = true,
  showCard = true,
  cardVariant = 'elevated',
  cardElevation = '2',
  theme = 'auto',
  animated = true,
  className,
  onDataPointClick,
  onLegendClick
}) => {
  const chartRef = useRef<Chart>(null);

  // Get theme colors from CSS variables
  const getThemeColors = () => {
    const root = document.documentElement;
    const isDarkTheme = theme === 'dark' || 
      (theme === 'auto' && root.classList.contains('dark-theme'));

    return {
      primary: getComputedStyle(root).getPropertyValue('--autodmca-primary-500').trim(),
      secondary: getComputedStyle(root).getPropertyValue('--autodmca-secondary-500').trim(),
      success: getComputedStyle(root).getPropertyValue('--autodmca-success-500').trim(),
      warning: getComputedStyle(root).getPropertyValue('--autodmca-warning-500').trim(),
      danger: getComputedStyle(root).getPropertyValue('--autodmca-danger-500').trim(),
      info: getComputedStyle(root).getPropertyValue('--autodmca-info-500').trim(),
      text: getComputedStyle(root).getPropertyValue('--autodmca-text-primary').trim(),
      textSecondary: getComputedStyle(root).getPropertyValue('--autodmca-text-secondary').trim(),
      textMuted: getComputedStyle(root).getPropertyValue('--autodmca-text-muted').trim(),
      surface: getComputedStyle(root).getPropertyValue('--autodmca-surface-card').trim(),
      border: getComputedStyle(root).getPropertyValue('--autodmca-surface-border').trim(),
      isDark: isDarkTheme
    };
  };

  // Enhanced default options
  const getEnhancedOptions = () => {
    const colors = getThemeColors();
    
    const baseOptions = {
      responsive,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: 'bottom' as const,
          labels: {
            padding: 20,
            usePointStyle: true,
            font: {
              family: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif',
              size: 12,
              weight: '500' as const
            },
            color: colors.text,
            generateLabels: (chart: any) => {
              const original = Chart.defaults.plugins.legend.labels.generateLabels;
              const labels = original.call(this, chart);
              
              labels.forEach((label: any) => {
                label.borderRadius = 4;
                label.boxWidth = 12;
                label.boxHeight = 12;
              });
              
              return labels;
            }
          },
          onClick: onLegendClick
        },
        tooltip: {
          backgroundColor: colors.surface,
          titleColor: colors.text,
          bodyColor: colors.textSecondary,
          borderColor: colors.border,
          borderWidth: 1,
          cornerRadius: 8,
          displayColors: true,
          font: {
            family: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif'
          },
          padding: 12,
          boxPadding: 4
        },
        title: {
          display: !!title,
          text: title,
          font: {
            family: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif',
            size: 16,
            weight: '600' as const
          },
          color: colors.text,
          padding: {
            top: 10,
            bottom: 20
          }
        },
        subtitle: {
          display: !!subtitle,
          text: subtitle,
          font: {
            family: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif',
            size: 12,
            weight: '400' as const
          },
          color: colors.textSecondary,
          padding: {
            bottom: 20
          }
        }
      },
      scales: {},
      animation: animated ? {
        duration: 1000,
        easing: 'easeInOutQuart' as const
      } : false,
      onClick: onDataPointClick
    };

    // Configure scales based on chart type
    if (['line', 'bar', 'area'].includes(type)) {
      baseOptions.scales = {
        x: {
          grid: {
            color: colors.border,
            borderColor: colors.border
          },
          ticks: {
            color: colors.textMuted,
            font: {
              family: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif',
              size: 11
            }
          }
        },
        y: {
          grid: {
            color: colors.border,
            borderColor: colors.border
          },
          ticks: {
            color: colors.textMuted,
            font: {
              family: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif',
              size: 11
            }
          }
        }
      };
    }

    // Merge with user options
    return {
      ...baseOptions,
      ...userOptions,
      plugins: {
        ...baseOptions.plugins,
        ...userOptions.plugins
      }
    };
  };

  // Enhanced data with theme colors
  const getEnhancedData = () => {
    const colors = getThemeColors();
    const colorPalette = [
      colors.primary,
      colors.secondary,
      colors.success,
      colors.warning,
      colors.info,
      colors.danger
    ];

    if (!data || !data.datasets) return data;

    const enhancedData = { ...data };
    
    enhancedData.datasets = data.datasets.map((dataset: any, index: number) => {
      const baseColor = colorPalette[index % colorPalette.length];
      
      return {
        ...dataset,
        backgroundColor: dataset.backgroundColor || 
          (type === 'line' || type === 'area' ? 
            `${baseColor}20` : baseColor),
        borderColor: dataset.borderColor || baseColor,
        borderWidth: dataset.borderWidth || (type === 'line' ? 3 : 1),
        borderRadius: dataset.borderRadius || (type === 'bar' ? 6 : 0),
        tension: dataset.tension || (type === 'line' ? 0.4 : 0),
        fill: dataset.fill !== undefined ? dataset.fill : type === 'area',
        pointBackgroundColor: dataset.pointBackgroundColor || baseColor,
        pointBorderColor: dataset.pointBorderColor || colors.surface,
        pointBorderWidth: dataset.pointBorderWidth || 2,
        pointRadius: dataset.pointRadius || 4,
        pointHoverRadius: dataset.pointHoverRadius || 6,
        hoverBorderWidth: dataset.hoverBorderWidth || 3,
        hoverBorderColor: dataset.hoverBorderColor || baseColor
      };
    });

    return enhancedData;
  };

  const renderChart = () => {
    if (loading) {
      return (
        <div style={{ height }}>
          <EnhancedLoading type="skeleton" variant="custom" lines={6} />
        </div>
      );
    }

    if (error) {
      return (
        <EmptyState
          variant="error"
          title="Chart Error"
          description={error}
          className="in-card"
        />
      );
    }

    if (!data || !data.datasets || data.datasets.length === 0) {
      return (
        <EmptyState
          variant="default"
          title="No Data"
          description="No data available to display in the chart."
          icon="📊"
          className="in-card"
        />
      );
    }

    return (
      <div 
        className={classNames('enhanced-chart-container', className)}
        style={{ height }}
      >
        <Chart
          ref={chartRef}
          type={type}
          data={getEnhancedData()}
          options={getEnhancedOptions()}
          className="enhanced-chart"
        />
      </div>
    );
  };

  if (showCard) {
    return (
      <EnhancedCard
        variant={cardVariant}
        elevation={cardElevation}
        className={classNames('enhanced-chart-card', className)}
      >
        {renderChart()}
      </EnhancedCard>
    );
  }

  return renderChart();
};

export interface QuickStatsProps {
  stats: Array<{
    label: string;
    value: string | number;
    change?: number;
    changeLabel?: string;
    color?: 'primary' | 'secondary' | 'success' | 'warning' | 'danger' | 'info';
    icon?: string;
  }>;
  loading?: boolean;
  className?: string;
}

export const QuickStats: React.FC<QuickStatsProps> = ({
  stats,
  loading = false,
  className
}) => {
  if (loading) {
    return (
      <div className={classNames('quick-stats-grid', className)}>
        {Array.from({ length: 4 }, (_, i) => (
          <EnhancedCard key={i} variant="elevated" elevation="1">
            <EnhancedLoading type="skeleton" variant="card" lines={2} />
          </EnhancedCard>
        ))}
      </div>
    );
  }

  return (
    <div className={classNames('quick-stats-grid', className)}>
      {stats.map((stat, index) => (
        <EnhancedCard
          key={index}
          variant="elevated"
          elevation="2"
          className={classNames('quick-stat-card', 'card-hover-lift', `stat-${stat.color || 'primary'}`)}
        >
          <div className="quick-stat-content">
            {stat.icon && (
              <div className="quick-stat-icon">
                {stat.icon}
              </div>
            )}
            <div className="quick-stat-value">{stat.value}</div>
            <div className="quick-stat-label">{stat.label}</div>
            {stat.change !== undefined && (
              <div className={classNames('quick-stat-change', {
                'positive': stat.change > 0,
                'negative': stat.change < 0,
                'neutral': stat.change === 0
              })}>
                <span className="change-icon">
                  {stat.change > 0 ? '↗️' : stat.change < 0 ? '↘️' : '➡️'}
                </span>
                <span className="change-value">
                  {stat.change > 0 ? '+' : ''}{stat.change}%
                </span>
                {stat.changeLabel && (
                  <span className="change-label">{stat.changeLabel}</span>
                )}
              </div>
            )}
          </div>
        </EnhancedCard>
      ))}
    </div>
  );
};