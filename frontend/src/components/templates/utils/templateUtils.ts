import { DMCATemplate } from '../../../types/templates';
import { EnhancedDMCATemplate, TemplateSearchFilter, AdvancedSearchQuery } from '../types/enhanced';

/**
 * Utility functions for template operations
 */

// Search and filtering utilities
export const createSearchFilter = (
  field: keyof DMCATemplate | 'global',
  operator: 'contains' | 'equals' | 'starts_with' | 'ends_with' | 'regex',
  value: string,
  negated = false
): TemplateSearchFilter => ({
  field,
  operator,
  value,
  negated
});

export const parseAdvancedSearchQuery = (query: string): AdvancedSearchQuery => {
  const filters: TemplateSearchFilter[] = [];
  let operator: 'AND' | 'OR' = 'AND';
  
  // Simple parsing logic - can be enhanced with more sophisticated parsing
  const tokens = query.split(/\s+/);
  let currentField: keyof DMCATemplate | 'global' = 'global';
  let currentOperator: 'contains' | 'equals' | 'starts_with' | 'ends_with' | 'regex' = 'contains';
  let negated = false;
  
  for (let i = 0; i < tokens.length; i++) {
    const token = tokens[i];
    
    if (token.toLowerCase() === 'and') {
      operator = 'AND';
      continue;
    }
    
    if (token.toLowerCase() === 'or') {
      operator = 'OR';
      continue;
    }
    
    if (token.toLowerCase() === 'not') {
      negated = true;
      continue;
    }
    
    // Field:value syntax
    if (token.includes(':')) {
      const [field, value] = token.split(':', 2);
      filters.push(createSearchFilter(
        field as keyof DMCATemplate,
        'contains',
        value,
        negated
      ));
      negated = false;
      continue;
    }
    
    // Quoted exact match
    if (token.startsWith('"') && token.endsWith('"')) {
      filters.push(createSearchFilter(
        'global',
        'equals',
        token.slice(1, -1),
        negated
      ));
      negated = false;
      continue;
    }
    
    // Regular search term
    filters.push(createSearchFilter(
      'global',
      'contains',
      token,
      negated
    ));
    negated = false;
  }
  
  return { filters, operator };
};

export const applySearchFilters = (
  templates: DMCATemplate[],
  filters: TemplateSearchFilter[],
  operator: 'AND' | 'OR' = 'AND'
): DMCATemplate[] => {
  if (filters.length === 0) return templates;
  
  return templates.filter(template => {
    const results = filters.map(filter => {
      const { field, operator: filterOp, value, negated } = filter;
      let fieldValue: string;
      
      if (field === 'global') {
        fieldValue = Object.values(template).join(' ').toLowerCase();
      } else {
        fieldValue = String(template[field] || '').toLowerCase();
      }
      
      const searchValue = value.toLowerCase();
      let matches = false;
      
      switch (filterOp) {
        case 'contains':
          matches = fieldValue.includes(searchValue);
          break;
        case 'equals':
          matches = fieldValue === searchValue;
          break;
        case 'starts_with':
          matches = fieldValue.startsWith(searchValue);
          break;
        case 'ends_with':
          matches = fieldValue.endsWith(searchValue);
          break;
        case 'regex':
          try {
            matches = new RegExp(searchValue, 'i').test(fieldValue);
          } catch {
            matches = fieldValue.includes(searchValue);
          }
          break;
      }
      
      return negated ? !matches : matches;
    });
    
    return operator === 'AND' 
      ? results.every(result => result)
      : results.some(result => result);
  });
};

// Template enhancement utilities
export const enhanceTemplate = (
  template: DMCATemplate,
  metadata?: {
    favorites: string[];
    recentlyViewed: string[];
    usageStats?: Record<string, number>;
  }
): EnhancedDMCATemplate => {
  const enhanced: EnhancedDMCATemplate = {
    ...template,
    isFavorite: metadata?.favorites?.includes(template.id) || false,
    isRecentlyViewed: metadata?.recentlyViewed?.includes(template.id) || false,
    usageScore: metadata?.usageStats?.[template.id] || template.usage_count || 0,
    previewContent: template.content ? template.content.substring(0, 200) + '...' : undefined,
    validationStatus: 'valid' // Default - can be enhanced with actual validation
  };
  
  return enhanced;
};

export const enhanceTemplates = (
  templates: DMCATemplate[],
  metadata?: {
    favorites: string[];
    recentlyViewed: string[];
    usageStats?: Record<string, number>;
  }
): EnhancedDMCATemplate[] => {
  return templates.map(template => enhanceTemplate(template, metadata));
};

// Sorting utilities
export const sortTemplates = (
  templates: DMCATemplate[],
  sortBy: string,
  sortOrder: 'asc' | 'desc' = 'asc'
): DMCATemplate[] => {
  return [...templates].sort((a, b) => {
    let aVal, bVal;
    
    switch (sortBy) {
      case 'name':
        aVal = a.name.toLowerCase();
        bVal = b.name.toLowerCase();
        break;
      case 'category':
        aVal = a.category.toLowerCase();
        bVal = b.category.toLowerCase();
        break;
      case 'created_at':
      case 'updated_at':
        aVal = new Date(a[sortBy]).getTime();
        bVal = new Date(b[sortBy]).getTime();
        break;
      case 'usage_count':
        aVal = a.usage_count || 0;
        bVal = b.usage_count || 0;
        break;
      default:
        return 0;
    }
    
    if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1;
    if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1;
    return 0;
  });
};

// Grouping utilities
export const groupTemplatesByCategory = (
  templates: DMCATemplate[]
): Record<string, DMCATemplate[]> => {
  return templates.reduce((groups, template) => {
    const category = template.category || 'Uncategorized';
    if (!groups[category]) {
      groups[category] = [];
    }
    groups[category].push(template);
    return groups;
  }, {} as Record<string, DMCATemplate[]>);
};

export const groupTemplatesByTag = (
  templates: DMCATemplate[]
): Record<string, DMCATemplate[]> => {
  const groups: Record<string, DMCATemplate[]> = {};
  
  templates.forEach(template => {
    if (!template.tags || template.tags.length === 0) {
      const key = 'No Tags';
      if (!groups[key]) groups[key] = [];
      groups[key].push(template);
    } else {
      template.tags.forEach(tag => {
        if (!groups[tag]) groups[tag] = [];
        groups[tag].push(template);
      });
    }
  });
  
  return groups;
};

// Validation utilities
export const validateTemplate = (template: Partial<DMCATemplate>): string[] => {
  const errors: string[] = [];
  
  if (!template.name || template.name.trim().length < 3) {
    errors.push('Template name must be at least 3 characters long');
  }
  
  if (!template.description || template.description.trim().length === 0) {
    errors.push('Description is required');
  }
  
  if (!template.category || template.category.trim().length === 0) {
    errors.push('Category is required');
  }
  
  if (!template.content || template.content.trim().length < 50) {
    errors.push('Template content must be at least 50 characters long');
  }
  
  return errors;
};

export const validateTemplateVariable = (variable: any): string[] => {
  const errors: string[] = [];
  
  if (!variable.name || variable.name.trim().length === 0) {
    errors.push('Variable name is required');
  }
  
  if (!variable.label || variable.label.trim().length === 0) {
    errors.push('Variable label is required');
  }
  
  if (!variable.type) {
    errors.push('Variable type is required');
  }
  
  if (variable.type === 'select' && (!variable.options || variable.options.length === 0)) {
    errors.push('Select variables must have options');
  }
  
  return errors;
};

// Export/Import utilities
export const serializeTemplate = (template: DMCATemplate, format: 'json' | 'csv'): string => {
  switch (format) {
    case 'json':
      return JSON.stringify(template, null, 2);
    case 'csv':
      const csvHeaders = ['id', 'name', 'description', 'category', 'is_active', 'created_at', 'updated_at'];
      const csvValues = csvHeaders.map(header => 
        JSON.stringify(template[header as keyof DMCATemplate] || '')
      );
      return csvValues.join(',');
    default:
      throw new Error(`Unsupported format: ${format}`);
  }
};

export const serializeTemplates = (
  templates: DMCATemplate[], 
  format: 'json' | 'csv'
): string => {
  switch (format) {
    case 'json':
      return JSON.stringify(templates, null, 2);
    case 'csv':
      const headers = ['id', 'name', 'description', 'category', 'is_active', 'created_at', 'updated_at'];
      const csvLines = [
        headers.join(','),
        ...templates.map(template => 
          headers.map(header => 
            JSON.stringify(template[header as keyof DMCATemplate] || '')
          ).join(',')
        )
      ];
      return csvLines.join('\n');
    default:
      throw new Error(`Unsupported format: ${format}`);
  }
};

// Analytics utilities
export const calculateTemplateAnalytics = (templates: DMCATemplate[]) => {
  const totalTemplates = templates.length;
  const activeTemplates = templates.filter(t => t.is_active).length;
  const categoryCounts = templates.reduce((acc, template) => {
    acc[template.category] = (acc[template.category] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);
  
  const tagCounts = templates.reduce((acc, template) => {
    template.tags?.forEach(tag => {
      acc[tag] = (acc[tag] || 0) + 1;
    });
    return acc;
  }, {} as Record<string, number>);
  
  const languageCounts = templates.reduce((acc, template) => {
    const lang = template.language || 'unknown';
    acc[lang] = (acc[lang] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);
  
  return {
    totalTemplates,
    activeTemplates,
    inactiveTemplates: totalTemplates - activeTemplates,
    categoryCounts,
    tagCounts,
    languageCounts,
    mostPopularCategory: Object.keys(categoryCounts).reduce((a, b) => 
      categoryCounts[a] > categoryCounts[b] ? a : b
    ),
    mostPopularTags: Object.keys(tagCounts)
      .sort((a, b) => tagCounts[b] - tagCounts[a])
      .slice(0, 10)
  };
};

// Performance utilities
export const debounce = <T extends (...args: any[]) => any>(
  func: T,
  delay: number
): ((...args: Parameters<T>) => void) => {
  let timeoutId: NodeJS.Timeout;
  
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func(...args), delay);
  };
};

export const throttle = <T extends (...args: any[]) => any>(
  func: T,
  limit: number
): ((...args: Parameters<T>) => void) => {
  let inThrottle: boolean;
  
  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
};

export const memoize = <T extends (...args: any[]) => any>(
  func: T,
  getKey?: (...args: Parameters<T>) => string
): T => {
  const cache = new Map<string, ReturnType<T>>();
  
  return ((...args: Parameters<T>) => {
    const key = getKey ? getKey(...args) : JSON.stringify(args);
    
    if (cache.has(key)) {
      return cache.get(key);
    }
    
    const result = func(...args);
    cache.set(key, result);
    return result;
  }) as T;
};