import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import AutomationSettings from './AutomationSettings';

// Mock PrimeReact components for testing
vi.mock('primereact/card', () => ({
  Card: ({ children, title }: any) => <div data-testid="card" title={title}>{children}</div>
}));

vi.mock('primereact/slider', () => ({
  Slider: ({ value, onChange, ...props }: any) => (
    <input
      type="range"
      value={value}
      onChange={(e) => onChange({ value: parseInt(e.target.value) })}
      data-testid="slider"
      {...props}
    />
  )
}));

vi.mock('primereact/inputswitch', () => ({
  InputSwitch: ({ checked, onChange, ...props }: any) => (
    <input
      type="checkbox"
      checked={checked}
      onChange={(e) => onChange({ value: e.target.checked })}
      data-testid="input-switch"
      {...props}
    />
  )
}));

vi.mock('primereact/inputnumber', () => ({
  InputNumber: ({ value, onValueChange, ...props }: any) => (
    <input
      type="number"
      value={value}
      onChange={(e) => onValueChange({ value: parseInt(e.target.value) })}
      data-testid="input-number"
      {...props}
    />
  )
}));

vi.mock('primereact/button', () => ({
  Button: ({ label, onClick, ...props }: any) => (
    <button onClick={onClick} data-testid="button" {...props}>
      {label}
    </button>
  )
}));

vi.mock('primereact/accordion', () => ({
  Accordion: ({ children }: any) => <div data-testid="accordion">{children}</div>,
  AccordionTab: ({ children, header }: any) => (
    <div data-testid="accordion-tab" data-header={header}>
      {children}
    </div>
  )
}));

vi.mock('primereact/selectbutton', () => ({
  SelectButton: ({ value, options, onChange }: any) => (
    <select 
      value={value} 
      onChange={(e) => onChange({ value: e.target.value })}
      data-testid="select-button"
    >
      {options.map((opt: any) => (
        <option key={opt.value} value={opt.value}>{opt.label}</option>
      ))}
    </select>
  )
}));

vi.mock('primereact/datatable', () => ({
  DataTable: ({ children, value }: any) => (
    <div data-testid="data-table">
      {value && value.length > 0 && <span>Table with {value.length} rows</span>}
      {children}
    </div>
  )
}));

vi.mock('primereact/column', () => ({
  Column: ({ header }: any) => <div data-testid="column">{header}</div>
}));

vi.mock('primereact/toast', () => ({
  Toast: React.forwardRef((props: any, ref: any) => <div data-testid="toast" ref={ref} />)
}));

vi.mock('primereact/confirmdialog', () => ({
  ConfirmDialog: (props: any) => <div data-testid="confirm-dialog" {...props} />
}));

vi.mock('primereact/chart', () => ({
  Chart: ({ type, data }: any) => (
    <div data-testid="chart" data-type={type}>
      Mock Chart: {JSON.stringify(data)}
    </div>
  )
}));

vi.mock('primereact/knob', () => ({
  Knob: ({ value }: any) => <div data-testid="knob">Value: {value}</div>
}));

vi.mock('primereact/message', () => ({
  Message: ({ text, severity }: any) => (
    <div data-testid="message" data-severity={severity}>{text}</div>
  )
}));

// Mock other PrimeReact components
const mockComponents = [
  'Divider', 'Badge', 'Panel', 'ProgressBar', 'Tag', 'Tooltip', 
  'Dropdown', 'Image', 'Calendar'
];

mockComponents.forEach(componentName => {
  vi.mock(`primereact/${componentName.toLowerCase()}`, () => ({
    [componentName]: ({ children, ...props }: any) => 
      <div data-testid={componentName.toLowerCase()} {...props}>{children}</div>
  }));
});

// Mock the EnhancedCard component
vi.mock('../common/EnhancedCard', () => ({
  EnhancedCard: ({ children, title, ...props }: any) => (
    <div data-testid="enhanced-card" data-title={title} {...props}>
      {children}
    </div>
  )
}));

// Mock automation service
vi.mock('../../services/automationService', () => ({
  automationService: {
    loadConfig: vi.fn(),
    updateConfig: vi.fn()
  }
}));

describe('AutomationSettings Component', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
  });

  it('renders without crashing', () => {
    render(<AutomationSettings />);
    expect(screen.getByText('Automation Settings')).toBeInTheDocument();
  });

  it('displays the main title and description', () => {
    render(<AutomationSettings />);
    expect(screen.getByText('Automation Settings')).toBeInTheDocument();
    expect(screen.getByText(/Configure intelligent automation/)).toBeInTheDocument();
  });

  it('shows complexity level selector', () => {
    render(<AutomationSettings />);
    const selectButton = screen.getByTestId('select-button');
    expect(selectButton).toBeInTheDocument();
  });

  it('displays automation statistics', () => {
    render(<AutomationSettings />);
    expect(screen.getByText('Automation Effectiveness')).toBeInTheDocument();
  });

  it('shows accordion sections', () => {
    render(<AutomationSettings />);
    expect(screen.getByTestId('accordion')).toBeInTheDocument();
  });

  it('handles complexity level changes', async () => {
    render(<AutomationSettings />);
    const selectButton = screen.getByTestId('select-button');
    
    fireEvent.change(selectButton, { target: { value: 'advanced' } });
    await waitFor(() => {
      expect(selectButton.value).toBe('advanced');
    });
  });

  it('displays platform rules table', () => {
    render(<AutomationSettings />);
    const dataTable = screen.getByTestId('data-table');
    expect(dataTable).toBeInTheDocument();
    expect(screen.getByText(/Table with \d+ rows/)).toBeInTheDocument();
  });

  it('shows save configuration button', () => {
    render(<AutomationSettings />);
    const saveButton = screen.getByText('Save Configuration');
    expect(saveButton).toBeInTheDocument();
  });

  it('displays reset to defaults button', () => {
    render(<AutomationSettings />);
    const resetButton = screen.getByText('Reset to Defaults');
    expect(resetButton).toBeInTheDocument();
  });

  it('shows automation effectiveness chart', () => {
    render(<AutomationSettings />);
    const chart = screen.getByTestId('chart');
    expect(chart).toBeInTheDocument();
    expect(chart).toHaveAttribute('data-type', 'doughnut');
  });

  it('displays accuracy knob', () => {
    render(<AutomationSettings />);
    const knob = screen.getByTestId('knob');
    expect(knob).toBeInTheDocument();
  });

  it('handles threshold changes', async () => {
    render(<AutomationSettings />);
    const sliders = screen.getAllByTestId('slider');
    
    // Auto-approval threshold slider should exist
    expect(sliders.length).toBeGreaterThan(0);
    
    fireEvent.change(sliders[0], { target: { value: '85' } });
    
    await waitFor(() => {
      expect(sliders[0].value).toBe('85');
    });
  });

  it('shows test mode section', () => {
    render(<AutomationSettings />);
    expect(screen.getByText('Test & Preview Mode')).toBeInTheDocument();
  });

  it('displays batch processing configuration', () => {
    render(<AutomationSettings />);
    expect(screen.getByText('Smart Batching & Grouping')).toBeInTheDocument();
  });

  it('shows learning preferences section', () => {
    render(<AutomationSettings />);
    expect(screen.getByText('Adaptive AI Learning')).toBeInTheDocument();
  });

  it('handles switch toggles', async () => {
    render(<AutomationSettings />);
    const switches = screen.getAllByTestId('input-switch');
    
    expect(switches.length).toBeGreaterThan(0);
    
    fireEvent.change(switches[0], { target: { checked: false } });
    
    await waitFor(() => {
      expect(switches[0].checked).toBe(false);
    });
  });

  it('shows unsaved changes indicator when configured', async () => {
    render(<AutomationSettings />);
    const slider = screen.getAllByTestId('slider')[0];
    
    // Change a value to trigger unsaved changes
    fireEvent.change(slider, { target: { value: '75' } });
    
    await waitFor(() => {
      expect(screen.getByText('Unsaved Changes')).toBeInTheDocument();
    });
  });

  it('displays platform-specific rules correctly', () => {
    render(<AutomationSettings />);
    expect(screen.getByText('Platform-Specific Rules')).toBeInTheDocument();
    
    // Should show data table with platform rules
    const dataTable = screen.getByTestId('data-table');
    expect(dataTable).toBeInTheDocument();
  });

  it('shows export configuration in advanced mode', async () => {
    render(<AutomationSettings />);
    const selectButton = screen.getByTestId('select-button');
    
    // Switch to advanced mode
    fireEvent.change(selectButton, { target: { value: 'advanced' } });
    
    await waitFor(() => {
      expect(screen.getByText('Export Configuration')).toBeInTheDocument();
    });
  });

  it('handles test simulation', async () => {
    render(<AutomationSettings />);
    const runTestButton = screen.getByText('Run Test Simulation');
    expect(runTestButton).toBeInTheDocument();
    
    fireEvent.click(runTestButton);
    
    await waitFor(() => {
      expect(screen.getByText('Running Test...')).toBeInTheDocument();
    });
  });

  it('displays confidence preview information in advanced mode', async () => {
    render(<AutomationSettings />);
    const selectButton = screen.getByTestId('select-button');
    
    fireEvent.change(selectButton, { target: { value: 'advanced' } });
    
    await waitFor(() => {
      // Should show preview information for thresholds
      const previewElements = screen.getAllByText(/~\d+% of cases will be auto-processed/);
      expect(previewElements.length).toBeGreaterThan(0);
    });
  });
});

/**
 * Integration Tests
 */
describe('AutomationSettings Integration', () => {
  it('persists settings to localStorage', async () => {
    render(<AutomationSettings />);
    const slider = screen.getAllByTestId('slider')[0];
    
    fireEvent.change(slider, { target: { value: '80' } });
    
    const saveButton = screen.getByText('Save Configuration');
    fireEvent.click(saveButton);
    
    await waitFor(() => {
      const savedConfig = localStorage.getItem('automationConfig');
      expect(savedConfig).toBeTruthy();
    });
  });

  it('loads settings from localStorage on mount', () => {
    // Pre-populate localStorage
    const testConfig = {
      autoApproveEnabled: true,
      autoApproveThreshold: 85,
      autoRejectThreshold: 30
    };
    localStorage.setItem('automationConfig', JSON.stringify(testConfig));
    
    render(<AutomationSettings />);
    
    // Component should load with the saved values
    const sliders = screen.getAllByTestId('slider');
    expect(sliders.length).toBeGreaterThan(0);
  });

  it('validates threshold ranges', async () => {
    render(<AutomationSettings />);
    const numberInputs = screen.getAllByTestId('input-number');
    
    if (numberInputs.length > 0) {
      fireEvent.change(numberInputs[0], { target: { value: '150' } });
      
      await waitFor(() => {
        // Should clamp to maximum value
        expect(parseInt(numberInputs[0].value)).toBeLessThanOrEqual(100);
      });
    }
  });
});

/**
 * Accessibility Tests
 */
describe('AutomationSettings Accessibility', () => {
  it('has proper ARIA labels and roles', () => {
    render(<AutomationSettings />);
    
    // Check for main heading
    expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('Automation Settings');
  });

  it('supports keyboard navigation', () => {
    render(<AutomationSettings />);
    
    const interactiveElements = [
      ...screen.getAllByTestId('slider'),
      ...screen.getAllByTestId('input-switch'),
      ...screen.getAllByTestId('button')
    ];
    
    // All interactive elements should be focusable
    interactiveElements.forEach(element => {
      expect(element).not.toHaveAttribute('tabindex', '-1');
    });
  });

  it('provides meaningful labels for controls', () => {
    render(<AutomationSettings />);
    
    // Check for descriptive text content
    expect(screen.getByText('Auto-Approval Confidence')).toBeInTheDocument();
    expect(screen.getByText('Auto-Rejection Threshold')).toBeInTheDocument();
    expect(screen.getByText('Smart Batching & Grouping')).toBeInTheDocument();
  });
});