# DMCA Template Library - Accessibility Guidelines

## Overview

This document provides comprehensive accessibility guidelines for the DMCA Template Library components. These guidelines ensure WCAG 2.1 AA+ compliance and create an inclusive user experience for all users, including those using assistive technologies.

## Table of Contents

1. [Core Accessibility Principles](#core-accessibility-principles)
2. [Implementation Guidelines](#implementation-guidelines)
3. [Component-Specific Requirements](#component-specific-requirements)
4. [Testing Requirements](#testing-requirements)
5. [Development Checklist](#development-checklist)
6. [Resources and Tools](#resources-and-tools)

## Core Accessibility Principles

### WCAG 2.1 AA Compliance

All components must adhere to the four principles of accessibility:

#### 1. Perceivable
- **Color Contrast**: Minimum 4.5:1 for normal text, 3:1 for large text
- **Alternative Text**: All images and icons have descriptive alt text
- **Information Not Conveyed by Color Alone**: Use icons, patterns, or text alongside color
- **Scalable Text**: Support up to 200% zoom without horizontal scrolling

#### 2. Operable
- **Keyboard Navigation**: All functionality accessible via keyboard
- **Focus Management**: Clear focus indicators and logical tab order
- **Timing**: No time limits or user-controlled timing
- **Seizures**: No content that causes seizures

#### 3. Understandable
- **Clear Language**: Use plain language and consistent terminology
- **Predictable Navigation**: Consistent navigation patterns
- **Input Assistance**: Clear labels and error messages
- **Context Changes**: User-initiated context changes only

#### 4. Robust
- **Valid HTML**: Semantic markup and proper ARIA usage
- **Assistive Technology**: Compatible with screen readers and other AT
- **Future Compatibility**: Use standard web technologies

## Implementation Guidelines

### Semantic HTML Structure

Always use semantic HTML elements before adding ARIA:

```tsx
// ✅ Good - Semantic HTML
<main role="main" aria-label="Template Library Dashboard">
  <header role="banner">
    <nav role="navigation" aria-label="Breadcrumb">
      <ol>
        <li><a href="/">Dashboard</a></li>
        <li>Templates</li>
      </ol>
    </nav>
  </header>
  
  <section role="search" aria-label="Template Search">
    <form role="search">
      <label htmlFor="search">Search templates</label>
      <input id="search" type="search" />
    </form>
  </section>
  
  <aside role="complementary" aria-label="Filters">
    <!-- Filter content -->
  </aside>
</main>

// ❌ Bad - Divs without semantic meaning
<div className="dashboard">
  <div className="header">
    <div className="nav">
      <!-- No semantic structure -->
    </div>
  </div>
</div>
```

### ARIA Implementation

Use ARIA attributes to enhance semantic HTML:

```tsx
// Grid with proper ARIA
<div 
  role="grid"
  aria-label="Template library"
  aria-rowcount={totalRows}
  aria-colcount={columnsCount}
  aria-multiselectable="true"
  tabIndex={0}
>
  {templates.map((template, index) => (
    <div
      key={template.id}
      role="gridcell"
      aria-selected={selected}
      aria-label={`Template: ${template.name}`}
      aria-describedby={`${template.id}-description`}
      tabIndex={focused ? 0 : -1}
    >
      <!-- Template content -->
    </div>
  ))}
</div>
```

### Focus Management

#### Focus Trapping

Use the accessibility hook for focus management:

```tsx
import { useAccessibility } from '../../hooks/useAccessibility';

const MyModal = ({ visible, onHide }) => {
  const { manageFocus } = useAccessibility();
  
  useEffect(() => {
    if (visible) {
      manageFocus.saveFocus();
      const cleanup = manageFocus.trap(modalRef.current);
      return cleanup;
    }
  }, [visible, manageFocus]);
  
  const handleClose = () => {
    onHide();
    manageFocus.restore();
  };
};
```

#### Focus Indicators

Ensure all focusable elements have visible focus indicators:

```css
.focus-visible,
*:focus-visible {
  outline: 3px solid var(--focus-color, #005fcc) !important;
  outline-offset: 2px !important;
  border-radius: 4px;
}
```

### Screen Reader Support

#### Live Regions

Use the accessibility hook for announcements:

```tsx
const { announce } = useAccessibility();

const handleSearch = (query) => {
  // Perform search
  const results = performSearch(query);
  
  // Announce results
  announce(`Search completed. ${results.length} templates found.`);
};

const handleError = (error) => {
  // Announce error with assertive priority
  announce(`Error: ${error.message}`, 'assertive');
};
```

#### ARIA Labels and Descriptions

Provide comprehensive labeling:

```tsx
<AutoComplete
  id={searchId}
  aria-label="Search templates"
  aria-describedby={`${searchId}-help`}
  role="combobox"
  aria-expanded={showSuggestions}
  aria-haspopup="listbox"
  aria-autocomplete="list"
  aria-owns={suggestionsId}
/>

<div id={`${searchId}-help`} className="sr-only">
  Use the search box to find templates. Type to see suggestions.
  Press Enter to search or Escape to clear.
</div>
```

### Keyboard Navigation

#### Standard Patterns

Implement standard keyboard navigation:

```tsx
const handleKeyDown = (e: KeyboardEvent) => {
  switch (e.key) {
    case 'Enter':
    case ' ':
      e.preventDefault();
      handleActivate();
      break;
    case 'Escape':
      handleClose();
      break;
    case 'ArrowUp':
      e.preventDefault();
      moveFocus('up');
      break;
    case 'ArrowDown':
      e.preventDefault();
      moveFocus('down');
      break;
    case 'Home':
      e.preventDefault();
      moveFocus('first');
      break;
    case 'End':
      e.preventDefault();
      moveFocus('last');
      break;
  }
};
```

#### Keyboard Shortcuts

Register global shortcuts:

```tsx
useEffect(() => {
  const shortcuts = [
    accessibility.keyboard.registerShortcut('ctrl+/', focusSearch, 'Focus search'),
    accessibility.keyboard.registerShortcut('ctrl+f', focusFilters, 'Focus filters'),
    accessibility.keyboard.registerShortcut('escape', closeDialogs, 'Close dialogs')
  ];

  return () => {
    shortcuts.forEach(cleanup => cleanup());
  };
}, []);
```

## Component-Specific Requirements

### EnhancedTemplateLibraryDashboard

#### Required Elements
- Skip navigation links
- ARIA landmarks (main, banner, complementary, search)
- Keyboard shortcuts registration
- Live regions for announcements
- Focus management for modals

#### Implementation
```tsx
// Skip links
<div className="skip-links" role="navigation" aria-label="Skip navigation">
  <a href="#search-section" className="skip-link">Skip to search</a>
  <a href="#filters-section" className="skip-link">Skip to filters</a>
  <a href="#templates-section" className="skip-link">Skip to templates</a>
</div>

// Main landmark
<main role="main" aria-label="Template Library Dashboard">
  <section id="toolbar-section" role="banner" aria-label="Template Library Toolbar">
    <!-- Toolbar content -->
  </section>
  
  <div role="region" aria-label="Template Library Content">
    <aside role="complementary" aria-label="Template Filters and Search">
      <!-- Filters and search -->
    </aside>
    
    <section role="region" aria-label="Template Grid">
      <!-- Template grid -->
    </section>
  </div>
</main>
```

### EnhancedTemplateSearch

#### Required Elements
- Combobox role with proper ARIA attributes
- Search suggestions with listbox role
- Keyboard navigation support
- Search announcements

#### Implementation
```tsx
<AutoComplete
  role="combobox"
  aria-label="Search templates"
  aria-describedby={`${searchId}-help`}
  aria-expanded={showSuggestions}
  aria-haspopup="listbox"
  aria-autocomplete="list"
  aria-owns={suggestionsId}
  onKeyDown={handleKeyDown}
/>

<div id={`${searchId}-help`} className="sr-only">
  Search for templates by name, category, or tags.
  {isAdvanced && " Advanced search mode is enabled."}
</div>
```

### EnhancedTemplateGrid

#### Required Elements
- Grid role with proper ARIA attributes
- Keyboard navigation (arrow keys)
- Selection announcements
- Focus management

#### Implementation
```tsx
<div
  role="grid"
  aria-label={`Template library with ${templates.length} templates`}
  aria-multiselectable={showSelection}
  aria-activedescendant={focusedId}
  tabIndex={0}
  onKeyDown={handleGridNavigation}
>
  {templates.map(template => (
    <div
      key={template.id}
      role="gridcell"
      id={`template-${template.id}`}
      aria-selected={selected}
      aria-label={`Template: ${template.name}`}
      tabIndex={focused ? 0 : -1}
    >
      <!-- Template card -->
    </div>
  ))}
</div>
```

### EnhancedTemplateCard

#### Required Elements
- Proper ARIA attributes for selection state
- Accessible action buttons
- Descriptive content
- Focus management

#### Implementation
```tsx
<div
  role="gridcell"
  aria-selected={selected}
  aria-label={`Template: ${template.name}`}
  aria-describedby={`${template.id}-description`}
  id={`template-${template.id}`}
  tabIndex={focused ? 0 : -1}
>
  <Checkbox
    checked={selected}
    aria-label={`Select ${template.name}`}
    onChange={handleSelection}
  />
  
  <Button
    icon="pi pi-heart"
    aria-label={`${isFavorite ? 'Remove from' : 'Add to'} favorites`}
    aria-pressed={isFavorite}
    onClick={handleFavorite}
  />
  
  <p id={`${template.id}-description`}>
    {template.description}
  </p>
</div>
```

### TemplateFilters

#### Required Elements
- Form labels for all inputs
- Fieldset grouping where appropriate
- Clear button states
- Filter announcements

#### Implementation
```tsx
<fieldset>
  <legend>Filter Templates</legend>
  
  <div className="filter-group">
    <label htmlFor="category-filter">
      <i className="pi pi-tag" aria-hidden="true" />
      Category
    </label>
    <Dropdown
      id="category-filter"
      value={category}
      onChange={handleCategoryChange}
      options={categories}
      aria-describedby="category-help"
    />
    <div id="category-help" className="sr-only">
      Filter templates by category
    </div>
  </div>
</fieldset>
```

## Testing Requirements

### Automated Testing

#### Unit Tests
```tsx
import { axe, toHaveNoViolations } from 'jest-axe';

expect.extend(toHaveNoViolations);

test('should not have accessibility violations', async () => {
  const { container } = render(<Component />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

#### Integration Tests
```tsx
test('should support keyboard navigation', async () => {
  render(<Component />);
  
  // Test tab navigation
  await userEvent.tab();
  expect(screen.getByRole('button')).toHaveFocus();
  
  // Test arrow key navigation
  await userEvent.keyboard('{ArrowDown}');
  expect(screen.getByRole('gridcell')).toHaveFocus();
});
```

### Manual Testing

#### Screen Reader Testing
1. Test with NVDA (Windows)
2. Test with JAWS (Windows)
3. Test with VoiceOver (macOS)
4. Test with Orca (Linux)

#### Keyboard Testing
1. Tab through all interactive elements
2. Test arrow key navigation in grids
3. Test keyboard shortcuts
4. Test focus trapping in modals

#### Visual Testing
1. Test at 200% zoom
2. Test with high contrast mode
3. Test focus indicators
4. Test color contrast with tools

### Browser Testing Matrix

| Browser | Desktop | Mobile | Screen Reader |
|---------|---------|---------|---------------|
| Chrome  | ✅      | ✅      | NVDA          |
| Firefox | ✅      | ✅      | NVDA          |
| Safari  | ✅      | ✅      | VoiceOver     |
| Edge    | ✅      | ✅      | NVDA/JAWS     |

## Development Checklist

### Before Starting Development
- [ ] Review WCAG 2.1 AA guidelines
- [ ] Understand component requirements
- [ ] Plan keyboard navigation patterns
- [ ] Design focus management strategy

### During Development
- [ ] Use semantic HTML elements
- [ ] Add proper ARIA attributes
- [ ] Implement keyboard navigation
- [ ] Add focus management
- [ ] Include screen reader announcements
- [ ] Test with keyboard only
- [ ] Run automated accessibility tests

### Before Code Review
- [ ] Verify WCAG compliance
- [ ] Test with screen reader
- [ ] Check color contrast
- [ ] Validate HTML
- [ ] Test keyboard navigation
- [ ] Review ARIA implementation

### Before Production
- [ ] Complete accessibility audit
- [ ] Cross-browser testing
- [ ] Screen reader testing
- [ ] Performance testing with AT
- [ ] Documentation updated

## Resources and Tools

### Testing Tools
- **axe-core**: Automated accessibility testing
- **WAVE**: Web accessibility evaluation
- **Lighthouse**: Chrome accessibility audit
- **Color Oracle**: Color blindness simulator
- **Contrast**: Color contrast checker

### Screen Readers
- **NVDA**: Free Windows screen reader
- **JAWS**: Commercial Windows screen reader
- **VoiceOver**: Built-in macOS/iOS screen reader
- **TalkBack**: Android screen reader

### Documentation
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
- [MDN Accessibility](https://developer.mozilla.org/en-US/docs/Web/Accessibility)
- [WebAIM Resources](https://webaim.org/)

### Browser Extensions
- **axe DevTools**: Browser accessibility testing
- **WAVE Extension**: Quick accessibility checks
- **Accessibility Insights**: Microsoft accessibility testing
- **Colour Contrast Analyser**: Real-time contrast checking

## Common Accessibility Mistakes to Avoid

### ❌ Don't
- Use `div` and `span` for interactive elements
- Rely only on color to convey information
- Skip heading levels (h1 → h3)
- Use placeholder text as labels
- Remove focus outlines without replacement
- Auto-play media with sound
- Use generic link text ("click here")

### ✅ Do
- Use semantic HTML elements
- Provide alternative text for images
- Include skip navigation links
- Use proper heading hierarchy
- Provide clear error messages
- Test with keyboard only
- Include ARIA labels for complex widgets

## Support and Questions

For accessibility questions or support:

1. Review this documentation
2. Check WCAG 2.1 guidelines
3. Test with screen readers
4. Consult with accessibility experts
5. Use automated testing tools

Remember: Accessibility is not a feature to be added later—it's a fundamental requirement that should be built into every component from the start.