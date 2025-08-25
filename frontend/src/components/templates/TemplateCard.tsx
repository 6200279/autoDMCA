import React, { useState } from 'react';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { Tag } from 'primereact/tag';
import { Chip } from 'primereact/chip';
import { Badge } from 'primereact/badge';
import { Menu } from 'primereact/menu';
import { Tooltip } from 'primereact/tooltip';
import { Checkbox } from 'primereact/checkbox';
import { DMCATemplate, SUPPORTED_LANGUAGES, JURISDICTIONS } from '../../types/templates';
import './TemplateCard.css';

interface TemplateCardProps {
  template: DMCATemplate;
  selected?: boolean;
  showCheckbox?: boolean;
  onSelectionChange?: (templateId: string, selected: boolean) => void;
  onEdit?: (template: DMCATemplate) => void;
  onView?: (template: DMCATemplate) => void;
  onDuplicate?: (template: DMCATemplate) => void;
  onDelete?: (template: DMCATemplate) => void;
  onToggleFavorite?: (template: DMCATemplate) => void;
  isFavorite?: boolean;
}

const TemplateCard: React.FC<TemplateCardProps> = ({
  template,
  selected = false,
  showCheckbox = false,
  onSelectionChange,
  onEdit,
  onView,
  onDuplicate,
  onDelete,
  onToggleFavorite,
  isFavorite = false
}) => {
  const [menuVisible, setMenuVisible] = useState(false);
  const [isHovered, setIsHovered] = useState(false);

  const getStatusSeverity = (isActive: boolean): "success" | "secondary" => {
    return isActive ? 'success' : 'secondary';
  };

  const getCategoryColor = (category: string): string => {
    const colors = [
      'bg-blue-100 text-blue-800',
      'bg-green-100 text-green-800', 
      'bg-yellow-100 text-yellow-800',
      'bg-purple-100 text-purple-800',
      'bg-pink-100 text-pink-800',
      'bg-indigo-100 text-indigo-800'
    ];
    const index = category.length % colors.length;
    return colors[index];
  };

  const formatUsageCount = (count: number): string => {
    if (count >= 1000) {
      return `${(count / 1000).toFixed(1)}k`;
    }
    return count.toString();
  };

  const getLanguageLabel = (langCode: string): string => {
    return SUPPORTED_LANGUAGES.find(l => l.value === langCode)?.label || langCode;
  };

  const getJurisdictionLabel = (jurisdictionCode: string): string => {
    return JURISDICTIONS.find(j => j.value === jurisdictionCode)?.label || jurisdictionCode;
  };

  const menuItems = [
    {
      label: 'View Details',
      icon: 'pi pi-eye',
      command: () => onView?.(template)
    },
    {
      label: 'Edit Template',
      icon: 'pi pi-pencil',
      command: () => onEdit?.(template)
    },
    {
      label: 'Duplicate',
      icon: 'pi pi-copy',
      command: () => onDuplicate?.(template)
    },
    {
      separator: true
    },
    {
      label: isFavorite ? 'Remove from Favorites' : 'Add to Favorites',
      icon: isFavorite ? 'pi pi-heart-fill' : 'pi pi-heart',
      command: () => onToggleFavorite?.(template)
    },
    {
      separator: true
    },
    {
      label: 'Delete',
      icon: 'pi pi-trash',
      className: 'text-red-500',
      command: () => onDelete?.(template)
    }
  ];

  const cardHeader = () => (
    <div className="template-card-header">
      {/* Visual Preview Section */}
      <div className="template-visual-preview">
        <div className="template-icon-container">
          <i className="pi pi-file-text template-icon"></i>
          {template.is_system && (
            <div className="system-badge">
              <i className="pi pi-shield"></i>
            </div>
          )}
        </div>
        
        {/* Selection Checkbox */}
        {showCheckbox && (
          <div className="template-selection">
            <Checkbox
              checked={selected}
              onChange={(e) => onSelectionChange?.(template.id, e.checked || false)}
              aria-label={`Select template ${template.name}`}
            />
          </div>
        )}

        {/* Favorite Toggle */}
        <Button
          icon={isFavorite ? 'pi pi-heart-fill' : 'pi pi-heart'}
          className={`p-button-text p-button-rounded template-favorite ${isFavorite ? 'favorited' : ''}`}
          onClick={() => onToggleFavorite?.(template)}
          tooltip="Toggle favorite"
          tooltipOptions={{ position: 'top' }}
          aria-label={`${isFavorite ? 'Remove from' : 'Add to'} favorites`}
        />

        {/* Quick Actions Menu */}
        <div className="template-quick-menu">
          <Menu
            model={menuItems}
            popup
            ref={(el) => el}
            onShow={() => setMenuVisible(true)}
            onHide={() => setMenuVisible(false)}
          />
          <Button
            icon="pi pi-ellipsis-v"
            className="p-button-text p-button-rounded"
            onClick={(e) => {
              const menu = e.currentTarget.parentElement?.querySelector('.p-menu') as any;
              menu?.toggle(e);
            }}
            tooltip="More actions"
            tooltipOptions={{ position: 'top' }}
            aria-label="Template actions menu"
            aria-haspopup="true"
            aria-expanded={menuVisible}
          />
        </div>
      </div>
    </div>
  );

  const cardContent = () => (
    <div className="template-card-body">
      {/* Title and Description */}
      <div className="template-info">
        <h3 className="template-title" title={template.name}>
          {template.name}
        </h3>
        <p className="template-description" title={template.description}>
          {template.description}
        </p>
      </div>

      {/* Category and Status Tags */}
      <div className="template-tags">
        <Chip
          label={template.category}
          className={`category-chip ${getCategoryColor(template.category)}`}
        />
        <Tag
          value={template.is_active ? 'Active' : 'Inactive'}
          severity={getStatusSeverity(template.is_active)}
          className="status-tag"
        />
        {template.is_system && (
          <Tag value="System" severity="info" className="system-tag" />
        )}
      </div>

      {/* Custom Tags */}
      {template.tags && template.tags.length > 0 && (
        <div className="template-custom-tags">
          {template.tags.slice(0, 3).map((tag, index) => (
            <Chip
              key={index}
              label={tag}
              className="custom-tag"
            />
          ))}
          {template.tags.length > 3 && (
            <span className="additional-tags">
              +{template.tags.length - 3} more
            </span>
          )}
        </div>
      )}

      {/* Metadata */}
      <div className="template-metadata">
        <div className="metadata-row">
          <div className="metadata-item">
            <i className="pi pi-globe"></i>
            <span>
              {template.language ? getLanguageLabel(template.language) : 'English'}
            </span>
          </div>
          {template.jurisdiction && (
            <div className="metadata-item">
              <i className="pi pi-map"></i>
              <span>{getJurisdictionLabel(template.jurisdiction)}</span>
            </div>
          )}
        </div>
        
        <div className="metadata-row">
          <div className="metadata-item">
            <i className="pi pi-chart-bar"></i>
            <span>{formatUsageCount(template.usage_count || 0)} uses</span>
          </div>
          <div className="metadata-item">
            <i className="pi pi-clock"></i>
            <span>{new Date(template.updated_at).toLocaleDateString()}</span>
          </div>
        </div>
      </div>
    </div>
  );

  const cardFooter = () => (
    <div className="template-card-footer">
      {/* Primary Actions */}
      <div className="primary-actions">
        <Button
          label="View"
          icon="pi pi-eye"
          className="p-button-outlined p-button-sm"
          onClick={() => onView?.(template)}
        />
        <Button
          label="Edit"
          icon="pi pi-pencil"
          className="p-button-sm"
          onClick={() => onEdit?.(template)}
        />
      </div>

      {/* Variables Indicator */}
      {template.variables && template.variables.length > 0 && (
        <div className="variables-indicator">
          <Badge
            value={template.variables.length}
            className="variables-badge"
          />
          <span className="variables-label">variables</span>
        </div>
      )}
    </div>
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    switch (e.key) {
      case 'Enter':
      case ' ':
        e.preventDefault();
        onView?.(template);
        break;
      case 'e':
        if (e.ctrlKey || e.metaKey) {
          e.preventDefault();
          onEdit?.(template);
        }
        break;
      case 'd':
        if (e.ctrlKey || e.metaKey) {
          e.preventDefault();
          onDuplicate?.(template);
        }
        break;
      case 'f':
        if (e.ctrlKey || e.metaKey) {
          e.preventDefault();
          onToggleFavorite?.(template);
        }
        break;
      case 's':
        if (e.ctrlKey || e.metaKey && showCheckbox) {
          e.preventDefault();
          onSelectionChange?.(template.id, !selected);
        }
        break;
    }
  };

  return (
    <div 
      className={`template-card-wrapper ${selected ? 'selected' : ''} ${isHovered ? 'hovered' : ''}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onKeyDown={handleKeyDown}
      tabIndex={0}
      role="button"
      aria-label={`Template: ${template.name}. ${template.description}. Status: ${template.is_active ? 'Active' : 'Inactive'}. Press Enter to view, Ctrl+E to edit, Ctrl+D to duplicate, Ctrl+F to toggle favorite${showCheckbox ? ', Ctrl+S to toggle selection' : ''}.`}
    >
      <Tooltip target=".template-card-wrapper" />
      <Card
        className="template-card"
        header={cardHeader}
        footer={cardFooter}
      >
        {cardContent()}
      </Card>
    </div>
  );
};

export default TemplateCard;