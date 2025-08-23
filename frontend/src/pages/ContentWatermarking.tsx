import React, { useState, useEffect, useRef } from 'react';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { FileUpload } from 'primereact/fileupload';
import { TabView, TabPanel } from 'primereact/tabview';
import { InputText } from 'primereact/inputtext';
import { InputTextarea } from 'primereact/inputtextarea';
import { Dropdown } from 'primereact/dropdown';
import { Slider } from 'primereact/slider';
import { Toast } from 'primereact/toast';
import { ProgressBar } from 'primereact/progressbar';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Tag } from 'primereact/tag';
import { Badge } from 'primereact/badge';
import { Panel } from 'primereact/panel';
import { Divider } from 'primereact/divider';
import { Dialog } from 'primereact/dialog';
import { Image } from 'primereact/image';
import { Message } from 'primereact/message';
import { confirmDialog, ConfirmDialog } from 'primereact/confirmdialog';
import api from '../services/api';

interface WatermarkJob {
  id: number;
  job_name: string;
  status: string;
  progress_percentage: number;
  watermark_type: string;
  original_filename: string;
  created_at: string;
  completed_at?: string;
  output_file_path?: string;
}

interface WatermarkTemplate {
  id: number;
  template_name: string;
  description?: string;
  watermark_type: string;
  is_default: boolean;
  usage_count: number;
  created_at: string;
}

interface WatermarkStats {
  total_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  success_rate: number;
  total_templates: number;
}

const ContentWatermarking: React.FC = () => {
  const toast = useRef<Toast>(null);
  const fileUploadRef = useRef<FileUpload>(null);

  // State
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(false);
  const [jobs, setJobs] = useState<WatermarkJob[]>([]);
  const [templates, setTemplates] = useState<WatermarkTemplate[]>([]);
  const [stats, setStats] = useState<WatermarkStats | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [previewImage, setPreviewImage] = useState<string | null>(null);

  // Watermark configuration
  const [jobName, setJobName] = useState('');
  const [watermarkType, setWatermarkType] = useState('visible_text');
  const [watermarkText, setWatermarkText] = useState('© Protected Content');
  const [position, setPosition] = useState('bottom_right');
  const [opacity, setOpacity] = useState(0.7);
  const [fontSize, setFontSize] = useState(36);
  const [fontColor, setFontColor] = useState('white');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);

  // Template creation
  const [showTemplateDialog, setShowTemplateDialog] = useState(false);
  const [templateName, setTemplateName] = useState('');
  const [templateDescription, setTemplateDescription] = useState('');

  // Options
  const watermarkTypes = [
    { label: 'Visible Text', value: 'visible_text' },
    { label: 'Invisible Watermark', value: 'invisible' },
    { label: 'Visible Image', value: 'visible_image' }
  ];

  const positions = [
    { label: 'Top Left', value: 'top_left' },
    { label: 'Top Right', value: 'top_right' },
    { label: 'Bottom Left', value: 'bottom_left' },
    { label: 'Bottom Right', value: 'bottom_right' },
    { label: 'Center', value: 'center' }
  ];

  const fontColors = [
    { label: 'White', value: 'white' },
    { label: 'Black', value: 'black' }
  ];

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [jobsRes, templatesRes, statsRes] = await Promise.all([
        api.get('/watermarking/jobs'),
        api.get('/watermarking/templates'),
        api.get('/watermarking/stats')
      ]);

      setJobs(jobsRes.data);
      setTemplates(templatesRes.data);
      setStats(statsRes.data);
    } catch (error) {
      console.error('Error loading watermarking data:', error);
      showError('Failed to load data');
    }
  };

  const showSuccess = (message: string) => {
    toast.current?.show({ severity: 'success', summary: 'Success', detail: message });
  };

  const showError = (message: string) => {
    toast.current?.show({ severity: 'error', summary: 'Error', detail: message });
  };

  const showInfo = (message: string) => {
    toast.current?.show({ severity: 'info', summary: 'Info', detail: message });
  };

  const onFileSelect = (event: any) => {
    setSelectedFiles(event.files);
  };

  const onFileRemove = (file: File) => {
    setSelectedFiles(prev => prev.filter(f => f !== file));
  };

  const handleWatermark = async () => {
    if (!jobName.trim()) {
      showError('Please enter a job name');
      return;
    }

    if (selectedFiles.length === 0) {
      showError('Please select at least one image');
      return;
    }

    try {
      setLoading(true);

      for (const file of selectedFiles) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('job_name', `${jobName} - ${file.name}`);
        
        const config = {
          watermark_type: watermarkType,
          text: watermarkText,
          position,
          opacity,
          font_size: fontSize,
          font_color: fontColor,
          data: `Protected by AutoDMCA - ${Date.now()}`
        };
        
        formData.append('config', JSON.stringify(config));

        const response = await api.post('/watermarking/upload', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });

        showSuccess(`Watermarking job created for ${file.name}`);
      }

      // Clear form and reload data
      setJobName('');
      setSelectedFiles([]);
      fileUploadRef.current?.clear();
      await loadData();

    } catch (error: any) {
      console.error('Error creating watermark job:', error);
      showError(error.response?.data?.detail || 'Failed to create watermark job');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyWatermark = async (file: File) => {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await api.post('/watermarking/verify', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });

      const result = response.data;
      
      if (result.verified) {
        showSuccess(`Watermark verified! Confidence: ${(result.confidence_score * 100).toFixed(1)}%`);
      } else {
        showInfo(result.error || 'No watermark found in this image');
      }

    } catch (error: any) {
      console.error('Error verifying watermark:', error);
      showError('Failed to verify watermark');
    }
  };

  const handleDeleteJob = async (jobId: number) => {
    try {
      await api.delete(`/watermarking/jobs/${jobId}`);
      showSuccess('Job deleted successfully');
      await loadData();
    } catch (error: any) {
      console.error('Error deleting job:', error);
      showError('Failed to delete job');
    }
  };

  const confirmDeleteJob = (job: WatermarkJob) => {
    confirmDialog({
      message: `Are you sure you want to delete the job "${job.job_name}"?`,
      header: 'Delete Job',
      icon: 'pi pi-exclamation-triangle',
      accept: () => handleDeleteJob(job.id)
    });
  };

  const handleSaveTemplate = async () => {
    if (!templateName.trim()) {
      showError('Please enter a template name');
      return;
    }

    try {
      const templateData = {
        template_name: templateName,
        description: templateDescription,
        watermark_type: watermarkType,
        config: {
          text: watermarkText,
          position,
          opacity,
          font_size: fontSize,
          font_color: fontColor
        }
      };

      await api.post('/watermarking/templates', templateData);
      
      showSuccess('Template saved successfully');
      setShowTemplateDialog(false);
      setTemplateName('');
      setTemplateDescription('');
      await loadData();

    } catch (error: any) {
      console.error('Error saving template:', error);
      showError('Failed to save template');
    }
  };

  const getStatusSeverity = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'processing':
        return 'info';
      case 'failed':
        return 'danger';
      default:
        return 'warning';
    }
  };

  const statusBodyTemplate = (rowData: WatermarkJob) => {
    return <Tag value={rowData.status} severity={getStatusSeverity(rowData.status)} />;
  };

  const progressBodyTemplate = (rowData: WatermarkJob) => {
    return (
      <div>
        <ProgressBar value={rowData.progress_percentage} />
        <small>{rowData.progress_percentage.toFixed(0)}%</small>
      </div>
    );
  };

  const actionsBodyTemplate = (rowData: WatermarkJob) => {
    return (
      <div className="flex gap-2">
        {rowData.output_file_path && (
          <Button
            icon="pi pi-download"
            size="small"
            severity="secondary"
            tooltip="Download"
            onClick={() => showInfo('Download functionality would be implemented here')}
          />
        )}
        <Button
          icon="pi pi-trash"
          size="small"
          severity="danger"
          tooltip="Delete"
          onClick={() => confirmDeleteJob(rowData)}
        />
      </div>
    );
  };

  const renderCreateWatermark = () => (
    <div className="grid">
      <div className="col-12 md:col-8">
        <Card title="Create Watermark" className="mb-4">
          {/* File Upload */}
          <div className="field">
            <label className="block mb-2 font-semibold">Select Images</label>
            <FileUpload
              ref={fileUploadRef}
              name="files"
              multiple
              accept="image/*"
              maxFileSize={10000000}
              customUpload
              onSelect={onFileSelect}
              onRemove={(e) => onFileRemove(e.file)}
              emptyTemplate={
                <div className="text-center p-4">
                  <i className="pi pi-cloud-upload text-4xl text-400 mb-3"></i>
                  <div className="text-600">Drag and drop images here or click to browse</div>
                  <small className="text-500">Supported: JPG, PNG, GIF (Max 10MB)</small>
                </div>
              }
            />
          </div>

          {/* Job Configuration */}
          <div className="field">
            <label htmlFor="jobName" className="block mb-2 font-semibold">Job Name</label>
            <InputText
              id="jobName"
              value={jobName}
              onChange={(e) => setJobName(e.target.value)}
              placeholder="Enter job name"
              className="w-full"
            />
          </div>

          <div className="field">
            <label className="block mb-2 font-semibold">Watermark Type</label>
            <Dropdown
              value={watermarkType}
              onChange={(e) => setWatermarkType(e.value)}
              options={watermarkTypes}
              className="w-full"
            />
          </div>

          {watermarkType === 'visible_text' && (
            <>
              <div className="field">
                <label className="block mb-2 font-semibold">Watermark Text</label>
                <InputText
                  value={watermarkText}
                  onChange={(e) => setWatermarkText(e.target.value)}
                  placeholder="Enter watermark text"
                  className="w-full"
                />
              </div>

              <div className="grid">
                <div className="col-6">
                  <label className="block mb-2 font-semibold">Position</label>
                  <Dropdown
                    value={position}
                    onChange={(e) => setPosition(e.value)}
                    options={positions}
                    className="w-full"
                  />
                </div>
                <div className="col-6">
                  <label className="block mb-2 font-semibold">Font Color</label>
                  <Dropdown
                    value={fontColor}
                    onChange={(e) => setFontColor(e.value)}
                    options={fontColors}
                    className="w-full"
                  />
                </div>
              </div>

              <div className="grid">
                <div className="col-6">
                  <label className="block mb-2 font-semibold">Opacity: {Math.round(opacity * 100)}%</label>
                  <Slider
                    value={opacity}
                    onChange={(e) => setOpacity(e.value as number)}
                    min={0.1}
                    max={1.0}
                    step={0.1}
                    className="w-full"
                  />
                </div>
                <div className="col-6">
                  <label className="block mb-2 font-semibold">Font Size: {fontSize}px</label>
                  <Slider
                    value={fontSize}
                    onChange={(e) => setFontSize(e.value as number)}
                    min={12}
                    max={72}
                    step={4}
                    className="w-full"
                  />
                </div>
              </div>
            </>
          )}

          <div className="flex gap-3 mt-4">
            <Button
              label={loading ? "Processing..." : "Apply Watermarks"}
              icon={loading ? "pi pi-spin pi-spinner" : "pi pi-shield"}
              onClick={handleWatermark}
              disabled={loading || selectedFiles.length === 0}
              className="flex-1"
            />
            <Button
              label="Save as Template"
              icon="pi pi-save"
              severity="secondary"
              onClick={() => setShowTemplateDialog(true)}
            />
          </div>
        </Card>
      </div>

      <div className="col-12 md:col-4">
        {/* Stats Card */}
        {stats && (
          <Card title="Your Statistics" className="mb-4">
            <div className="grid text-center">
              <div className="col-6">
                <div className="text-2xl font-bold text-blue-500">{stats.total_jobs}</div>
                <div className="text-sm text-600">Total Jobs</div>
              </div>
              <div className="col-6">
                <div className="text-2xl font-bold text-green-500">{stats.success_rate.toFixed(0)}%</div>
                <div className="text-sm text-600">Success Rate</div>
              </div>
              <div className="col-6 mt-3">
                <div className="text-2xl font-bold text-orange-500">{stats.completed_jobs}</div>
                <div className="text-sm text-600">Completed</div>
              </div>
              <div className="col-6 mt-3">
                <div className="text-2xl font-bold text-purple-500">{stats.total_templates}</div>
                <div className="text-sm text-600">Templates</div>
              </div>
            </div>
          </Card>
        )}

        {/* Tips Card */}
        <Card title="Watermarking Tips">
          <ul className="list-none p-0 m-0">
            <li className="flex align-items-center mb-2">
              <i className="pi pi-check text-green-500 mr-2" />
              <span className="text-sm">Use invisible watermarks for subtle protection</span>
            </li>
            <li className="flex align-items-center mb-2">
              <i className="pi pi-check text-green-500 mr-2" />
              <span className="text-sm">Lower opacity blends better with images</span>
            </li>
            <li className="flex align-items-center mb-2">
              <i className="pi pi-check text-green-500 mr-2" />
              <span className="text-sm">Corner positions are less intrusive</span>
            </li>
            <li className="flex align-items-center">
              <i className="pi pi-check text-green-500 mr-2" />
              <span className="text-sm">Save templates for consistent branding</span>
            </li>
          </ul>
        </Card>
      </div>
    </div>
  );

  const renderJobHistory = () => (
    <Card title="Watermarking Jobs">
      <DataTable value={jobs} paginator rows={10} emptyMessage="No watermarking jobs found">
        <Column field="job_name" header="Job Name" />
        <Column field="original_filename" header="File" />
        <Column field="watermark_type" header="Type" />
        <Column field="status" header="Status" body={statusBodyTemplate} />
        <Column field="progress_percentage" header="Progress" body={progressBodyTemplate} />
        <Column 
          field="created_at" 
          header="Created" 
          body={(rowData) => new Date(rowData.created_at).toLocaleDateString()}
        />
        <Column header="Actions" body={actionsBodyTemplate} />
      </DataTable>
    </Card>
  );

  const renderVerification = () => (
    <div className="grid">
      <div className="col-12 md:col-8">
        <Card title="Verify Watermark">
          <p className="text-600 mb-4">
            Upload an image to check if it contains a watermark created with our system.
          </p>
          
          <FileUpload
            name="verifyFile"
            accept="image/*"
            maxFileSize={10000000}
            customUpload
            auto
            onSelect={(e) => {
              if (e.files.length > 0) {
                handleVerifyWatermark(e.files[0]);
              }
            }}
            emptyTemplate={
              <div className="text-center p-4">
                <i className="pi pi-search text-4xl text-400 mb-3"></i>
                <div className="text-600">Drop image here to verify watermark</div>
                <small className="text-500">Supported: JPG, PNG, GIF</small>
              </div>
            }
          />
        </Card>
      </div>
      
      <div className="col-12 md:col-4">
        <Card title="Verification Process">
          <div className="mb-3">
            <h5>How it works:</h5>
            <ol className="text-sm">
              <li className="mb-2">Upload the image you want to verify</li>
              <li className="mb-2">Our system scans for watermark patterns</li>
              <li className="mb-2">Results show verification status and confidence</li>
              <li>Original metadata is preserved when possible</li>
            </ol>
          </div>
          
          <Message 
            severity="info" 
            text="Only watermarks created with our system can be verified." 
          />
        </Card>
      </div>
    </div>
  );

  return (
    <div className="p-4">
      <Toast ref={toast} />
      <ConfirmDialog />
      
      <div className="flex justify-content-between align-items-center mb-4">
        <h1 className="text-3xl font-bold text-900">Content Watermarking</h1>
        <Tag value="Protect Your Content" severity="info" />
      </div>

      <TabView activeIndex={activeTab} onTabChange={(e) => setActiveTab(e.index)}>
        <TabPanel header="Create Watermarks" leftIcon="pi pi-plus-circle">
          {renderCreateWatermark()}
        </TabPanel>

        <TabPanel header="Job History" leftIcon="pi pi-history">
          {renderJobHistory()}
        </TabPanel>

        <TabPanel header="Verify Watermarks" leftIcon="pi pi-search">
          {renderVerification()}
        </TabPanel>

        <TabPanel header="Templates" leftIcon="pi pi-bookmark">
          <Card title="Watermark Templates">
            {templates.length > 0 ? (
              <DataTable value={templates}>
                <Column field="template_name" header="Name" />
                <Column field="description" header="Description" />
                <Column field="watermark_type" header="Type" />
                <Column 
                  field="usage_count" 
                  header="Used" 
                  body={(rowData) => <Badge value={rowData.usage_count} />}
                />
                <Column 
                  field="created_at" 
                  header="Created" 
                  body={(rowData) => new Date(rowData.created_at).toLocaleDateString()}
                />
              </DataTable>
            ) : (
              <Message 
                severity="info" 
                text="No templates found. Create watermarks and save them as templates for quick reuse." 
              />
            )}
          </Card>
        </TabPanel>
      </TabView>

      {/* Template Save Dialog */}
      <Dialog
        header="Save as Template"
        visible={showTemplateDialog}
        onHide={() => setShowTemplateDialog(false)}
        style={{ width: '500px' }}
        modal
      >
        <div className="field">
          <label htmlFor="templateName" className="block mb-2 font-semibold">Template Name</label>
          <InputText
            id="templateName"
            value={templateName}
            onChange={(e) => setTemplateName(e.target.value)}
            placeholder="Enter template name"
            className="w-full"
          />
        </div>

        <div className="field">
          <label htmlFor="templateDescription" className="block mb-2 font-semibold">Description (Optional)</label>
          <InputTextarea
            id="templateDescription"
            value={templateDescription}
            onChange={(e) => setTemplateDescription(e.target.value)}
            placeholder="Describe this template..."
            rows={3}
            className="w-full"
          />
        </div>

        <div className="flex justify-content-end gap-2">
          <Button
            label="Cancel"
            severity="secondary"
            onClick={() => setShowTemplateDialog(false)}
          />
          <Button
            label="Save Template"
            icon="pi pi-save"
            onClick={handleSaveTemplate}
          />
        </div>
      </Dialog>
    </div>
  );
};

export default ContentWatermarking;