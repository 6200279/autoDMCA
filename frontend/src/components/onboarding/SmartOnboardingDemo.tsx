import React, { useState } from 'react';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { Dialog } from 'primereact/dialog';
import { Toast } from 'primereact/toast';
import type { OnboardingConfiguration } from '../../types/api';
import SmartOnboarding from './SmartOnboarding';

const SmartOnboardingDemo: React.FC = () => {
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [completedConfig, setCompletedConfig] = useState<OnboardingConfiguration | null>(null);

  const handleOnboardingComplete = (config: OnboardingConfiguration) => {
    console.log('Onboarding completed with configuration:', config);
    setCompletedConfig(config);
    setShowOnboarding(false);
    
    // Here you would typically:
    // 1. Save the configuration to your backend
    // 2. Initialize monitoring with the settings
    // 3. Redirect to the main dashboard
  };

  const handleSkipOnboarding = () => {
    console.log('Onboarding skipped - using default settings');
    setShowOnboarding(false);
  };

  const resetDemo = () => {
    setCompletedConfig(null);
    setShowOnboarding(true);
  };

  return (
    <div className="smart-onboarding-demo p-4">
      <Card className="text-center">
        <h2>Smart Onboarding System Demo</h2>
        <p className="text-muted-color mb-4">
          Experience the intelligent onboarding flow that automatically configures 
          content protection based on industry selection and content analysis.
        </p>
        
        <div className="demo-features mb-4">
          <div className="grid">
            <div className="col-12 md:col-4">
              <div className="feature-highlight">
                <i className="pi pi-bolt" style={{ fontSize: '2rem', color: 'var(--orange-500)' }}></i>
                <h4>AI-Powered Analysis</h4>
                <p>Analyzes uploaded content to detect type, style, and optimal protection settings</p>
              </div>
            </div>
            <div className="col-12 md:col-4">
              <div className="feature-highlight">
                <i className="pi pi-cog" style={{ fontSize: '2rem', color: 'var(--blue-500)' }}></i>
                <h4>Industry Presets</h4>
                <p>Pre-configured settings for photographers, musicians, authors, and more</p>
              </div>
            </div>
            <div className="col-12 md:col-4">
              <div className="feature-highlight">
                <i className="pi pi-search" style={{ fontSize: '2rem', color: 'var(--green-500)' }}></i>
                <h4>Smart Discovery</h4>
                <p>Auto-detects platforms from social handles and suggests monitoring keywords</p>
              </div>
            </div>
          </div>
        </div>

        {completedConfig ? (
          <div className="completion-summary">
            <div className="success-message mb-4">
              <i className="pi pi-check-circle" style={{ fontSize: '3rem', color: 'var(--green-500)' }}></i>
              <h3>Setup Completed!</h3>
              <p>Your protection system has been configured with the following settings:</p>
            </div>
            
            <Card className="config-summary text-left mb-4">
              <div className="grid">
                <div className="col-12 md:col-6">
                  <h5>Content Protection</h5>
                  <ul>
                    {completedConfig.industry && <li><strong>Industry:</strong> {completedConfig.industry}</li>}
                    <li><strong>Content Types:</strong> {completedConfig.contentTypes.join(', ') || 'Not specified'}</li>
                    <li><strong>Keywords:</strong> {completedConfig.keywords.length} terms</li>
                    <li><strong>Platforms:</strong> {completedConfig.platforms.length} monitored</li>
                  </ul>
                </div>
                <div className="col-12 md:col-6">
                  <h5>Settings</h5>
                  <ul>
                    <li><strong>Scan Frequency:</strong> {completedConfig.scanFrequency}</li>
                    <li><strong>Priority:</strong> {completedConfig.priority}</li>
                    <li><strong>Watermarking:</strong> {completedConfig.watermarkEnabled ? 'Enabled' : 'Disabled'}</li>
                    <li><strong>Auto Takedown:</strong> {completedConfig.autoTakedown ? 'Enabled' : 'Disabled'}</li>
                  </ul>
                </div>
              </div>
              
              {Object.keys(completedConfig.socialHandles).length > 0 && (
                <div className="mt-3">
                  <h5>Social Media Accounts</h5>
                  <ul>
                    {Object.entries(completedConfig.socialHandles)
                      .filter(([_, handle]) => handle?.trim())
                      .map(([platform, handle]) => (
                        <li key={platform}><strong>{platform}:</strong> {handle}</li>
                      ))
                    }
                  </ul>
                </div>
              )}
            </Card>
            
            <Button 
              label="Try Again" 
              icon="pi pi-refresh" 
              onClick={resetDemo}
              className="p-button-outlined"
            />
          </div>
        ) : (
          <div className="demo-actions">
            <Button 
              label="Start Smart Onboarding" 
              icon="pi pi-play" 
              size="large"
              onClick={() => setShowOnboarding(true)}
              className="demo-start-button"
            />
            <p className="text-sm text-muted-color mt-2">
              Click to experience the intelligent setup process
            </p>
          </div>
        )}
      </Card>

      <Dialog
        visible={showOnboarding}
        onHide={() => setShowOnboarding(false)}
        modal
        className="smart-onboarding-dialog"
        style={{ width: '95vw', maxWidth: '1200px' }}
        showHeader={false}
        closable={false}
      >
        <SmartOnboarding
          onComplete={handleOnboardingComplete}
          onSkip={handleSkipOnboarding}
        />
      </Dialog>

      <style jsx>{`
        .smart-onboarding-demo .feature-highlight {
          text-align: center;
          padding: 1rem;
        }
        
        .smart-onboarding-demo .feature-highlight h4 {
          margin: 1rem 0 0.5rem 0;
          color: var(--text-color);
        }
        
        .smart-onboarding-demo .feature-highlight p {
          color: var(--text-color-secondary);
          font-size: 0.875rem;
          line-height: 1.4;
        }
        
        .demo-start-button {
          background: linear-gradient(135deg, var(--primary-color) 0%, var(--blue-400) 100%);
          border: none;
          box-shadow: 0 4px 15px rgba(var(--primary-color-rgb), 0.3);
          transition: transform 0.2s ease;
        }
        
        .demo-start-button:hover {
          transform: translateY(-2px);
          box-shadow: 0 6px 20px rgba(var(--primary-color-rgb), 0.4);
        }
        
        .success-message {
          text-align: center;
        }
        
        .config-summary ul {
          list-style: none;
          padding-left: 0;
        }
        
        .config-summary li {
          padding: 0.25rem 0;
          border-bottom: 1px solid var(--surface-border);
        }
        
        .config-summary li:last-child {
          border-bottom: none;
        }
        
        :global(.smart-onboarding-dialog .p-dialog-content) {
          padding: 0;
          background: var(--surface-ground);
        }
      `}</style>
    </div>
  );
};

export default SmartOnboardingDemo;