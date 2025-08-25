import React, { useState } from 'react';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { Dropdown } from 'primereact/dropdown';
import { Tag } from 'primereact/tag';
import { Divider } from 'primereact/divider';
import { EnhancedCard } from '../../common/EnhancedCard';
import { 
  DEFAULT_CATEGORIES, 
  JURISDICTIONS,
  SUPPORTED_LANGUAGES,
  TemplateVariable
} from '../../../types/templates';
import { WizardFormData, TemplateStarter } from '../TemplateCreationWizard';

interface StepTypeSelectionProps {
  formData: WizardFormData;
  errors: Record<string, string>;
  onChange: (updates: Partial<WizardFormData>) => void;
}

// Template starters for common DMCA scenarios
const TEMPLATE_STARTERS: TemplateStarter[] = [
  {
    id: 'general-dmca',
    name: 'General DMCA Takedown',
    description: 'Standard DMCA takedown notice for most copyright infringement cases',
    category: 'General DMCA',
    icon: 'pi pi-file-o',
    jurisdiction: 'US',
    language: 'en',
    tags: ['standard', 'copyright', 'takedown'],
    content: `Dear {{platform_name}} Team,

I am writing to notify you of copyright infringement occurring on your platform at the following URL(s):

**Infringing Content:**
- {{infringing_url}}

**Original Work:**
- Title: {{work_title}}
- Copyright Owner: {{copyright_owner}}
- Original Location: {{original_url}}

**Good Faith Statement:**
I have a good faith belief that the use of the copyrighted material described above is not authorized by the copyright owner, its agent, or the law.

**Accuracy Statement:**
I swear, under penalty of perjury, that the information in this notification is accurate and that I am the copyright owner or am authorized to act on behalf of the owner of an exclusive right that is allegedly infringed.

**Contact Information:**
- Name: {{contact_name}}
- Email: {{contact_email}}
- Phone: {{contact_phone}}

Please remove or disable access to this infringing material as soon as possible.

Sincerely,
{{signature}}`,
    variables: [
      { name: 'platform_name', label: 'Platform Name', type: 'text', required: true, placeholder: 'e.g., YouTube, Facebook' },
      { name: 'infringing_url', label: 'Infringing URL', type: 'url', required: true, placeholder: 'URL of the infringing content' },
      { name: 'work_title', label: 'Work Title', type: 'text', required: true, placeholder: 'Title of your copyrighted work' },
      { name: 'copyright_owner', label: 'Copyright Owner', type: 'text', required: true, placeholder: 'Name of copyright owner' },
      { name: 'original_url', label: 'Original URL', type: 'url', required: false, placeholder: 'URL of original work (optional)' },
      { name: 'contact_name', label: 'Contact Name', type: 'text', required: true, placeholder: 'Your full name' },
      { name: 'contact_email', label: 'Contact Email', type: 'email', required: true, placeholder: 'Your email address' },
      { name: 'contact_phone', label: 'Contact Phone', type: 'text', required: false, placeholder: 'Your phone number (optional)' },
      { name: 'signature', label: 'Digital Signature', type: 'text', required: true, placeholder: 'Your name for signature' }
    ]
  },
  {
    id: 'social-media-dmca',
    name: 'Social Media DMCA',
    description: 'Optimized for social media platforms like Facebook, Instagram, Twitter',
    category: 'Social Media',
    icon: 'pi pi-share-alt',
    jurisdiction: 'US',
    language: 'en',
    tags: ['social-media', 'facebook', 'instagram', 'twitter'],
    content: `Subject: DMCA Takedown Notice - Copyright Infringement

Dear {{platform_name}} Copyright Team,

I am submitting this DMCA takedown notice regarding unauthorized use of my copyrighted content on your platform.

**Infringing Content Details:**
- Post/Content URL: {{infringing_url}}
- Account: {{infringing_account}}
- Date Posted: {{date_posted}}

**Original Copyrighted Work:**
- Title/Description: {{work_title}}
- Copyright Owner: {{copyright_owner}}
- Publication Date: {{publication_date}}
- Original Source: {{original_url}}

**Statement of Good Faith:**
I have a good faith belief that the disputed use is not authorized by the copyright owner, its agent, or the law.

**Statement of Accuracy:**
Under penalty of perjury, I certify that this notification is accurate and that I am authorized to act on behalf of the copyright owner.

**Requested Action:**
Please remove or disable access to the infringing content immediately.

**Contact Information:**
{{contact_name}}
{{contact_email}}
{{contact_address}}

Digital Signature: {{signature}}
Date: {{current_date}}`,
    variables: [
      { name: 'platform_name', label: 'Social Media Platform', type: 'select', required: true, options: ['Facebook', 'Instagram', 'Twitter', 'TikTok', 'LinkedIn', 'Other'] },
      { name: 'infringing_url', label: 'Infringing Post URL', type: 'url', required: true, placeholder: 'Direct link to the infringing post' },
      { name: 'infringing_account', label: 'Infringing Account', type: 'text', required: true, placeholder: 'Username or account name' },
      { name: 'date_posted', label: 'Date Posted', type: 'date', required: false },
      { name: 'work_title', label: 'Work Title/Description', type: 'text', required: true, placeholder: 'Description of your copyrighted work' },
      { name: 'copyright_owner', label: 'Copyright Owner', type: 'text', required: true, placeholder: 'Name of copyright owner' },
      { name: 'publication_date', label: 'Original Publication Date', type: 'date', required: false },
      { name: 'original_url', label: 'Original Source URL', type: 'url', required: false, placeholder: 'Where your original work was published' },
      { name: 'contact_name', label: 'Your Full Name', type: 'text', required: true },
      { name: 'contact_email', label: 'Email Address', type: 'email', required: true },
      { name: 'contact_address', label: 'Mailing Address', type: 'textarea', required: true, placeholder: 'Your complete mailing address' },
      { name: 'signature', label: 'Digital Signature', type: 'text', required: true, placeholder: 'Type your name' },
      { name: 'current_date', label: 'Current Date', type: 'date', required: true, default_value: new Date().toISOString().split('T')[0] }
    ]
  },
  {
    id: 'search-engine-dmca',
    name: 'Search Engine DMCA',
    description: 'For removing infringing content from search results (Google, Bing, etc.)',
    category: 'Search Engines',
    icon: 'pi pi-search',
    jurisdiction: 'US',
    language: 'en',
    tags: ['search-engine', 'google', 'bing', 'results'],
    content: `Subject: DMCA Copyright Infringement Notice - Search Results Removal

Dear {{search_engine}} Legal Team,

I am requesting the removal of search results that link to copyright-infringing content under the Digital Millennium Copyright Act (DMCA).

**Search Results to Remove:**
{{#each infringing_results}}
- Search Query: "{{search_query}}"
- Infringing URL: {{url}}
- Result Title: {{title}}
{{/each}}

**Copyrighted Work Information:**
- Work Title: {{work_title}}
- Copyright Owner: {{copyright_owner}}
- Work Description: {{work_description}}
- Original Publication: {{original_url}}

**Statement of Good Faith:**
I have a good faith belief that the use of the copyrighted material in the manner complained of is not authorized by the copyright owner, its agent, or the law.

**Accuracy Statement:**
I swear, under penalty of perjury, that the information in this notification is accurate and that I am the copyright owner or authorized to act on behalf of the copyright owner.

**Contact Information:**
Name: {{contact_name}}
Title: {{contact_title}}
Organization: {{organization}}
Email: {{contact_email}}
Phone: {{contact_phone}}
Address: {{contact_address}}

Please remove these search results from your index at your earliest convenience.

Electronically signed,
{{signature}}
{{current_date}}`,
    variables: [
      { name: 'search_engine', label: 'Search Engine', type: 'select', required: true, options: ['Google', 'Bing', 'Yahoo', 'DuckDuckGo', 'Other'] },
      { name: 'search_query', label: 'Search Query', type: 'text', required: true, placeholder: 'The search terms used' },
      { name: 'work_title', label: 'Copyrighted Work Title', type: 'text', required: true },
      { name: 'copyright_owner', label: 'Copyright Owner', type: 'text', required: true },
      { name: 'work_description', label: 'Work Description', type: 'textarea', required: true, placeholder: 'Brief description of the copyrighted work' },
      { name: 'original_url', label: 'Original Work URL', type: 'url', required: false, placeholder: 'Official source of your work' },
      { name: 'contact_name', label: 'Contact Name', type: 'text', required: true },
      { name: 'contact_title', label: 'Your Title', type: 'text', required: false, placeholder: 'e.g., Copyright Agent, Artist, etc.' },
      { name: 'organization', label: 'Organization', type: 'text', required: false, placeholder: 'Company or organization name' },
      { name: 'contact_email', label: 'Email Address', type: 'email', required: true },
      { name: 'contact_phone', label: 'Phone Number', type: 'text', required: false },
      { name: 'contact_address', label: 'Mailing Address', type: 'textarea', required: true },
      { name: 'signature', label: 'Digital Signature', type: 'text', required: true },
      { name: 'current_date', label: 'Date', type: 'date', required: true, default_value: new Date().toISOString().split('T')[0] }
    ]
  },
  {
    id: 'hosting-provider-dmca',
    name: 'Hosting Provider DMCA',
    description: 'For websites hosted on platforms like GoDaddy, Cloudflare, AWS',
    category: 'Hosting Providers',
    icon: 'pi pi-server',
    jurisdiction: 'US',
    language: 'en',
    tags: ['hosting', 'web-hosting', 'server'],
    content: `Subject: DMCA Takedown Notice - Hosted Website Copyright Infringement

Dear {{hosting_provider}} Abuse Team,

I am writing to report copyright infringement on a website hosted by your service under the provisions of the Digital Millennium Copyright Act (DMCA).

**Website Details:**
- Infringing Website: {{infringing_domain}}
- Hosting Account: {{hosting_account}} (if known)
- Specific Infringing Pages: {{infringing_pages}}

**Copyrighted Material:**
- Work Title: {{work_title}}
- Copyright Owner: {{copyright_owner}}
- Copyright Registration: {{copyright_registration}} (if applicable)
- Original Source: {{original_source}}

**Description of Infringement:**
{{infringement_description}}

**Good Faith Statement:**
I have a good faith belief that the use of the copyrighted material described above on the infringing website is not authorized by the copyright owner, its agent, or the law.

**Perjury Statement:**
I swear, under penalty of perjury, that the information in this notification is accurate and that I am the copyright owner or am authorized to act on behalf of the owner.

**Requested Action:**
Please forward this notice to your customer and request immediate removal of the infringing content. If the content is not removed promptly, please consider suspending the hosting account.

**Contact Information:**
{{contact_name}}
{{contact_title}}
{{contact_email}}
{{contact_phone}}
{{contact_address}}

Electronic Signature: {{signature}}
Date: {{current_date}}

Note: This notice complies with the requirements of 17 U.S.C. § 512(c)(3)(A).`,
    variables: [
      { name: 'hosting_provider', label: 'Hosting Provider', type: 'text', required: true, placeholder: 'e.g., GoDaddy, Cloudflare, AWS' },
      { name: 'infringing_domain', label: 'Infringing Domain', type: 'url', required: true, placeholder: 'Full domain/website URL' },
      { name: 'hosting_account', label: 'Hosting Account Info', type: 'text', required: false, placeholder: 'Account info if known' },
      { name: 'infringing_pages', label: 'Specific Infringing Pages', type: 'textarea', required: true, placeholder: 'List specific URLs with infringing content' },
      { name: 'work_title', label: 'Copyrighted Work', type: 'text', required: true },
      { name: 'copyright_owner', label: 'Copyright Owner', type: 'text', required: true },
      { name: 'copyright_registration', label: 'Copyright Registration', type: 'text', required: false, placeholder: 'Registration number if available' },
      { name: 'original_source', label: 'Original Source', type: 'url', required: false },
      { name: 'infringement_description', label: 'Infringement Description', type: 'textarea', required: true, placeholder: 'Detailed description of how your work is being infringed' },
      { name: 'contact_name', label: 'Contact Name', type: 'text', required: true },
      { name: 'contact_title', label: 'Your Title', type: 'text', required: false },
      { name: 'contact_email', label: 'Email Address', type: 'email', required: true },
      { name: 'contact_phone', label: 'Phone Number', type: 'text', required: false },
      { name: 'contact_address', label: 'Mailing Address', type: 'textarea', required: true },
      { name: 'signature', label: 'Digital Signature', type: 'text', required: true },
      { name: 'current_date', label: 'Date', type: 'date', required: true, default_value: new Date().toISOString().split('T')[0] }
    ]
  }
];

export const StepTypeSelection: React.FC<StepTypeSelectionProps> = ({
  formData,
  errors,
  onChange
}) => {
  const [selectedCategory, setSelectedCategory] = useState(formData.category || '');
  const [showAllStarters, setShowAllStarters] = useState(false);

  // Get template starters for selected category
  const getFilteredStarters = () => {
    if (!selectedCategory) return TEMPLATE_STARTERS.slice(0, 4);
    
    const filtered = TEMPLATE_STARTERS.filter(starter => 
      starter.category === selectedCategory
    );
    
    if (filtered.length === 0) {
      return TEMPLATE_STARTERS.slice(0, 4);
    }
    
    return showAllStarters ? filtered : filtered.slice(0, 4);
  };

  const handleCategoryChange = (category: string) => {
    setSelectedCategory(category);
    onChange({ category });
  };

  const handleStarterSelect = (starter: TemplateStarter) => {
    onChange({
      selectedStarter: starter,
      category: starter.category,
      content: starter.content,
      variables: starter.variables,
      tags: starter.tags,
      jurisdiction: starter.jurisdiction,
      language: starter.language
    });
  };

  const handleStartFromScratch = () => {
    if (!selectedCategory) {
      return;
    }
    
    onChange({
      selectedStarter: undefined,
      category: selectedCategory,
      content: '',
      variables: [],
      tags: [],
      jurisdiction: 'US',
      language: 'en'
    });
  };

  return (
    <div className="step-type-selection">
      <div className="step-header mb-4">
        <h4 className="m-0 mb-2">Choose Template Type</h4>
        <p className="text-color-secondary m-0">
          Select a category and choose from pre-built templates or start from scratch.
        </p>
      </div>

      {/* Category Selection */}
      <EnhancedCard className="mb-4">
        <h5>Template Category</h5>
        <div className="field">
          <Dropdown
            value={selectedCategory}
            onChange={(e) => handleCategoryChange(e.value)}
            options={DEFAULT_CATEGORIES.map(cat => ({ label: cat, value: cat }))}
            placeholder="Select a category for your template"
            className={`w-full ${errors.category ? 'p-invalid' : ''}`}
            showClear
            filter
          />
          {errors.category && (
            <small className="p-error block mt-1">{errors.category}</small>
          )}
          <small className="block mt-2 text-color-secondary">
            Choose the category that best fits your DMCA use case. This helps us suggest the right template starters.
          </small>
        </div>
      </EnhancedCard>

      {/* Template Starters */}
      {selectedCategory && (
        <div className="template-starters">
          <div className="flex justify-content-between align-items-center mb-3">
            <h5 className="m-0">Template Starters</h5>
            <Button
              label="Start from Scratch"
              icon="pi pi-plus"
              className="p-button-outlined p-button-sm"
              onClick={handleStartFromScratch}
            />
          </div>
          
          <div className="grid">
            {getFilteredStarters().map((starter) => (
              <div key={starter.id} className="col-12 md:col-6">
                <Card 
                  className={`h-full cursor-pointer starter-card ${formData.selectedStarter?.id === starter.id ? 'selected' : ''}`}
                  onClick={() => handleStarterSelect(starter)}
                >
                  <div className="flex align-items-start gap-3">
                    <i className={`${starter.icon} text-primary text-2xl`} />
                    <div className="flex-1">
                      <h6 className="m-0 mb-2">{starter.name}</h6>
                      <p className="text-sm text-color-secondary m-0 mb-3">
                        {starter.description}
                      </p>
                      <div className="flex flex-wrap gap-1 mb-2">
                        {starter.tags.slice(0, 3).map((tag, index) => (
                          <Tag 
                            key={index} 
                            value={tag} 
                            severity="info" 
                            className="text-xs"
                          />
                        ))}
                        {starter.tags.length > 3 && (
                          <Tag 
                            value={`+${starter.tags.length - 3} more`} 
                            severity="secondary" 
                            className="text-xs"
                          />
                        )}
                      </div>
                      <small className="text-color-secondary">
                        {starter.variables.length} variables • {starter.jurisdiction} jurisdiction
                      </small>
                    </div>
                    {formData.selectedStarter?.id === starter.id && (
                      <i className="pi pi-check-circle text-primary text-xl" />
                    )}
                  </div>
                </Card>
              </div>
            ))}
          </div>

          {TEMPLATE_STARTERS.filter(s => s.category === selectedCategory).length > 4 && !showAllStarters && (
            <div className="text-center mt-3">
              <Button
                label={`Show ${TEMPLATE_STARTERS.filter(s => s.category === selectedCategory).length - 4} More Templates`}
                className="p-button-text"
                onClick={() => setShowAllStarters(true)}
              />
            </div>
          )}
        </div>
      )}

      {/* Selected Starter Preview */}
      {formData.selectedStarter && (
        <div className="selected-starter-preview mt-4">
          <Divider />
          <div className="flex align-items-center gap-3 mb-3">
            <i className="pi pi-check-circle text-primary text-xl" />
            <div>
              <h6 className="m-0">Selected: {formData.selectedStarter.name}</h6>
              <small className="text-color-secondary">
                This template includes {formData.selectedStarter.variables.length} pre-configured variables
              </small>
            </div>
          </div>
          
          <EnhancedCard className="starter-preview-content">
            <h6>Template Preview</h6>
            <div className="template-content-preview">
              {formData.selectedStarter.content.split('\n').slice(0, 8).map((line, index) => (
                <p key={index} className="m-0 text-sm" style={{ 
                  fontFamily: 'monospace',
                  color: line.includes('{{') ? 'var(--primary-color)' : 'var(--text-color)',
                  fontWeight: line.includes('{{') ? 'bold' : 'normal'
                }}>
                  {line || ' '}
                </p>
              ))}
              {formData.selectedStarter.content.split('\n').length > 8 && (
                <p className="m-0 text-sm text-color-secondary mt-2">
                  ... and {formData.selectedStarter.content.split('\n').length - 8} more lines
                </p>
              )}
            </div>
          </EnhancedCard>
        </div>
      )}

      {/* Help Text */}
      <div className="help-section mt-4 p-3 bg-blue-50 border-round">
        <div className="flex align-items-start gap-2">
          <i className="pi pi-info-circle text-blue-600 mt-1" />
          <div>
            <h6 className="m-0 mb-2 text-blue-700">Template Starters</h6>
            <ul className="m-0 text-blue-600 text-sm">
              <li>Choose a pre-built template to get started quickly with proven language</li>
              <li>All templates include commonly used variables and proper legal formatting</li>
              <li>You can customize everything in the following steps</li>
              <li>Starting from scratch gives you complete control over content and structure</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StepTypeSelection;