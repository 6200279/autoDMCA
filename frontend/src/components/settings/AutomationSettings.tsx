import React, { useState, useEffect, useCallback, useMemo } from 'react';
import './AutomationSettings.css';
import { Card } from 'primereact/card';
import { Slider } from 'primereact/slider';
import { InputSwitch } from 'primereact/inputswitch';
import { InputNumber } from 'primereact/inputnumber';
import { Dropdown } from 'primereact/dropdown';
import { Button } from 'primereact/button';
import { Divider } from 'primereact/divider';
import { Badge } from 'primereact/badge';
import { Panel } from 'primereact/panel';
import { Accordion, AccordionTab } from 'primereact/accordion';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Chart } from 'primereact/chart';
import { ProgressBar } from 'primereact/progressbar';
import { Tag } from 'primereact/tag';
import { Tooltip } from 'primereact/tooltip';
import { ConfirmDialog } from 'primereact/confirmdialog';
import { Toast } from 'primereact/toast';
import { Knob } from 'primereact/knob';
import { SelectButton } from 'primereact/selectbutton';
import { Message } from 'primereact/message';
import { classNames } from 'primereact/utils';

import { EnhancedCard } from '../common/EnhancedCard';
import { automationService, AutomationConfig, PlatformRule } from '../../services/automationService';

interface AutomationStatistics {
  totalProcessed: number;
  autoApproved: number;
  autoRejected: number;
  manualReview: number;
  accuracy: number;
  timesSaved: number;
  falsePositiveRate: number;
  efficiency: number;
}

interface PreviewMode {
  enabled: boolean;
  sampleSize: number;
  confidence: number;
}

const AutomationSettings: React.FC = () => {
  const [config, setConfig] = useState<AutomationConfig>({
    autoApproveEnabled: true,
    autoApproveThreshold: 90,
    autoRejectThreshold: 40,
    autoMoveEnabled: true,
    autoEscalateHours: 48,
    smartGroupingEnabled: true,
    minGroupSize: 3,
    learnFromUserActions: true,
    adaptiveThresholds: true,
    businessHoursOnly: false,
    weekendProcessing: true,
    platformRules: {}
  });

  const [originalConfig, setOriginalConfig] = useState<AutomationConfig>(config);
  const [previewMode, setPreviewMode] = useState<PreviewMode>({
    enabled: false,
    sampleSize: 10,
    confidence: 85
  });
  
  const [statistics, setStatistics] = useState<AutomationStatistics>({
    totalProcessed: 1247,
    autoApproved: 892,
    autoRejected: 123,
    manualReview: 232,
    accuracy: 94.2,
    timesSaved: 18.5,
    falsePositiveRate: 2.1,
    efficiency: 89.7
  });

  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [testMode, setTestMode] = useState(false);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [activeAccordion, setActiveAccordion] = useState<number>(0);

  // Progressive disclosure options
  const complexityLevels = [
    { label: 'Basic', value: 'basic' },
    { label: 'Intermediate', value: 'intermediate' },
    { label: 'Advanced', value: 'advanced' }
  ];
  const [complexityLevel, setComplexityLevel] = useState('intermediate');

  // Platform rules data
  const defaultPlatforms = [
    'YouTube', 'Instagram', 'TikTok', 'Facebook', 'Twitter', 'OnlyFans', 'Reddit', 'Discord'
  ];

  const platformRulesData = useMemo(() => {
    return defaultPlatforms.map(platform => ({
      platform,
      ...(config.platformRules[platform] || {
        autoApproveThreshold: config.autoApproveThreshold,
        responseTimeoutHours: config.autoEscalateHours,
        autoEscalate: true,
        preferredTemplate: 'standard'
      })
    }));
  }, [config]);

  // Load config on mount
  useEffect(() => {
    const loadConfig = async () => {
      automationService.loadConfig();
      // In a real implementation, this would come from the service
      setOriginalConfig(config);
    };
    loadConfig();
  }, []);

  // Track changes
  useEffect(() => {
    setHasUnsavedChanges(JSON.stringify(config) !== JSON.stringify(originalConfig));
  }, [config, originalConfig]);

  const handleConfigChange = useCallback((field: keyof AutomationConfig, value: any) => {
    setConfig(prev => ({
      ...prev,
      [field]: value
    }));
  }, []);

  const handlePlatformRuleChange = useCallback((platform: string, field: keyof PlatformRule, value: any) => {
    setConfig(prev => ({
      ...prev,
      platformRules: {
        ...prev.platformRules,
        [platform]: {
          ...prev.platformRules[platform],
          platform,
          [field]: value
        }
      }
    }));
  }, []);

  const saveConfiguration = useCallback(async () => {
    try {
      automationService.updateConfig(config);
      setOriginalConfig(config);
      setHasUnsavedChanges(false);
      // Show success toast
    } catch (error) {
      console.error('Failed to save configuration:', error);
    }
  }, [config]);

  const resetToDefaults = useCallback(() => {
    setShowConfirmDialog(true);
  }, []);

  const confirmReset = useCallback(() => {
    const defaultConfig: AutomationConfig = {
      autoApproveEnabled: true,
      autoApproveThreshold: 90,
      autoRejectThreshold: 40,
      autoMoveEnabled: true,
      autoEscalateHours: 48,
      smartGroupingEnabled: true,
      minGroupSize: 3,
      learnFromUserActions: true,
      adaptiveThresholds: true,
      businessHoursOnly: false,
      weekendProcessing: true,
      platformRules: {}
    };
    setConfig(defaultConfig);
    setShowConfirmDialog(false);
  }, []);

  const runPreview = useCallback(async () => {
    setTestMode(true);
    // Simulate test run with current settings
    setTimeout(() => {
      setTestMode(false);
      setPreviewMode({
        ...previewMode,
        confidence: Math.floor(Math.random() * 15) + 85
      });
    }, 2000);
  }, [previewMode]);

  // Chart data for statistics
  const efficiencyChartData = {
    labels: ['Auto Approved', 'Auto Rejected', 'Manual Review'],
    datasets: [{
      data: [statistics.autoApproved, statistics.autoRejected, statistics.manualReview],
      backgroundColor: ['#22c55e', '#ef4444', '#f59e0b'],
      borderWidth: 0
    }]
  };

  const efficiencyChartOptions = {
    plugins: {
      legend: {
        position: 'bottom' as const
      }
    },
    maintainAspectRatio: false
  };

  const getConfidencePreview = useCallback((threshold: number) => {
    const impact = Math.round((threshold - 50) * 2.1);
    const efficiency = Math.max(60, Math.min(95, 85 + (threshold - 80) * 0.5));
    return `~${impact}% of cases will be auto-processed (${efficiency}% efficiency)`;
  }, []);

  const renderThresholdSlider = (
    label: string,
    value: number,
    onChange: (value: number) => void,
    min: number = 0,
    max: number = 100,
    step: number = 5,
    tooltip?: string
  ) => (
    <div className="automation-threshold-control">
      <div className="flex justify-content-between align-items-center mb-3">
        <label className="font-semibold text-900">
          {label}
          {tooltip && (
            <>
              <i className="pi pi-info-circle ml-2 cursor-pointer" data-pr-tooltip={tooltip} />
              <Tooltip target=".pi-info-circle" />
            </>
          )}
        </label>
        <div className="flex align-items-center gap-2">
          <InputNumber
            value={value}
            onValueChange={(e) => onChange(e.value || 0)}
            min={min}
            max={max}
            size={3}
            suffix="%"
            className="w-6rem"
          />
          <Badge value={value > 80 ? 'High' : value > 60 ? 'Medium' : 'Low'} 
                 severity={value > 80 ? 'success' : value > 60 ? 'warning' : 'danger'} />
        </div>
      </div>
      <Slider
        value={value}
        onChange={(e) => onChange(e.value as number)}
        min={min}
        max={max}
        step={step}
        className="w-full automation-slider"
      />
      {complexityLevel === 'advanced' && (
        <div className="text-sm text-600 mt-2">
          <i className="pi pi-lightbulb mr-1" />
          {getConfidencePreview(value)}
        </div>
      )}
    </div>
  );

  const renderBasicSettings = () => (
    <div className="grid">
      <div className="col-12 md:col-6">
        <EnhancedCard title="Auto-Approval Settings" variant="outlined" className="h-full">
          <div className="flex align-items-center justify-content-between mb-4">
            <label className="font-semibold">Enable Auto-Approval</label>
            <InputSwitch
              checked={config.autoApproveEnabled}
              onChange={(e) => handleConfigChange('autoApproveEnabled', e.value)}
            />
          </div>
          
          {config.autoApproveEnabled && (
            <div className="mt-4">
              {renderThresholdSlider(
                'Auto-Approval Confidence',
                config.autoApproveThreshold,
                (value) => handleConfigChange('autoApproveThreshold', value),
                70,
                98,
                2,
                'Content above this confidence level will be automatically approved for takedown'
              )}
            </div>
          )}
          
          <div className="mt-4 p-3 bg-green-50 border-round">
            <div className="flex align-items-center gap-2">
              <i className="pi pi-check-circle text-green-600" />
              <span className="text-sm">
                Currently saves ~{statistics.timesSaved} hours per week
              </span>
            </div>
          </div>
        </EnhancedCard>
      </div>

      <div className="col-12 md:col-6">
        <EnhancedCard title="Auto-Rejection Settings" variant="outlined" className="h-full">
          {renderThresholdSlider(
            'Auto-Rejection Threshold',
            config.autoRejectThreshold,
            (value) => handleConfigChange('autoRejectThreshold', value),
            10,
            60,
            5,
            'Content below this confidence level will be automatically rejected'
          )}
          
          <div className="mt-4 p-3 bg-orange-50 border-round">
            <div className="flex align-items-center gap-2">
              <i className="pi pi-shield text-orange-600" />
              <span className="text-sm">
                False positive rate: {statistics.falsePositiveRate}%
              </span>
            </div>
          </div>
        </EnhancedCard>
      </div>
    </div>
  );

  const renderEscalationSettings = () => (
    <EnhancedCard title="Time-Based Escalation Rules" variant="outlined">
      <div className="grid">
        <div className="col-12 md:col-6">
          <div className="field">
            <label className="font-semibold">Enable Auto-Movement</label>
            <div className="mt-2">
              <InputSwitch
                checked={config.autoMoveEnabled}
                onChange={(e) => handleConfigChange('autoMoveEnabled', e.value)}
              />
            </div>
          </div>
          
          {config.autoMoveEnabled && (
            <div className="field mt-4">
              <label className="font-semibold">Auto-Escalation Time</label>
              <div className="mt-2 flex align-items-center gap-2">
                <InputNumber
                  value={config.autoEscalateHours}
                  onValueChange={(e) => handleConfigChange('autoEscalateHours', e.value || 48)}
                  min={1}
                  max={168}
                  suffix=" hours"
                  className="w-full"
                />
              </div>
              <small className="text-600">
                Tasks will escalate to manual review after this time
              </small>
            </div>
          )}
        </div>

        <div className="col-12 md:col-6">
          <div className="field">
            <label className="font-semibold">Business Hours Only</label>
            <div className="mt-2">
              <InputSwitch
                checked={config.businessHoursOnly}
                onChange={(e) => handleConfigChange('businessHoursOnly', e.value)}
              />
            </div>
            <small className="text-600 block mt-1">
              Restrict automation to business hours (9 AM - 5 PM)
            </small>
          </div>
          
          <div className="field mt-4">
            <label className="font-semibold">Weekend Processing</label>
            <div className="mt-2">
              <InputSwitch
                checked={config.weekendProcessing}
                onChange={(e) => handleConfigChange('weekendProcessing', e.value)}
              />
            </div>
          </div>
        </div>
      </div>
    </EnhancedCard>
  );

  const renderPlatformRules = () => (
    <EnhancedCard title="Platform-Specific Rules" variant="outlined">
      <DataTable
        value={platformRulesData}
        responsiveLayout="scroll"
        className="automation-platform-table"
      >
        <Column 
          field="platform" 
          header="Platform"
          body={(rowData) => (
            <div className="flex align-items-center gap-2">
              <i className={`pi pi-${rowData.platform.toLowerCase()}`} />
              {rowData.platform}
            </div>
          )}
        />
        <Column 
          field="autoApproveThreshold" 
          header="Auto-Approve %"
          body={(rowData) => (
            <InputNumber
              value={rowData.autoApproveThreshold}
              onValueChange={(e) => 
                handlePlatformRuleChange(rowData.platform, 'autoApproveThreshold', e.value)
              }
              min={60}
              max={98}
              suffix="%"
              size={3}
            />
          )}
        />
        <Column 
          field="responseTimeoutHours" 
          header="Timeout (hours)"
          body={(rowData) => (
            <InputNumber
              value={rowData.responseTimeoutHours}
              onValueChange={(e) => 
                handlePlatformRuleChange(rowData.platform, 'responseTimeoutHours', e.value)
              }
              min={1}
              max={168}
              size={3}
            />
          )}
        />
        <Column 
          field="autoEscalate" 
          header="Auto-Escalate"
          body={(rowData) => (
            <InputSwitch
              checked={rowData.autoEscalate}
              onChange={(e) => 
                handlePlatformRuleChange(rowData.platform, 'autoEscalate', e.value)
              }
            />
          )}
        />
        <Column 
          field="preferredTemplate" 
          header="Template"
          body={(rowData) => (
            <Dropdown
              value={rowData.preferredTemplate}
              options={[
                { label: 'Standard', value: 'standard' },
                { label: 'Express', value: 'express' },
                { label: 'Detailed', value: 'detailed' }
              ]}
              onChange={(e) => 
                handlePlatformRuleChange(rowData.platform, 'preferredTemplate', e.value)
              }
              className="w-full"
            />
          )}
        />
      </DataTable>
    </EnhancedCard>
  );

  const renderBatchProcessing = () => (
    <EnhancedCard title="Smart Batching & Grouping" variant="outlined">
      <div className="grid">
        <div className="col-12 md:col-6">
          <div className="field">
            <label className="font-semibold">Enable Smart Grouping</label>
            <div className="mt-2">
              <InputSwitch
                checked={config.smartGroupingEnabled}
                onChange={(e) => handleConfigChange('smartGroupingEnabled', e.value)}
              />
            </div>
            <small className="text-600 block mt-1">
              Automatically group similar infringements for batch processing
            </small>
          </div>

          {config.smartGroupingEnabled && (
            <div className="field mt-4">
              <label className="font-semibold">Minimum Group Size</label>
              <div className="mt-2">
                <InputNumber
                  value={config.minGroupSize}
                  onValueChange={(e) => handleConfigChange('minGroupSize', e.value || 3)}
                  min={2}
                  max={20}
                  className="w-full"
                />
              </div>
            </div>
          )}
        </div>

        <div className="col-12 md:col-6">
          <div className="p-3 bg-blue-50 border-round">
            <h4 className="mt-0 mb-3 text-blue-900">Grouping Methods</h4>
            <ul className="list-none p-0 m-0 text-sm">
              <li className="flex align-items-center gap-2 mb-2">
                <i className="pi pi-check text-blue-600" />
                By platform and similarity
              </li>
              <li className="flex align-items-center gap-2 mb-2">
                <i className="pi pi-check text-blue-600" />
                By content creator profile
              </li>
              <li className="flex align-items-center gap-2 mb-2">
                <i className="pi pi-check text-blue-600" />
                By upload time proximity
              </li>
              <li className="flex align-items-center gap-2">
                <i className="pi pi-check text-blue-600" />
                By content fingerprint match
              </li>
            </ul>
          </div>
        </div>
      </div>
    </EnhancedCard>
  );

  const renderLearningPreferences = () => (
    <EnhancedCard title="Adaptive AI Learning" variant="outlined">
      <div className="grid">
        <div className="col-12 md:col-6">
          <div className="field">
            <label className="font-semibold">Learn from User Actions</label>
            <div className="mt-2">
              <InputSwitch
                checked={config.learnFromUserActions}
                onChange={(e) => handleConfigChange('learnFromUserActions', e.value)}
              />
            </div>
            <small className="text-600 block mt-1">
              AI adjusts based on your approval/rejection patterns
            </small>
          </div>

          <div className="field mt-4">
            <label className="font-semibold">Adaptive Thresholds</label>
            <div className="mt-2">
              <InputSwitch
                checked={config.adaptiveThresholds}
                onChange={(e) => handleConfigChange('adaptiveThresholds', e.value)}
              />
            </div>
            <small className="text-600 block mt-1">
              Automatically adjust confidence thresholds over time
            </small>
          </div>
        </div>

        <div className="col-12 md:col-6">
          <div className="text-center">
            <Knob
              value={statistics.accuracy}
              size={120}
              readOnly
              valueTemplate="{value}%"
              className="mb-3"
            />
            <div className="font-semibold text-900">Model Accuracy</div>
            <div className="text-sm text-600">Based on last 30 days</div>
          </div>
        </div>
      </div>
      
      {(config.learnFromUserActions || config.adaptiveThresholds) && (
        <div className="mt-4 p-3 bg-purple-50 border-round">
          <div className="flex align-items-center gap-2 mb-2">
            <i className="pi pi-brain text-purple-600" />
            <span className="font-semibold text-purple-900">AI Insights</span>
          </div>
          <div className="text-sm text-purple-700">
            System has processed {statistics.totalProcessed} cases and improved accuracy by 12.3% over the past month.
          </div>
        </div>
      )}
    </EnhancedCard>
  );

  const renderTestMode = () => (
    <EnhancedCard title="Test & Preview Mode" variant="outlined">
      <div className="grid">
        <div className="col-12 md:col-8">
          <div className="field">
            <label className="font-semibold">Enable Preview Mode</label>
            <div className="mt-2">
              <InputSwitch
                checked={previewMode.enabled}
                onChange={(e) => setPreviewMode({...previewMode, enabled: e.value})}
              />
            </div>
            <small className="text-600 block mt-1">
              Show what automation would do without executing actions
            </small>
          </div>

          {previewMode.enabled && (
            <div className="field mt-4">
              <label className="font-semibold">Sample Size for Testing</label>
              <div className="mt-2">
                <InputNumber
                  value={previewMode.sampleSize}
                  onValueChange={(e) => setPreviewMode({...previewMode, sampleSize: e.value || 10})}
                  min={1}
                  max={100}
                  className="w-full"
                />
              </div>
            </div>
          )}

          <div className="mt-4">
            <Button
              label={testMode ? "Running Test..." : "Run Test Simulation"}
              icon={testMode ? "pi pi-spin pi-spinner" : "pi pi-play"}
              onClick={runPreview}
              disabled={testMode}
              severity="info"
            />
          </div>
        </div>

        <div className="col-12 md:col-4">
          <div className="text-center">
            <div className="text-6xl mb-2">{previewMode.confidence}%</div>
            <div className="font-semibold text-900">Predicted Accuracy</div>
            <div className="text-sm text-600">With current settings</div>
          </div>
        </div>
      </div>

      {previewMode.enabled && (
        <div className="mt-4 p-3 bg-yellow-50 border-round">
          <div className="flex align-items-center gap-2">
            <i className="pi pi-exclamation-triangle text-yellow-600" />
            <span className="text-yellow-800">
              Preview mode active - automation actions will be logged but not executed
            </span>
          </div>
        </div>
      )}
    </EnhancedCard>
  );

  const renderStatistics = () => (
    <EnhancedCard title="Automation Effectiveness" variant="outlined">
      <div className="grid">
        <div className="col-12 lg:col-8">
          <div className="grid">
            <div className="col-6 md:col-3">
              <div className="text-center">
                <div className="text-4xl font-bold text-blue-600 mb-1">
                  {statistics.totalProcessed.toLocaleString()}
                </div>
                <div className="text-sm text-600">Total Processed</div>
              </div>
            </div>
            <div className="col-6 md:col-3">
              <div className="text-center">
                <div className="text-4xl font-bold text-green-600 mb-1">
                  {Math.round((statistics.autoApproved / statistics.totalProcessed) * 100)}%
                </div>
                <div className="text-sm text-600">Auto-Approved</div>
              </div>
            </div>
            <div className="col-6 md:col-3">
              <div className="text-center">
                <div className="text-4xl font-bold text-orange-600 mb-1">
                  {statistics.timesSaved.toFixed(1)}h
                </div>
                <div className="text-sm text-600">Time Saved/Week</div>
              </div>
            </div>
            <div className="col-6 md:col-3">
              <div className="text-center">
                <div className="text-4xl font-bold text-purple-600 mb-1">
                  {statistics.efficiency.toFixed(1)}%
                </div>
                <div className="text-sm text-600">Efficiency</div>
              </div>
            </div>
          </div>

          <Divider />

          <div className="grid">
            <div className="col-12 md:col-6">
              <ProgressBar 
                value={(statistics.autoApproved / statistics.totalProcessed) * 100} 
                showValue={false}
                className="mb-2"
              />
              <div className="flex justify-content-between text-sm">
                <span>Auto-Approved: {statistics.autoApproved}</span>
                <span>{Math.round((statistics.autoApproved / statistics.totalProcessed) * 100)}%</span>
              </div>
            </div>
            <div className="col-12 md:col-6">
              <ProgressBar 
                value={statistics.falsePositiveRate} 
                showValue={false}
                className="mb-2"
                color="#ef4444"
              />
              <div className="flex justify-content-between text-sm">
                <span>False Positive Rate</span>
                <span>{statistics.falsePositiveRate}%</span>
              </div>
            </div>
          </div>
        </div>

        <div className="col-12 lg:col-4">
          <div style={{ height: '200px' }}>
            <Chart type="doughnut" data={efficiencyChartData} options={efficiencyChartOptions} />
          </div>
        </div>
      </div>
    </EnhancedCard>
  );

  return (
    <div className="automation-settings">
      <div className="flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="text-3xl font-bold text-900 mt-0 mb-2">Automation Settings</h2>
          <p className="text-600 mt-0">
            Configure intelligent automation to streamline your content protection workflow
          </p>
        </div>

        <div className="flex align-items-center gap-3">
          <SelectButton
            value={complexityLevel}
            onChange={(e) => setComplexityLevel(e.value)}
            options={complexityLevels}
            size="small"
          />
          
          {hasUnsavedChanges && (
            <Tag severity="warning" value="Unsaved Changes" />
          )}
        </div>
      </div>

      {previewMode.enabled && (
        <Message 
          severity="warn" 
          text="Preview mode is active - changes will be simulated but not executed"
          className="mb-4"
        />
      )}

      <div className="grid">
        <div className="col-12">
          {renderStatistics()}
        </div>

        <div className="col-12">
          <Accordion activeIndex={activeAccordion} onTabChange={(e) => setActiveAccordion(e.index as number)}>
            <AccordionTab header="Auto-Approval & Rejection Thresholds">
              {renderBasicSettings()}
            </AccordionTab>

            <AccordionTab header="Time-Based Escalation Rules">
              {renderEscalationSettings()}
            </AccordionTab>

            <AccordionTab header="Platform-Specific Configuration">
              {renderPlatformRules()}
            </AccordionTab>

            <AccordionTab header="Smart Batching & Grouping">
              {renderBatchProcessing()}
            </AccordionTab>

            <AccordionTab header="Adaptive AI Learning">
              {renderLearningPreferences()}
            </AccordionTab>

            <AccordionTab header="Test & Preview Mode">
              {renderTestMode()}
            </AccordionTab>
          </Accordion>
        </div>
      </div>

      {/* Action Bar */}
      <div className="fixed-bottom-bar bg-white border-top-1 surface-border p-3">
        <div className="flex justify-content-between align-items-center max-w-screen-xl mx-auto">
          <div className="flex align-items-center gap-3">
            <Button
              label="Reset to Defaults"
              icon="pi pi-refresh"
              severity="secondary"
              outlined
              onClick={resetToDefaults}
            />
            
            {complexityLevel === 'advanced' && (
              <Button
                label="Export Configuration"
                icon="pi pi-download"
                severity="secondary"
                outlined
                onClick={() => {
                  const dataStr = JSON.stringify(config, null, 2);
                  const dataBlob = new Blob([dataStr], {type: 'application/json'});
                  const url = URL.createObjectURL(dataBlob);
                  const link = document.createElement('a');
                  link.href = url;
                  link.download = 'automation-config.json';
                  link.click();
                  URL.revokeObjectURL(url);
                }}
              />
            )}
          </div>

          <div className="flex align-items-center gap-2">
            <Button
              label="Save Configuration"
              icon="pi pi-save"
              disabled={!hasUnsavedChanges}
              onClick={saveConfiguration}
            />
          </div>
        </div>
      </div>

      <ConfirmDialog 
        visible={showConfirmDialog}
        onHide={() => setShowConfirmDialog(false)}
        message="Are you sure you want to reset all settings to their default values? This action cannot be undone."
        header="Reset Configuration"
        icon="pi pi-exclamation-triangle"
        accept={confirmReset}
        acceptClassName="p-button-danger"
      />

    </div>
  );
};

export default AutomationSettings;