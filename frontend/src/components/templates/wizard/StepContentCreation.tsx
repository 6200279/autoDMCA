import React, { useState, useRef } from 'react';
import { Editor } from 'primereact/editor';
import { Button } from 'primereact/button';
import { Dialog } from 'primereact/dialog';
import { InputText } from 'primereact/inputtext';
import { Dropdown } from 'primereact/dropdown';
import { Card } from 'primereact/card';
import { Divider } from 'primereact/divider';
import { Toast } from 'primereact/toast';
import { EnhancedCard } from '../../common/EnhancedCard';
import { EnhancedButton } from '../../common/EnhancedButton';
import { templatesApi } from '../../../services/api';
import { TemplateVariable } from '../../../types/templates';
import { WizardFormData } from '../TemplateCreationWizard';

interface StepContentCreationProps {
  formData: WizardFormData;
  errors: Record<string, string>;
  onChange: (updates: Partial<WizardFormData>) => void;
}

interface ContentSuggestion {
  title: string;
  description: string;
  content: string;
  category: string;
}

interface VariableInsertion {
  name: string;
  label: string;
  type: TemplateVariable['type'];
  required: boolean;
  placeholder?: string;
}

const CONTENT_SUGGESTIONS: ContentSuggestion[] = [
  {
    title: 'Professional Opening',
    description: 'Formal greeting and identification',
    category: 'opening',
    content: `Dear {{platform_name}} Legal Team,

I am writing to notify you of copyright infringement occurring on your platform. I am the copyright owner of the material described below and request immediate removal of the infringing content.`
  },
  {
    title: 'Detailed Infringement Description', 
    description: 'Comprehensive description of the infringement',
    category: 'body',
    content: `**Infringing Content Details:**
- Location: {{infringing_url}}
- Posted by: {{infringing_user}}
- Date discovered: {{discovery_date}}
- Description: {{infringement_description}}

**Original Copyrighted Work:**
- Title: {{work_title}}
- Copyright owner: {{copyright_owner}}
- Original location: {{original_url}}
- Publication date: {{publication_date}}`
  },
  {
    title: 'Good Faith Statement',
    description: 'Required DMCA good faith belief statement',
    category: 'legal',
    content: `**Good Faith Statement:**
I have a good faith belief that the use of the copyrighted material described above is not authorized by the copyright owner, its agent, or the law.`
  },
  {
    title: 'Perjury Statement',
    description: 'Required DMCA accuracy and perjury statement',
    category: 'legal',
    content: `**Statement of Accuracy:**
I swear, under penalty of perjury, that the information in this notification is accurate and that I am the copyright owner or am authorized to act on behalf of the owner of an exclusive right that is allegedly infringed.`
  },
  {
    title: 'Contact Information',
    description: 'Complete contact details section',
    category: 'contact',
    content: `**Contact Information:**
Name: {{contact_name}}
Title: {{contact_title}}
Organization: {{organization}}
Email: {{contact_email}}
Phone: {{contact_phone}}
Address: {{contact_address}}`
  },
  {
    title: 'Professional Closing',
    description: 'Formal closing with signature',
    category: 'closing',
    content: `I request that you remove or disable access to this infringing material as soon as possible. Please confirm the removal by replying to this email.

Thank you for your prompt attention to this matter.

Sincerely,
{{signature}}
{{current_date}}`
  }
];

const COMMON_VARIABLES: VariableInsertion[] = [
  { name: 'platform_name', label: 'Platform Name', type: 'text', required: true, placeholder: 'e.g., YouTube, Facebook' },
  { name: 'infringing_url', label: 'Infringing URL', type: 'url', required: true },
  { name: 'work_title', label: 'Work Title', type: 'text', required: true },
  { name: 'copyright_owner', label: 'Copyright Owner', type: 'text', required: true },
  { name: 'contact_name', label: 'Contact Name', type: 'text', required: true },
  { name: 'contact_email', label: 'Contact Email', type: 'email', required: true },
  { name: 'signature', label: 'Digital Signature', type: 'text', required: true },
  { name: 'current_date', label: 'Current Date', type: 'date', required: true }
];

export const StepContentCreation: React.FC<StepContentCreationProps> = ({
  formData,
  errors,
  onChange
}) => {
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [showVariableInserter, setShowVariableInserter] = useState(false);
  const [selectedSuggestion, setSelectedSuggestion] = useState<ContentSuggestion | null>(null);
  const [newVariable, setNewVariable] = useState<VariableInsertion>({
    name: '',
    label: '',
    type: 'text',
    required: false
  });
  const [extractingVariables, setExtractingVariables] = useState(false);
  const [insertPosition, setInsertPosition] = useState<'cursor' | 'end'>('cursor');
  
  const editorRef = useRef<any>(null);
  const toast = useRef<Toast>(null);

  const handleContentChange = (value: string) => {
    onChange({ content: value || '' });
  };

  // Auto-extract variables from content
  const handleExtractVariables = async () => {
    if (!formData.content.trim()) {
      toast.current?.show({
        severity: 'warn',
        summary: 'No Content',
        detail: 'Please add some content first before extracting variables'
      });
      return;
    }

    setExtractingVariables(true);
    try {
      const response = await templatesApi.extractVariables(formData.content);
      const extractedVariables = response.data;
      
      // Merge with existing variables, avoiding duplicates
      const existingNames = new Set(formData.variables.map(v => v.name));
      const newVariables = extractedVariables.filter((v: TemplateVariable) => !existingNames.has(v.name));
      
      if (newVariables.length > 0) {
        onChange({ variables: [...formData.variables, ...newVariables] });
        
        toast.current?.show({
          severity: 'success',
          summary: 'Variables Extracted',
          detail: `Found ${newVariables.length} new variables in your content`
        });
      } else {
        toast.current?.show({
          severity: 'info',
          summary: 'No New Variables',
          detail: 'All variables in your content have already been defined'
        });
      }
    } catch (error) {
      console.error('Error extracting variables:', error);
      toast.current?.show({
        severity: 'error',
        summary: 'Extraction Error',
        detail: 'Failed to extract variables from content'
      });
    } finally {
      setExtractingVariables(false);
    }
  };

  // Insert content suggestion
  const insertSuggestion = (suggestion: ContentSuggestion) => {
    const currentContent = formData.content || '';
    const newContent = insertPosition === 'end' 
      ? currentContent + '\n\n' + suggestion.content
      : suggestion.content + '\n\n' + currentContent;
    
    onChange({ content: newContent });
    setShowSuggestions(false);
    
    toast.current?.show({
      severity: 'success',
      summary: 'Content Added',
      detail: `${suggestion.title} has been added to your template`
    });
  };

  // Insert variable
  const insertVariable = (variable: VariableInsertion) => {
    const variableText = `{{${variable.name}}}`;
    const currentContent = formData.content || '';
    
    // Try to insert at cursor position if editor is available
    if (editorRef.current?.getEditor) {
      const editor = editorRef.current.getEditor();
      const selection = editor.getSelection();
      if (selection) {
        editor.insertText(selection.index, variableText);
      } else {
        onChange({ content: currentContent + variableText });
      }
    } else {
      onChange({ content: currentContent + variableText });
    }
    
    // Add variable to form data if it doesn't exist
    const existingVariable = formData.variables.find(v => v.name === variable.name);
    if (!existingVariable) {
      const newVar: TemplateVariable = {
        name: variable.name,
        label: variable.label,
        type: variable.type,
        required: variable.required,
        placeholder: variable.placeholder || '',
        description: '',
        default_value: '',
        options: variable.type === 'select' ? [] : undefined
      };
      onChange({ variables: [...formData.variables, newVar] });
    }
    
    setShowVariableInserter(false);
  };

  // Create custom variable
  const createCustomVariable = () => {
    if (!newVariable.name.trim() || !newVariable.label.trim()) {
      toast.current?.show({
        severity: 'error',
        summary: 'Invalid Variable',
        detail: 'Variable name and label are required'
      });
      return;
    }

    if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(newVariable.name)) {
      toast.current?.show({
        severity: 'error',
        summary: 'Invalid Variable Name',
        detail: 'Variable name must be a valid identifier (letters, numbers, underscores)'
      });
      return;
    }

    insertVariable(newVariable);
    setNewVariable({ name: '', label: '', type: 'text', required: false });
  };

  const suggestionsByCategory = CONTENT_SUGGESTIONS.reduce((acc, suggestion) => {
    if (!acc[suggestion.category]) {
      acc[suggestion.category] = [];
    }
    acc[suggestion.category].push(suggestion);
    return acc;
  }, {} as Record<string, ContentSuggestion[]>);

  return (
    <div className="step-content-creation">
      <Toast ref={toast} />
      
      <div className="step-header mb-4">
        <h4 className="m-0 mb-2">Template Content</h4>
        <p className="text-color-secondary m-0">
          Write your DMCA template content using variables for dynamic content. Use the helpers below for guidance.
        </p>
      </div>

      {/* Content Editor Toolbar */}
      <EnhancedCard className="mb-4">
        <div className="flex flex-wrap justify-content-between align-items-center gap-2">
          <div className="flex flex-wrap gap-2">
            <EnhancedButton
              label="Content Suggestions"
              icon="pi pi-lightbulb"
              size="small"
              variant="outlined"
              onClick={() => setShowSuggestions(true)}
            />
            <EnhancedButton
              label="Insert Variable"
              icon="pi pi-plus"
              size="small"
              variant="outlined"
              onClick={() => setShowVariableInserter(true)}
            />
            <EnhancedButton
              label="Extract Variables"
              icon="pi pi-code"
              size="small"
              variant="outlined"
              onClick={handleExtractVariables}
              loading={extractingVariables}
            />
          </div>
          
          <div className="flex align-items-center gap-2">
            <small className="text-color-secondary">
              Variables: {formData.variables.length}
            </small>
            <Button
              icon="pi pi-question-circle"
              className="p-button-text p-button-sm"
              tooltip="Template Help"
            />
          </div>
        </div>
      </EnhancedCard>

      {/* Main Content Editor */}
      <EnhancedCard className="mb-4">
        <div className="field">
          <label className="block mb-2 font-medium">
            Template Content <span className="text-red-500">*</span>
          </label>
          <Editor
            ref={editorRef}
            value={formData.content}
            onTextChange={(e) => handleContentChange(e.htmlValue || '')}
            style={{ height: '500px' }}
            modules={{
              toolbar: [
                [{ 'header': [1, 2, 3, false] }],
                ['bold', 'italic', 'underline'],
                [{ 'list': 'ordered'}, { 'list': 'bullet' }],
                ['blockquote', 'code-block'],
                ['link'],
                ['clean']
              ]
            }}
            placeholder="Start writing your DMCA template content here. Use {{variable_name}} syntax for dynamic content that users can customize."
          />
          {errors.content && (
            <small className="p-error block mt-1">{errors.content}</small>
          )}
          <div className="flex justify-content-between align-items-center mt-2">
            <small className="text-color-secondary">
              Use {{variable_name}} syntax to insert dynamic content
            </small>
            <small className="text-color-secondary">
              {formData.content.length} characters
            </small>
          </div>
        </div>
      </EnhancedCard>

      {/* Template Syntax Help */}
      <div className="template-syntax-help p-3 bg-blue-50 border-round">
        <div className="flex align-items-start gap-2">
          <i className="pi pi-info-circle text-blue-600 text-xl mt-1" />
          <div>
            <h6 className="m-0 mb-2 text-blue-700">Template Syntax Guide</h6>
            <div className="grid">
              <div className="col-12 md:col-6">
                <ul className="m-0 text-blue-600 text-sm">
                  <li><code>{'{{'}variable_name{'}}'}</code> - Insert variable value</li>
                  <li><code>{'{{'}contact_name{'}}'}</code> - User's contact name</li>
                  <li><code>{'{{'}current_date{'}}'}</code> - Today's date</li>
                </ul>
              </div>
              <div className="col-12 md:col-6">
                <ul className="m-0 text-blue-600 text-sm">
                  <li><strong>Bold text:</strong> Use **bold** or editor toolbar</li>
                  <li><strong>Lists:</strong> Use bullets or numbers from toolbar</li>
                  <li><strong>Links:</strong> Use link button in toolbar</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Content Suggestions Dialog */}
      <Dialog
        header="Content Suggestions"
        visible={showSuggestions}
        style={{ width: '800px' }}
        modal
        onHide={() => setShowSuggestions(false)}
        maximizable
      >
        <div className="content-suggestions">
          <div className="mb-3">
            <div className="flex align-items-center gap-2 mb-2">
              <label>Insert Position:</label>
              <Dropdown
                value={insertPosition}
                onChange={(e) => setInsertPosition(e.value)}
                options={[
                  { label: 'At cursor position', value: 'cursor' },
                  { label: 'At end of content', value: 'end' }
                ]}
                className="w-12rem"
              />
            </div>
          </div>
          
          {Object.entries(suggestionsByCategory).map(([category, suggestions]) => (
            <div key={category} className="mb-4">
              <h6 className="text-capitalize mb-2">{category.replace('_', ' ')} Sections</h6>
              <div className="grid">
                {suggestions.map((suggestion, index) => (
                  <div key={index} className="col-12 md:col-6 mb-3">
                    <Card 
                      className="h-full cursor-pointer suggestion-card"
                      onClick={() => insertSuggestion(suggestion)}
                    >
                      <h6 className="m-0 mb-2">{suggestion.title}</h6>
                      <p className="text-sm text-color-secondary m-0 mb-3">
                        {suggestion.description}
                      </p>
                      <div className="text-xs text-color-secondary font-monospace">
                        {suggestion.content.substring(0, 100)}...
                      </div>
                    </Card>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Dialog>

      {/* Variable Inserter Dialog */}
      <Dialog
        header="Insert Variable"
        visible={showVariableInserter}
        style={{ width: '600px' }}
        modal
        onHide={() => setShowVariableInserter(false)}
      >
        <div className="variable-inserter">
          <h6>Common Variables</h6>
          <div className="grid mb-4">
            {COMMON_VARIABLES.map((variable) => (
              <div key={variable.name} className="col-12 md:col-6 mb-2">
                <Button
                  label={`{{${variable.name}}}`}
                  className="w-full text-left p-button-outlined"
                  onClick={() => insertVariable(variable)}
                />
                <small className="block mt-1 text-color-secondary">
                  {variable.label}
                </small>
              </div>
            ))}
          </div>
          
          <Divider />
          
          <h6>Create Custom Variable</h6>
          <div className="grid">
            <div className="col-12 md:col-6">
              <div className="field">
                <label>Variable Name</label>
                <InputText
                  value={newVariable.name}
                  onChange={(e) => setNewVariable(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="e.g., company_name"
                  className="w-full"
                />
              </div>
            </div>
            <div className="col-12 md:col-6">
              <div className="field">
                <label>Display Label</label>
                <InputText
                  value={newVariable.label}
                  onChange={(e) => setNewVariable(prev => ({ ...prev, label: e.target.value }))}
                  placeholder="e.g., Company Name"
                  className="w-full"
                />
              </div>
            </div>
            <div className="col-12 md:col-6">
              <div className="field">
                <label>Variable Type</label>
                <Dropdown
                  value={newVariable.type}
                  onChange={(e) => setNewVariable(prev => ({ ...prev, type: e.value }))}
                  options={[
                    { label: 'Text', value: 'text' },
                    { label: 'Email', value: 'email' },
                    { label: 'URL', value: 'url' },
                    { label: 'Date', value: 'date' },
                    { label: 'Number', value: 'number' },
                    { label: 'Text Area', value: 'textarea' },
                    { label: 'Select', value: 'select' }
                  ]}
                  className="w-full"
                />
              </div>
            </div>
            <div className="col-12 md:col-6 flex align-items-end">
              <EnhancedButton
                label="Insert Variable"
                icon="pi pi-plus"
                onClick={createCustomVariable}
                className="w-full"
                disabled={!newVariable.name.trim() || !newVariable.label.trim()}
              />
            </div>
          </div>
        </div>
      </Dialog>
    </div>
  );
};

export default StepContentCreation;