import React from 'react';
import { Panel } from 'primereact/panel';
import { Badge } from 'primereact/badge';
import { Divider } from 'primereact/divider';
import { ProgressBar } from 'primereact/progressbar';

interface ValidationResult {
  field: string;
  rule: string;
  message: string;
  isValid: boolean;
  error?: string;
}

interface ValidationPanelProps {
  validationResults: ValidationResult[];
  collapsed: boolean;
  onToggle: (collapsed: boolean) => void;
}

interface ValidationRule {
  name: string;
  description: string;
  severity: 'error' | 'warning' | 'info';
  icon: string;
  color: string;
}

const VALIDATION_RULES: Record<string, ValidationRule> = {
  required: {
    name: 'Required Fields',
    description: 'All required fields must be filled',
    severity: 'error',
    icon: 'pi-exclamation-circle',
    color: 'var(--red-500)'
  },
  minLength: {
    name: 'Minimum Length',
    description: 'Fields must meet minimum character requirements',
    severity: 'warning',
    icon: 'pi-info-circle',
    color: 'var(--orange-500)'
  },
  maxLength: {
    name: 'Maximum Length',
    description: 'Fields must not exceed maximum character limits',
    severity: 'warning',
    icon: 'pi-info-circle',
    color: 'var(--orange-500)'
  },
  format: {
    name: 'Format Validation',
    description: 'Fields must follow proper format rules',
    severity: 'error',
    icon: 'pi-times-circle',
    color: 'var(--red-500)'
  }
};

const LEGAL_COMPLIANCE_CHECKS = [
  {
    name: 'DMCA Requirements',
    description: 'Template includes required DMCA elements',
    items: [
      'Copyright holder identification',
      'Description of copyrighted work',
      'Location of infringing material',
      'Good faith statement',
      'Accuracy statement under penalty of perjury',
      'Physical or electronic signature'
    ]
  },
  {
    name: 'Legal Language',
    description: 'Template uses appropriate legal terminology',
    items: [
      'Professional tone maintained',
      'Clear and specific language',
      'Proper legal references',
      'No threatening language'
    ]
  },
  {
    name: 'Formatting Standards',
    description: 'Template follows standard formatting',
    items: [
      'Proper document structure',
      'Clear sections and headers',
      'Consistent variable usage',
      'Professional appearance'
    ]
  }
];

export const ValidationPanel: React.FC<ValidationPanelProps> = ({
  validationResults,
  collapsed,
  onToggle
}) => {
  // Calculate validation statistics
  const totalChecks = validationResults.length;
  const passedChecks = validationResults.filter(result => result.isValid).length;
  const failedChecks = totalChecks - passedChecks;
  const validationScore = totalChecks > 0 ? Math.round((passedChecks / totalChecks) * 100) : 0;

  // Group results by severity
  const errorResults = validationResults.filter(result => !result.isValid && 
    VALIDATION_RULES[result.rule.split(':')[0]]?.severity === 'error');
  const warningResults = validationResults.filter(result => !result.isValid && 
    VALIDATION_RULES[result.rule.split(':')[0]]?.severity === 'warning');

  // Determine overall validation status
  const getValidationStatus = () => {
    if (errorResults.length > 0) return 'error';
    if (warningResults.length > 0) return 'warning';
    return 'success';
  };

  const status = getValidationStatus();

  // Panel header with status
  const validationHeader = (
    <div className="validation-header">
      <div className="validation-title">
        <i className="pi pi-shield mr-2"></i>
        Template Validation
      </div>
      <div className="validation-badges">
        {status === 'error' && (
          <Badge value={`${errorResults.length} errors`} severity="danger" />
        )}
        {status === 'warning' && warningResults.length > 0 && (
          <Badge value={`${warningResults.length} warnings`} severity="warning" className="ml-2" />
        )}
        {status === 'success' && (
          <Badge value="Valid" severity="success" />
        )}
      </div>
    </div>
  );

  return (
    <Panel
      header={validationHeader}
      collapsed={collapsed}
      onToggle={(e) => onToggle(!e.value)}
      toggleable
      className="validation-panel mt-3"
    >
      <div className="validation-content">
        {/* Validation Score */}
        <div className="validation-score mb-4">
          <div className="score-header">
            <span className="score-label">Validation Score</span>
            <span className={`score-value ${status}`}>{validationScore}%</span>
          </div>
          <ProgressBar 
            value={validationScore}
            className={`validation-progress ${status}`}
          />
          <div className="score-details">
            <small className="text-color-secondary">
              {passedChecks} of {totalChecks} checks passed
            </small>
          </div>
        </div>

        <Divider />

        {/* Validation Results */}
        {errorResults.length > 0 && (
          <div className="validation-section errors-section">
            <div className="section-header">
              <i className="pi pi-times-circle text-red-500 mr-2"></i>
              <strong className="text-red-700">Errors ({errorResults.length})</strong>
            </div>
            <div className="validation-items">
              {errorResults.map((result, index) => (
                <div key={index} className="validation-item error">
                  <div className="item-icon">
                    <i className="pi pi-times text-red-500"></i>
                  </div>
                  <div className="item-content">
                    <div className="item-field">{result.field.replace('_', ' ')}</div>
                    <div className="item-message">{result.error || result.message}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {warningResults.length > 0 && (
          <div className="validation-section warnings-section">
            <div className="section-header">
              <i className="pi pi-exclamation-triangle text-orange-500 mr-2"></i>
              <strong className="text-orange-700">Warnings ({warningResults.length})</strong>
            </div>
            <div className="validation-items">
              {warningResults.map((result, index) => (
                <div key={index} className="validation-item warning">
                  <div className="item-icon">
                    <i className="pi pi-exclamation-triangle text-orange-500"></i>
                  </div>
                  <div className="item-content">
                    <div className="item-field">{result.field.replace('_', ' ')}</div>
                    <div className="item-message">{result.error || result.message}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {errorResults.length === 0 && warningResults.length === 0 && (
          <div className="validation-success">
            <div className="success-icon">
              <i className="pi pi-check-circle text-green-500 text-4xl"></i>
            </div>
            <div className="success-message">
              <h5 className="text-green-700 mb-2">All Validation Checks Passed!</h5>
              <p className="text-color-secondary mb-0">
                Your template meets all basic validation requirements.
              </p>
            </div>
          </div>
        )}

        <Divider className="my-4" />

        {/* Legal Compliance Checklist */}
        <div className="compliance-checklist">
          <div className="checklist-header mb-3">
            <i className="pi pi-verified mr-2 text-primary"></i>
            <strong>Legal Compliance Guide</strong>
          </div>
          
          {LEGAL_COMPLIANCE_CHECKS.map((check, index) => (
            <div key={index} className="compliance-section">
              <div className="compliance-title">
                <i className="pi pi-bookmark mr-2 text-primary"></i>
                <strong>{check.name}</strong>
              </div>
              <p className="compliance-description text-color-secondary">
                {check.description}
              </p>
              <ul className="compliance-items">
                {check.items.map((item, itemIndex) => (
                  <li key={itemIndex} className="compliance-item">
                    <i className="pi pi-circle text-color-secondary mr-2"></i>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
          
          <div className="compliance-note mt-3 p-3">
            <div className="note-header">
              <i className="pi pi-info-circle text-blue-500 mr-2"></i>
              <strong className="text-blue-700">Note</strong>
            </div>
            <p className="text-blue-600 mb-0 text-sm">
              This checklist provides general guidance for DMCA compliance. 
              For specific legal situations, consult with a qualified attorney.
            </p>
          </div>
        </div>
      </div>

      <style jsx>{`
        .validation-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          width: 100%;
        }

        .validation-title {
          display: flex;
          align-items: center;
          font-weight: 600;
          color: var(--primary-color);
        }

        .validation-badges {
          display: flex;
          align-items: center;
        }

        .validation-content {
          padding: 0.5rem 0;
        }

        .validation-score {
          text-align: center;
        }

        .score-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 0.75rem;
        }

        .score-label {
          font-weight: 500;
          color: var(--text-color);
        }

        .score-value {
          font-weight: 700;
          font-size: 1.2rem;
        }

        .score-value.success {
          color: var(--green-500);
        }

        .score-value.warning {
          color: var(--orange-500);
        }

        .score-value.error {
          color: var(--red-500);
        }

        .validation-progress.success :global(.p-progressbar-value) {
          background: var(--green-500);
        }

        .validation-progress.warning :global(.p-progressbar-value) {
          background: var(--orange-500);
        }

        .validation-progress.error :global(.p-progressbar-value) {
          background: var(--red-500);
        }

        .score-details {
          margin-top: 0.5rem;
        }

        .validation-section {
          margin-bottom: 1.5rem;
        }

        .section-header {
          display: flex;
          align-items: center;
          margin-bottom: 0.75rem;
          font-weight: 600;
        }

        .validation-items {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .validation-item {
          display: flex;
          align-items: flex-start;
          padding: 0.75rem;
          border-radius: 6px;
          border: 1px solid var(--surface-border);
          background: white;
        }

        .validation-item.error {
          border-color: var(--red-200);
          background: var(--red-50);
        }

        .validation-item.warning {
          border-color: var(--orange-200);
          background: var(--orange-50);
        }

        .item-icon {
          margin-right: 0.75rem;
          padding-top: 0.125rem;
        }

        .item-content {
          flex: 1;
          min-width: 0;
        }

        .item-field {
          font-weight: 600;
          text-transform: capitalize;
          margin-bottom: 0.25rem;
          color: var(--text-color);
        }

        .item-message {
          color: var(--text-color-secondary);
          font-size: 0.875rem;
          line-height: 1.4;
        }

        .validation-success {
          display: flex;
          flex-direction: column;
          align-items: center;
          text-align: center;
          padding: 2rem 1rem;
        }

        .success-icon {
          margin-bottom: 1rem;
        }

        .success-message h5 {
          margin-bottom: 0.5rem;
        }

        .compliance-checklist {
          background: var(--surface-50);
          padding: 1rem;
          border-radius: 6px;
          border: 1px solid var(--surface-border);
        }

        .checklist-header {
          display: flex;
          align-items: center;
          color: var(--primary-color);
          font-weight: 600;
        }

        .compliance-section {
          margin-bottom: 1.5rem;
        }

        .compliance-section:last-child {
          margin-bottom: 1rem;
        }

        .compliance-title {
          display: flex;
          align-items: center;
          margin-bottom: 0.5rem;
          font-weight: 600;
          color: var(--text-color);
        }

        .compliance-description {
          margin-bottom: 0.75rem;
          font-size: 0.9rem;
          line-height: 1.4;
        }

        .compliance-items {
          list-style: none;
          padding: 0;
          margin: 0;
        }

        .compliance-item {
          display: flex;
          align-items: flex-start;
          margin-bottom: 0.5rem;
          color: var(--text-color-secondary);
          font-size: 0.875rem;
          line-height: 1.4;
        }

        .compliance-note {
          background: var(--blue-50);
          border: 1px solid var(--blue-200);
          border-radius: 6px;
        }

        .note-header {
          display: flex;
          align-items: center;
          margin-bottom: 0.5rem;
          font-weight: 600;
        }

        /* Dark theme */
        .p-dark .validation-item {
          background: var(--surface-800);
          border-color: var(--surface-600);
        }

        .p-dark .validation-item.error {
          background: rgba(var(--red-500-rgb), 0.1);
          border-color: var(--red-400);
        }

        .p-dark .validation-item.warning {
          background: rgba(var(--orange-500-rgb), 0.1);
          border-color: var(--orange-400);
        }

        .p-dark .compliance-checklist {
          background: var(--surface-800);
          border-color: var(--surface-600);
        }

        .p-dark .compliance-note {
          background: rgba(var(--blue-500-rgb), 0.1);
          border-color: var(--blue-400);
        }

        /* Responsive */
        @media (max-width: 768px) {
          .validation-header {
            flex-direction: column;
            gap: 0.5rem;
            align-items: flex-start;
          }

          .validation-badges {
            align-self: flex-end;
          }

          .score-header {
            flex-direction: column;
            gap: 0.25rem;
            text-align: center;
          }

          .validation-item {
            flex-direction: column;
            text-align: left;
          }

          .item-icon {
            margin-right: 0;
            margin-bottom: 0.5rem;
            align-self: flex-start;
          }
        }
      `}</style>
    </Panel>
  );
};