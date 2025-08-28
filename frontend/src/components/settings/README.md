# AutomationSettings Component

A comprehensive automation configuration component for the Content Protection Platform that enables users to fine-tune AI-driven content protection workflows.

## Overview

The AutomationSettings component provides a sophisticated interface for configuring automated content protection processes, including confidence thresholds, escalation rules, platform-specific configurations, and AI learning preferences.

## Features

### 🎯 Core Automation Features

- **Auto-Approval Thresholds**: Configure confidence levels for automatic approval of takedown requests
- **Auto-Rejection Filters**: Set thresholds for automatically rejecting low-confidence detections
- **Time-Based Escalation**: Define rules for escalating stalled requests
- **Smart Batching**: Group similar infringements for efficient batch processing
- **Adaptive AI Learning**: Enable machine learning to improve accuracy over time

### 📊 Advanced Configuration

- **Platform-Specific Rules**: Customize settings per platform (YouTube, Instagram, TikTok, etc.)
- **Progressive Disclosure**: Three complexity levels (Basic, Intermediate, Advanced)
- **Test Mode**: Preview automation impact without executing actions
- **Statistics Dashboard**: Real-time effectiveness and performance metrics
- **Export/Import**: Save and load configuration files

### 🔧 Technical Features

- **Real-time Validation**: Instant feedback on configuration changes
- **Local Storage Persistence**: Settings automatically saved and restored
- **Change Tracking**: Visual indicators for unsaved modifications
- **Accessibility Support**: WCAG compliant with keyboard navigation
- **Responsive Design**: Optimized for desktop and mobile devices

## Component Structure

```
AutomationSettings/
├── AutomationSettings.tsx       # Main component
├── AutomationSettings.css       # Enhanced styling
├── AutomationSettings.test.tsx  # Comprehensive tests
└── index.ts                     # Export definitions
```

## Usage

### Basic Implementation

```typescript
import { AutomationSettings } from '../components/settings';

function SettingsPage() {
  return (
    <div>
      <h1>Platform Settings</h1>
      <AutomationSettings />
    </div>
  );
}
```

### Integration with Settings Page

```typescript
import { TabPanel } from 'primereact/tabview';
import { AutomationSettings } from '../components/settings';

// Add as a tab in existing settings
<TabPanel header="Automation" leftIcon="pi pi-cog">
  <AutomationSettings />
</TabPanel>
```

## Configuration Interface

### Auto-Approval Settings

```typescript
interface AutoApprovalConfig {
  enabled: boolean;           // Enable/disable auto-approval
  threshold: number;          // Confidence percentage (70-98%)
  preview: string;            // Impact preview text
}
```

### Platform Rules

```typescript
interface PlatformRule {
  platform: string;            // Platform identifier
  autoApproveThreshold: number; // Platform-specific confidence
  responseTimeoutHours: number; // Escalation timeout
  autoEscalate: boolean;       // Auto-escalation enabled
  preferredTemplate: string;   // Default template
}
```

### Learning Configuration

```typescript
interface LearningConfig {
  learnFromUserActions: boolean;  // Adapt from user behavior
  adaptiveThresholds: boolean;    // Auto-adjust thresholds
  falsePositiveTracking: boolean; // Track and reduce errors
}
```

## API Integration

### Service Layer

The component integrates with the `automationService`:

```typescript
import { automationService } from '../../services/automationService';

// Load configuration
automationService.loadConfig();

// Save configuration
automationService.updateConfig(newConfig);

// Get effectiveness statistics
const stats = automationService.getEffectivenessStats();
```

### Local Storage

Settings are automatically persisted:

```typescript
// Automatically saved on configuration changes
localStorage.setItem('automationConfig', JSON.stringify(config));

// Loaded on component mount
const savedConfig = localStorage.getItem('automationConfig');
```

## Styling & Theming

### CSS Custom Properties

The component uses design tokens for consistent styling:

```css
/* Slider customization */
.automation-slider .p-slider-range {
  background: linear-gradient(90deg, var(--primary-400) 0%, var(--primary-600) 100%);
}

/* Card hover effects */
.automation-settings .enhanced-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

/* Dark mode support */
[data-theme="dark"] .automation-settings {
  --surface-card: var(--surface-900);
}
```

### Responsive Design

```css
@media (max-width: 768px) {
  .automation-settings {
    padding: var(--spacing-3);
  }
  
  .fixed-bottom-bar .flex {
    flex-direction: column;
    gap: var(--spacing-2);
  }
}
```

## State Management

### Configuration State

```typescript
const [config, setConfig] = useState<AutomationConfig>({
  autoApproveEnabled: true,
  autoApproveThreshold: 90,
  autoRejectThreshold: 40,
  // ... other config options
});
```

### Change Tracking

```typescript
const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

useEffect(() => {
  setHasUnsavedChanges(
    JSON.stringify(config) !== JSON.stringify(originalConfig)
  );
}, [config, originalConfig]);
```

### Progressive Disclosure

```typescript
const [complexityLevel, setComplexityLevel] = useState<'basic' | 'intermediate' | 'advanced'>('intermediate');

// Conditionally render advanced features
{complexityLevel === 'advanced' && (
  <AdvancedSettingsPanel />
)}
```

## Testing

### Unit Tests

```bash
npm run test AutomationSettings.test.tsx
```

### Coverage Report

```bash
npm run test:coverage -- AutomationSettings
```

### Test Structure

- **Component Rendering**: Verifies all UI elements render correctly
- **User Interactions**: Tests sliders, switches, and form controls
- **State Management**: Validates configuration changes and persistence
- **Integration**: Tests service layer integration and localStorage
- **Accessibility**: Ensures WCAG compliance and keyboard navigation

## Performance Considerations

### Optimization Techniques

1. **Memoized Callbacks**: Prevent unnecessary re-renders
2. **Debounced Updates**: Batch configuration changes
3. **Lazy Loading**: Progressive disclosure for advanced features
4. **Virtual Scrolling**: Efficient rendering of large platform lists

### Performance Metrics

- Initial render: <100ms
- Configuration updates: <50ms
- Local storage operations: <10ms
- Test simulation: <2s

## Accessibility Features

### WCAG 2.1 AA Compliance

- **Keyboard Navigation**: Full functionality without mouse
- **Screen Reader Support**: Proper ARIA labels and descriptions
- **High Contrast Mode**: Enhanced visibility for vision impaired users
- **Focus Management**: Clear focus indicators and logical tab order

### Implementation Examples

```typescript
// ARIA labels for sliders
<Slider
  aria-label="Auto-approval confidence threshold"
  aria-valuetext={`${value}% confidence`}
  aria-describedby="threshold-description"
/>

// Keyboard shortcuts
useEffect(() => {
  const handleKeyDown = (event: KeyboardEvent) => {
    if (event.ctrlKey && event.key === 's') {
      event.preventDefault();
      saveConfiguration();
    }
  };
  
  document.addEventListener('keydown', handleKeyDown);
  return () => document.removeEventListener('keydown', handleKeyDown);
}, []);
```

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Dependencies

### Required

- React 18+
- PrimeReact 10+
- TypeScript 4.5+

### Optional

- React Testing Library (for tests)
- Vitest (for testing framework)

## Contributing

### Development Setup

1. Clone the repository
2. Install dependencies: `npm install`
3. Start development server: `npm run dev`
4. Run tests: `npm run test`

### Code Style

- Follow existing TypeScript patterns
- Use PrimeReact components consistently
- Maintain accessibility standards
- Add comprehensive tests for new features

### Pull Request Guidelines

1. Update tests for any changed functionality
2. Ensure all tests pass
3. Update documentation as needed
4. Follow semantic commit conventions

## Troubleshooting

### Common Issues

**Configuration not saving:**
```typescript
// Check localStorage availability
if (typeof Storage !== 'undefined') {
  localStorage.setItem('automationConfig', JSON.stringify(config));
}
```

**Performance issues with large datasets:**
```typescript
// Implement pagination for platform rules
const paginatedRules = useMemo(() => {
  return platformRules.slice(page * pageSize, (page + 1) * pageSize);
}, [platformRules, page, pageSize]);
```

**Accessibility warnings:**
```typescript
// Ensure all interactive elements have labels
<InputSwitch
  inputId="auto-approve-switch"
  aria-labelledby="auto-approve-label"
/>
<label id="auto-approve-label">Enable Auto-Approval</label>
```

## License

MIT License - see LICENSE file for details.

## Support

For issues and support:
- GitHub Issues: [Repository Issues](https://github.com/your-org/autodmca/issues)
- Documentation: [Component Docs](https://docs.autodmca.com/components/automation-settings)
- Email: support@autodmca.com