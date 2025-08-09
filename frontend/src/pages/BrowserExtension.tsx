import React, { useState, useEffect } from 'react';
import { Card } from 'primereact/card';
import { TabView, TabPanel } from 'primereact/tabview';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Button } from 'primereact/button';
import { Badge } from 'primereact/badge';
import { Tag } from 'primereact/tag';
import { InputSwitch } from 'primereact/inputswitch';
import { Panel } from 'primereact/panel';
import { Timeline } from 'primereact/timeline';
import { Steps } from 'primereact/steps';
import { Divider } from 'primereact/divider';
import { Chip } from 'primereact/chip';
import { ProgressBar } from 'primereact/progressbar';
import { Skeleton } from 'primereact/skeleton';
import { Dialog } from 'primereact/dialog';
import { InputText } from 'primereact/inputtext';
import { Dropdown } from 'primereact/dropdown';
import { Message } from 'primereact/message';
import { Avatar } from 'primereact/avatar';
import { ConfirmDialog } from 'primereact/confirmdialog';
import { confirmDialog } from 'primereact/confirmdialog';
import { Toast } from 'primereact/toast';
import { useRef } from 'react';

// Browser Extension specific types
interface BrowserExtension {
  id: string;
  name: string;
  browser: 'chrome' | 'firefox' | 'edge' | 'safari';
  version: string;
  isInstalled: boolean;
  isActive: boolean;
  lastSync: string;
  downloadUrl: string;
  storeUrl: string;
  icon: string;
  permissions: string[];
}

interface ExtensionActivity {
  id: string;
  action: string;
  url: string;
  timestamp: string;
  success: boolean;
  platform?: string;
  details?: string;
}

interface ExtensionSettings {
  autoDetection: boolean;
  contextMenu: boolean;
  notifications: boolean;
  bulkSelection: boolean;
  autoReporting: boolean;
  dataCollection: boolean;
  syncSettings: boolean;
  quickActions: boolean;
}

interface InstallationStep {
  label: string;
  command?: string;
}

const BrowserExtension: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState(0);
  const [extensions, setExtensions] = useState<BrowserExtension[]>([]);
  const [activities, setActivities] = useState<ExtensionActivity[]>([]);
  const [settings, setSettings] = useState<ExtensionSettings>({
    autoDetection: true,
    contextMenu: true,
    notifications: true,
    bulkSelection: false,
    autoReporting: false,
    dataCollection: true,
    syncSettings: true,
    quickActions: true
  });
  const [showPermissionsDialog, setShowPermissionsDialog] = useState(false);
  const [selectedExtension, setSelectedExtension] = useState<BrowserExtension | null>(null);
  const [activeStep, setActiveStep] = useState(0);
  const toast = useRef<Toast>(null);

  // Mock data - replace with API calls
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      
      // Simulate API call
      setTimeout(() => {
        setExtensions([
          {
            id: 'chrome-ext-1',
            name: 'AutoDMCA Chrome Extension',
            browser: 'chrome',
            version: '2.1.5',
            isInstalled: true,
            isActive: true,
            lastSync: '2025-01-09T14:30:00Z',
            downloadUrl: '/downloads/autodmca-chrome-extension.zip',
            storeUrl: 'https://chrome.google.com/webstore/detail/autodmca/abc123',
            icon: 'pi pi-chrome',
            permissions: ['activeTab', 'contextMenus', 'storage', 'notifications']
          },
          {
            id: 'firefox-ext-1',
            name: 'AutoDMCA Firefox Add-on',
            browser: 'firefox',
            version: '2.1.3',
            isInstalled: false,
            isActive: false,
            lastSync: '',
            downloadUrl: '/downloads/autodmca-firefox-addon.xpi',
            storeUrl: 'https://addons.mozilla.org/firefox/addon/autodmca/',
            icon: 'pi pi-firefox',
            permissions: ['activeTab', 'contextMenus', 'storage', 'notifications']
          },
          {
            id: 'edge-ext-1',
            name: 'AutoDMCA Edge Extension',
            browser: 'edge',
            version: '2.1.4',
            isInstalled: false,
            isActive: false,
            lastSync: '',
            downloadUrl: '/downloads/autodmca-edge-extension.zip',
            storeUrl: 'https://microsoftedge.microsoft.com/addons/detail/autodmca/def456',
            icon: 'pi pi-microsoft',
            permissions: ['activeTab', 'contextMenus', 'storage', 'notifications']
          }
        ]);

        setActivities([
          {
            id: '1',
            action: 'Content Reported',
            url: 'https://example.com/infringing-content',
            timestamp: '2025-01-09T14:30:00Z',
            success: true,
            platform: 'Generic Website',
            details: 'Image detected and reported automatically'
          },
          {
            id: '2',
            action: 'Bulk Selection',
            url: 'https://social-platform.com/user/profile',
            timestamp: '2025-01-09T13:15:00Z',
            success: true,
            platform: 'Social Media',
            details: '5 images selected for reporting'
          },
          {
            id: '3',
            action: 'Context Menu Used',
            url: 'https://another-site.com/gallery',
            timestamp: '2025-01-09T12:45:00Z',
            success: true,
            platform: 'Image Gallery',
            details: 'Right-click report initiated'
          },
          {
            id: '4',
            action: 'Auto-Detection Triggered',
            url: 'https://marketplace.com/listings',
            timestamp: '2025-01-09T11:20:00Z',
            success: false,
            platform: 'Marketplace',
            details: 'Detection failed - content analysis error'
          }
        ]);

        setLoading(false);
      }, 1500);
    };

    loadData();
  }, []);

  const installationSteps: InstallationStep[] = [
    { label: 'Download Extension' },
    { label: 'Install in Browser' },
    { label: 'Grant Permissions' },
    { label: 'Sign In to AutoDMCA' },
    { label: 'Configure Settings' },
    { label: 'Test Extension' }
  ];

  const handleInstallExtension = (extension: BrowserExtension) => {
    confirmDialog({
      message: `This will redirect you to the ${extension.browser} extension store. Continue?`,
      header: 'Install Extension',
      icon: 'pi pi-download',
      accept: () => {
        window.open(extension.storeUrl, '_blank');
        toast.current?.show({
          severity: 'info',
          summary: 'Installation Started',
          detail: `Opening ${extension.browser} extension store...`,
          life: 3000
        });
      }
    });
  };

  const handleToggleExtension = (extensionId: string, active: boolean) => {
    setExtensions(prev =>
      prev.map(ext =>
        ext.id === extensionId ? { ...ext, isActive: active } : ext
      )
    );
    
    toast.current?.show({
      severity: active ? 'success' : 'info',
      summary: active ? 'Extension Activated' : 'Extension Deactivated',
      detail: `Extension is now ${active ? 'active' : 'inactive'}`,
      life: 3000
    });
  };

  const handleSettingsChange = (key: keyof ExtensionSettings, value: boolean) => {
    setSettings(prev => ({ ...prev, [key]: value }));
    
    toast.current?.show({
      severity: 'success',
      summary: 'Settings Updated',
      detail: `${key} has been ${value ? 'enabled' : 'disabled'}`,
      life: 2000
    });
  };

  const getBrowserIcon = (browser: string) => {
    switch (browser) {
      case 'chrome': return 'pi pi-chrome';
      case 'firefox': return 'pi pi-firefox';
      case 'edge': return 'pi pi-microsoft';
      case 'safari': return 'pi pi-apple';
      default: return 'pi pi-globe';
    }
  };

  const getBrowserColor = (browser: string) => {
    switch (browser) {
      case 'chrome': return '#4285f4';
      case 'firefox': return '#ff6611';
      case 'edge': return '#0078d4';
      case 'safari': return '#007aff';
      default: return '#6c757d';
    }
  };

  const getStatusSeverity = (success: boolean) => {
    return success ? 'success' : 'danger';
  };

  const renderExtensionStatus = (extension: BrowserExtension) => {
    if (!extension.isInstalled) {
      return <Badge value="Not Installed" severity="warning" />;
    }
    if (!extension.isActive) {
      return <Badge value="Inactive" severity="secondary" />;
    }
    return <Badge value="Active" severity="success" />;
  };

  const renderActivityIcon = (activity: ExtensionActivity) => {
    const iconMap = {
      'Content Reported': 'pi pi-flag',
      'Bulk Selection': 'pi pi-clone',
      'Context Menu Used': 'pi pi-cursor',
      'Auto-Detection Triggered': 'pi pi-eye'
    };
    
    return (
      <div className={`flex align-items-center justify-content-center w-3rem h-3rem border-circle ${
        activity.success ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'
      }`}>
        <i className={iconMap[activity.action as keyof typeof iconMap] || 'pi pi-circle'} />
      </div>
    );
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="mb-6">
          <Skeleton width="20rem" height="2rem" className="mb-2" />
          <Skeleton width="30rem" height="1rem" />
        </div>
        
        <div className="grid">
          <div className="col-12 lg:col-8">
            <Card>
              <Skeleton width="100%" height="20rem" />
            </Card>
          </div>
          <div className="col-12 lg:col-4">
            <Card>
              <Skeleton width="100%" height="20rem" />
            </Card>
          </div>
        </div>
      </div>
    );
  }

  const installedExtensions = extensions.filter(ext => ext.isInstalled);
  const activeExtensions = extensions.filter(ext => ext.isInstalled && ext.isActive);

  return (
    <div className="browser-extension-page">
      <Toast ref={toast} />
      <ConfirmDialog />
      
      {/* Page Header */}
      <div className="flex justify-content-between align-items-start mb-6">
        <div>
          <h1 className="text-3xl font-bold text-900 m-0 mb-2">
            Browser Extensions
          </h1>
          <p className="text-600 text-lg m-0">
            Install and manage AutoDMCA browser extensions for instant content protection
          </p>
        </div>
        
        <div className="flex gap-2">
          <Chip 
            label={`${installedExtensions.length} Installed`} 
            icon="pi pi-download" 
            className="bg-blue-100 text-blue-800"
          />
          <Chip 
            label={`${activeExtensions.length} Active`} 
            icon="pi pi-check-circle" 
            className="bg-green-100 text-green-800"
          />
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid mb-6">
        <div className="col-12 md:col-3">
          <Card className="bg-blue-50 border-blue-200 h-full">
            <div className="flex align-items-center">
              <div className="flex align-items-center justify-content-center bg-blue-100 border-circle" style={{width: '3rem', height: '3rem'}}>
                <i className="pi pi-download text-blue-600 text-xl" />
              </div>
              <div className="ml-3">
                <div className="text-blue-900 font-medium text-lg">{installedExtensions.length}</div>
                <div className="text-blue-700 text-sm">Installed Extensions</div>
              </div>
            </div>
          </Card>
        </div>
        
        <div className="col-12 md:col-3">
          <Card className="bg-green-50 border-green-200 h-full">
            <div className="flex align-items-center">
              <div className="flex align-items-center justify-content-center bg-green-100 border-circle" style={{width: '3rem', height: '3rem'}}>
                <i className="pi pi-check-circle text-green-600 text-xl" />
              </div>
              <div className="ml-3">
                <div className="text-green-900 font-medium text-lg">{activeExtensions.length}</div>
                <div className="text-green-700 text-sm">Active Extensions</div>
              </div>
            </div>
          </Card>
        </div>
        
        <div className="col-12 md:col-3">
          <Card className="bg-orange-50 border-orange-200 h-full">
            <div className="flex align-items-center">
              <div className="flex align-items-center justify-content-center bg-orange-100 border-circle" style={{width: '3rem', height: '3rem'}}>
                <i className="pi pi-clock text-orange-600 text-xl" />
              </div>
              <div className="ml-3">
                <div className="text-orange-900 font-medium text-lg">{activities.length}</div>
                <div className="text-orange-700 text-sm">Recent Activities</div>
              </div>
            </div>
          </Card>
        </div>
        
        <div className="col-12 md:col-3">
          <Card className="bg-purple-50 border-purple-200 h-full">
            <div className="flex align-items-center">
              <div className="flex align-items-center justify-content-center bg-purple-100 border-circle" style={{width: '3rem', height: '3rem'}}>
                <i className="pi pi-shield text-purple-600 text-xl" />
              </div>
              <div className="ml-3">
                <div className="text-purple-900 font-medium text-lg">98%</div>
                <div className="text-purple-700 text-sm">Success Rate</div>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Main Content Tabs */}
      <Card>
        <TabView activeIndex={activeTab} onTabChange={(e) => setActiveTab(e.index)}>
          
          {/* Extensions Overview Tab */}
          <TabPanel header="Extensions" leftIcon="pi pi-download mr-2">
            <div className="grid">
              {extensions.map((extension) => (
                <div key={extension.id} className="col-12 lg:col-6 mb-4">
                  <Card className="h-full">
                    <div className="flex align-items-start justify-content-between mb-4">
                      <div className="flex align-items-center">
                        <Avatar 
                          icon={getBrowserIcon(extension.browser)}
                          style={{ 
                            backgroundColor: getBrowserColor(extension.browser),
                            color: 'white'
                          }}
                          size="large"
                        />
                        <div className="ml-3">
                          <div className="font-semibold text-lg">{extension.name}</div>
                          <div className="text-600 text-sm">Version {extension.version}</div>
                        </div>
                      </div>
                      {renderExtensionStatus(extension)}
                    </div>
                    
                    <div className="mb-4">
                      <div className="flex align-items-center justify-content-between mb-2">
                        <span className="text-600">Browser:</span>
                        <Chip 
                          label={extension.browser.charAt(0).toUpperCase() + extension.browser.slice(1)}
                          icon={getBrowserIcon(extension.browser)}
                          style={{ backgroundColor: getBrowserColor(extension.browser), color: 'white' }}
                        />
                      </div>
                      
                      {extension.isInstalled && (
                        <div className="flex align-items-center justify-content-between mb-2">
                          <span className="text-600">Last Sync:</span>
                          <span className="text-900">
                            {new Date(extension.lastSync).toLocaleDateString()}
                          </span>
                        </div>
                      )}
                    </div>
                    
                    <div className="flex gap-2 flex-wrap">
                      {!extension.isInstalled ? (
                        <>
                          <Button
                            label="Install"
                            icon="pi pi-download"
                            severity="success"
                            onClick={() => handleInstallExtension(extension)}
                          />
                          <Button
                            label="Manual Download"
                            icon="pi pi-file"
                            outlined
                            onClick={() => window.open(extension.downloadUrl)}
                          />
                        </>
                      ) : (
                        <>
                          <div className="flex align-items-center">
                            <span className="mr-2">Active:</span>
                            <InputSwitch
                              checked={extension.isActive}
                              onChange={(e) => handleToggleExtension(extension.id, e.value)}
                            />
                          </div>
                          <Button
                            label="Permissions"
                            icon="pi pi-shield"
                            outlined
                            size="small"
                            onClick={() => {
                              setSelectedExtension(extension);
                              setShowPermissionsDialog(true);
                            }}
                          />
                          <Button
                            label="Update"
                            icon="pi pi-refresh"
                            outlined
                            size="small"
                          />
                        </>
                      )}
                    </div>
                  </Card>
                </div>
              ))}
            </div>
          </TabPanel>

          {/* Installation Guide Tab */}
          <TabPanel header="Installation Guide" leftIcon="pi pi-book mr-2">
            <div className="grid">
              <div className="col-12 lg:col-8">
                <Card title="Step-by-Step Installation">
                  <Steps 
                    model={installationSteps} 
                    activeIndex={activeStep}
                    onSelect={(e) => setActiveStep(e.index)}
                    readOnly={false}
                  />
                  
                  <Divider />
                  
                  <div className="installation-step-content">
                    {activeStep === 0 && (
                      <div>
                        <h3>Download Extension</h3>
                        <p>Choose your browser and download the appropriate extension:</p>
                        <div className="flex gap-3 flex-wrap">
                          {extensions.map((ext) => (
                            <Button
                              key={ext.id}
                              label={`Download for ${ext.browser}`}
                              icon={getBrowserIcon(ext.browser)}
                              onClick={() => handleInstallExtension(ext)}
                              className="mb-2"
                            />
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {activeStep === 1 && (
                      <div>
                        <h3>Install in Browser</h3>
                        <p>Follow these browser-specific instructions:</p>
                        <Panel header="Chrome" className="mb-3">
                          <ol>
                            <li>Open Chrome and navigate to <code>chrome://extensions/</code></li>
                            <li>Enable "Developer mode" in the top right</li>
                            <li>Click "Load unpacked" and select the extension folder</li>
                            <li>The extension will appear in your browser toolbar</li>
                          </ol>
                        </Panel>
                        <Panel header="Firefox" className="mb-3">
                          <ol>
                            <li>Open Firefox and navigate to <code>about:addons</code></li>
                            <li>Click the gear icon and select "Install Add-on From File..."</li>
                            <li>Select the downloaded .xpi file</li>
                            <li>Click "Add" to install the extension</li>
                          </ol>
                        </Panel>
                      </div>
                    )}
                    
                    {activeStep === 2 && (
                      <div>
                        <h3>Grant Permissions</h3>
                        <p>The extension requires the following permissions:</p>
                        <ul>
                          <li><strong>Active Tab:</strong> To analyze content on the current page</li>
                          <li><strong>Context Menus:</strong> To add right-click reporting options</li>
                          <li><strong>Storage:</strong> To save your preferences and settings</li>
                          <li><strong>Notifications:</strong> To alert you about detected content</li>
                        </ul>
                        <Message severity="info" text="All permissions are used solely for AutoDMCA functionality and your data remains secure." />
                      </div>
                    )}
                    
                    {/* Continue with other steps... */}
                  </div>
                </Card>
              </div>
              
              <div className="col-12 lg:col-4">
                <Card title="Quick Start">
                  <div className="mb-4">
                    <h4>Browser Support</h4>
                    <div className="flex flex-column gap-2">
                      <div className="flex align-items-center">
                        <i className="pi pi-chrome text-blue-500 mr-2" />
                        <span>Chrome 88+</span>
                        <Badge value="Stable" severity="success" className="ml-auto" />
                      </div>
                      <div className="flex align-items-center">
                        <i className="pi pi-firefox text-orange-500 mr-2" />
                        <span>Firefox 85+</span>
                        <Badge value="Stable" severity="success" className="ml-auto" />
                      </div>
                      <div className="flex align-items-center">
                        <i className="pi pi-microsoft text-blue-600 mr-2" />
                        <span>Edge 88+</span>
                        <Badge value="Beta" severity="warning" className="ml-auto" />
                      </div>
                    </div>
                  </div>
                  
                  <div className="mb-4">
                    <h4>Features</h4>
                    <ul className="list-none p-0">
                      <li className="flex align-items-center mb-2">
                        <i className="pi pi-check text-green-500 mr-2" />
                        <span>Right-click reporting</span>
                      </li>
                      <li className="flex align-items-center mb-2">
                        <i className="pi pi-check text-green-500 mr-2" />
                        <span>Auto-detection</span>
                      </li>
                      <li className="flex align-items-center mb-2">
                        <i className="pi pi-check text-green-500 mr-2" />
                        <span>Bulk operations</span>
                      </li>
                      <li className="flex align-items-center mb-2">
                        <i className="pi pi-check text-green-500 mr-2" />
                        <span>Real-time sync</span>
                      </li>
                    </ul>
                  </div>
                  
                  <Button
                    label="Download Now"
                    icon="pi pi-download"
                    className="w-full"
                    onClick={() => handleInstallExtension(extensions[0])}
                  />
                </Card>
              </div>
            </div>
          </TabPanel>

          {/* Settings Tab */}
          <TabPanel header="Settings" leftIcon="pi pi-cog mr-2">
            <div className="grid">
              <div className="col-12 lg:col-8">
                <Card title="Extension Settings">
                  <div className="flex flex-column gap-4">
                    
                    <Panel header="Detection & Reporting" toggleable>
                      <div className="flex flex-column gap-3">
                        <div className="flex align-items-center justify-content-between">
                          <div>
                            <div className="font-medium">Auto-Detection</div>
                            <div className="text-600 text-sm">Automatically detect protected content on web pages</div>
                          </div>
                          <InputSwitch
                            checked={settings.autoDetection}
                            onChange={(e) => handleSettingsChange('autoDetection', e.value)}
                          />
                        </div>
                        
                        <div className="flex align-items-center justify-content-between">
                          <div>
                            <div className="font-medium">Context Menu</div>
                            <div className="text-600 text-sm">Enable right-click reporting options</div>
                          </div>
                          <InputSwitch
                            checked={settings.contextMenu}
                            onChange={(e) => handleSettingsChange('contextMenu', e.value)}
                          />
                        </div>
                        
                        <div className="flex align-items-center justify-content-between">
                          <div>
                            <div className="font-medium">Auto-Reporting</div>
                            <div className="text-600 text-sm">Automatically submit takedown requests for high-confidence matches</div>
                          </div>
                          <InputSwitch
                            checked={settings.autoReporting}
                            onChange={(e) => handleSettingsChange('autoReporting', e.value)}
                          />
                        </div>
                      </div>
                    </Panel>
                    
                    <Panel header="User Interface" toggleable>
                      <div className="flex flex-column gap-3">
                        <div className="flex align-items-center justify-content-between">
                          <div>
                            <div className="font-medium">Notifications</div>
                            <div className="text-600 text-sm">Show browser notifications for detected content</div>
                          </div>
                          <InputSwitch
                            checked={settings.notifications}
                            onChange={(e) => handleSettingsChange('notifications', e.value)}
                          />
                        </div>
                        
                        <div className="flex align-items-center justify-content-between">
                          <div>
                            <div className="font-medium">Bulk Selection</div>
                            <div className="text-600 text-sm">Enable multi-select interface for batch operations</div>
                          </div>
                          <InputSwitch
                            checked={settings.bulkSelection}
                            onChange={(e) => handleSettingsChange('bulkSelection', e.value)}
                          />
                        </div>
                        
                        <div className="flex align-items-center justify-content-between">
                          <div>
                            <div className="font-medium">Quick Actions</div>
                            <div className="text-600 text-sm">Show quick action buttons on detected content</div>
                          </div>
                          <InputSwitch
                            checked={settings.quickActions}
                            onChange={(e) => handleSettingsChange('quickActions', e.value)}
                          />
                        </div>
                      </div>
                    </Panel>
                    
                    <Panel header="Privacy & Data" toggleable>
                      <div className="flex flex-column gap-3">
                        <div className="flex align-items-center justify-content-between">
                          <div>
                            <div className="font-medium">Data Collection</div>
                            <div className="text-600 text-sm">Allow anonymous usage data collection for improvements</div>
                          </div>
                          <InputSwitch
                            checked={settings.dataCollection}
                            onChange={(e) => handleSettingsChange('dataCollection', e.value)}
                          />
                        </div>
                        
                        <div className="flex align-items-center justify-content-between">
                          <div>
                            <div className="font-medium">Sync Settings</div>
                            <div className="text-600 text-sm">Synchronize settings across all your devices</div>
                          </div>
                          <InputSwitch
                            checked={settings.syncSettings}
                            onChange={(e) => handleSettingsChange('syncSettings', e.value)}
                          />
                        </div>
                      </div>
                    </Panel>
                  </div>
                </Card>
              </div>
              
              <div className="col-12 lg:col-4">
                <Card title="Privacy Information" className="mb-4">
                  <div className="flex flex-column gap-3">
                    <div className="flex align-items-start">
                      <i className="pi pi-shield text-green-500 mr-2 mt-1" />
                      <div>
                        <div className="font-medium text-sm">Secure Communication</div>
                        <div className="text-600 text-xs">All data is encrypted in transit</div>
                      </div>
                    </div>
                    <div className="flex align-items-start">
                      <i className="pi pi-lock text-blue-500 mr-2 mt-1" />
                      <div>
                        <div className="font-medium text-sm">Local Storage</div>
                        <div className="text-600 text-xs">Settings stored locally on your device</div>
                      </div>
                    </div>
                    <div className="flex align-items-start">
                      <i className="pi pi-eye-slash text-purple-500 mr-2 mt-1" />
                      <div>
                        <div className="font-medium text-sm">No Personal Data</div>
                        <div className="text-600 text-xs">We don't collect personal browsing data</div>
                      </div>
                    </div>
                  </div>
                  
                  <Divider />
                  
                  <Button
                    label="View Privacy Policy"
                    icon="pi pi-external-link"
                    text
                    className="w-full"
                  />
                </Card>
                
                <Card title="Extension Status">
                  <div className="flex flex-column gap-2">
                    <div className="flex justify-content-between align-items-center">
                      <span>Chrome Extension</span>
                      <Tag value="Active" severity="success" />
                    </div>
                    <div className="flex justify-content-between align-items-center">
                      <span>Firefox Add-on</span>
                      <Tag value="Not Installed" severity="warning" />
                    </div>
                    <div className="flex justify-content-between align-items-center">
                      <span>Edge Extension</span>
                      <Tag value="Not Installed" severity="warning" />
                    </div>
                  </div>
                  
                  <Divider />
                  
                  <div className="text-center">
                    <div className="text-2xl font-bold text-900 mb-1">98.5%</div>
                    <div className="text-600 text-sm">Overall Success Rate</div>
                    <ProgressBar value={98.5} className="mt-2" />
                  </div>
                </Card>
              </div>
            </div>
          </TabPanel>

          {/* Activity Monitor Tab */}
          <TabPanel header="Activity" leftIcon="pi pi-chart-line mr-2">
            <div className="grid">
              <div className="col-12 lg:col-8">
                <Card title="Extension Activity Log">
                  <DataTable
                    value={activities}
                    paginator
                    rows={10}
                    responsiveLayout="scroll"
                    emptyMessage="No activity recorded yet"
                  >
                    <Column 
                      field="action" 
                      header="Action" 
                      body={(activity) => (
                        <div className="flex align-items-center">
                          <Tag 
                            value={activity.action} 
                            severity={getStatusSeverity(activity.success)}
                            className="mr-2"
                          />
                          {activity.platform && (
                            <Badge value={activity.platform} />
                          )}
                        </div>
                      )}
                    />
                    <Column 
                      field="url" 
                      header="URL" 
                      body={(activity) => (
                        <a 
                          href={activity.url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:text-blue-800"
                        >
                          {activity.url.substring(0, 50)}...
                        </a>
                      )}
                    />
                    <Column 
                      field="timestamp" 
                      header="Time"
                      body={(activity) => new Date(activity.timestamp).toLocaleString()}
                    />
                    <Column 
                      field="success" 
                      header="Status"
                      body={(activity) => (
                        <i className={`pi ${activity.success ? 'pi-check text-green-500' : 'pi-times text-red-500'}`} />
                      )}
                    />
                  </DataTable>
                </Card>
              </div>
              
              <div className="col-12 lg:col-4">
                <Card title="Activity Timeline" className="mb-4">
                  <Timeline
                    value={activities.slice(0, 5)}
                    marker={(activity) => renderActivityIcon(activity)}
                    content={(activity) => (
                      <div className="ml-3">
                        <div className="font-medium text-sm">{activity.action}</div>
                        <div className="text-600 text-xs mb-1">
                          {new Date(activity.timestamp).toLocaleTimeString()}
                        </div>
                        {activity.details && (
                          <div className="text-700 text-xs">{activity.details}</div>
                        )}
                      </div>
                    )}
                  />
                </Card>
                
                <Card title="Quick Actions">
                  <div className="flex flex-column gap-2">
                    <Button
                      label="Refresh Extensions"
                      icon="pi pi-refresh"
                      outlined
                      className="w-full"
                    />
                    <Button
                      label="Clear Activity Log"
                      icon="pi pi-trash"
                      severity="danger"
                      outlined
                      className="w-full"
                    />
                    <Button
                      label="Export Data"
                      icon="pi pi-download"
                      outlined
                      className="w-full"
                    />
                    <Button
                      label="Test Extension"
                      icon="pi pi-play"
                      outlined
                      className="w-full"
                    />
                  </div>
                </Card>
              </div>
            </div>
          </TabPanel>

        </TabView>
      </Card>

      {/* Permissions Dialog */}
      <Dialog
        visible={showPermissionsDialog}
        onHide={() => setShowPermissionsDialog(false)}
        header={`${selectedExtension?.name} Permissions`}
        style={{ width: '500px' }}
      >
        {selectedExtension && (
          <div className="flex flex-column gap-3">
            <p>This extension requests the following permissions:</p>
            
            {selectedExtension.permissions.map((permission, index) => (
              <div key={index} className="flex align-items-start gap-3">
                <i className="pi pi-shield text-blue-500 mt-1" />
                <div>
                  <div className="font-medium">{permission}</div>
                  <div className="text-600 text-sm">
                    {permission === 'activeTab' && 'Access to view and analyze content on the current browser tab'}
                    {permission === 'contextMenus' && 'Add right-click menu options for quick reporting'}
                    {permission === 'storage' && 'Save extension settings and preferences locally'}
                    {permission === 'notifications' && 'Display desktop notifications for detected content'}
                  </div>
                </div>
              </div>
            ))}
            
            <Divider />
            
            <div className="flex justify-content-end gap-2">
              <Button
                label="Revoke All"
                icon="pi pi-times"
                severity="danger"
                outlined
                onClick={() => setShowPermissionsDialog(false)}
              />
              <Button
                label="Close"
                onClick={() => setShowPermissionsDialog(false)}
              />
            </div>
          </div>
        )}
      </Dialog>
    </div>
  );
};

export default BrowserExtension;