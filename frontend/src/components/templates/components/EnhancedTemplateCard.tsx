import React, { useState, useMemo, useCallback, useRef, useId } from 'react';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { Badge } from 'primereact/badge';
import { Chip } from 'primereact/chip';
import { Checkbox } from 'primereact/checkbox';
import { Menu } from 'primereact/menu';
import { ProgressSpinner } from 'primereact/progressspinner';
import { Tooltip } from 'primereact/tooltip';
import { useTemplateLibraryContext } from '../context/TemplateLibraryContext';
import { TemplateCardProps, TemplateAction } from '../types/enhanced';
import { formatDistanceToNow } from 'date-fns';

interface EnhancedTemplateCardProps extends Omit<TemplateCardProps, 'template'> {
  template: any; // Use any since we're enhancing the base template
  focused?: boolean;
  showThumbnail?: boolean;
  showPreview?: boolean;
  showMetadata?: boolean;
  showUsageStats?: boolean;
  compactMode?: boolean;
}

const EnhancedTemplateCard: React.FC<EnhancedTemplateCardProps> = ({
  template,
  layout,
  selected = false,
  selectionMode,
  focused = false,
  showThumbnail = true,
  showPreview = false,
  showMetadata = true,
  showUsageStats = false,
  showCheckbox = false,
  compactMode = false,
  onSelectionChange,
  onClick,
  onDoubleClick,
  className = '',
  style
}) => {
  const {
    actions,
    enhancedActions,
    config,
    viewPreferences
  } = useTemplateLibraryContext();

  const [isHovered, setIsHovered] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [previewExpanded, setPreviewExpanded] = useState(false);
  const menuRef = useRef<Menu>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const cardId = useId();
  const descriptionId = useId();

  const isFavorite = actions.selection?.favorites.includes(template.id) || false;

  // Card actions menu
  const cardActions: TemplateAction[] = useMemo(() => [
    {
      id: 'view',
      label: 'View Details',
      icon: 'pi pi-eye',
      handler: () => onClick?.(template)
    },
    {
      id: 'edit',
      label: 'Edit Template',
      icon: 'pi pi-pencil',
      handler: () => console.log('Edit template:', template.id)
    },
    {
      id: 'duplicate',
      label: 'Duplicate',
      icon: 'pi pi-copy',
      handler: async () => {
        setIsLoading(true);
        try {
          // Simulate API call delay
          await new Promise(resolve => setTimeout(resolve, 1000));
          console.log('Duplicate template:', template.id);
        } finally {
          setIsLoading(false);
        }
      }
    },
    {
      id: 'favorite',
      label: isFavorite ? 'Remove from Favorites' : 'Add to Favorites',
      icon: isFavorite ? 'pi pi-heart-fill' : 'pi pi-heart',
      handler: () => actions.toggleFavorite(template.id)
    },
    {
      id: 'delete',
      label: 'Delete',
      icon: 'pi pi-trash',
      severity: 'danger' as const,
      handler: () => console.log('Delete template:', template.id)
    }
  ], [template.id, isFavorite, actions, onClick]);

  const menuItems = cardActions.map(action => ({
    label: action.label,
    icon: action.icon,
    command: () => action.handler(template),
    className: action.severity === 'danger' ? 'text-red-500' : ''
  }));

  // Handle card click
  const handleCardClick = useCallback((e: React.MouseEvent) => {
    if (e.target instanceof HTMLElement) {
      // Don't trigger card click if clicking on interactive elements
      if (e.target.closest('.p-checkbox, .p-button, .card-menu, .card-actions')) {
        return;
      }
    }
    
    onClick?.(template);
  }, [template, onClick]);

  // Handle double click
  const handleDoubleClick = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    onDoubleClick?.(template);
  }, [template, onDoubleClick]);

  // Handle selection change
  const handleSelectionChange = useCallback((e: any) => {
    onSelectionChange?.(template.id, e.checked);
  }, [template.id, onSelectionChange]);

  // Format dates
  const formatDate = (dateString: string) => {
    try {
      return formatDistanceToNow(new Date(dateString), { addSuffix: true });
    } catch {
      return dateString;
    }
  };

  // Get status badge
  const getStatusBadge = () => {
    if (template.is_active) {
      return <Badge value="Active" severity="success" className="status-badge" />;
    } else {
      return <Badge value="Inactive" severity="warning" className="status-badge" />;
    }
  };

  // Get validation status indicator
  const getValidationIndicator = () => {
    const status = template.validationStatus || 'valid';
    const severity = status === 'valid' ? 'success' : status === 'warning' ? 'warning' : 'danger';
    const icon = status === 'valid' ? 'pi-check-circle' : status === 'warning' ? 'pi-exclamation-triangle' : 'pi-times-circle';
    
    return (
      <i 
        className={`pi ${icon} validation-indicator ${severity}`}
        data-pr-tooltip={`Validation: ${status}`}
        data-pr-position="top"
      />
    );
  };

  // Card header
  const cardHeader = showThumbnail && (
    <div className="card-thumbnail-section">
      {template.thumbnailUrl ? (
        <img
          src={template.thumbnailUrl}
          alt={`${template.name} thumbnail`}
          className="card-thumbnail"
          onError={(e) => {
            e.currentTarget.style.display = 'none';
          }}
        />
      ) : (
        <div className="card-thumbnail-placeholder">
          <i className="pi pi-file-text placeholder-icon" />
        </div>
      )}
      {isFavorite && (
        <i className="pi pi-heart-fill favorite-indicator" />
      )}
      {template.isRecentlyViewed && (
        <Badge value="Recent" severity="info" className="recent-badge" />
      )}
    </div>
  );

  // Card title
  const cardTitle = (
    <div className="card-title-section">
      <h3 className="card-title" title={template.name}>
        {template.name}
      </h3>
      {showMetadata && (
        <div className="card-metadata">
          <span className="category-badge">
            <i className="pi pi-tag" />
            {template.category}
          </span>
          {getValidationIndicator()}
        </div>
      )}
    </div>
  );

  // Card subtitle/description
  const cardSubtitle = showMetadata && (
    <p className="card-description" title={template.description} id={descriptionId}>
      {compactMode 
        ? template.description?.substring(0, 60) + (template.description?.length > 60 ? '...' : '')
        : template.description?.substring(0, 120) + (template.description?.length > 120 ? '...' : '')
      }
    </p>
  );

  // Card content (preview)
  const cardContent = showPreview && template.previewContent && (
    <div className="card-preview-section">
      <div className={`card-preview-content ${previewExpanded ? 'expanded' : 'collapsed'}`}>
        {previewExpanded ? template.content : template.previewContent}
      </div>
      <Button
        label={previewExpanded ? 'Show Less' : 'Show More'}
        icon={previewExpanded ? 'pi pi-chevron-up' : 'pi pi-chevron-down'}
        className="p-button-text p-button-sm preview-toggle"
        onClick={(e) => {
          e.stopPropagation();
          setPreviewExpanded(!previewExpanded);
        }}
      />
    </div>
  );

  // Card footer
  const cardFooter = (
    <div className="card-footer">
      {/* Tags */}
      {template.tags && template.tags.length > 0 && (
        <div className="card-tags">
          {template.tags.slice(0, compactMode ? 2 : 3).map((tag: string, index: number) => (
            <Chip
              key={index}
              label={tag}
              className="template-tag"
              onClick={(e) => {
                e.stopPropagation();
                actions.setFilters({ tags: [tag] });
              }}
            />
          ))}
          {template.tags.length > (compactMode ? 2 : 3) && (
            <span className="more-tags">+{template.tags.length - (compactMode ? 2 : 3)} more</span>
          )}
        </div>
      )}

      {/* Stats and actions */}
      <div className="card-footer-bottom">
        <div className="card-stats">
          {showUsageStats && (
            <span className="usage-count" title="Usage count">
              <i className="pi pi-chart-line" />
              {template.usage_count || 0}
            </span>
          )}
          <span className="updated-date" title={`Last updated: ${template.updated_at}`}>
            <i className="pi pi-clock" />
            {formatDate(template.updated_at)}
          </span>
        </div>

        <div className="card-actions">
          {/* Quick favorite toggle */}
          <Button
            icon={isFavorite ? 'pi pi-heart-fill' : 'pi pi-heart'}
            className={`p-button-text p-button-sm favorite-btn ${isFavorite ? 'favorited' : ''}`}
            onClick={(e) => {
              e.stopPropagation();
              actions.toggleFavorite(template.id);
            }}
            tooltip={isFavorite ? 'Remove from favorites' : 'Add to favorites'}
          />

          {/* Status badge */}
          {getStatusBadge()}

          {/* More actions menu */}
          <Button
            icon="pi pi-ellipsis-v"
            className="p-button-text p-button-sm card-menu"
            onClick={(e) => {
              e.stopPropagation();
              menuRef.current?.toggle(e);
            }}
            tooltip="More actions"
          />
          <Menu
            ref={menuRef}
            model={menuItems}
            popup
            className="card-context-menu"
          />
        </div>
      </div>
    </div>
  );

  const cardClass = [
    'enhanced-template-card',
    layout.size,
    layout.type,
    selected && 'selected',
    focused && 'focused',
    isHovered && 'hovered',
    compactMode && 'compact',
    template.is_active ? 'active' : 'inactive',
    className
  ].filter(Boolean).join(' ');

  return (
    <>
      <Tooltip target=".validation-indicator" />
      <div
        ref={cardRef}
        className={cardClass}
        style={style}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        onClick={handleCardClick}
        onDoubleClick={handleDoubleClick}
        role="gridcell"
        tabIndex={focused ? 0 : -1}
        aria-selected={selected}
        aria-label={`Template: ${template.name}`}
        aria-describedby={`${cardId}-description ${descriptionId}`}
        id={`template-${template.id}`}
        data-template-id={template.id}
      >
        {/* Loading overlay */}
        {isLoading && (
          <div className="card-loading-overlay">
            <ProgressSpinner size="30px" />
          </div>
        )}

        {/* Selection checkbox */}
        {showCheckbox && (
          <div className="card-selection-checkbox">
            <Checkbox
              checked={selected}
              onChange={handleSelectionChange}
              className="template-checkbox"
              aria-label={`Select ${template.name}`}
              onClick={(e) => e.stopPropagation()}
            />
          </div>
        )}

        {/* Main card content */}
        <Card
          header={cardHeader}
          title={cardTitle}
          subTitle={cardSubtitle}
          footer={cardFooter}
          className="template-card-content"
        >
          {cardContent}
        </Card>
      </div>
    </>
  );
};

export default React.memo(EnhancedTemplateCard);