import React, { useState, useRef } from 'react';
import { TabView, TabPanel } from 'primereact/tabview';
import { Card } from 'primereact/card';
import { FileUpload, FileUploadHandlerEvent } from 'primereact/fileupload';
import { Button } from 'primereact/button';
import { Dialog } from 'primereact/dialog';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { ProgressBar } from 'primereact/progressbar';
import { Slider } from 'primereact/slider';
import { Dropdown } from 'primereact/dropdown';
import { InputText } from 'primereact/inputtext';
import { InputTextarea } from 'primereact/inputtextarea';
import { Checkbox } from 'primereact/checkbox';
import { Toast } from 'primereact/toast';
import { ConfirmDialog } from 'primereact/confirmdialog';
import { Chip } from 'primereact/chip';
import { Badge } from 'primereact/badge';
import { Panel } from 'primereact/panel';
import { Splitter, SplitterPanel } from 'primereact/splitter';
import { Timeline } from 'primereact/timeline';
import { Chart } from 'primereact/chart';
import { Tag } from 'primereact/tag';

// Types for watermarking system
interface WatermarkSettings {
  id: string;
  name: string;
  type: WatermarkType;
  strength: number;
  subscriberId?: string;
  subscriberName?: string;
  metadata: Record<string, any>;
  createdAt: Date;
  isActive: boolean;
}

interface WatermarkedContent {
  id: string;
  filename: string;
  originalSize: number;
  watermarkedSize: number;
  watermarkId: string;
  watermarkType: WatermarkType;
  subscriberId: string;
  subscriberName: string;
  uploadDate: Date;
  status: 'processing' | 'completed' | 'failed';
  downloadUrl?: string;
  previewUrl?: string;
  leakDetections?: LeakDetection[];
}

interface LeakDetection {
  id: string;
  detectedAt: Date;
  source: string;
  confidence: number;
  watermarkData: string;
  evidenceUrl: string;
  status: 'verified' | 'investigating' | 'false-positive';
  subscriberId: string;
  subscriberName: string;
}

interface BatchProcessing {
  id: string;
  totalFiles: number;
  processedFiles: number;
  failedFiles: number;
  status: 'running' | 'completed' | 'paused' | 'failed';
  startTime: Date;
  estimatedCompletion?: Date;
}

type WatermarkType = 
  | 'invisible-digital'
  | 'subscriber-specific'
  | 'metadata-exif'
  | 'steganographic'
  | 'audio-inaudible'
  | 'text-hidden';

const ContentWatermarking: React.FC = () => {
  // State management
  const [activeIndex, setActiveIndex] = useState(0);
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [watermarkSettings, setWatermarkSettings] = useState<WatermarkSettings[]>([]);
  const [watermarkedContent, setWatermarkedContent] = useState<WatermarkedContent[]>([]);
  const [leakDetections, setLeakDetections] = useState<LeakDetection[]>([]);
  const [batchProcessing, setBatchProcessing] = useState<BatchProcessing | null>(null);
  
  // Dialog states
  const [showWatermarkDialog, setShowWatermarkDialog] = useState(false);
  const [showBatchDialog, setShowBatchDialog] = useState(false);
  const [showLeakAnalysisDialog, setShowLeakAnalysisDialog] = useState(false);
  const [showPreviewDialog, setShowPreviewDialog] = useState(false);
  const [showSettingsDialog, setShowSettingsDialog] = useState(false);
  
  // Form states
  const [selectedWatermarkType, setSelectedWatermarkType] = useState<WatermarkType>('invisible-digital');
  const [watermarkStrength, setWatermarkStrength] = useState(75);
  const [subscriberId, setSubscriberId] = useState('');
  const [subscriberName, setSubscriberName] = useState('');
  const [watermarkName, setWatermarkName] = useState('');
  const [watermarkMetadata, setWatermarkMetadata] = useState('');
  const [selectedContent, setSelectedContent] = useState<WatermarkedContent | null>(null);
  const [processingProgress, setProcessingProgress] = useState(0);
  
  // Refs
  const toast = useRef<Toast>(null);
  const fileUploadRef = useRef<FileUpload>(null);

  // Watermark type options
  const watermarkTypes = [
    { label: 'Invisible Digital Watermark', value: 'invisible-digital', icon: 'pi pi-eye-slash' },
    { label: 'Subscriber-Specific ID', value: 'subscriber-specific', icon: 'pi pi-user' },
    { label: 'Metadata/EXIF Watermark', value: 'metadata-exif', icon: 'pi pi-info-circle' },
    { label: 'Steganographic Watermark', value: 'steganographic', icon: 'pi pi-image' },
    { label: 'Audio Inaudible Marker', value: 'audio-inaudible', icon: 'pi pi-volume-off' },
    { label: 'Hidden Text Watermark', value: 'text-hidden', icon: 'pi pi-file-word' }
  ];

  // Mock data for demonstration
  React.useEffect(() => {
    const mockWatermarks: WatermarkSettings[] = [
      {
        id: 'wm-001',
        name: 'Premium Subscriber Watermark',
        type: 'subscriber-specific',
        strength: 80,
        subscriberId: 'sub-001',
        subscriberName: 'John Doe Premium',
        metadata: { tier: 'premium', region: 'US' },
        createdAt: new Date('2024-01-15'),
        isActive: true
      },
      {
        id: 'wm-002',
        name: 'Standard Digital Watermark',
        type: 'invisible-digital',
        strength: 70,
        subscriberId: 'sub-002',
        subscriberName: 'Jane Smith',
        metadata: { tier: 'standard' },
        createdAt: new Date('2024-01-20'),
        isActive: true
      }
    ];

    const mockContent: WatermarkedContent[] = [
      {
        id: 'content-001',
        filename: 'exclusive_video_001.mp4',
        originalSize: 125000000,
        watermarkedSize: 125001500,
        watermarkId: 'wm-001',
        watermarkType: 'subscriber-specific',
        subscriberId: 'sub-001',
        subscriberName: 'John Doe Premium',
        uploadDate: new Date('2024-02-01'),
        status: 'completed',
        downloadUrl: '/downloads/exclusive_video_001_watermarked.mp4',
        previewUrl: '/previews/exclusive_video_001_preview.jpg',
        leakDetections: []
      },
      {
        id: 'content-002',
        filename: 'premium_photo_set.zip',
        originalSize: 45000000,
        watermarkedSize: 45002000,
        watermarkId: 'wm-002',
        watermarkType: 'invisible-digital',
        subscriberId: 'sub-002',
        subscriberName: 'Jane Smith',
        uploadDate: new Date('2024-02-02'),
        status: 'completed',
        downloadUrl: '/downloads/premium_photo_set_watermarked.zip',
        leakDetections: [
          {
            id: 'leak-001',
            detectedAt: new Date('2024-02-05'),
            source: 'unauthorized-site.com',
            confidence: 95,
            watermarkData: 'sub-002-2024-02-02-premium',
            evidenceUrl: '/evidence/leak-001-evidence.pdf',
            status: 'verified',
            subscriberId: 'sub-002',
            subscriberName: 'Jane Smith'
          }
        ]
      }
    ];

    const mockLeaks: LeakDetection[] = [
      {
        id: 'leak-001',
        detectedAt: new Date('2024-02-05'),
        source: 'unauthorized-site.com',
        confidence: 95,
        watermarkData: 'sub-002-2024-02-02-premium',
        evidenceUrl: '/evidence/leak-001-evidence.pdf',
        status: 'verified',
        subscriberId: 'sub-002',
        subscriberName: 'Jane Smith'
      },
      {
        id: 'leak-002',
        detectedAt: new Date('2024-02-07'),
        source: 'piracy-forum.net',
        confidence: 88,
        watermarkData: 'sub-001-2024-02-01-premium',
        evidenceUrl: '/evidence/leak-002-evidence.pdf',
        status: 'investigating',
        subscriberId: 'sub-001',
        subscriberName: 'John Doe Premium'
      }
    ];

    setWatermarkSettings(mockWatermarks);
    setWatermarkedContent(mockContent);
    setLeakDetections(mockLeaks);
  }, []);

  // File upload handler
  const onFileUpload = (event: FileUploadHandlerEvent) => {
    const files = Array.from(event.files);
    setUploadedFiles(prev => [...prev, ...files]);
    
    toast.current?.show({
      severity: 'success',
      summary: 'Files Uploaded',
      detail: `${files.length} file(s) ready for watermarking`
    });
  };

  // Create watermark
  const handleCreateWatermark = () => {
    const newWatermark: WatermarkSettings = {
      id: `wm-${Date.now()}`,
      name: watermarkName,
      type: selectedWatermarkType,
      strength: watermarkStrength,
      subscriberId: subscriberId || undefined,
      subscriberName: subscriberName || undefined,
      metadata: watermarkMetadata ? JSON.parse(watermarkMetadata) : {},
      createdAt: new Date(),
      isActive: true
    };

    setWatermarkSettings(prev => [...prev, newWatermark]);
    setShowWatermarkDialog(false);
    
    // Reset form
    setWatermarkName('');
    setSubscriberId('');
    setSubscriberName('');
    setWatermarkMetadata('');
    setWatermarkStrength(75);

    toast.current?.show({
      severity: 'success',
      summary: 'Watermark Created',
      detail: `Watermark "${newWatermark.name}" created successfully`
    });
  };

  // Process files with watermark
  const handleProcessFiles = async (watermarkId: string) => {
    if (uploadedFiles.length === 0) {
      toast.current?.show({
        severity: 'warn',
        summary: 'No Files',
        detail: 'Please upload files first'
      });
      return;
    }

    const watermark = watermarkSettings.find(w => w.id === watermarkId);
    if (!watermark) return;

    // Simulate processing
    setProcessingProgress(0);
    const interval = setInterval(() => {
      setProcessingProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          
          // Create watermarked content entries
          const newContent: WatermarkedContent[] = uploadedFiles.map((file, index) => ({
            id: `content-${Date.now()}-${index}`,
            filename: file.name,
            originalSize: file.size,
            watermarkedSize: file.size + Math.floor(file.size * 0.001), // Simulate size increase
            watermarkId: watermark.id,
            watermarkType: watermark.type,
            subscriberId: watermark.subscriberId || 'anonymous',
            subscriberName: watermark.subscriberName || 'Anonymous User',
            uploadDate: new Date(),
            status: 'completed',
            downloadUrl: `/downloads/${file.name}_watermarked`,
            previewUrl: `/previews/${file.name}_preview`,
            leakDetections: []
          }));

          setWatermarkedContent(prev => [...prev, ...newContent]);
          setUploadedFiles([]);
          
          toast.current?.show({
            severity: 'success',
            summary: 'Processing Complete',
            detail: `${newContent.length} file(s) watermarked successfully`
          });
          
          return 100;
        }
        return prev + 10;
      });
    }, 500);
  };

  // Format file size
  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Status badge template
  const statusBodyTemplate = (rowData: WatermarkedContent) => {
    const severity = rowData.status === 'completed' ? 'success' : 
                    rowData.status === 'processing' ? 'info' : 'danger';
    return <Badge value={rowData.status} severity={severity} />;
  };

  // Leak detection badge template
  const leakBodyTemplate = (rowData: WatermarkedContent) => {
    const leakCount = rowData.leakDetections?.length || 0;
    if (leakCount === 0) {
      return <Tag value="No Leaks" severity="success" icon="pi pi-check" />;
    }
    return <Tag value={`${leakCount} Leak${leakCount > 1 ? 's' : ''}`} severity="danger" icon="pi pi-exclamation-triangle" />;
  };

  // Actions template
  const actionsBodyTemplate = (rowData: WatermarkedContent) => {
    return (
      <div className="flex gap-2">
        <Button
          icon="pi pi-eye"
          size="small"
          outlined
          tooltip="Preview"
          onClick={() => {
            setSelectedContent(rowData);
            setShowPreviewDialog(true);
          }}
        />
        <Button
          icon="pi pi-download"
          size="small"
          outlined
          tooltip="Download"
          onClick={() => {
            toast.current?.show({
              severity: 'info',
              summary: 'Download Started',
              detail: `Downloading ${rowData.filename}`
            });
          }}
        />
        <Button
          icon="pi pi-search"
          size="small"
          outlined
          tooltip="Analyze for Leaks"
          onClick={() => {
            setSelectedContent(rowData);
            setShowLeakAnalysisDialog(true);
          }}
        />
      </div>
    );
  };

  // Leak confidence template
  const confidenceBodyTemplate = (rowData: LeakDetection) => {
    const getColor = (confidence: number) => {
      if (confidence >= 90) return 'success';
      if (confidence >= 70) return 'warning';
      return 'danger';
    };

    return (
      <div className="flex align-items-center gap-2">
        <ProgressBar
          value={rowData.confidence}
          style={{ width: '100px' }}
          color={getColor(rowData.confidence)}
        />
        <span className="text-sm font-medium">{rowData.confidence}%</span>
      </div>
    );
  };

  // Leak status template
  const leakStatusBodyTemplate = (rowData: LeakDetection) => {
    const severity = rowData.status === 'verified' ? 'danger' : 
                    rowData.status === 'investigating' ? 'warning' : 'info';
    return <Badge value={rowData.status} severity={severity} />;
  };

  // Chrome extension data
  const extensionFeatures = [
    { icon: 'pi pi-globe', title: 'Auto-Watermark', description: 'Automatically watermark content as you browse' },
    { icon: 'pi pi-shield', title: 'Real-time Protection', description: 'Instant content protection on upload' },
    { icon: 'pi pi-bell', title: 'Leak Alerts', description: 'Get notified when leaks are detected' },
    { icon: 'pi pi-cog', title: 'Custom Settings', description: 'Configure watermarking preferences' }
  ];

  return (
    <div className="content-watermarking p-4">
      <Toast ref={toast} />
      <ConfirmDialog />

      {/* Header */}
      <div className="flex justify-content-between align-items-center mb-4">
        <div>
          <h1 className="text-3xl font-bold text-900 m-0">Content Watermarking</h1>
          <p className="text-600 mt-2 mb-0">
            Protect your content with invisible watermarks and track leak sources
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            icon="pi pi-cog"
            label="Settings"
            outlined
            onClick={() => setShowSettingsDialog(true)}
          />
          <Button
            icon="pi pi-plus"
            label="New Watermark"
            onClick={() => setShowWatermarkDialog(true)}
          />
        </div>
      </div>

      {/* Main Content */}
      <TabView activeIndex={activeIndex} onTabChange={(e) => setActiveIndex(e.index)}>
        
        {/* Upload & Watermark Tab */}
        <TabPanel header="Upload & Watermark" leftIcon="pi pi-upload">
          <div className="grid">
            
            {/* File Upload Section */}
            <div className="col-12 lg:col-8">
              <Card title="Upload Content for Watermarking" className="h-full">
                <FileUpload
                  ref={fileUploadRef}
                  name="content"
                  multiple
                  accept="image/*,video/*,audio/*,.zip,.rar"
                  maxFileSize={500000000} // 500MB
                  customUpload
                  uploadHandler={onFileUpload}
                  emptyTemplate={
                    <div className="text-center py-6">
                      <i className="pi pi-cloud-upload text-6xl text-400"></i>
                      <p className="text-600 mt-3 mb-0">
                        Drag and drop files here or click to select
                      </p>
                      <p className="text-400 text-sm mt-1">
                        Supports images, videos, audio files, and archives (max 500MB per file)
                      </p>
                    </div>
                  }
                />

                {/* Uploaded Files Preview */}
                {uploadedFiles.length > 0 && (
                  <div className="mt-4">
                    <h5>Uploaded Files ({uploadedFiles.length})</h5>
                    <div className="flex flex-wrap gap-2">
                      {uploadedFiles.map((file, index) => (
                        <Chip
                          key={index}
                          label={`${file.name} (${formatFileSize(file.size)})`}
                          icon="pi pi-file"
                          removable
                          onRemove={() => {
                            setUploadedFiles(prev => prev.filter((_, i) => i !== index));
                          }}
                        />
                      ))}
                    </div>
                  </div>
                )}

                {/* Processing Progress */}
                {processingProgress > 0 && processingProgress < 100 && (
                  <div className="mt-4">
                    <h5>Processing Files...</h5>
                    <ProgressBar value={processingProgress} />
                  </div>
                )}
              </Card>
            </div>

            {/* Watermark Selection */}
            <div className="col-12 lg:col-4">
              <Card title="Select Watermark" className="h-full">
                {watermarkSettings.length > 0 ? (
                  <div className="flex flex-column gap-3">
                    {watermarkSettings.map(watermark => (
                      <div
                        key={watermark.id}
                        className="p-3 border-1 border-200 border-round hover:bg-50 cursor-pointer transition-colors"
                      >
                        <div className="flex justify-content-between align-items-start mb-2">
                          <span className="font-semibold text-900">{watermark.name}</span>
                          <Tag
                            value={watermark.type.replace('-', ' ')}
                            severity="info"
                            className="text-xs"
                          />
                        </div>
                        <div className="text-sm text-600 mb-2">
                          Strength: {watermark.strength}%
                        </div>
                        {watermark.subscriberName && (
                          <div className="text-sm text-500 mb-3">
                            <i className="pi pi-user mr-2"></i>
                            {watermark.subscriberName}
                          </div>
                        )}
                        <Button
                          label="Apply Watermark"
                          size="small"
                          className="w-full"
                          disabled={uploadedFiles.length === 0}
                          onClick={() => handleProcessFiles(watermark.id)}
                        />
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-4">
                    <i className="pi pi-info-circle text-4xl text-400 mb-3"></i>
                    <p className="text-600">No watermarks available</p>
                    <Button
                      label="Create Watermark"
                      size="small"
                      onClick={() => setShowWatermarkDialog(true)}
                    />
                  </div>
                )}
              </Card>
            </div>
          </div>
        </TabPanel>

        {/* Watermarked Content Tab */}
        <TabPanel header="Watermarked Content" leftIcon="pi pi-shield">
          <Card>
            <div className="flex justify-content-between align-items-center mb-4">
              <h3 className="m-0">Watermarked Content Library</h3>
              <div className="flex gap-2">
                <Button
                  icon="pi pi-refresh"
                  label="Refresh"
                  outlined
                  size="small"
                  onClick={() => {
                    toast.current?.show({
                      severity: 'info',
                      summary: 'Refreshed',
                      detail: 'Content library updated'
                    });
                  }}
                />
                <Button
                  icon="pi pi-download"
                  label="Batch Download"
                  size="small"
                  onClick={() => setShowBatchDialog(true)}
                />
              </div>
            </div>
            
            <DataTable
              value={watermarkedContent}
              paginator
              rows={10}
              dataKey="id"
              emptyMessage="No watermarked content found"
              className="p-datatable-sm"
            >
              <Column field="filename" header="Filename" sortable />
              <Column
                field="watermarkType"
                header="Watermark Type"
                body={(rowData) => (
                  <Tag
                    value={rowData.watermarkType.replace('-', ' ')}
                    severity="info"
                  />
                )}
              />
              <Column
                field="subscriberName"
                header="Subscriber"
                sortable
              />
              <Column
                field="originalSize"
                header="Size"
                body={(rowData) => formatFileSize(rowData.originalSize)}
                sortable
              />
              <Column
                field="uploadDate"
                header="Date"
                body={(rowData) => rowData.uploadDate.toLocaleDateString()}
                sortable
              />
              <Column
                field="status"
                header="Status"
                body={statusBodyTemplate}
              />
              <Column
                header="Leak Status"
                body={leakBodyTemplate}
              />
              <Column
                header="Actions"
                body={actionsBodyTemplate}
                style={{ width: '120px' }}
              />
            </DataTable>
          </Card>
        </TabPanel>

        {/* Leak Detection Tab */}
        <TabPanel header="Leak Detection" leftIcon="pi pi-exclamation-triangle">
          <div className="grid">
            
            {/* Leak Statistics */}
            <div className="col-12">
              <div className="grid">
                <div className="col-12 md:col-3">
                  <Card className="text-center">
                    <div className="text-900 font-medium mb-2">Total Leaks Detected</div>
                    <div className="text-4xl font-bold text-red-500">{leakDetections.length}</div>
                  </Card>
                </div>
                <div className="col-12 md:col-3">
                  <Card className="text-center">
                    <div className="text-900 font-medium mb-2">Verified Leaks</div>
                    <div className="text-4xl font-bold text-orange-500">
                      {leakDetections.filter(l => l.status === 'verified').length}
                    </div>
                  </Card>
                </div>
                <div className="col-12 md:col-3">
                  <Card className="text-center">
                    <div className="text-900 font-medium mb-2">Under Investigation</div>
                    <div className="text-4xl font-bold text-yellow-500">
                      {leakDetections.filter(l => l.status === 'investigating').length}
                    </div>
                  </Card>
                </div>
                <div className="col-12 md:col-3">
                  <Card className="text-center">
                    <div className="text-900 font-medium mb-2">Average Confidence</div>
                    <div className="text-4xl font-bold text-blue-500">
                      {leakDetections.length > 0 
                        ? Math.round(leakDetections.reduce((acc, l) => acc + l.confidence, 0) / leakDetections.length)
                        : 0}%
                    </div>
                  </Card>
                </div>
              </div>
            </div>

            {/* Leak Detection Table */}
            <div className="col-12">
              <Card title="Detected Leaks">
                <DataTable
                  value={leakDetections}
                  paginator
                  rows={10}
                  dataKey="id"
                  emptyMessage="No leaks detected"
                  className="p-datatable-sm"
                >
                  <Column
                    field="detectedAt"
                    header="Detected"
                    body={(rowData) => rowData.detectedAt.toLocaleDateString()}
                    sortable
                  />
                  <Column field="source" header="Source" sortable />
                  <Column field="subscriberName" header="Subscriber" sortable />
                  <Column
                    field="confidence"
                    header="Confidence"
                    body={confidenceBodyTemplate}
                    sortable
                  />
                  <Column
                    field="status"
                    header="Status"
                    body={leakStatusBodyTemplate}
                  />
                  <Column
                    header="Actions"
                    body={(rowData) => (
                      <div className="flex gap-1">
                        <Button
                          icon="pi pi-eye"
                          size="small"
                          outlined
                          tooltip="View Evidence"
                          onClick={() => {
                            toast.current?.show({
                              severity: 'info',
                              summary: 'Evidence',
                              detail: 'Opening evidence file...'
                            });
                          }}
                        />
                        <Button
                          icon="pi pi-send"
                          size="small"
                          outlined
                          tooltip="Send DMCA"
                          onClick={() => {
                            toast.current?.show({
                              severity: 'success',
                              summary: 'DMCA Takedown',
                              detail: 'DMCA notice prepared for sending'
                            });
                          }}
                        />
                      </div>
                    )}
                    style={{ width: '80px' }}
                  />
                </DataTable>
              </Card>
            </div>
          </div>
        </TabPanel>

        {/* Chrome Extension Tab */}
        <TabPanel header="Browser Extension" leftIcon="pi pi-globe">
          <div className="grid">
            
            {/* Extension Overview */}
            <div className="col-12 lg:col-6">
              <Card title="AutoDMCA Chrome Extension">
                <div className="text-center mb-4">
                  <i className="pi pi-chrome text-6xl text-blue-500 mb-3"></i>
                  <h3 className="text-900 mb-2">Automated Content Watermarking</h3>
                  <p className="text-600 line-height-3">
                    Automatically watermark your content as you upload to social media platforms, 
                    OnlyFans, and other content sites. Real-time protection with zero effort.
                  </p>
                </div>

                <div className="flex flex-column gap-3 mb-4">
                  {extensionFeatures.map((feature, index) => (
                    <div key={index} className="flex align-items-center gap-3 p-3 border-1 border-200 border-round">
                      <i className={`${feature.icon} text-2xl text-primary`}></i>
                      <div>
                        <div className="font-semibold text-900">{feature.title}</div>
                        <div className="text-600 text-sm">{feature.description}</div>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="flex gap-2">
                  <Button
                    icon="pi pi-download"
                    label="Download Extension"
                    className="flex-1"
                    onClick={() => {
                      toast.current?.show({
                        severity: 'info',
                        summary: 'Download Started',
                        detail: 'AutoDMCA Chrome Extension downloading...'
                      });
                    }}
                  />
                  <Button
                    icon="pi pi-book"
                    label="Setup Guide"
                    outlined
                    onClick={() => {
                      toast.current?.show({
                        severity: 'info',
                        summary: 'Opening Guide',
                        detail: 'Setup instructions will open in a new tab'
                      });
                    }}
                  />
                </div>
              </Card>
            </div>

            {/* Extension Settings */}
            <div className="col-12 lg:col-6">
              <Card title="Extension Configuration">
                <div className="flex flex-column gap-4">
                  
                  <div>
                    <label className="block text-900 font-medium mb-2">
                      Default Watermark Type
                    </label>
                    <Dropdown
                      value={selectedWatermarkType}
                      options={watermarkTypes}
                      onChange={(e) => setSelectedWatermarkType(e.value)}
                      optionLabel="label"
                      optionValue="value"
                      className="w-full"
                    />
                  </div>

                  <div>
                    <label className="block text-900 font-medium mb-2">
                      Default Watermark Strength: {watermarkStrength}%
                    </label>
                    <Slider
                      value={watermarkStrength}
                      onChange={(e) => setWatermarkStrength(e.value as number)}
                      min={10}
                      max={100}
                      step={5}
                      className="w-full"
                    />
                  </div>

                  <div className="flex align-items-center gap-2">
                    <Checkbox
                      inputId="auto-watermark"
                      checked={true}
                      onChange={() => {}}
                    />
                    <label htmlFor="auto-watermark" className="text-900">
                      Enable automatic watermarking
                    </label>
                  </div>

                  <div className="flex align-items-center gap-2">
                    <Checkbox
                      inputId="leak-notifications"
                      checked={true}
                      onChange={() => {}}
                    />
                    <label htmlFor="leak-notifications" className="text-900">
                      Enable leak detection notifications
                    </label>
                  </div>

                  <div className="flex align-items-center gap-2">
                    <Checkbox
                      inputId="batch-processing"
                      checked={false}
                      onChange={() => {}}
                    />
                    <label htmlFor="batch-processing" className="text-900">
                      Enable batch processing for multiple uploads
                    </label>
                  </div>

                  <Button
                    label="Save Configuration"
                    className="w-full mt-3"
                    onClick={() => {
                      toast.current?.show({
                        severity: 'success',
                        summary: 'Settings Saved',
                        detail: 'Extension configuration updated successfully'
                      });
                    }}
                  />
                </div>
              </Card>

              {/* Extension Status */}
              <Card title="Extension Status" className="mt-3">
                <div className="flex align-items-center gap-3 p-3 bg-green-50 border-round">
                  <i className="pi pi-check-circle text-2xl text-green-600"></i>
                  <div>
                    <div className="font-semibold text-green-900">Extension Active</div>
                    <div className="text-green-700 text-sm">
                      Version 2.1.0 - Last sync: 2 minutes ago
                    </div>
                  </div>
                </div>

                <div className="mt-3">
                  <div className="flex justify-content-between align-items-center mb-2">
                    <span className="text-900 font-medium">Files Watermarked Today</span>
                    <span className="text-primary font-bold">247</span>
                  </div>
                  <div className="flex justify-content-between align-items-center mb-2">
                    <span className="text-900 font-medium">Active Watermarks</span>
                    <span className="text-primary font-bold">{watermarkSettings.filter(w => w.isActive).length}</span>
                  </div>
                  <div className="flex justify-content-between align-items-center">
                    <span className="text-900 font-medium">Leaks Detected This Week</span>
                    <span className="text-red-600 font-bold">{leakDetections.length}</span>
                  </div>
                </div>
              </Card>
            </div>
          </div>
        </TabPanel>

        {/* Analytics Tab */}
        <TabPanel header="Analytics" leftIcon="pi pi-chart-line">
          <div className="grid">
            
            {/* Watermarking Statistics */}
            <div className="col-12 lg:col-6">
              <Card title="Watermarking Statistics">
                <Chart
                  type="doughnut"
                  data={{
                    labels: watermarkTypes.map(t => t.label),
                    datasets: [{
                      data: watermarkTypes.map(() => Math.floor(Math.random() * 100) + 10),
                      backgroundColor: [
                        '#FF6384',
                        '#36A2EB',
                        '#FFCE56',
                        '#4BC0C0',
                        '#9966FF',
                        '#FF9F40'
                      ]
                    }]
                  }}
                  options={{
                    responsive: true,
                    plugins: {
                      legend: {
                        position: 'bottom'
                      }
                    }
                  }}
                />
              </Card>
            </div>

            {/* Leak Detection Timeline */}
            <div className="col-12 lg:col-6">
              <Card title="Leak Detection Timeline">
                <Timeline
                  value={leakDetections.slice(0, 5)}
                  content={(item) => (
                    <div className="p-3">
                      <div className="font-semibold text-900">{item.source}</div>
                      <div className="text-600 text-sm mb-2">
                        Subscriber: {item.subscriberName}
                      </div>
                      <div className="flex align-items-center gap-2">
                        <Badge
                          value={`${item.confidence}% confidence`}
                          severity={item.confidence >= 90 ? 'success' : 'warning'}
                        />
                        <Badge value={item.status} severity="info" />
                      </div>
                    </div>
                  )}
                  marker={(item) => (
                    <span
                      className={`flex w-2rem h-2rem align-items-center justify-content-center text-white border-circle z-1 shadow-1 ${
                        item.status === 'verified' ? 'bg-red-500' : 
                        item.status === 'investigating' ? 'bg-yellow-500' : 'bg-blue-500'
                      }`}
                    >
                      <i className="pi pi-exclamation-triangle"></i>
                    </span>
                  )}
                />
              </Card>
            </div>

            {/* Performance Metrics */}
            <div className="col-12">
              <Card title="Performance Metrics">
                <div className="grid">
                  <div className="col-12 md:col-2">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-blue-500 mb-1">1,247</div>
                      <div className="text-600 text-sm">Total Files Watermarked</div>
                    </div>
                  </div>
                  <div className="col-12 md:col-2">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-green-500 mb-1">98.7%</div>
                      <div className="text-600 text-sm">Success Rate</div>
                    </div>
                  </div>
                  <div className="col-12 md:col-2">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-orange-500 mb-1">2.3s</div>
                      <div className="text-600 text-sm">Avg Processing Time</div>
                    </div>
                  </div>
                  <div className="col-12 md:col-2">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-red-500 mb-1">{leakDetections.length}</div>
                      <div className="text-600 text-sm">Leaks Detected</div>
                    </div>
                  </div>
                  <div className="col-12 md:col-2">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-purple-500 mb-1">89%</div>
                      <div className="text-600 text-sm">Leak Detection Accuracy</div>
                    </div>
                  </div>
                  <div className="col-12 md:col-2">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-cyan-500 mb-1">47</div>
                      <div className="text-600 text-sm">Active Subscribers</div>
                    </div>
                  </div>
                </div>
              </Card>
            </div>
          </div>
        </TabPanel>
      </TabView>

      {/* Create Watermark Dialog */}
      <Dialog
        header="Create New Watermark"
        visible={showWatermarkDialog}
        style={{ width: '600px' }}
        onHide={() => setShowWatermarkDialog(false)}
        footer={
          <div className="flex justify-content-end gap-2">
            <Button
              label="Cancel"
              outlined
              onClick={() => setShowWatermarkDialog(false)}
            />
            <Button
              label="Create Watermark"
              onClick={handleCreateWatermark}
              disabled={!watermarkName.trim()}
            />
          </div>
        }
      >
        <div className="flex flex-column gap-4">
          <div>
            <label className="block text-900 font-medium mb-2">
              Watermark Name *
            </label>
            <InputText
              value={watermarkName}
              onChange={(e) => setWatermarkName(e.target.value)}
              placeholder="Enter watermark name"
              className="w-full"
            />
          </div>

          <div>
            <label className="block text-900 font-medium mb-2">
              Watermark Type
            </label>
            <Dropdown
              value={selectedWatermarkType}
              options={watermarkTypes}
              onChange={(e) => setSelectedWatermarkType(e.value)}
              optionLabel="label"
              optionValue="value"
              className="w-full"
            />
          </div>

          <div>
            <label className="block text-900 font-medium mb-2">
              Watermark Strength: {watermarkStrength}%
            </label>
            <Slider
              value={watermarkStrength}
              onChange={(e) => setWatermarkStrength(e.value as number)}
              min={10}
              max={100}
              step={5}
              className="w-full"
            />
            <div className="text-sm text-600 mt-1">
              Higher strength provides better protection but may affect quality
            </div>
          </div>

          <div className="grid">
            <div className="col-6">
              <label className="block text-900 font-medium mb-2">
                Subscriber ID
              </label>
              <InputText
                value={subscriberId}
                onChange={(e) => setSubscriberId(e.target.value)}
                placeholder="Optional subscriber ID"
                className="w-full"
              />
            </div>
            <div className="col-6">
              <label className="block text-900 font-medium mb-2">
                Subscriber Name
              </label>
              <InputText
                value={subscriberName}
                onChange={(e) => setSubscriberName(e.target.value)}
                placeholder="Optional subscriber name"
                className="w-full"
              />
            </div>
          </div>

          <div>
            <label className="block text-900 font-medium mb-2">
              Metadata (JSON)
            </label>
            <InputTextarea
              value={watermarkMetadata}
              onChange={(e) => setWatermarkMetadata(e.target.value)}
              placeholder='{"tier": "premium", "region": "US"}'
              rows={3}
              className="w-full"
            />
            <div className="text-sm text-600 mt-1">
              Additional metadata in JSON format (optional)
            </div>
          </div>
        </div>
      </Dialog>

      {/* Preview Dialog */}
      <Dialog
        header={`Preview: ${selectedContent?.filename}`}
        visible={showPreviewDialog}
        style={{ width: '800px', height: '600px' }}
        onHide={() => setShowPreviewDialog(false)}
        maximizable
      >
        {selectedContent && (
          <div className="flex flex-column gap-4">
            <div className="grid">
              <div className="col-6">
                <Card title="Original" className="h-full">
                  <div className="text-center text-600 py-6">
                    <i className="pi pi-image text-6xl mb-3"></i>
                    <p>Original content preview</p>
                  </div>
                </Card>
              </div>
              <div className="col-6">
                <Card title="Watermarked" className="h-full">
                  <div className="text-center text-600 py-6">
                    <i className="pi pi-shield text-6xl mb-3"></i>
                    <p>Watermarked content preview</p>
                    <div className="text-sm text-success mt-2">
                      <i className="pi pi-check-circle mr-1"></i>
                      Watermark applied successfully
                    </div>
                  </div>
                </Card>
              </div>
            </div>

            <Card title="Watermark Details">
              <div className="grid">
                <div className="col-4">
                  <strong>Type:</strong> {selectedContent.watermarkType.replace('-', ' ')}
                </div>
                <div className="col-4">
                  <strong>Subscriber:</strong> {selectedContent.subscriberName}
                </div>
                <div className="col-4">
                  <strong>Date:</strong> {selectedContent.uploadDate.toLocaleDateString()}
                </div>
              </div>
            </Card>
          </div>
        )}
      </Dialog>

      {/* Leak Analysis Dialog */}
      <Dialog
        header="Leak Analysis"
        visible={showLeakAnalysisDialog}
        style={{ width: '700px' }}
        onHide={() => setShowLeakAnalysisDialog(false)}
      >
        {selectedContent && (
          <div className="flex flex-column gap-4">
            <Card title="Content Information">
              <div className="grid">
                <div className="col-6">
                  <strong>Filename:</strong> {selectedContent.filename}
                </div>
                <div className="col-6">
                  <strong>Subscriber:</strong> {selectedContent.subscriberName}
                </div>
                <div className="col-6">
                  <strong>Watermark Type:</strong> {selectedContent.watermarkType}
                </div>
                <div className="col-6">
                  <strong>Upload Date:</strong> {selectedContent.uploadDate.toLocaleDateString()}
                </div>
              </div>
            </Card>

            <Card title="Scan Results">
              {selectedContent.leakDetections && selectedContent.leakDetections.length > 0 ? (
                <div className="flex flex-column gap-3">
                  {selectedContent.leakDetections.map(leak => (
                    <div key={leak.id} className="p-3 border-1 border-200 border-round">
                      <div className="flex justify-content-between align-items-start mb-2">
                        <div>
                          <div className="font-semibold text-900">{leak.source}</div>
                          <div className="text-600 text-sm">
                            Detected: {leak.detectedAt.toLocaleDateString()}
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <Badge
                            value={`${leak.confidence}% confidence`}
                            severity={leak.confidence >= 90 ? 'success' : 'warning'}
                          />
                          <Badge value={leak.status} severity="info" />
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          label="View Evidence"
                          size="small"
                          outlined
                          icon="pi pi-eye"
                        />
                        <Button
                          label="Send DMCA"
                          size="small"
                          icon="pi pi-send"
                        />
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-4">
                  <i className="pi pi-check-circle text-4xl text-green-500 mb-3"></i>
                  <p className="text-600">No leaks detected for this content</p>
                </div>
              )}
            </Card>

            <Button
              label="Start New Scan"
              className="w-full"
              onClick={() => {
                toast.current?.show({
                  severity: 'info',
                  summary: 'Scan Started',
                  detail: 'Scanning for new leaks across the internet...'
                });
              }}
            />
          </div>
        )}
      </Dialog>

      {/* Batch Processing Dialog */}
      <Dialog
        header="Batch Processing"
        visible={showBatchDialog}
        style={{ width: '600px' }}
        onHide={() => setShowBatchDialog(false)}
      >
        <div className="flex flex-column gap-4">
          <div className="text-center">
            <i className="pi pi-download text-4xl text-primary mb-3"></i>
            <h3 className="text-900 mb-2">Batch Download Watermarked Content</h3>
            <p className="text-600">
              Download multiple watermarked files in a single ZIP archive
            </p>
          </div>

          <Card title="Selected Files">
            <div className="text-900 font-medium mb-2">
              {watermarkedContent.filter(c => c.status === 'completed').length} files available for download
            </div>
            <div className="text-600 text-sm">
              Total size: {formatFileSize(
                watermarkedContent
                  .filter(c => c.status === 'completed')
                  .reduce((total, c) => total + c.watermarkedSize, 0)
              )}
            </div>
          </Card>

          <div className="flex gap-2">
            <Button
              label="Download All"
              className="flex-1"
              icon="pi pi-download"
              onClick={() => {
                toast.current?.show({
                  severity: 'success',
                  summary: 'Download Started',
                  detail: 'Preparing batch download...'
                });
                setShowBatchDialog(false);
              }}
            />
            <Button
              label="Cancel"
              outlined
              onClick={() => setShowBatchDialog(false)}
            />
          </div>
        </div>
      </Dialog>

      {/* Settings Dialog */}
      <Dialog
        header="Watermarking Settings"
        visible={showSettingsDialog}
        style={{ width: '600px' }}
        onHide={() => setShowSettingsDialog(false)}
        footer={
          <div className="flex justify-content-end gap-2">
            <Button
              label="Cancel"
              outlined
              onClick={() => setShowSettingsDialog(false)}
            />
            <Button
              label="Save Settings"
              onClick={() => {
                toast.current?.show({
                  severity: 'success',
                  summary: 'Settings Saved',
                  detail: 'Watermarking settings updated successfully'
                });
                setShowSettingsDialog(false);
              }}
            />
          </div>
        }
      >
        <div className="flex flex-column gap-4">
          <Panel header="Default Settings" toggleable>
            <div className="flex flex-column gap-3">
              <div>
                <label className="block text-900 font-medium mb-2">
                  Default Watermark Type
                </label>
                <Dropdown
                  value={selectedWatermarkType}
                  options={watermarkTypes}
                  onChange={(e) => setSelectedWatermarkType(e.value)}
                  optionLabel="label"
                  optionValue="value"
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-900 font-medium mb-2">
                  Default Strength: {watermarkStrength}%
                </label>
                <Slider
                  value={watermarkStrength}
                  onChange={(e) => setWatermarkStrength(e.value as number)}
                  min={10}
                  max={100}
                  step={5}
                  className="w-full"
                />
              </div>
            </div>
          </Panel>

          <Panel header="Processing Options" toggleable>
            <div className="flex flex-column gap-3">
              <div className="flex align-items-center gap-2">
                <Checkbox inputId="auto-process" checked={true} />
                <label htmlFor="auto-process">Auto-process uploaded files</label>
              </div>
              <div className="flex align-items-center gap-2">
                <Checkbox inputId="preserve-metadata" checked={true} />
                <label htmlFor="preserve-metadata">Preserve original metadata</label>
              </div>
              <div className="flex align-items-center gap-2">
                <Checkbox inputId="backup-original" checked={false} />
                <label htmlFor="backup-original">Keep backup of original files</label>
              </div>
            </div>
          </Panel>

          <Panel header="Security Settings" toggleable>
            <div className="flex flex-column gap-3">
              <div className="flex align-items-center gap-2">
                <Checkbox inputId="encrypt-watermarks" checked={true} />
                <label htmlFor="encrypt-watermarks">Encrypt watermark data</label>
              </div>
              <div className="flex align-items-center gap-2">
                <Checkbox inputId="multi-layer" checked={true} />
                <label htmlFor="multi-layer">Apply multiple watermark layers</label>
              </div>
              <div className="flex align-items-center gap-2">
                <Checkbox inputId="robustness-test" checked={false} />
                <label htmlFor="robustness-test">Run robustness tests</label>
              </div>
            </div>
          </Panel>
        </div>
      </Dialog>
    </div>
  );
};

export default ContentWatermarking;