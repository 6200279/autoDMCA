import React, { useState, useRef } from 'react';
import { Button } from 'primereact/button';
import { OverlayPanel } from 'primereact/overlaypanel';
import { InputText } from 'primereact/inputtext';
import { Divider } from 'primereact/divider';
import { Chip } from 'primereact/chip';
import { ScrollPanel } from 'primereact/scrollpanel';
import { TemplateVariable } from '../../../types/templates';

interface VariableInserterProps {
  variables: TemplateVariable[];
  onInsertVariable: (variableName: string) => void;
}

interface CommonVariable {
  name: string;
  label: string;
  description: string;
  category: string;
}

const COMMON_VARIABLES: CommonVariable[] = [
  // Date/Time Variables
  { name: 'date', label: 'Current Date', description: 'Today\'s date', category: 'Date/Time' },
  { name: 'time', label: 'Current Time', description: 'Current time', category: 'Date/Time' },
  { name: 'timestamp', label: 'Timestamp', description: 'Full date and time', category: 'Date/Time' },
  
  // Legal Variables
  { name: 'sender_name', label: 'Sender Name', description: 'Name of the person sending the notice', category: 'Legal' },
  { name: 'sender_company', label: 'Sender Company', description: 'Company name', category: 'Legal' },
  { name: 'sender_address', label: 'Sender Address', description: 'Complete mailing address', category: 'Legal' },
  { name: 'sender_email', label: 'Sender Email', description: 'Contact email address', category: 'Legal' },
  { name: 'sender_phone', label: 'Sender Phone', description: 'Contact phone number', category: 'Legal' },
  
  // Content Variables
  { name: 'infringing_url', label: 'Infringing URL', description: 'URL of infringing content', category: 'Content' },
  { name: 'original_url', label: 'Original URL', description: 'URL of original content', category: 'Content' },
  { name: 'content_title', label: 'Content Title', description: 'Title of the copyrighted work', category: 'Content' },
  { name: 'content_description', label: 'Content Description', description: 'Description of copyrighted work', category: 'Content' },
  
  // Platform Variables
  { name: 'platform_name', label: 'Platform Name', description: 'Name of the platform/website', category: 'Platform' },
  { name: 'platform_contact', label: 'Platform Contact', description: 'Platform contact information', category: 'Platform' },
  { name: 'case_number', label: 'Case Number', description: 'Reference case number', category: 'Platform' }
];

export const VariableInserter: React.FC<VariableInserterProps> = ({
  variables,
  onInsertVariable
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const overlayPanelRef = useRef<OverlayPanel>(null);

  // Group common variables by category
  const categorizedVariables = COMMON_VARIABLES.reduce((acc, variable) => {
    if (!acc[variable.category]) {
      acc[variable.category] = [];
    }
    acc[variable.category].push(variable);
    return acc;
  }, {} as Record<string, CommonVariable[]>);

  const categories = ['all', ...Object.keys(categorizedVariables)];

  // Filter variables based on search and category
  const filteredCommonVariables = COMMON_VARIABLES.filter(variable => {
    const matchesSearch = searchTerm === '' || 
      variable.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      variable.label.toLowerCase().includes(searchTerm.toLowerCase()) ||
      variable.description.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesCategory = selectedCategory === 'all' || variable.category === selectedCategory;
    
    return matchesSearch && matchesCategory;
  });

  const filteredTemplateVariables = variables.filter(variable => {
    return searchTerm === '' || 
      variable.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      variable.label.toLowerCase().includes(searchTerm.toLowerCase());
  });

  const handleInsertVariable = (variableName: string) => {
    onInsertVariable(variableName);
    overlayPanelRef.current?.hide();
  };

  const toggleOverlay = (event: React.MouseEvent) => {
    overlayPanelRef.current?.toggle(event);
  };

  return (
    <>
      <div className="variable-inserter-toolbar">
        <Button
          icon="pi pi-code"
          label="Insert Variable"
          className="p-button-outlined p-button-sm"
          onClick={toggleOverlay}
          tooltip="Insert a variable into the template"
          tooltipOptions={{ position: 'bottom' }}
        />
        
        <div className="quick-variables">
          {variables.slice(0, 3).map((variable, index) => (
            <Chip
              key={index}
              label={variable.name}
              className="variable-chip cursor-pointer"
              onClick={() => handleInsertVariable(variable.name)}
              title={`Insert {{${variable.name}}}`}
            />
          ))}
        </div>
      </div>

      <OverlayPanel 
        ref={overlayPanelRef} 
        style={{ width: '400px', maxHeight: '500px' }}
        className="variable-inserter-panel"
      >
        <div className="variable-inserter-content">
          {/* Header */}
          <div className="variable-inserter-header">
            <h4 className="m-0 mb-3">Insert Variable</h4>
            
            {/* Search */}
            <div className="field">
              <InputText
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search variables..."
                className="w-full"
                icon="pi pi-search"
              />
            </div>
            
            {/* Category Filter */}
            <div className="category-filter">
              {categories.map(category => (
                <Chip
                  key={category}
                  label={category === 'all' ? 'All' : category}
                  className={`category-chip cursor-pointer ${selectedCategory === category ? 'selected' : ''}`}
                  onClick={() => setSelectedCategory(category)}
                />
              ))}
            </div>
          </div>

          <Divider />

          <ScrollPanel style={{ height: '300px' }}>
            {/* Template Variables */}
            {filteredTemplateVariables.length > 0 && (
              <div className="variable-section">
                <h5 className="section-title">Template Variables</h5>
                <div className="variables-grid">
                  {filteredTemplateVariables.map((variable, index) => (
                    <div
                      key={`template-${index}`}
                      className="variable-item clickable"
                      onClick={() => handleInsertVariable(variable.name)}
                    >
                      <div className="variable-name">{variable.name}</div>
                      <div className="variable-label">{variable.label}</div>
                      {variable.description && (
                        <div className="variable-description">{variable.description}</div>
                      )}
                      <div className="variable-syntax">{'{{' + variable.name + '}}'}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {filteredTemplateVariables.length > 0 && <Divider />}

            {/* Common Variables */}
            <div className="variable-section">
              <h5 className="section-title">Common Variables</h5>
              
              {selectedCategory === 'all' ? (
                // Show all categories
                Object.entries(categorizedVariables).map(([category, categoryVariables]) => {
                  const filteredCategoryVars = categoryVariables.filter(variable =>
                    searchTerm === '' || 
                    variable.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                    variable.label.toLowerCase().includes(searchTerm.toLowerCase()) ||
                    variable.description.toLowerCase().includes(searchTerm.toLowerCase())
                  );

                  if (filteredCategoryVars.length === 0) return null;

                  return (
                    <div key={category} className="category-group">
                      <h6 className="category-header">{category}</h6>
                      <div className="variables-grid">
                        {filteredCategoryVars.map((variable, index) => (
                          <div
                            key={`${category}-${index}`}
                            className="variable-item clickable"
                            onClick={() => handleInsertVariable(variable.name)}
                          >
                            <div className="variable-name">{variable.name}</div>
                            <div className="variable-label">{variable.label}</div>
                            <div className="variable-description">{variable.description}</div>
                            <div className="variable-syntax">{'{{' + variable.name + '}}'}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })
              ) : (
                // Show specific category
                <div className="variables-grid">
                  {filteredCommonVariables.map((variable, index) => (
                    <div
                      key={`common-${index}`}
                      className="variable-item clickable"
                      onClick={() => handleInsertVariable(variable.name)}
                    >
                      <div className="variable-name">{variable.name}</div>
                      <div className="variable-label">{variable.label}</div>
                      <div className="variable-description">{variable.description}</div>
                      <div className="variable-syntax">{'{{' + variable.name + '}}'}</div>
                    </div>
                  ))}
                </div>
              )}
              
              {filteredCommonVariables.length === 0 && filteredTemplateVariables.length === 0 && (
                <div className="no-variables">
                  <i className="pi pi-search text-4xl mb-2 block text-color-secondary"></i>
                  <p className="text-color-secondary m-0">No variables found matching "{searchTerm}"</p>
                </div>
              )}
            </div>
          </ScrollPanel>
        </div>
      </OverlayPanel>

      <style jsx>{`
        .variable-inserter-toolbar {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          margin-bottom: 1rem;
          flex-wrap: wrap;
        }

        .quick-variables {
          display: flex;
          gap: 0.5rem;
          flex-wrap: wrap;
        }

        .variable-chip {
          font-size: 0.75rem !important;
          padding: 0.25rem 0.5rem !important;
          transition: all 0.2s;
        }

        .variable-chip:hover {
          background-color: var(--primary-color) !important;
          color: white !important;
        }

        .variable-inserter-content {
          padding: 0.5rem;
        }

        .category-filter {
          display: flex;
          gap: 0.25rem;
          flex-wrap: wrap;
          margin-top: 0.75rem;
        }

        .category-chip {
          font-size: 0.75rem !important;
          padding: 0.25rem 0.5rem !important;
          border: 1px solid var(--surface-border) !important;
          background: white !important;
          color: var(--text-color) !important;
          transition: all 0.2s;
        }

        .category-chip:hover {
          border-color: var(--primary-color) !important;
        }

        .category-chip.selected {
          background: var(--primary-color) !important;
          color: white !important;
          border-color: var(--primary-color) !important;
        }

        .variable-section {
          margin-bottom: 1.5rem;
        }

        .section-title {
          color: var(--primary-color);
          font-weight: 600;
          margin-bottom: 0.75rem;
          font-size: 1rem;
        }

        .category-group {
          margin-bottom: 1rem;
        }

        .category-header {
          color: var(--text-color-secondary);
          font-weight: 500;
          margin-bottom: 0.5rem;
          font-size: 0.875rem;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }

        .variables-grid {
          display: grid;
          gap: 0.5rem;
        }

        .variable-item {
          padding: 0.75rem;
          border: 1px solid var(--surface-border);
          border-radius: 6px;
          background: white;
          transition: all 0.2s;
        }

        .variable-item.clickable {
          cursor: pointer;
        }

        .variable-item.clickable:hover {
          border-color: var(--primary-color);
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
          transform: translateY(-1px);
        }

        .variable-name {
          font-weight: 600;
          color: var(--primary-color);
          font-family: Monaco, Menlo, 'Ubuntu Mono', monospace;
          font-size: 0.875rem;
          margin-bottom: 0.25rem;
        }

        .variable-label {
          color: var(--text-color);
          font-weight: 500;
          margin-bottom: 0.25rem;
          font-size: 0.875rem;
        }

        .variable-description {
          color: var(--text-color-secondary);
          font-size: 0.75rem;
          margin-bottom: 0.5rem;
          line-height: 1.4;
        }

        .variable-syntax {
          font-family: Monaco, Menlo, 'Ubuntu Mono', monospace;
          font-size: 0.75rem;
          color: var(--green-600);
          background: rgba(var(--green-500), 0.1);
          padding: 0.25rem 0.5rem;
          border-radius: 3px;
          display: inline-block;
        }

        .no-variables {
          text-align: center;
          padding: 2rem;
        }

        /* Dark theme support */
        .p-dark .variable-item {
          background: var(--surface-800);
          border-color: var(--surface-600);
        }

        .p-dark .variable-item:hover {
          border-color: var(--primary-color);
        }

        .p-dark .category-chip {
          background: var(--surface-700) !important;
          border-color: var(--surface-600) !important;
          color: var(--text-color) !important;
        }
      `}</style>
    </>
  );
};