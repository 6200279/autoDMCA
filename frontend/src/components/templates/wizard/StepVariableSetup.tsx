import React, { useState } from 'react';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Button } from 'primereact/button';
import { Dialog } from 'primereact/dialog';
import { InputText } from 'primereact/inputtext';
import { InputTextarea } from 'primereact/inputtextarea';
import { Dropdown } from 'primereact/dropdown';
import { Checkbox } from 'primereact/checkbox';
import { Chips } from 'primereact/chips';
import { Tag } from 'primereact/tag';
import { Card } from 'primereact/card';
import { Divider } from 'primereact/divider';
import { ConfirmDialog, confirmDialog } from 'primereact/confirmdialog';
import { EnhancedCard } from '../../common/EnhancedCard';
import { EnhancedButton } from '../../common/EnhancedButton';
import { TemplateVariable, VARIABLE_TYPES } from '../../../types/templates';
import { WizardFormData } from '../TemplateCreationWizard';

interface StepVariableSetupProps {
  formData: WizardFormData;
  errors: Record<string, string>;
  onChange: (updates: Partial<WizardFormData>) => void;
}

interface VariableValidationError {
  field: string;
  message: string;
}

export const StepVariableSetup: React.FC<StepVariableSetupProps> = ({
  formData,
  errors,
  onChange
}) => {
  const [showVariableDialog, setShowVariableDialog] = useState(false);
  const [editingVariable, setEditingVariable] = useState<TemplateVariable | null>(null);
  const [editingIndex, setEditingIndex] = useState<number>(-1);
  const [variableForm, setVariableForm] = useState<TemplateVariable>({
    name: '',
    label: '',
    type: 'text',
    required: false,
    default_value: '',
    description: '',
    options: [],
    validation_pattern: '',
    placeholder: ''
  });
  const [variableErrors, setVariableErrors] = useState<VariableValidationError[]>([]);

  // Reset variable form
  const resetVariableForm = () => {
    setVariableForm({
      name: '',
      label: '',
      type: 'text',
      required: false,
      default_value: '',
      description: '',
      options: [],
      validation_pattern: '',
      placeholder: ''
    });
    setVariableErrors([]);
  };

  // Open dialog for new variable
  const handleAddVariable = () => {
    resetVariableForm();
    setEditingVariable(null);
    setEditingIndex(-1);
    setShowVariableDialog(true);
  };

  // Open dialog for editing variable
  const handleEditVariable = (variable: TemplateVariable, index: number) => {
    setVariableForm({ ...variable });
    setEditingVariable(variable);
    setEditingIndex(index);
    setVariableErrors([]);
    setShowVariableDialog(true);
  };

  // Validate variable form
  const validateVariable = (variable: TemplateVariable): VariableValidationError[] => {
    const errors: VariableValidationError[] = [];
    
    if (!variable.name.trim()) {
      errors.push({ field: 'name', message: 'Variable name is required' });
    } else if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(variable.name)) {
      errors.push({ field: 'name', message: 'Variable name must be a valid identifier (letters, numbers, underscores)' });
    } else {
      // Check for duplicate names (excluding current variable being edited)
      const existingVariables = editingIndex >= 0 
        ? formData.variables.filter((_, index) => index !== editingIndex)
        : formData.variables;
      
      if (existingVariables.some(v => v.name === variable.name)) {
        errors.push({ field: 'name', message: 'Variable name already exists' });
      }
    }
    
    if (!variable.label.trim()) {
      errors.push({ field: 'label', message: 'Variable label is required' });
    }
    
    if (variable.type === 'select' && (!variable.options || variable.options.length === 0)) {
      errors.push({ field: 'options', message: 'Select variables must have at least one option' });
    }
    
    if (variable.validation_pattern) {
      try {
        new RegExp(variable.validation_pattern);
      } catch {
        errors.push({ field: 'validation_pattern', message: 'Invalid regular expression pattern' });
      }
    }
    
    return errors;
  };

  // Save variable
  const handleSaveVariable = () => {
    const errors = validateVariable(variableForm);
    setVariableErrors(errors);
    
    if (errors.length > 0) {
      return;
    }
    
    const updatedVariables = [...formData.variables];
    
    if (editingIndex >= 0) {
      updatedVariables[editingIndex] = variableForm;
    } else {
      updatedVariables.push(variableForm);
    }
    
    onChange({ variables: updatedVariables });
    setShowVariableDialog(false);
  };

  // Delete variable
  const handleDeleteVariable = (index: number) => {
    confirmDialog({
      message: 'Are you sure you want to delete this variable?',
      header: 'Confirm Delete',
      icon: 'pi pi-exclamation-triangle',
      accept: () => {
        const updatedVariables = formData.variables.filter((_, i) => i !== index);
        onChange({ variables: updatedVariables });
      }
    });
  };

  // Move variable up/down
  const moveVariable = (index: number, direction: 'up' | 'down') => {
    const newIndex = direction === 'up' ? index - 1 : index + 1;
    if (newIndex < 0 || newIndex >= formData.variables.length) return;
    
    const updatedVariables = [...formData.variables];
    [updatedVariables[index], updatedVariables[newIndex]] = [updatedVariables[newIndex], updatedVariables[index]];
    
    onChange({ variables: updatedVariables });
  };

  // Detect unused variables in content
  const getUnusedVariables = (): TemplateVariable[] => {
    const content = formData.content || '';
    return formData.variables.filter(variable => 
      !content.includes(`{{${variable.name}}}`)
    );
  };

  // Detect variables in content that aren't defined
  const getMissingVariables = (): string[] => {
    const content = formData.content || '';
    const variablePattern = /\{\{([^}]+)\}\}/g;
    const matches = [...content.matchAll(variablePattern)];
    const contentVariables = matches.map(match => match[1].trim());
    const definedVariables = new Set(formData.variables.map(v => v.name));
    
    return [...new Set(contentVariables.filter(name => !definedVariables.has(name)))];
  };

  // Auto-create missing variables
  const createMissingVariables = () => {
    const missingNames = getMissingVariables();
    const newVariables: TemplateVariable[] = missingNames.map(name => ({
      name,
      label: name.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' '),
      type: 'text',
      required: true,
      default_value: '',
      description: '',
      placeholder: `Enter ${name.replace(/_/g, ' ')}`,
      options: [],
      validation_pattern: ''
    }));
    
    onChange({ variables: [...formData.variables, ...newVariables] });
  };

  // Get error for specific field
  const getFieldError = (field: string): string | undefined => {
    return variableErrors.find(error => error.field === field)?.message;
  };

  // Render variable type icon
  const renderVariableType = (variable: TemplateVariable) => {
    const typeIcons = {
      text: 'pi pi-font',
      email: 'pi pi-envelope',
      url: 'pi pi-link',
      date: 'pi pi-calendar',
      number: 'pi pi-hashtag',
      textarea: 'pi pi-align-left',
      select: 'pi pi-list'
    };
    
    return (
      <div className="flex align-items-center gap-2">
        <i className={typeIcons[variable.type]} />
        <Tag value={variable.type} severity="info" className="text-xs" />
      </div>
    );
  };

  // Render required indicator
  const renderRequired = (variable: TemplateVariable) => {
    return variable.required ? (
      <i className="pi pi-check text-green-500" title="Required" />
    ) : (
      <i className="pi pi-times text-gray-400" title="Optional" />
    );
  };

  // Render actions column
  const renderActions = (variable: TemplateVariable, options: any) => {
    const index = options.rowIndex;
    
    return (
      <div className="flex gap-1">
        <Button
          icon="pi pi-arrow-up"
          className="p-button-text p-button-sm"
          onClick={() => moveVariable(index, 'up')}
          disabled={index === 0}
          tooltip="Move up"
        />
        <Button
          icon="pi pi-arrow-down"
          className="p-button-text p-button-sm"
          onClick={() => moveVariable(index, 'down')}
          disabled={index === formData.variables.length - 1}
          tooltip="Move down"
        />
        <Button
          icon="pi pi-pencil"
          className="p-button-text p-button-sm"
          onClick={() => handleEditVariable(variable, index)}
          tooltip="Edit variable"
        />
        <Button
          icon="pi pi-trash"
          className="p-button-text p-button-sm p-button-danger"
          onClick={() => handleDeleteVariable(index)}
          tooltip="Delete variable"
        />
      </div>
    );
  };

  const unusedVariables = getUnusedVariables();
  const missingVariables = getMissingVariables();

  return (
    <div className="step-variable-setup">
      <ConfirmDialog />
      
      <div className="step-header mb-4">
        <h4 className="m-0 mb-2">Variable Configuration</h4>
        <p className="text-color-secondary m-0">
          Configure the dynamic variables in your template. Variables allow users to customize the content for each takedown request.
        </p>
      </div>

      {/* Variable Analysis */}
      {(missingVariables.length > 0 || unusedVariables.length > 0) && (
        <div className="variable-analysis mb-4">
          {missingVariables.length > 0 && (
            <EnhancedCard className="mb-3 bg-yellow-50 border-yellow-200">
              <div className="flex align-items-center justify-content-between">
                <div className="flex align-items-center gap-3">
                  <i className="pi pi-exclamation-triangle text-yellow-600 text-xl" />
                  <div>
                    <h6 className="m-0 text-yellow-700">Missing Variables Found</h6>
                    <p className="m-0 text-sm text-yellow-600">
                      Your content references {missingVariables.length} undefined variable(s): {missingVariables.join(', ')}
                    </p>
                  </div>
                </div>
                <EnhancedButton
                  label="Create Missing"
                  icon="pi pi-plus"
                  size="small"
                  onClick={createMissingVariables}
                />
              </div>
            </EnhancedCard>
          )}
          
          {unusedVariables.length > 0 && (
            <EnhancedCard className="mb-3 bg-blue-50 border-blue-200">
              <div className="flex align-items-center gap-3">
                <i className="pi pi-info-circle text-blue-600 text-xl" />
                <div>
                  <h6 className="m-0 text-blue-700">Unused Variables</h6>
                  <p className="m-0 text-sm text-blue-600">
                    {unusedVariables.length} variable(s) are defined but not used in your content: {unusedVariables.map(v => v.name).join(', ')}
                  </p>
                </div>
              </div>
            </EnhancedCard>
          )}
        </div>
      )}

      {/* Variables Table */}
      <EnhancedCard className="mb-4">
        <div className="flex justify-content-between align-items-center mb-3">
          <h5 className="m-0">Template Variables ({formData.variables.length})</h5>
          <EnhancedButton
            label="Add Variable"
            icon="pi pi-plus"
            size="small"
            onClick={handleAddVariable}
          />
        </div>
        
        {formData.variables.length === 0 ? (
          <div className="text-center py-6">
            <div className="mb-3">
              <i className="pi pi-tags text-4xl text-color-secondary" />
            </div>
            <h6 className="text-color-secondary">No Variables Defined</h6>
            <p className="text-color-secondary mb-4">
              Variables make your templates dynamic by allowing users to customize content.
              Add variables that correspond to the {'{{variable_name}}'} placeholders in your content.
            </p>
            <EnhancedButton
              label="Add First Variable"
              icon="pi pi-plus"
              onClick={handleAddVariable}
            />
          </div>
        ) : (
          <DataTable 
            value={formData.variables} 
            responsiveLayout="scroll"
            className="variable-table"
            stripedRows
          >
            <Column 
              field="name" 
              header="Name" 
              body={(variable) => (
                <code className="text-primary font-semibold">
                  {variable.name}
                </code>
              )}
            />
            <Column field="label" header="Label" />
            <Column 
              field="type" 
              header="Type" 
              body={renderVariableType}
            />
            <Column 
              field="required" 
              header="Required" 
              body={renderRequired}
            />
            <Column 
              field="default_value" 
              header="Default" 
              body={(variable) => (
                <span className="text-sm text-color-secondary">
                  {variable.default_value || '—'}
                </span>
              )}
            />
            <Column 
              header="Actions"
              body={renderActions}
              style={{ width: '200px' }}
            />
          </DataTable>
        )}
      </EnhancedCard>

      {/* Variable Usage Guide */}
      <div className="variable-guide">
        <EnhancedCard className="bg-green-50 border-green-200">
          <div className="flex align-items-start gap-3">
            <i className="pi pi-check-circle text-green-600 text-xl mt-1" />
            <div>
              <h6 className="m-0 mb-2 text-green-700">Variable Best Practices</h6>
              <ul className="m-0 text-green-600 text-sm">
                <li>Use descriptive names like 'contact_name' instead of 'name'</li>
                <li>Mark essential fields as required to ensure complete takedown notices</li>
                <li>Provide helpful placeholder text to guide users</li>
                <li>Use appropriate types (email, url, date) for validation</li>
                <li>Add descriptions to explain complex or legal variables</li>
                <li>Order variables logically for better user experience</li>
              </ul>
            </div>
          </div>
        </EnhancedCard>
      </div>

      {/* Variable Editor Dialog */}
      <Dialog
        header={editingVariable ? 'Edit Variable' : 'Add Variable'}
        visible={showVariableDialog}
        style={{ width: '700px' }}
        modal
        onHide={() => setShowVariableDialog(false)}
        footer={
          <div className="flex justify-content-end gap-2">
            <Button
              label="Cancel"
              className="p-button-outlined"
              onClick={() => setShowVariableDialog(false)}
            />
            <EnhancedButton
              label={editingVariable ? 'Update Variable' : 'Add Variable'}
              icon="pi pi-check"
              onClick={handleSaveVariable}
            />
          </div>
        }
      >
        <div className="variable-editor-form">
          <div className="grid">
            {/* Basic Information */}
            <div className="col-12">
              <h6>Basic Information</h6>
              <Divider className="mt-2 mb-3" />
            </div>
            
            <div className="col-12 md:col-6">
              <div className="field">
                <label htmlFor="var_name" className="block mb-2 font-medium">
                  Variable Name <span className="text-red-500">*</span>
                </label>
                <InputText
                  id="var_name"
                  value={variableForm.name}
                  onChange={(e) => setVariableForm(prev => ({ ...prev, name: e.target.value }))}
                  className={`w-full ${getFieldError('name') ? 'p-invalid' : ''}`}
                  placeholder="e.g., contact_name"
                />
                {getFieldError('name') && (
                  <small className="p-error block mt-1">{getFieldError('name')}</small>
                )}
                <small className="block mt-1 text-color-secondary">
                  Use letters, numbers, and underscores only
                </small>
              </div>
            </div>

            <div className="col-12 md:col-6">
              <div className="field">
                <label htmlFor="var_label" className="block mb-2 font-medium">
                  Display Label <span className="text-red-500">*</span>
                </label>
                <InputText
                  id="var_label"
                  value={variableForm.label}
                  onChange={(e) => setVariableForm(prev => ({ ...prev, label: e.target.value }))}
                  className={`w-full ${getFieldError('label') ? 'p-invalid' : ''}`}
                  placeholder="e.g., Contact Name"
                />
                {getFieldError('label') && (
                  <small className="p-error block mt-1">{getFieldError('label')}</small>
                )}
              </div>
            </div>

            <div className="col-12 md:col-6">
              <div className="field">
                <label htmlFor="var_type" className="block mb-2 font-medium">Type</label>
                <Dropdown
                  id="var_type"
                  value={variableForm.type}
                  onChange={(e) => setVariableForm(prev => ({ ...prev, type: e.value }))}
                  options={VARIABLE_TYPES}
                  className="w-full"
                />
              </div>
            </div>

            <div className="col-12 md:col-6">
              <div className="field">
                <label className="block mb-2 font-medium">Settings</label>
                <div className="flex align-items-center gap-3">
                  <div className="flex align-items-center">
                    <Checkbox
                      checked={variableForm.required}
                      onChange={(e) => setVariableForm(prev => ({ ...prev, required: e.checked || false }))}
                    />
                    <label className="ml-2">Required field</label>
                  </div>
                </div>
              </div>
            </div>

            <div className="col-12">
              <div className="field">
                <label htmlFor="var_description" className="block mb-2 font-medium">Description</label>
                <InputTextarea
                  id="var_description"
                  value={variableForm.description}
                  onChange={(e) => setVariableForm(prev => ({ ...prev, description: e.target.value }))}
                  rows={2}
                  className="w-full"
                  placeholder="Explain what this variable is used for and provide any guidance for users"
                />
              </div>
            </div>

            {/* Input Configuration */}
            <div className="col-12">
              <h6>Input Configuration</h6>
              <Divider className="mt-2 mb-3" />
            </div>

            <div className="col-12 md:col-6">
              <div className="field">
                <label htmlFor="var_placeholder" className="block mb-2 font-medium">Placeholder Text</label>
                <InputText
                  id="var_placeholder"
                  value={variableForm.placeholder}
                  onChange={(e) => setVariableForm(prev => ({ ...prev, placeholder: e.target.value }))}
                  className="w-full"
                  placeholder="Hint text for users"
                />
              </div>
            </div>

            <div className="col-12 md:col-6">
              <div className="field">
                <label htmlFor="var_default" className="block mb-2 font-medium">Default Value</label>
                <InputText
                  id="var_default"
                  value={variableForm.default_value}
                  onChange={(e) => setVariableForm(prev => ({ ...prev, default_value: e.target.value }))}
                  className="w-full"
                  placeholder="Optional default value"
                />
              </div>
            </div>

            {/* Select Options */}
            {variableForm.type === 'select' && (
              <div className="col-12">
                <div className="field">
                  <label htmlFor="var_options" className="block mb-2 font-medium">
                    Select Options <span className="text-red-500">*</span>
                  </label>
                  <Chips
                    id="var_options"
                    value={variableForm.options || []}
                    onChange={(e) => setVariableForm(prev => ({ ...prev, options: e.value }))}
                    placeholder="Add options (press Enter)"
                    className={`w-full ${getFieldError('options') ? 'p-invalid' : ''}`}
                  />
                  {getFieldError('options') && (
                    <small className="p-error block mt-1">{getFieldError('options')}</small>
                  )}
                  <small className="block mt-1 text-color-secondary">
                    Add each option and press Enter
                  </small>
                </div>
              </div>
            )}

            {/* Validation Pattern */}
            <div className="col-12">
              <div className="field">
                <label htmlFor="var_pattern" className="block mb-2 font-medium">Validation Pattern (Advanced)</label>
                <InputText
                  id="var_pattern"
                  value={variableForm.validation_pattern}
                  onChange={(e) => setVariableForm(prev => ({ ...prev, validation_pattern: e.target.value }))}
                  className={`w-full ${getFieldError('validation_pattern') ? 'p-invalid' : ''}`}
                  placeholder="Regular expression for validation (optional)"
                />
                {getFieldError('validation_pattern') && (
                  <small className="p-error block mt-1">{getFieldError('validation_pattern')}</small>
                )}
                <small className="block mt-1 text-color-secondary">
                  Optional regular expression to validate user input
                </small>
              </div>
            </div>
          </div>
        </div>
      </Dialog>
    </div>
  );
};

export default StepVariableSetup;