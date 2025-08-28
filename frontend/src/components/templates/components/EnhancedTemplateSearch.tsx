import React, { useState, useCallback, useRef, useMemo, useId } from 'react';
import { AutoComplete } from 'primereact/autocomplete';
import { Button } from 'primereact/button';
import { Chip } from 'primereact/chip';
import { Dropdown } from 'primereact/dropdown';
import { Badge } from 'primereact/badge';
import { useTemplateLibraryContext } from '../context/TemplateLibraryContext';
import { SearchSuggestion, TemplateSearchProps } from '../types/enhanced';
import { parseAdvancedSearchQuery } from '../utils/templateUtils';
import { useAccessibility } from '../../../hooks/useAccessibility';

interface EnhancedTemplateSearchProps extends Omit<TemplateSearchProps, 'onValueChange'> {
  showAdvancedSearch?: boolean;
  showSearchHistory?: boolean;
  showQuickFilters?: boolean;
  onAdvancedSearchToggle?: (enabled: boolean) => void;
  className?: string;
}

const EnhancedTemplateSearch: React.FC<EnhancedTemplateSearchProps> = ({
  value,
  suggestions = [],
  showHistory = true,
  showSuggestions = true,
  showAdvancedSearch = false,
  showSearchHistory = true,
  showQuickFilters = true,
  placeholder = "Search templates by name, category, tags...",
  onSearch,
  onSuggestionSelect,
  onAdvancedSearchToggle,
  className = ''
}) => {
  const { 
    actions, 
    enhancedActions,
    searchSuggestions,
    recentlyViewed,
    config 
  } = useTemplateLibraryContext();

  const [isAdvancedMode, setIsAdvancedMode] = useState(false);
  const [searchHistory, setSearchHistory] = useState<string[]>(() => {
    const saved = localStorage.getItem('template-search-history');
    return saved ? JSON.parse(saved) : [];
  });
  
  const searchInputRef = useRef<any>(null);
  const searchId = useId();
  const suggestionsId = useId();
  const accessibility = useAccessibility({ announcements: true });

  // Quick filter options
  const quickFilters = [
    'Copyright Notice',
    'Takedown Request', 
    'DMCA',
    'Content Removal',
    'Social Media',
    'Video Platform'
  ];

  // Search operators info
  const searchOperators = [
    { label: 'Exact phrase', example: '"dmca notice"', description: 'Use quotes for exact matches' },
    { label: 'Field search', example: 'category:social', description: 'Search specific fields' },
    { label: 'Exclude', example: 'NOT inactive', description: 'Exclude terms' },
    { label: 'Multiple terms', example: 'copyright AND takedown', description: 'Combine with AND/OR' }
  ];

  // Enhanced suggestions with types and metadata
  const enhancedSuggestions = useMemo(() => {
    const suggestions: SearchSuggestion[] = [];
    
    if (!value) return suggestions;

    const query = value.toLowerCase();
    
    // Template name suggestions
    searchSuggestions.forEach(suggestion => {
      suggestions.push({
        type: 'template',
        value: suggestion,
        label: suggestion,
        icon: 'pi pi-file-text'
      });
    });
    
    // Recent searches
    if (showSearchHistory) {
      searchHistory
        .filter(term => term.toLowerCase().includes(query))
        .slice(0, 3)
        .forEach(term => {
          suggestions.push({
            type: 'recent',
            value: term,
            label: term,
            icon: 'pi pi-history',
            description: 'Recent search'
          });
        });
    }
    
    // Popular searches (mock data - could come from analytics)
    const popularSearches = ['DMCA Notice', 'Copyright', 'Takedown'];
    popularSearches
      .filter(term => term.toLowerCase().includes(query))
      .forEach(term => {
        suggestions.push({
          type: 'popular',
          value: term,
          label: term,
          icon: 'pi pi-star',
          description: 'Popular search'
        });
      });

    return suggestions.slice(0, 10);
  }, [value, searchSuggestions, searchHistory, showSearchHistory]);

  const handleSearchChange = useCallback((newValue: string) => {
    actions.setFilters({ search: newValue });
    
    // Announce search results count
    if (newValue.trim()) {
      // This would typically come from a search results count
      setTimeout(() => {
        accessibility.announce(`Search updated. ${newValue ? 'Type to see suggestions' : 'Search cleared'}`);
      }, 100);
    }
    
    // Track search event
    if (config.enableAnalytics) {
      enhancedActions.trackEvent({
        type: 'search',
        payload: { query: newValue, isAdvanced: isAdvancedMode },
        timestamp: new Date().toISOString()
      });
    }
  }, [actions, isAdvancedMode, config.enableAnalytics, enhancedActions, accessibility]);

  const handleSearchSubmit = useCallback(() => {
    if (value.trim()) {
      // Add to search history
      setSearchHistory(prev => {
        const updated = [value, ...prev.filter(item => item !== value)].slice(0, 10);
        localStorage.setItem('template-search-history', JSON.stringify(updated));
        return updated;
      });
      
      // Parse advanced search if in advanced mode
      if (isAdvancedMode && value.includes(':')) {
        const query = parseAdvancedSearchQuery(value);
        console.log('Advanced search query:', query);
        accessibility.announce(`Advanced search performed for: ${value}`, 'assertive');
      } else {
        accessibility.announce(`Search performed for: ${value}`, 'assertive');
      }
      
      onSearch?.(value);
    }
  }, [value, isAdvancedMode, onSearch, accessibility]);

  const handleSuggestionSelect = useCallback((suggestion: SearchSuggestion) => {
    handleSearchChange(suggestion.value);
    onSuggestionSelect?.(suggestion);
  }, [handleSearchChange, onSuggestionSelect]);

  const handleQuickFilterClick = useCallback((filter: string) => {
    handleSearchChange(filter);
  }, [handleSearchChange]);

  const handleClearSearch = useCallback(() => {
    handleSearchChange('');
    searchInputRef.current?.focus();
  }, [handleSearchChange]);

  const toggleAdvancedMode = useCallback(() => {
    const newMode = !isAdvancedMode;
    setIsAdvancedMode(newMode);
    onAdvancedSearchToggle?.(newMode);
  }, [isAdvancedMode, onAdvancedSearchToggle]);

  const clearSearchHistory = useCallback(() => {
    setSearchHistory([]);
    localStorage.removeItem('template-search-history');
  }, []);

  const suggestionTemplate = (suggestion: SearchSuggestion) => (
    <div className="search-suggestion-item">
      <i className={`${suggestion.icon} suggestion-icon suggestion-${suggestion.type}`} />
      <div className="suggestion-content">
        <span className="suggestion-label">{suggestion.label}</span>
        {suggestion.description && (
          <small className="suggestion-description">{suggestion.description}</small>
        )}
      </div>
      {suggestion.count && (
        <Badge value={suggestion.count} className="suggestion-count" />
      )}
    </div>
  );

  return (
    <div className={`enhanced-template-search ${className}`}>
      {/* Main Search Section */}
      <div className="search-main-section">
        <div className="search-header">
          <h2 className="search-title">Find Your Perfect Template</h2>
          <p className="search-subtitle">
            Search through our comprehensive library with advanced filters
          </p>
        </div>

        <div className="search-input-container">
          <div className="search-input-wrapper">
            <span className="p-input-icon-left p-input-icon-right">
              <i className="pi pi-search search-icon" />
              <AutoComplete
                ref={searchInputRef}
                value={value}
                suggestions={showSuggestions ? enhancedSuggestions : []}
                completeMethod={() => {}} // Suggestions are computed, not fetched
                onChange={(e) => handleSearchChange(e.value)}
                onSelect={(e) => handleSuggestionSelect(e.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleSearchSubmit();
                  } else if (e.key === 'Escape') {
                    handleClearSearch();
                  }
                }}
                placeholder={placeholder}
                className="w-full search-autocomplete"
                inputClassName="search-input-field"
                panelClassName="search-suggestions-panel"
                itemTemplate={suggestionTemplate}
                id={searchId}
                aria-label="Search templates"
                aria-describedby={`${searchId}-help`}
                role="combobox"
                aria-expanded={showSuggestions && enhancedSuggestions.length > 0}
                aria-haspopup="listbox"
                aria-autocomplete="list"
                aria-owns={suggestionsId}
              />
              <div className="search-actions" role="group" aria-label="Search actions">
                {value && (
                  <Button
                    icon="pi pi-times"
                    className="p-button-text search-clear-btn"
                    onClick={handleClearSearch}
                    tooltip="Clear search"
                    aria-label="Clear search"
                  />
                )}
                <Button
                  icon="pi pi-search"
                  className="p-button-text search-submit-btn"
                  onClick={handleSearchSubmit}
                  tooltip="Search"
                  aria-label="Submit search"
                />
              </div>
            </span>
          </div>

          {/* Advanced Search Toggle */}
          {showAdvancedSearch && (
            <div className="search-mode-toggle">
              <Button
                label={isAdvancedMode ? 'Simple Search' : 'Advanced Search'}
                icon={isAdvancedMode ? 'pi pi-eye' : 'pi pi-cog'}
                className="p-button-text search-mode-btn"
                onClick={toggleAdvancedMode}
                tooltip={isAdvancedMode ? 'Switch to simple search' : 'Enable advanced search with operators'}
              />
            </div>
          )}
        </div>

        {/* Advanced Search Help */}
        {isAdvancedMode && (
          <div className="search-operators-help" role="region" aria-labelledby={`${searchId}-operators-title`}>
            <div id={`${searchId}-help`} className="sr-only">
              Advanced search mode is enabled. Use operators like quotes for exact phrases, category:name for field search, and AND/OR for multiple terms.
            </div>
            <h4 id={`${searchId}-operators-title`}>Search Operators:</h4>
            <div className="operators-grid">
              {searchOperators.map((op, index) => (
                <div key={index} className="operator-item">
                  <code className="operator-example">{op.example}</code>
                  <small className="operator-description">{op.description}</small>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Quick Filters */}
        {showQuickFilters && !value && (
          <div className="quick-filters-section">
            <span className="quick-filters-label">Quick search:</span>
            <div className="quick-filters-list">
              {quickFilters.map((filter, index) => (
                <Chip
                  key={index}
                  label={filter}
                  className="quick-filter-chip"
                  onClick={() => handleQuickFilterClick(filter)}
                />
              ))}
            </div>
          </div>
        )}

        {/* Search History */}
        {showSearchHistory && searchHistory.length > 0 && !value && (
          <div className="search-history-section">
            <div className="search-history-header">
              <span className="search-history-label">Recent searches:</span>
              <Button
                icon="pi pi-trash"
                className="p-button-text p-button-sm"
                onClick={clearSearchHistory}
                tooltip="Clear search history"
              />
            </div>
            <div className="search-history-list">
              {searchHistory.slice(0, 5).map((term, index) => (
                <Chip
                  key={index}
                  label={term}
                  className="search-history-chip"
                  onClick={() => handleSearchChange(term)}
                  removable
                  onRemove={() => {
                    const updated = searchHistory.filter(item => item !== term);
                    setSearchHistory(updated);
                    localStorage.setItem('template-search-history', JSON.stringify(updated));
                  }}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default React.memo(EnhancedTemplateSearch);