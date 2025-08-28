import React from 'react';
import { AutomationSettings } from '../components/settings';
import { EnhancedCard } from '../components/common/EnhancedCard';
import { Button } from 'primereact/button';
import { Badge } from 'primereact/badge';
import { Divider } from 'primereact/divider';

/**
 * Demo page showcasing the comprehensive AutomationSettings component
 * This component demonstrates all the automation configuration features:
 * - Auto-approval/rejection thresholds
 * - Time-based escalation rules  
 * - Platform-specific rules configuration
 * - Learning preferences (adaptive AI)
 * - Batch processing settings
 * - Progressive disclosure preferences
 * - Test mode and preview functionality
 * - Statistics and effectiveness tracking
 */
const AutomationSettingsDemo: React.FC = () => {
  return (
    <div className="automation-settings-demo">
      {/* Hero Section */}
      <div className="bg-gradient-to-r from-primary-50 to-primary-100 p-6 border-round-lg mb-6">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-4xl font-bold text-900 mb-3">
            Automation Settings Component
          </h1>
          <p className="text-xl text-600 mb-4">
            Comprehensive automation configuration for Content Protection Platform
          </p>
          <div className="flex justify-content-center flex-wrap gap-2 mb-4">
            <Badge value="Auto-Approval" severity="success" />
            <Badge value="Smart Batching" severity="info" />
            <Badge value="AI Learning" severity="warning" />
            <Badge value="Platform Rules" />
            <Badge value="Test Mode" severity="danger" />
          </div>
          <Button 
            label="View Implementation" 
            icon="pi pi-github" 
            outlined 
            onClick={() => window.open('https://github.com/your-repo/AutomationSettings.tsx', '_blank')}
          />
        </div>
      </div>

      {/* Feature Overview */}
      <div className="grid mb-6">
        <div className="col-12 lg:col-4">
          <EnhancedCard
            title="🎯 Smart Thresholds"
            variant="outlined"
            className="h-full text-center"
          >
            <ul className="list-none p-0 m-0 text-left">
              <li className="flex align-items-center gap-2 mb-2">
                <i className="pi pi-check text-green-600" />
                <span>Confidence-based auto-approval</span>
              </li>
              <li className="flex align-items-center gap-2 mb-2">
                <i className="pi pi-check text-green-600" />
                <span>Smart rejection filters</span>
              </li>
              <li className="flex align-items-center gap-2 mb-2">
                <i className="pi pi-check text-green-600" />
                <span>Visual impact preview</span>
              </li>
              <li className="flex align-items-center gap-2">
                <i className="pi pi-check text-green-600" />
                <span>Real-time efficiency tracking</span>
              </li>
            </ul>
          </EnhancedCard>
        </div>

        <div className="col-12 lg:col-4">
          <EnhancedCard
            title="⏱️ Time Management"
            variant="outlined"
            className="h-full text-center"
          >
            <ul className="list-none p-0 m-0 text-left">
              <li className="flex align-items-center gap-2 mb-2">
                <i className="pi pi-check text-green-600" />
                <span>Auto-escalation rules</span>
              </li>
              <li className="flex align-items-center gap-2 mb-2">
                <i className="pi pi-check text-green-600" />
                <span>Business hours control</span>
              </li>
              <li className="flex align-items-center gap-2 mb-2">
                <i className="pi pi-check text-green-600" />
                <span>Weekend processing</span>
              </li>
              <li className="flex align-items-center gap-2">
                <i className="pi pi-check text-green-600" />
                <span>Timeout configurations</span>
              </li>
            </ul>
          </EnhancedCard>
        </div>

        <div className="col-12 lg:col-4">
          <EnhancedCard
            title="🧠 AI Learning"
            variant="outlined"
            className="h-full text-center"
          >
            <ul className="list-none p-0 m-0 text-left">
              <li className="flex align-items-center gap-2 mb-2">
                <i className="pi pi-check text-green-600" />
                <span>Adaptive thresholds</span>
              </li>
              <li className="flex align-items-center gap-2 mb-2">
                <i className="pi pi-check text-green-600" />
                <span>Pattern recognition</span>
              </li>
              <li className="flex align-items-center gap-2 mb-2">
                <i className="pi pi-check text-green-600" />
                <span>Accuracy tracking</span>
              </li>
              <li className="flex align-items-center gap-2">
                <i className="pi pi-check text-green-600" />
                <span>False positive reduction</span>
              </li>
            </ul>
          </EnhancedCard>
        </div>
      </div>

      {/* Technical Features */}
      <div className="grid mb-6">
        <div className="col-12 lg:col-6">
          <EnhancedCard
            title="🔧 Technical Features"
            variant="outlined"
          >
            <div className="grid text-sm">
              <div className="col-6">
                <strong>UI Components:</strong>
                <ul className="list-none p-0 m-0 mt-2">
                  <li>• Interactive sliders</li>
                  <li>• Data tables</li>
                  <li>• Progress indicators</li>
                  <li>• Charts & visualizations</li>
                </ul>
              </div>
              <div className="col-6">
                <strong>State Management:</strong>
                <ul className="list-none p-0 m-0 mt-2">
                  <li>• Local storage persistence</li>
                  <li>• Change tracking</li>
                  <li>• Validation</li>
                  <li>• Undo/reset functionality</li>
                </ul>
              </div>
              <div className="col-6 mt-3">
                <strong>User Experience:</strong>
                <ul className="list-none p-0 m-0 mt-2">
                  <li>• Progressive disclosure</li>
                  <li>• Test mode simulation</li>
                  <li>• Real-time previews</li>
                  <li>• Accessibility support</li>
                </ul>
              </div>
              <div className="col-6 mt-3">
                <strong>Integration:</strong>
                <ul className="list-none p-0 m-0 mt-2">
                  <li>• Service layer binding</li>
                  <li>• Export/import config</li>
                  <li>• Platform APIs</li>
                  <li>• Analytics tracking</li>
                </ul>
              </div>
            </div>
          </EnhancedCard>
        </div>

        <div className="col-12 lg:col-6">
          <EnhancedCard
            title="📊 Business Impact"
            variant="outlined"
          >
            <div className="text-center mb-4">
              <div className="text-4xl font-bold text-primary-600 mb-2">80%+</div>
              <div className="text-sm text-600">Workload Reduction</div>
            </div>
            
            <div className="grid">
              <div className="col-6">
                <div className="text-center">
                  <div className="text-2xl font-semibold text-green-600">94.2%</div>
                  <div className="text-xs text-600">Accuracy Rate</div>
                </div>
              </div>
              <div className="col-6">
                <div className="text-center">
                  <div className="text-2xl font-semibold text-blue-600">18.5h</div>
                  <div className="text-xs text-600">Weekly Time Saved</div>
                </div>
              </div>
              <div className="col-6 mt-3">
                <div className="text-center">
                  <div className="text-2xl font-semibold text-orange-600">2.1%</div>
                  <div className="text-xs text-600">False Positive Rate</div>
                </div>
              </div>
              <div className="col-6 mt-3">
                <div className="text-center">
                  <div className="text-2xl font-semibold text-purple-600">89.7%</div>
                  <div className="text-xs text-600">Overall Efficiency</div>
                </div>
              </div>
            </div>
          </EnhancedCard>
        </div>
      </div>

      <Divider />

      {/* Main Component Demo */}
      <div className="mb-4">
        <h2 className="text-2xl font-semibold text-900 mb-2">Live Component Demo</h2>
        <p className="text-600 mb-4">
          Interact with the full AutomationSettings component below. All changes are persisted to localStorage.
        </p>
      </div>

      {/* Render the actual component */}
      <AutomationSettings />

      {/* Usage Instructions */}
      <div className="mt-8 p-4 bg-blue-50 border-round">
        <h3 className="text-lg font-semibold text-blue-900 mt-0 mb-3">
          <i className="pi pi-info-circle mr-2" />
          Usage Instructions
        </h3>
        <div className="grid">
          <div className="col-12 md:col-6">
            <h4 className="font-medium text-blue-800 mb-2">Getting Started:</h4>
            <ul className="text-sm text-blue-700 pl-4">
              <li>Adjust confidence thresholds using the sliders</li>
              <li>Enable/disable different automation features</li>
              <li>Configure platform-specific rules in the table</li>
              <li>Test your settings with the preview mode</li>
            </ul>
          </div>
          <div className="col-12 md:col-6">
            <h4 className="font-medium text-blue-800 mb-2">Pro Tips:</h4>
            <ul className="text-sm text-blue-700 pl-4">
              <li>Start with conservative thresholds (85%+ approval)</li>
              <li>Enable learning mode for continuous improvement</li>
              <li>Use platform-specific rules for optimal results</li>
              <li>Monitor statistics to fine-tune settings</li>
            </ul>
          </div>
        </div>
      </div>

      <style jsx>{`
        .automation-settings-demo {
          max-width: 1200px;
          margin: 0 auto;
          padding: 2rem;
        }

        .bg-gradient-to-r {
          background: linear-gradient(135deg, var(--primary-50) 0%, var(--primary-100) 100%);
        }

        @media (max-width: 768px) {
          .automation-settings-demo {
            padding: 1rem;
          }
        }
      `}</style>
    </div>
  );
};

export default AutomationSettingsDemo;