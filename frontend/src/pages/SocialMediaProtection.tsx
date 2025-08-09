import React, { useState, useEffect } from 'react';
import { TabView, TabPanel } from 'primereact/tabview';
import { Card } from 'primereact/card';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Button } from 'primereact/button';
import { Dialog } from 'primereact/dialog';
import { FileUpload } from 'primereact/fileupload';
import { Timeline } from 'primereact/timeline';
import { Tag } from 'primereact/tag';
import { Badge } from 'primereact/badge';
import { InputText } from 'primereact/inputtext';
import { Dropdown } from 'primereact/dropdown';
import { InputTextarea } from 'primereact/inputtextarea';
import { SelectButton } from 'primereact/selectbutton';
import { ProgressBar } from 'primereact/progressbar';
import { Chart } from 'primereact/chart';
import { Splitter, SplitterPanel } from 'primereact/splitter';
import { Panel } from 'primereact/panel';
import { Divider } from 'primereact/divider';
import { Message } from 'primereact/message';
import { Checkbox } from 'primereact/checkbox';
import { InputNumber } from 'primereact/inputnumber';
import { Calendar } from 'primereact/calendar';
import { Skeleton } from 'primereact/skeleton';
import { ConfirmDialog, confirmDialog } from 'primereact/confirmdialog';
import { Toast } from 'primereact/toast';
import { Toolbar } from 'primereact/toolbar';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

// Types for Social Media Impersonation Management
interface SocialMediaPlatform {
  id: string;
  name: string;
  icon: string;
  color: string;
  isConnected: boolean;
  lastScan?: Date;
  totalProfiles: number;
  impersonations: number;
  scanStatus: 'idle' | 'scanning' | 'completed' | 'error';
  apiStatus: 'connected' | 'disconnected' | 'limited';
  features: string[];
}

interface ImpersonationIncident {
  id: string;
  platformId: string;
  platform: string;
  profileUrl: string;
  profileName: string;
  detectedAt: Date;
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'detected' | 'reported' | 'under_review' | 'resolved' | 'escalated';
  confidenceScore: number;
  evidenceUrls: string[];
  reportedBy: 'ai' | 'user' | 'manual';
  similarityScore: number;
  estimatedFollowers: number;
  riskLevel: number;
  notes?: string;
}

interface ReportSubmission {
  platformId: string;
  profileUrl: string;
  description: string;
  evidence: File[];
  severity: 'low' | 'medium' | 'high' | 'critical';
  contactAttempted: boolean;
  additionalInfo?: string;
}

interface IdentityVerification {
  id: string;
  userId: string;
  documents: File[];
  status: 'pending' | 'approved' | 'rejected' | 'expired';
  submittedAt: Date;
  reviewedAt?: Date;
  expiresAt?: Date;
  notes?: string;
}

interface CaseProgression {
  id: string;
  incidentId: string;
  status: string;
  timestamp: Date;
  action: string;
  actor: string;
  notes?: string;
  attachments?: string[];
}

interface AutomationRule {
  id: string;
  name: string;
  platform: string;
  trigger: 'similarity_threshold' | 'keyword_match' | 'image_match';
  threshold: number;
  action: 'report' | 'escalate' | 'notify';
  isActive: boolean;
  createdAt: Date;
}

const SocialMediaProtection: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  
  // State management
  const [loading, setLoading] = useState(true);
  const [activeTabIndex, setActiveTabIndex] = useState(0);
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>([]);
  const [showReportDialog, setShowReportDialog] = useState(false);
  const [showVerificationDialog, setShowVerificationDialog] = useState(false);
  const [showDetailsDialog, setShowDetailsDialog] = useState(false);
  const [selectedIncident, setSelectedIncident] = useState<ImpersonationIncident | null>(null);
  const [globalFilter, setGlobalFilter] = useState('');
  const [selectedIncidents, setSelectedIncidents] = useState<ImpersonationIncident[]>([]);
  const [reportSubmission, setReportSubmission] = useState<ReportSubmission>({
    platformId: '',
    profileUrl: '',
    description: '',
    evidence: [],
    severity: 'medium',
    contactAttempted: false,
    additionalInfo: ''
  });

  // Mock data - in production, this would come from API
  const [platforms, setPlatforms] = useState<SocialMediaPlatform[]>([
    {
      id: 'instagram',
      name: 'Instagram',
      icon: 'pi pi-instagram',
      color: '#E4405F',
      isConnected: true,
      lastScan: new Date(Date.now() - 2 * 60 * 60 * 1000),
      totalProfiles: 12500,
      impersonations: 8,
      scanStatus: 'completed',
      apiStatus: 'connected',
      features: ['Profile Matching', 'Image Recognition', 'Story Monitoring']
    },
    {
      id: 'facebook',
      name: 'Facebook',
      icon: 'pi pi-facebook',
      color: '#1877F2',
      isConnected: true,
      lastScan: new Date(Date.now() - 1 * 60 * 60 * 1000),
      totalProfiles: 8200,
      impersonations: 5,
      scanStatus: 'scanning',
      apiStatus: 'connected',
      features: ['Profile Matching', 'Page Monitoring', 'Group Scanning']
    },
    {
      id: 'twitter',
      name: 'Twitter/X',
      icon: 'pi pi-twitter',
      color: '#1DA1F2',
      isConnected: false,
      lastScan: new Date(Date.now() - 24 * 60 * 60 * 1000),
      totalProfiles: 15300,
      impersonations: 12,
      scanStatus: 'error',
      apiStatus: 'limited',
      features: ['Tweet Monitoring', 'Handle Matching', 'Bio Analysis']
    },
    {
      id: 'tiktok',
      name: 'TikTok',
      icon: 'pi pi-video',
      color: '#FF0050',
      isConnected: true,
      lastScan: new Date(Date.now() - 30 * 60 * 1000),
      totalProfiles: 9800,
      impersonations: 6,
      scanStatus: 'completed',
      apiStatus: 'connected',
      features: ['Video Content Matching', 'Username Monitoring']
    },
    {
      id: 'onlyfans',
      name: 'OnlyFans',
      icon: 'pi pi-heart',
      color: '#00AFF0',
      isConnected: true,
      lastScan: new Date(Date.now() - 45 * 60 * 1000),
      totalProfiles: 4200,
      impersonations: 15,
      scanStatus: 'completed',
      apiStatus: 'connected',
      features: ['Profile Monitoring', 'Content Scanning', 'Revenue Protection']
    },
    {
      id: 'telegram',
      name: 'Telegram',
      icon: 'pi pi-send',
      color: '#0088CC',
      isConnected: false,
      lastScan: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000),
      totalProfiles: 2100,
      impersonations: 3,
      scanStatus: 'idle',
      apiStatus: 'disconnected',
      features: ['Channel Monitoring', 'Bot Detection']
    },
    {
      id: 'discord',
      name: 'Discord',
      icon: 'pi pi-comments',
      color: '#5865F2',
      isConnected: true,
      lastScan: new Date(Date.now() - 6 * 60 * 60 * 1000),
      totalProfiles: 1800,
      impersonations: 2,
      scanStatus: 'completed',
      apiStatus: 'connected',
      features: ['Server Monitoring', 'Username Tracking']
    },
    {
      id: 'linkedin',
      name: 'LinkedIn',
      icon: 'pi pi-linkedin',
      color: '#0077B5',
      isConnected: true,
      lastScan: new Date(Date.now() - 12 * 60 * 60 * 1000),
      totalProfiles: 3500,
      impersonations: 1,
      scanStatus: 'completed',
      apiStatus: 'connected',
      features: ['Professional Profile Matching', 'Company Page Monitoring']
    }
  ]);

  const [incidents, setIncidents] = useState<ImpersonationIncident[]>([
    {
      id: '1',
      platformId: 'instagram',
      platform: 'Instagram',
      profileUrl: 'https://instagram.com/fake_profile_1',
      profileName: '@fake_model_abc',
      detectedAt: new Date(Date.now() - 2 * 60 * 60 * 1000),
      severity: 'high',
      status: 'detected',
      confidenceScore: 92,
      evidenceUrls: ['evidence1.jpg', 'evidence2.jpg'],
      reportedBy: 'ai',
      similarityScore: 89,
      estimatedFollowers: 15200,
      riskLevel: 8,
      notes: 'High similarity in profile images and bio content'
    },
    {
      id: '2',
      platformId: 'onlyfans',
      platform: 'OnlyFans',
      profileUrl: 'https://onlyfans.com/fake_profile_2',
      profileName: 'Fake Content Creator',
      detectedAt: new Date(Date.now() - 4 * 60 * 60 * 1000),
      severity: 'critical',
      status: 'reported',
      confidenceScore: 96,
      evidenceUrls: ['evidence3.jpg'],
      reportedBy: 'ai',
      similarityScore: 94,
      estimatedFollowers: 8500,
      riskLevel: 9,
      notes: 'Using original content for revenue generation'
    },
    {
      id: '3',
      platformId: 'twitter',
      platform: 'Twitter/X',
      profileUrl: 'https://x.com/fake_handle',
      profileName: '@impersonator123',
      detectedAt: new Date(Date.now() - 8 * 60 * 60 * 1000),
      severity: 'medium',
      status: 'under_review',
      confidenceScore: 78,
      evidenceUrls: ['evidence4.jpg', 'evidence5.jpg'],
      reportedBy: 'user',
      similarityScore: 75,
      estimatedFollowers: 2300,
      riskLevel: 6,
      notes: 'Similar username pattern and bio content'
    }
  ]);

  const [caseProgression, setCaseProgression] = useState<CaseProgression[]>([
    {
      id: '1',
      incidentId: '1',
      status: 'Detected',
      timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000),
      action: 'AI Detection',
      actor: 'AutoDMCA AI',
      notes: 'Profile detected through image similarity analysis'
    },
    {
      id: '2',
      incidentId: '1',
      status: 'Analyzed',
      timestamp: new Date(Date.now() - 1.5 * 60 * 60 * 1000),
      action: 'Risk Assessment',
      actor: 'AutoDMCA AI',
      notes: 'High risk profile identified'
    },
    {
      id: '3',
      incidentId: '2',
      status: 'Reported',
      timestamp: new Date(Date.now() - 3 * 60 * 60 * 1000),
      action: 'Platform Report Submitted',
      actor: 'AutoDMCA System',
      notes: 'Automated report sent to OnlyFans'
    }
  ]);

  const [automationRules, setAutomationRules] = useState<AutomationRule[]>([
    {
      id: '1',
      name: 'High Similarity Auto-Report',
      platform: 'all',
      trigger: 'similarity_threshold',
      threshold: 85,
      action: 'report',
      isActive: true,
      createdAt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
    },
    {
      id: '2',
      name: 'OnlyFans Revenue Protection',
      platform: 'onlyfans',
      trigger: 'image_match',
      threshold: 90,
      action: 'escalate',
      isActive: true,
      createdAt: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000)
    }
  ]);

  // Simulate loading
  useEffect(() => {
    const timer = setTimeout(() => {
      setLoading(false);
    }, 1500);
    return () => clearTimeout(timer);
  }, []);

  // Helper functions
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'danger';
      case 'high': return 'warning';
      case 'medium': return 'info';
      case 'low': return 'success';
      default: return null;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'detected': return 'warning';
      case 'reported': return 'info';
      case 'under_review': return 'info';
      case 'resolved': return 'success';
      case 'escalated': return 'danger';
      default: return null;
    }
  };

  const getPlatformIcon = (platformId: string) => {
    const platform = platforms.find(p => p.id === platformId);
    return platform?.icon || 'pi pi-globe';
  };

  const formatTimestamp = (timestamp: Date) => {
    const now = new Date();
    const diffInHours = Math.floor((now.getTime() - timestamp.getTime()) / (1000 * 60 * 60));
    
    if (diffInHours < 1) {
      const diffInMinutes = Math.floor((now.getTime() - timestamp.getTime()) / (1000 * 60));
      return `${diffInMinutes}m ago`;
    } else if (diffInHours < 24) {
      return `${diffInHours}h ago`;
    } else {
      return timestamp.toLocaleDateString();
    }
  };

  // Event handlers
  const handleStartScan = (platformId: string) => {
    setPlatforms(prev => prev.map(p => 
      p.id === platformId ? { ...p, scanStatus: 'scanning' } : p
    ));
    
    // Simulate scan completion
    setTimeout(() => {
      setPlatforms(prev => prev.map(p => 
        p.id === platformId ? { 
          ...p, 
          scanStatus: 'completed',
          lastScan: new Date()
        } : p
      ));
    }, 3000);
  };

  const handleReportIncident = (incident: ImpersonationIncident) => {
    setIncidents(prev => prev.map(i => 
      i.id === incident.id ? { ...i, status: 'reported' } : i
    ));
    
    // Add to case progression
    const newProgress: CaseProgression = {
      id: Date.now().toString(),
      incidentId: incident.id,
      status: 'Reported',
      timestamp: new Date(),
      action: 'Manual Report Submitted',
      actor: user?.full_name || 'User',
      notes: 'Incident manually reported to platform'
    };
    
    setCaseProgression(prev => [...prev, newProgress]);
  };

  const handleResolveIncident = (incidentId: string) => {
    setIncidents(prev => prev.map(i => 
      i.id === incidentId ? { ...i, status: 'resolved' } : i
    ));
  };

  const handleBulkAction = (action: string, selectedIds: string[]) => {
    switch (action) {
      case 'report':
        selectedIds.forEach(id => {
          const incident = incidents.find(i => i.id === id);
          if (incident) handleReportIncident(incident);
        });
        break;
      case 'resolve':
        selectedIds.forEach(id => handleResolveIncident(id));
        break;
    }
  };

  const handleSubmitReport = () => {
    const newIncident: ImpersonationIncident = {
      id: Date.now().toString(),
      platformId: reportSubmission.platformId,
      platform: platforms.find(p => p.id === reportSubmission.platformId)?.name || 'Unknown',
      profileUrl: reportSubmission.profileUrl,
      profileName: 'Manual Report',
      detectedAt: new Date(),
      severity: reportSubmission.severity,
      status: 'reported',
      confidenceScore: 100,
      evidenceUrls: reportSubmission.evidence.map(f => f.name),
      reportedBy: 'user',
      similarityScore: 0,
      estimatedFollowers: 0,
      riskLevel: reportSubmission.severity === 'critical' ? 9 : 
                  reportSubmission.severity === 'high' ? 7 :
                  reportSubmission.severity === 'medium' ? 5 : 3,
      notes: reportSubmission.description
    };
    
    setIncidents(prev => [newIncident, ...prev]);
    setShowReportDialog(false);
    
    // Reset form
    setReportSubmission({
      platformId: '',
      profileUrl: '',
      description: '',
      evidence: [],
      severity: 'medium',
      contactAttempted: false,
      additionalInfo: ''
    });
  };

  // Column templates for DataTable
  const platformTemplate = (rowData: ImpersonationIncident) => (
    <div className="flex align-items-center gap-2">
      <i className={getPlatformIcon(rowData.platformId)} style={{ color: platforms.find(p => p.id === rowData.platformId)?.color }} />
      <span>{rowData.platform}</span>
    </div>
  );

  const profileTemplate = (rowData: ImpersonationIncident) => (
    <div className="flex flex-column gap-1">
      <span className="font-medium">{rowData.profileName}</span>
      <a href={rowData.profileUrl} target="_blank" rel="noopener noreferrer" className="text-sm text-primary">
        {rowData.profileUrl}
      </a>
    </div>
  );

  const severityTemplate = (rowData: ImpersonationIncident) => (
    <Tag 
      value={rowData.severity.toUpperCase()} 
      severity={getSeverityColor(rowData.severity)}
    />
  );

  const statusTemplate = (rowData: ImpersonationIncident) => (
    <Tag 
      value={rowData.status.replace('_', ' ').toUpperCase()} 
      severity={getStatusColor(rowData.status)}
    />
  );

  const confidenceTemplate = (rowData: ImpersonationIncident) => (
    <div className="flex align-items-center gap-2">
      <ProgressBar 
        value={rowData.confidenceScore} 
        showValue={false} 
        style={{ width: '60px', height: '6px' }}
      />
      <span className="text-sm font-medium">{rowData.confidenceScore}%</span>
    </div>
  );

  const riskTemplate = (rowData: ImpersonationIncident) => (
    <div className="flex align-items-center gap-2">
      <ProgressBar 
        value={rowData.riskLevel * 10} 
        showValue={false} 
        style={{ width: '60px', height: '6px' }}
        color={rowData.riskLevel >= 8 ? '#EF4444' : rowData.riskLevel >= 6 ? '#F59E0B' : '#10B981'}
      />
      <span className="text-sm font-medium">{rowData.riskLevel}/10</span>
    </div>
  );

  const actionsTemplate = (rowData: ImpersonationIncident) => (
    <div className="flex gap-1">
      <Button 
        icon="pi pi-eye" 
        size="small" 
        text 
        tooltip="View Details"
        onClick={() => {
          setSelectedIncident(rowData);
          setShowDetailsDialog(true);
        }}
      />
      <Button 
        icon="pi pi-flag" 
        size="small" 
        text 
        tooltip="Report"
        disabled={rowData.status === 'reported' || rowData.status === 'resolved'}
        onClick={() => handleReportIncident(rowData)}
      />
      <Button 
        icon="pi pi-check" 
        size="small" 
        text 
        tooltip="Mark Resolved"
        disabled={rowData.status === 'resolved'}
        onClick={() => handleResolveIncident(rowData.id)}
      />
      <Button 
        icon="pi pi-external-link" 
        size="small" 
        text 
        tooltip="Open Profile"
        onClick={() => window.open(rowData.profileUrl, '_blank')}
      />
    </div>
  );

  // Platform monitoring dashboard
  const renderPlatformMonitoring = () => (
    <div className="grid">
      <div className="col-12">
        <div className="flex justify-content-between align-items-center mb-4">
          <h3 className="m-0">Platform Monitoring Dashboard</h3>
          <div className="flex gap-2">
            <Button 
              label="Connect Platform" 
              icon="pi pi-plus" 
              size="small"
              onClick={() => {/* Handle platform connection */}}
            />
            <Button 
              label="Bulk Scan" 
              icon="pi pi-search" 
              outlined 
              size="small"
              onClick={() => {/* Handle bulk scan */}}
            />
          </div>
        </div>
      </div>

      {platforms.map(platform => (
        <div key={platform.id} className="col-12 lg:col-6 xl:col-4">
          <Card className="h-full">
            <div className="flex flex-column gap-3">
              <div className="flex justify-content-between align-items-center">
                <div className="flex align-items-center gap-3">
                  <i 
                    className={`${platform.icon} text-2xl`} 
                    style={{ color: platform.color }}
                  />
                  <div>
                    <h4 className="m-0">{platform.name}</h4>
                    <small className="text-600">
                      Last scan: {platform.lastScan ? formatTimestamp(platform.lastScan) : 'Never'}
                    </small>
                  </div>
                </div>
                <div className="flex align-items-center gap-2">
                  <Tag 
                    value={platform.apiStatus.toUpperCase()} 
                    severity={platform.apiStatus === 'connected' ? 'success' : 'danger'}
                    className="text-xs"
                  />
                  {platform.scanStatus === 'scanning' && (
                    <i className="pi pi-spin pi-spinner text-primary" />
                  )}
                </div>
              </div>

              <div className="grid">
                <div className="col-6">
                  <div className="text-center p-2 bg-blue-50 border-round">
                    <div className="text-2xl font-bold text-blue-600">{platform.totalProfiles.toLocaleString()}</div>
                    <div className="text-xs text-blue-900">Total Profiles</div>
                  </div>
                </div>
                <div className="col-6">
                  <div className="text-center p-2 bg-red-50 border-round">
                    <div className="text-2xl font-bold text-red-600">{platform.impersonations}</div>
                    <div className="text-xs text-red-900">Impersonations</div>
                  </div>
                </div>
              </div>

              <div className="flex flex-column gap-2">
                <div className="text-sm font-medium text-600">Features:</div>
                <div className="flex flex-wrap gap-1">
                  {platform.features.map((feature, index) => (
                    <Badge key={index} value={feature} size="small" />
                  ))}
                </div>
              </div>

              <div className="flex gap-2">
                <Button 
                  label="Scan Now" 
                  icon="pi pi-search" 
                  size="small" 
                  className="flex-1"
                  disabled={!platform.isConnected || platform.scanStatus === 'scanning'}
                  onClick={() => handleStartScan(platform.id)}
                />
                <Button 
                  icon="pi pi-cog" 
                  size="small" 
                  outlined
                  tooltip="Configure"
                  onClick={() => {/* Handle platform config */}}
                />
              </div>

              {platform.scanStatus === 'scanning' && (
                <ProgressBar mode="indeterminate" style={{ height: '4px' }} />
              )}
            </div>
          </Card>
        </div>
      ))}
    </div>
  );

  // Incident management table
  const renderIncidentManagement = () => (
    <div className="grid">
      <div className="col-12">
        <Card>
          <div className="flex justify-content-between align-items-center mb-4">
            <h3 className="m-0">Impersonation Incidents</h3>
            <div className="flex gap-2">
              <span className="p-input-icon-left">
                <i className="pi pi-search" />
                <InputText 
                  value={globalFilter} 
                  onChange={(e) => setGlobalFilter(e.target.value)} 
                  placeholder="Search incidents..."
                  size="small"
                />
              </span>
              <Button 
                label="Report New" 
                icon="pi pi-plus" 
                size="small"
                onClick={() => setShowReportDialog(true)}
              />
            </div>
          </div>

          <DataTable
            value={incidents}
            paginator
            rows={10}
            globalFilter={globalFilter}
            emptyMessage="No impersonation incidents found"
            selectionMode="multiple"
            selection={selectedIncidents}
            onSelectionChange={(e) => setSelectedIncidents(e.value as ImpersonationIncident[])}
            showGridlines
          >
            <Column selectionMode="multiple" headerStyle={{ width: '3rem' }} />
            <Column 
              field="platform" 
              header="Platform" 
              body={platformTemplate} 
              sortable
              style={{ minWidth: '120px' }}
            />
            <Column 
              field="profileName" 
              header="Profile" 
              body={profileTemplate}
              sortable
              style={{ minWidth: '200px' }}
            />
            <Column 
              field="severity" 
              header="Severity" 
              body={severityTemplate}
              sortable
              style={{ minWidth: '100px' }}
            />
            <Column 
              field="status" 
              header="Status" 
              body={statusTemplate}
              sortable
              style={{ minWidth: '120px' }}
            />
            <Column 
              field="confidenceScore" 
              header="Confidence" 
              body={confidenceTemplate}
              sortable
              style={{ minWidth: '120px' }}
            />
            <Column 
              field="riskLevel" 
              header="Risk" 
              body={riskTemplate}
              sortable
              style={{ minWidth: '100px' }}
            />
            <Column 
              field="estimatedFollowers" 
              header="Followers" 
              body={(rowData) => rowData.estimatedFollowers.toLocaleString()}
              sortable
              style={{ minWidth: '100px' }}
            />
            <Column 
              field="detectedAt" 
              header="Detected" 
              body={(rowData) => formatTimestamp(rowData.detectedAt)}
              sortable
              style={{ minWidth: '100px' }}
            />
            <Column 
              body={actionsTemplate}
              style={{ minWidth: '150px' }}
            />
          </DataTable>
        </Card>
      </div>
    </div>
  );

  // Case tracking timeline
  const renderCaseTracking = () => (
    <div className="grid">
      <div className="col-12 lg:col-8">
        <Card title="Case Progression Timeline">
          <Timeline
            value={caseProgression}
            align="alternate"
            className="customized-timeline"
            marker={(item) => (
              <span 
                className={`flex w-2rem h-2rem align-items-center justify-content-center text-white border-circle z-1 shadow-1`}
                style={{ backgroundColor: '#6366F1' }}
              >
                <i className="pi pi-check" />
              </span>
            )}
            content={(item) => (
              <Card className="mt-3">
                <div className="flex justify-content-between align-items-start mb-2">
                  <h6 className="m-0">{item.action}</h6>
                  <small className="text-600">{formatTimestamp(item.timestamp)}</small>
                </div>
                <p className="text-600 m-0 mb-2">{item.notes}</p>
                <div className="flex justify-content-between align-items-center">
                  <Tag value={item.status} />
                  <small className="text-500">by {item.actor}</small>
                </div>
              </Card>
            )}
          />
        </Card>
      </div>
      
      <div className="col-12 lg:col-4">
        <Card title="Case Statistics" className="mb-3">
          <div className="flex flex-column gap-3">
            <div className="flex justify-content-between">
              <span>Total Cases</span>
              <Badge value={incidents.length} />
            </div>
            <div className="flex justify-content-between">
              <span>Open Cases</span>
              <Badge value={incidents.filter(i => i.status !== 'resolved').length} severity="warning" />
            </div>
            <div className="flex justify-content-between">
              <span>Resolved Cases</span>
              <Badge value={incidents.filter(i => i.status === 'resolved').length} severity="success" />
            </div>
            <div className="flex justify-content-between">
              <span>Critical Cases</span>
              <Badge value={incidents.filter(i => i.severity === 'critical').length} severity="danger" />
            </div>
          </div>
        </Card>

        <Card title="Platform Reports">
          <div className="flex flex-column gap-2">
            {platforms.slice(0, 5).map(platform => (
              <div key={platform.id} className="flex justify-content-between align-items-center p-2 border-round hover:bg-gray-50">
                <div className="flex align-items-center gap-2">
                  <i className={platform.icon} style={{ color: platform.color }} />
                  <span className="text-sm">{platform.name}</span>
                </div>
                <Badge value={platform.impersonations} severity={platform.impersonations > 10 ? 'danger' : 'warning'} />
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );

  // Automation settings
  const renderAutomationSettings = () => (
    <div className="grid">
      <div className="col-12">
        <Card title="Automation Rules">
          <div className="flex justify-content-between align-items-center mb-4">
            <p className="text-600 m-0">Configure automated actions for impersonation detection</p>
            <Button 
              label="Create Rule" 
              icon="pi pi-plus" 
              size="small"
              onClick={() => {/* Handle create rule */}}
            />
          </div>

          <DataTable
            value={automationRules}
            showGridlines
            emptyMessage="No automation rules configured"
          >
            <Column field="name" header="Rule Name" sortable />
            <Column 
              field="platform" 
              header="Platform" 
              body={(rowData) => (
                <Tag value={rowData.platform === 'all' ? 'ALL PLATFORMS' : rowData.platform.toUpperCase()} />
              )}
              sortable 
            />
            <Column 
              field="trigger" 
              header="Trigger" 
              body={(rowData) => rowData.trigger.replace('_', ' ').toUpperCase()}
              sortable 
            />
            <Column 
              field="threshold" 
              header="Threshold" 
              body={(rowData) => `${rowData.threshold}%`}
              sortable 
            />
            <Column 
              field="action" 
              header="Action" 
              body={(rowData) => (
                <Tag value={rowData.action.toUpperCase()} severity="info" />
              )}
              sortable 
            />
            <Column 
              field="isActive" 
              header="Status" 
              body={(rowData) => (
                <Tag 
                  value={rowData.isActive ? 'ACTIVE' : 'INACTIVE'} 
                  severity={rowData.isActive ? 'success' : 'danger'}
                />
              )}
              sortable 
            />
            <Column 
              field="createdAt" 
              header="Created" 
              body={(rowData) => rowData.createdAt.toLocaleDateString()}
              sortable 
            />
            <Column 
              body={(rowData) => (
                <div className="flex gap-1">
                  <Button icon="pi pi-pencil" size="small" text tooltip="Edit" />
                  <Button icon="pi pi-trash" size="small" text tooltip="Delete" />
                  <Button 
                    icon={rowData.isActive ? "pi pi-pause" : "pi pi-play"} 
                    size="small" 
                    text 
                    tooltip={rowData.isActive ? "Disable" : "Enable"}
                  />
                </div>
              )}
            />
          </DataTable>
        </Card>
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="grid">
        <div className="col-12">
          <Skeleton width="100%" height="4rem" className="mb-4" />
          {Array.from({ length: 6 }).map((_, index) => (
            <div key={index} className="col-12 md:col-6 lg:col-4 mb-3">
              <Skeleton width="100%" height="200px" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="social-media-protection">
      <ConfirmDialog />
      <Toast />
      
      <div className="flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="m-0 text-900">Social Media Protection</h2>
          <p className="text-600 m-0 mt-1">Monitor and eliminate fake profiles across all platforms</p>
        </div>
        <div className="flex gap-2">
          <Button 
            label="Identity Verification" 
            icon="pi pi-verified" 
            outlined 
            size="small"
            onClick={() => setShowVerificationDialog(true)}
          />
          <Button 
            label="Analytics Report" 
            icon="pi pi-chart-line" 
            outlined 
            size="small"
            onClick={() => navigate('/reports/social-media')}
          />
        </div>
      </div>

      <TabView activeIndex={activeTabIndex} onTabChange={(e) => setActiveTabIndex(e.index)}>
        <TabPanel header="Platform Monitoring" leftIcon="pi pi-desktop">
          {renderPlatformMonitoring()}
        </TabPanel>
        
        <TabPanel header="Incidents" leftIcon="pi pi-exclamation-triangle">
          {renderIncidentManagement()}
        </TabPanel>
        
        <TabPanel header="Case Tracking" leftIcon="pi pi-history">
          {renderCaseTracking()}
        </TabPanel>
        
        <TabPanel header="Automation" leftIcon="pi pi-cog">
          {renderAutomationSettings()}
        </TabPanel>
      </TabView>

      {/* Report Submission Dialog */}
      <Dialog
        visible={showReportDialog}
        header="Report Impersonation"
        modal
        style={{ width: '600px' }}
        onHide={() => setShowReportDialog(false)}
        footer={
          <div className="flex gap-2">
            <Button 
              label="Cancel" 
              text 
              onClick={() => setShowReportDialog(false)} 
            />
            <Button 
              label="Submit Report" 
              onClick={handleSubmitReport}
              disabled={!reportSubmission.platformId || !reportSubmission.profileUrl}
            />
          </div>
        }
      >
        <div className="flex flex-column gap-4 pt-3">
          <div className="field">
            <label htmlFor="platform" className="block mb-2 font-medium">Platform *</label>
            <Dropdown
              id="platform"
              value={reportSubmission.platformId}
              onChange={(e) => setReportSubmission(prev => ({ ...prev, platformId: e.value }))}
              options={platforms.map(p => ({ label: p.name, value: p.id }))}
              placeholder="Select platform"
              className="w-full"
            />
          </div>

          <div className="field">
            <label htmlFor="profileUrl" className="block mb-2 font-medium">Profile URL *</label>
            <InputText
              id="profileUrl"
              value={reportSubmission.profileUrl}
              onChange={(e) => setReportSubmission(prev => ({ ...prev, profileUrl: e.target.value }))}
              placeholder="https://platform.com/fake-profile"
              className="w-full"
            />
          </div>

          <div className="field">
            <label htmlFor="severity" className="block mb-2 font-medium">Severity Level</label>
            <SelectButton
              value={reportSubmission.severity}
              onChange={(e) => setReportSubmission(prev => ({ ...prev, severity: e.value }))}
              options={[
                { label: 'Low', value: 'low' },
                { label: 'Medium', value: 'medium' },
                { label: 'High', value: 'high' },
                { label: 'Critical', value: 'critical' }
              ]}
              className="w-full"
            />
          </div>

          <div className="field">
            <label htmlFor="description" className="block mb-2 font-medium">Description *</label>
            <InputTextarea
              id="description"
              value={reportSubmission.description}
              onChange={(e) => setReportSubmission(prev => ({ ...prev, description: e.target.value }))}
              rows={4}
              placeholder="Describe the impersonation incident..."
              className="w-full"
            />
          </div>

          <div className="field">
            <label className="block mb-2 font-medium">Evidence Files</label>
            <FileUpload
              mode="basic"
              multiple
              accept="image/*,video/*"
              maxFileSize={10000000}
              onSelect={(e) => setReportSubmission(prev => ({ ...prev, evidence: e.files }))}
              chooseLabel="Upload Evidence"
              className="w-full"
            />
          </div>

          <div className="field">
            <div className="flex align-items-center gap-2">
              <Checkbox
                id="contactAttempted"
                checked={reportSubmission.contactAttempted}
                onChange={(e) => setReportSubmission(prev => ({ ...prev, contactAttempted: e.checked || false }))}
              />
              <label htmlFor="contactAttempted">I have attempted to contact the platform directly</label>
            </div>
          </div>
        </div>
      </Dialog>

      {/* Identity Verification Dialog */}
      <Dialog
        visible={showVerificationDialog}
        header="Identity Verification"
        modal
        style={{ width: '500px' }}
        onHide={() => setShowVerificationDialog(false)}
        footer={
          <div className="flex gap-2">
            <Button label="Cancel" text onClick={() => setShowVerificationDialog(false)} />
            <Button label="Submit Documents" />
          </div>
        }
      >
        <div className="flex flex-column gap-4 pt-3">
          <Message severity="info" text="Upload identity documents to strengthen takedown requests" />
          
          <div className="field">
            <label className="block mb-2 font-medium">Government ID</label>
            <FileUpload
              mode="basic"
              accept="image/*,application/pdf"
              maxFileSize={5000000}
              chooseLabel="Upload ID Document"
              className="w-full"
            />
          </div>

          <div className="field">
            <label className="block mb-2 font-medium">Proof of Ownership (Optional)</label>
            <FileUpload
              mode="basic"
              multiple
              accept="image/*,application/pdf"
              maxFileSize={5000000}
              chooseLabel="Upload Documents"
              className="w-full"
            />
            <small className="text-600">
              Model releases, contracts, copyright certificates, etc.
            </small>
          </div>
        </div>
      </Dialog>

      {/* Incident Details Dialog */}
      <Dialog
        visible={showDetailsDialog}
        header="Incident Details"
        modal
        style={{ width: '800px' }}
        onHide={() => setShowDetailsDialog(false)}
      >
        {selectedIncident && (
          <div className="grid pt-3">
            <div className="col-12 md:col-6">
              <div className="flex flex-column gap-3">
                <div className="field">
                  <label className="font-medium text-600">Platform</label>
                  <div className="flex align-items-center gap-2 mt-1">
                    <i className={getPlatformIcon(selectedIncident.platformId)} />
                    <span>{selectedIncident.platform}</span>
                  </div>
                </div>

                <div className="field">
                  <label className="font-medium text-600">Profile URL</label>
                  <div className="mt-1">
                    <a href={selectedIncident.profileUrl} target="_blank" rel="noopener noreferrer" className="text-primary">
                      {selectedIncident.profileUrl}
                    </a>
                  </div>
                </div>

                <div className="field">
                  <label className="font-medium text-600">Profile Name</label>
                  <div className="mt-1">{selectedIncident.profileName}</div>
                </div>

                <div className="field">
                  <label className="font-medium text-600">Detection Method</label>
                  <div className="mt-1">
                    <Tag value={selectedIncident.reportedBy.toUpperCase()} />
                  </div>
                </div>
              </div>
            </div>

            <div className="col-12 md:col-6">
              <div className="flex flex-column gap-3">
                <div className="field">
                  <label className="font-medium text-600">Confidence Score</label>
                  <div className="flex align-items-center gap-2 mt-1">
                    <ProgressBar 
                      value={selectedIncident.confidenceScore} 
                      style={{ width: '100px', height: '8px' }}
                      showValue={false}
                    />
                    <span>{selectedIncident.confidenceScore}%</span>
                  </div>
                </div>

                <div className="field">
                  <label className="font-medium text-600">Risk Level</label>
                  <div className="flex align-items-center gap-2 mt-1">
                    <ProgressBar 
                      value={selectedIncident.riskLevel * 10} 
                      style={{ width: '100px', height: '8px' }}
                      showValue={false}
                      color={selectedIncident.riskLevel >= 8 ? '#EF4444' : selectedIncident.riskLevel >= 6 ? '#F59E0B' : '#10B981'}
                    />
                    <span>{selectedIncident.riskLevel}/10</span>
                  </div>
                </div>

                <div className="field">
                  <label className="font-medium text-600">Estimated Followers</label>
                  <div className="mt-1">{selectedIncident.estimatedFollowers.toLocaleString()}</div>
                </div>

                <div className="field">
                  <label className="font-medium text-600">Detected At</label>
                  <div className="mt-1">{selectedIncident.detectedAt.toLocaleString()}</div>
                </div>
              </div>
            </div>

            <div className="col-12">
              <Divider />
              <div className="field">
                <label className="font-medium text-600">Notes</label>
                <div className="mt-1">{selectedIncident.notes}</div>
              </div>
            </div>

            <div className="col-12">
              <div className="flex justify-content-end gap-2">
                <Button 
                  label="Report to Platform" 
                  icon="pi pi-flag" 
                  disabled={selectedIncident.status === 'reported' || selectedIncident.status === 'resolved'}
                  onClick={() => {
                    handleReportIncident(selectedIncident);
                    setShowDetailsDialog(false);
                  }}
                />
                <Button 
                  label="Mark Resolved" 
                  icon="pi pi-check" 
                  outlined
                  disabled={selectedIncident.status === 'resolved'}
                  onClick={() => {
                    handleResolveIncident(selectedIncident.id);
                    setShowDetailsDialog(false);
                  }}
                />
              </div>
            </div>
          </div>
        )}
      </Dialog>
    </div>
  );
};

export default SocialMediaProtection;