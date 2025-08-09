// DMCA Template Validation and Legal Compliance Service

import { 
  IDMCATemplate, 
  TemplateValidationResult, 
  DMCARequiredElement,
  TemplatePreviewData 
} from '../types/dmca';

// 17 U.S.C. § 512(c)(3) Required Elements
const DMCA_REQUIRED_ELEMENTS = [
  {
    element: 'physical_signature',
    description: 'Physical or electronic signature of copyright owner or authorized agent',
    legalRequirement: '17 U.S.C. § 512(c)(3)(A)(i)',
    patterns: [
      /signature/i,
      /signed/i,
      /\{\{.*signature.*\}\}/i
    ]
  },
  {
    element: 'identification_of_work',
    description: 'Identification of the copyrighted work claimed to have been infringed',
    legalRequirement: '17 U.S.C. § 512(c)(3)(A)(ii)',
    patterns: [
      /copyright.*work/i,
      /copyrighted.*material/i,
      /\{\{.*work.*description.*\}\}/i,
      /original.*work/i
    ]
  },
  {
    element: 'identification_of_material',
    description: 'Identification of the infringing material and location',
    legalRequirement: '17 U.S.C. § 512(c)(3)(A)(iii)',
    patterns: [
      /infringing.*material/i,
      /infringing.*url/i,
      /\{\{.*url.*\}\}/i,
      /location.*material/i
    ]
  },
  {
    element: 'contact_information',
    description: 'Contact information for the complaining party',
    legalRequirement: '17 U.S.C. § 512(c)(3)(A)(iv)',
    patterns: [
      /contact.*information/i,
      /email.*address/i,
      /\{\{.*email.*\}\}/i,
      /phone.*number/i,
      /mailing.*address/i
    ]
  },
  {
    element: 'good_faith_statement',
    description: 'Statement of good faith belief that use is not authorized',
    legalRequirement: '17 U.S.C. § 512(c)(3)(A)(v)',
    patterns: [
      /good.*faith.*belief/i,
      /not.*authorized/i,
      /without.*permission/i,
      /believe.*in.*good.*faith/i
    ]
  },
  {
    element: 'accuracy_statement',
    description: 'Statement that information is accurate and under penalty of perjury',
    legalRequirement: '17 U.S.C. § 512(c)(3)(A)(vi)',
    patterns: [
      /penalty.*of.*perjury/i,
      /information.*accurate/i,
      /swear.*under.*penalty/i,
      /perjury/i,
      /accurate.*complete/i
    ]
  }
];

// Platform-specific validation rules
const PLATFORM_REQUIREMENTS = {
  'Instagram': {
    maxLength: 2000,
    requiredFields: ['infringing_url', 'copyright_work'],
    specificRequirements: ['Must include Instagram post URL', 'Requires image description']
  },
  'TikTok': {
    maxLength: 1500,
    requiredFields: ['video_url', 'timestamp'],
    specificRequirements: ['Must include TikTok video URL', 'Timestamp of infringement required']
  },
  'YouTube': {
    maxLength: 4000,
    requiredFields: ['video_url', 'timestamp_range'],
    specificRequirements: ['YouTube video URL required', 'Specific time range needed']
  },
  'OnlyFans': {
    maxLength: 3000,
    requiredFields: ['profile_url', 'content_description'],
    specificRequirements: ['Profile URL required', 'Detailed content description needed']
  },
  'Google': {
    maxLength: 10000,
    requiredFields: ['search_terms', 'infringing_urls'],
    specificRequirements: ['Specific search terms', 'Multiple URL format supported']
  }
};

/**
 * Validates a DMCA template for legal compliance
 */
export const validateDMCATemplate = (template: IDMCATemplate): TemplateValidationResult => {
  const errors: string[] = [];
  const warnings: string[] = [];
  const requiredElements: DMCARequiredElement[] = [];

  // Basic validation
  if (!template.title || template.title.trim().length === 0) {
    errors.push('Template title is required');
  }

  if (!template.content || template.content.trim().length === 0) {
    errors.push('Template content is required');
  }

  if (!template.category) {
    errors.push('Template category is required');
  }

  // DMCA Required Elements Validation
  DMCA_REQUIRED_ELEMENTS.forEach(element => {
    const isPresent = element.patterns.some(pattern => 
      pattern.test(template.content)
    );

    requiredElements.push({
      element: element.element,
      present: isPresent,
      description: element.description,
      legalRequirement: element.legalRequirement
    });

    if (!isPresent) {
      errors.push(`Missing required element: ${element.description}`);
    }
  });

  // Platform-specific validation
  if (template.platforms) {
    template.platforms.forEach(platform => {
      const platformReqs = PLATFORM_REQUIREMENTS[platform as keyof typeof PLATFORM_REQUIREMENTS];
      if (platformReqs) {
        // Check length restrictions
        const plainTextContent = template.content.replace(/<[^>]*>/g, '');
        if (plainTextContent.length > platformReqs.maxLength) {
          warnings.push(`Template may be too long for ${platform} (${plainTextContent.length}/${platformReqs.maxLength} chars)`);
        }

        // Check required fields
        platformReqs.requiredFields.forEach(field => {
          if (!template.content.includes(`{{${field}}}`)) {
            warnings.push(`Missing platform-specific variable for ${platform}: {{${field}}}`);
          }
        });
      }
    });
  }

  // Legal language validation
  const legalPhrases = [
    'under penalty of perjury',
    'good faith belief',
    'authorized by law',
    'copyright owner',
    'exclusive right'
  ];

  let legalPhraseCount = 0;
  legalPhrases.forEach(phrase => {
    if (template.content.toLowerCase().includes(phrase.toLowerCase())) {
      legalPhraseCount++;
    }
  });

  if (legalPhraseCount < 3) {
    warnings.push('Template may lack sufficient legal terminology');
  }

  // Calculate compliance score
  const totalRequired = DMCA_REQUIRED_ELEMENTS.length;
  const presentRequired = requiredElements.filter(el => el.present).length;
  const complianceScore = Math.round((presentRequired / totalRequired) * 100);

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
    complianceScore,
    requiredElements
  };
};

/**
 * Generates a preview of the template with sample data
 */
export const generateTemplatePreview = (
  template: IDMCATemplate, 
  previewData: TemplatePreviewData
): string => {
  let previewContent = template.content;

  // Replace common template variables
  const variableMap = {
    '{{creator_name}}': previewData.creatorName,
    '{{infringing_url}}': previewData.infringingUrl,
    '{{platform}}': previewData.platform,
    '{{work_description}}': previewData.workDescription,
    '{{contact_email}}': previewData.contactEmail,
    '{{copyright_url}}': previewData.copyrightUrl,
    '{{date_of_infringement}}': previewData.dateOfInfringement,
    '{{current_date}}': new Date().toLocaleDateString(),
    '{{signature}}': `[Digital Signature: ${previewData.creatorName}]`
  };

  Object.entries(variableMap).forEach(([variable, value]) => {
    previewContent = previewContent.replace(new RegExp(variable, 'g'), value);
  });

  return previewContent;
};

/**
 * Validates template variables and placeholders
 */
export const validateTemplateVariables = (template: IDMCATemplate): string[] => {
  const errors: string[] = [];
  const variablePattern = /\{\{([^}]+)\}\}/g;
  const matches = template.content.match(variablePattern);

  if (matches) {
    matches.forEach(match => {
      const variableName = match.replace(/[{}]/g, '');
      
      // Check for common typos in variable names
      const commonVariables = [
        'creator_name', 'infringing_url', 'platform', 
        'work_description', 'contact_email', 'copyright_url',
        'date_of_infringement', 'current_date', 'signature'
      ];

      if (!commonVariables.includes(variableName)) {
        errors.push(`Unknown or potentially misspelled variable: ${match}`);
      }
    });
  }

  return errors;
};

/**
 * Checks template for jurisdiction-specific requirements
 */
export const validateJurisdictionCompliance = (
  template: IDMCATemplate, 
  jurisdiction: string
): string[] => {
  const issues: string[] = [];

  switch (jurisdiction.toLowerCase()) {
    case 'eu':
    case 'gdpr':
      if (!template.content.includes('data protection') && 
          !template.content.includes('privacy rights')) {
        issues.push('EU/GDPR templates should reference data protection rights');
      }
      break;
    
    case 'uk':
      if (!template.content.includes('Copyright, Designs and Patents Act')) {
        issues.push('UK templates should reference relevant UK copyright law');
      }
      break;
    
    case 'canada':
      if (!template.content.includes('Copyright Act')) {
        issues.push('Canadian templates should reference the Copyright Act');
      }
      break;
    
    case 'australia':
      if (!template.content.includes('Copyright Act 1968')) {
        issues.push('Australian templates should reference Copyright Act 1968');
      }
      break;
  }

  return issues;
};

/**
 * Estimates template effectiveness based on content analysis
 */
export const analyzeTemplateEffectiveness = (template: IDMCATemplate): {
  score: number;
  strengths: string[];
  improvements: string[];
} => {
  const strengths: string[] = [];
  const improvements: string[] = [];
  let score = 50; // Base score

  // Check for professional tone
  if (template.content.includes('respectfully') || template.content.includes('kindly')) {
    strengths.push('Professional and respectful tone');
    score += 10;
  } else {
    improvements.push('Consider adding more courteous language');
  }

  // Check for specific details
  if (template.content.includes('specific') || template.content.includes('detailed')) {
    strengths.push('Requests specific information');
    score += 10;
  } else {
    improvements.push('Request more specific details about infringement');
  }

  // Check for legal completeness
  const legalPhrases = ['under penalty of perjury', 'good faith belief', 'exclusive right'];
  const legalCount = legalPhrases.filter(phrase => 
    template.content.toLowerCase().includes(phrase.toLowerCase())
  ).length;

  if (legalCount >= 2) {
    strengths.push('Contains essential legal language');
    score += 15;
  } else {
    improvements.push('Add more required legal terminology');
  }

  // Check length appropriateness
  const wordCount = template.content.split(' ').length;
  if (wordCount >= 100 && wordCount <= 500) {
    strengths.push('Appropriate length for readability');
    score += 10;
  } else if (wordCount < 100) {
    improvements.push('Template may be too brief');
  } else {
    improvements.push('Template may be too lengthy');
  }

  return {
    score: Math.min(100, Math.max(0, score)),
    strengths,
    improvements
  };
};