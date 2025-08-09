import React, { useState, useEffect, useRef } from 'react';
import { Card } from 'primereact/card';
import { TabView, TabPanel } from 'primereact/tabview';
import { InputText } from 'primereact/inputtext';
import { InputTextarea } from 'primereact/inputtextarea';
import { Button } from 'primereact/button';
import { Dropdown, DropdownChangeEvent } from 'primereact/dropdown';
import { FileUpload, FileUploadUploadEvent } from 'primereact/fileupload';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Tag } from 'primereact/tag';
import { ProgressBar } from 'primereact/progressbar';
import { Message } from 'primereact/message';
import { Divider } from 'primereact/divider';
import { Badge } from 'primereact/badge';
// import { Tooltip } from 'primereact/tooltip';
import { Toast } from 'primereact/toast';
import { confirmDialog } from 'primereact/confirmdialog';
import { Chip } from 'primereact/chip';
import { InputSwitch } from 'primereact/inputswitch';
import { Skeleton } from 'primereact/skeleton';
import { Panel } from 'primereact/panel';
import { MultiSelect, MultiSelectChangeEvent } from 'primereact/multiselect';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

// Types for submissions
export enum ContentType {
  IMAGES = 'images',
  VIDEOS = 'videos', 
  DOCUMENTS = 'documents',
  URLS = 'urls'
}

export enum PriorityLevel {
  NORMAL = 'normal',
  HIGH = 'high',
  URGENT = 'urgent'
}

export enum SubmissionStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  ACTIVE = 'active',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled'
}

export interface Submission {
  id: string;
  userId: number;
  profileId?: number;
  type: ContentType;
  priority: PriorityLevel;
  status: SubmissionStatus;
  title: string;
  urls: string[];
  files?: File[];
  tags: string[];
  category?: string;
  description?: string;
  progressPercentage: number;
  estimatedCompletion?: Date;
  autoMonitoring: boolean;
  notifyOnInfringement: boolean;
  createdAt: Date;
  updatedAt: Date;
  completedAt?: Date;
  errorMessage?: string;
  totalUrls: number;
  processedUrls: number;
  validUrls: number;
  invalidUrls: number;
}

export interface SubmissionForm {
  title: string;
  type: ContentType;
  priority: PriorityLevel;
  singleUrl: string;
  bulkUrls: string;
  tags: string[];
  category: string;
  description: string;
  autoMonitoring: boolean;
  notifyOnInfringement: boolean;
  files: File[];
}

const Submissions: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const toast = useRef<Toast>(null);
  const fileUploadRef = useRef<FileUpload>(null);

  // State
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState(0);
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [uploading, setUploading] = useState(false);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  const [form, setForm] = useState<SubmissionForm>({
    title: '',
    type: ContentType.URLS,
    priority: PriorityLevel.NORMAL,
    singleUrl: '',
    bulkUrls: '',
    tags: [],
    category: '',
    description: '',
    autoMonitoring: true,
    notifyOnInfringement: true,
    files: []
  });

  // Options for dropdowns
  const contentTypeOptions = [
    { label: 'URLs', value: ContentType.URLS, icon: 'pi pi-link' },
    { label: 'Images', value: ContentType.IMAGES, icon: 'pi pi-image' },
    { label: 'Videos', value: ContentType.VIDEOS, icon: 'pi pi-video' },
    { label: 'Documents', value: ContentType.DOCUMENTS, icon: 'pi pi-file' }
  ];

  const priorityOptions = [
    { label: 'Normal', value: PriorityLevel.NORMAL, color: '#6c757d' },
    { label: 'High', value: PriorityLevel.HIGH, color: '#fd7e14' },
    { label: 'Urgent', value: PriorityLevel.URGENT, color: '#dc3545' }
  ];

  const categoryOptions = [
    { label: 'Adult Content', value: 'adult' },
    { label: 'Social Media', value: 'social' },
    { label: 'E-commerce', value: 'ecommerce' },
    { label: 'Photography', value: 'photography' },
    { label: 'Music/Audio', value: 'music' },
    { label: 'Gaming', value: 'gaming' },
    { label: 'Educational', value: 'educational' },
    { label: 'Other', value: 'other' }
  ];

  const commonTags = [
    { label: 'Piracy', value: 'piracy' },
    { label: 'Unauthorized Distribution', value: 'unauthorized' },
    { label: 'Copyright Infringement', value: 'copyright' },
    { label: 'Trademark Violation', value: 'trademark' },
    { label: 'Identity Theft', value: 'identity' },
    { label: 'Deepfake', value: 'deepfake' },
    { label: 'Revenge Porn', value: 'revenge' },
    { label: 'Impersonation', value: 'impersonation' }
  ];

  // Mock data - in real app, this would come from API
  useEffect(() => {
    const mockSubmissions: Submission[] = [
      {
        id: '1',
        userId: user?.id || 1,
        profileId: 1,
        type: ContentType.URLS,
        priority: PriorityLevel.HIGH,
        status: SubmissionStatus.PROCESSING,
        title: 'Social Media Profile Protection',
        urls: ['https://instagram.com/fake-profile', 'https://tiktok.com/@impersonator'],
        tags: ['impersonation', 'social'],
        category: 'social',
        description: 'Monitoring suspicious accounts using my content',
        progressPercentage: 65,
        estimatedCompletion: new Date(Date.now() + 2 * 60 * 60 * 1000),
        autoMonitoring: true,
        notifyOnInfringement: true,
        createdAt: new Date(Date.now() - 6 * 60 * 60 * 1000),
        updatedAt: new Date(Date.now() - 1 * 60 * 60 * 1000),
        totalUrls: 2,
        processedUrls: 1,
        validUrls: 1,
        invalidUrls: 0
      },
      {
        id: '2',
        userId: user?.id || 1,
        type: ContentType.IMAGES,
        priority: PriorityLevel.NORMAL,
        status: SubmissionStatus.COMPLETED,
        title: 'Photography Portfolio Protection',
        urls: [],
        tags: ['copyright', 'photography'],
        category: 'photography',
        description: 'Uploaded portfolio images for monitoring',
        progressPercentage: 100,
        autoMonitoring: true,
        notifyOnInfringement: false,
        createdAt: new Date(Date.now() - 24 * 60 * 60 * 1000),
        updatedAt: new Date(Date.now() - 12 * 60 * 60 * 1000),
        completedAt: new Date(Date.now() - 12 * 60 * 60 * 1000),
        totalUrls: 0,
        processedUrls: 0,
        validUrls: 0,
        invalidUrls: 0
      },
      {
        id: '3',
        userId: user?.id || 1,
        type: ContentType.URLS,
        priority: PriorityLevel.URGENT,
        status: SubmissionStatus.FAILED,
        title: 'E-commerce Product Protection',
        urls: ['https://example.com/product1'],
        tags: ['piracy', 'ecommerce'],
        category: 'ecommerce',
        description: 'Product images being used without permission',
        progressPercentage: 0,
        autoMonitoring: false,
        notifyOnInfringement: true,
        createdAt: new Date(Date.now() - 48 * 60 * 60 * 1000),
        updatedAt: new Date(Date.now() - 36 * 60 * 60 * 1000),
        errorMessage: 'URL validation failed: Invalid domain',
        totalUrls: 1,
        processedUrls: 0,
        validUrls: 0,
        invalidUrls: 1
      }
    ];

    setTimeout(() => {
      setSubmissions(mockSubmissions);
      setLoading(false);
    }, 1000);
  }, [user?.id]);

  // Utility functions
  const showToast = (severity: 'success' | 'info' | 'warn' | 'error', summary: string, detail?: string) => {
    toast.current?.show({ severity, summary, detail, life: 5000 });
  };

  const validateUrl = (url: string): boolean => {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  };

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};

    if (!form.title.trim()) {
      errors.title = 'Title is required';
    }

    if (activeTab === 0) { // Single URL tab
      if (!form.singleUrl.trim()) {
        errors.singleUrl = 'URL is required';
      } else if (!validateUrl(form.singleUrl)) {
        errors.singleUrl = 'Please enter a valid URL';
      }
    } else if (activeTab === 1) { // Bulk URL tab
      if (!form.bulkUrls.trim()) {
        errors.bulkUrls = 'At least one URL is required';
      } else {
        const urls = form.bulkUrls.split('\n').map(url => url.trim()).filter(url => url);
        const invalidUrls = urls.filter(url => !validateUrl(url));
        if (invalidUrls.length > 0) {
          errors.bulkUrls = `Invalid URLs found: ${invalidUrls.slice(0, 3).join(', ')}${invalidUrls.length > 3 ? '...' : ''}`;
        }
      }
    } else if (activeTab === 2) { // File upload tab
      if (form.files.length === 0) {
        errors.files = 'At least one file is required';
      }
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Event handlers
  const handleInputChange = (field: keyof SubmissionForm, value: any) => {
    setForm(prev => ({ ...prev, [field]: value }));
    // Clear validation error when user starts typing
    if (validationErrors[field]) {
      setValidationErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  const handleFileUpload = (event: FileUploadUploadEvent) => {
    const uploadedFiles = Array.from(event.files) as File[];
    setForm(prev => ({ ...prev, files: [...prev.files, ...uploadedFiles] }));
    fileUploadRef.current?.clear();
    showToast('success', 'Files Added', `${uploadedFiles.length} file(s) added to submission`);
  };

  const removeFile = (index: number) => {
    setForm(prev => ({
      ...prev,
      files: prev.files.filter((_, i) => i !== index)
    }));
  };

  const handleSubmit = async () => {
    if (!validateForm()) {
      showToast('error', 'Validation Failed', 'Please fix the errors before submitting');
      return;
    }

    setUploading(true);
    
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 2000));

      let urls: string[] = [];
      
      if (activeTab === 0) {
        urls = [form.singleUrl];
      } else if (activeTab === 1) {
        urls = form.bulkUrls.split('\n').map(url => url.trim()).filter(url => url);
      }

      const newSubmission: Submission = {
        id: Date.now().toString(),
        userId: user?.id || 1,
        type: form.type,
        priority: form.priority,
        status: SubmissionStatus.PENDING,
        title: form.title,
        urls,
        tags: form.tags,
        category: form.category,
        description: form.description,
        progressPercentage: 0,
        autoMonitoring: form.autoMonitoring,
        notifyOnInfringement: form.notifyOnInfringement,
        createdAt: new Date(),
        updatedAt: new Date(),
        totalUrls: urls.length,
        processedUrls: 0,
        validUrls: 0,
        invalidUrls: 0,
        files: form.files.length > 0 ? form.files : undefined
      };

      setSubmissions(prev => [newSubmission, ...prev]);
      
      // Reset form
      setForm({
        title: '',
        type: ContentType.URLS,
        priority: PriorityLevel.NORMAL,
        singleUrl: '',
        bulkUrls: '',
        tags: [],
        category: '',
        description: '',
        autoMonitoring: true,
        notifyOnInfringement: true,
        files: []
      });
      
      setActiveTab(0);
      showToast('success', 'Submission Created', 'Your content has been submitted for monitoring');
    } catch (error) {
      showToast('error', 'Submission Failed', 'Please try again');
    } finally {
      setUploading(false);
    }
  };

  const cancelSubmission = (submissionId: string) => {
    confirmDialog({
      message: 'Are you sure you want to cancel this submission?',
      header: 'Cancel Submission',
      icon: 'pi pi-exclamation-triangle',
      accept: () => {
        setSubmissions(prev => 
          prev.map(sub => 
            sub.id === submissionId 
              ? { ...sub, status: SubmissionStatus.CANCELLED, progressPercentage: 0 }
              : sub
          )
        );
        showToast('info', 'Submission Cancelled', 'The submission has been cancelled');
      }
    });
  };

  const retrySubmission = (submissionId: string) => {
    setSubmissions(prev => 
      prev.map(sub => 
        sub.id === submissionId 
          ? { ...sub, status: SubmissionStatus.PENDING, progressPercentage: 0, errorMessage: undefined }
          : sub
      )
    );
    showToast('info', 'Submission Retried', 'The submission has been restarted');
  };

  const deleteSubmission = (submissionId: string) => {
    confirmDialog({
      message: 'Are you sure you want to delete this submission? This action cannot be undone.',
      header: 'Delete Submission',
      icon: 'pi pi-exclamation-triangle',
      accept: () => {
        setSubmissions(prev => prev.filter(sub => sub.id !== submissionId));
        showToast('info', 'Submission Deleted', 'The submission has been removed');
      }
    });
  };

  // Template functions for DataTable columns
  const statusTemplate = (rowData: Submission) => {
    const getSeverity = (status: SubmissionStatus) => {
      switch (status) {
        case SubmissionStatus.COMPLETED: return 'success';
        case SubmissionStatus.PROCESSING: return 'info';
        case SubmissionStatus.PENDING: return 'warning';
        case SubmissionStatus.FAILED: return 'danger';
        case SubmissionStatus.CANCELLED: return null;
        default: return 'info';
      }
    };

    return (
      <div className="flex align-items-center gap-2">
        <Tag value={rowData.status} severity={getSeverity(rowData.status)} />
        {rowData.progressPercentage > 0 && rowData.status === SubmissionStatus.PROCESSING && (
          <ProgressBar 
            value={rowData.progressPercentage} 
            style={{ width: '60px', height: '6px' }}
            showValue={false}
          />
        )}
      </div>
    );
  };

  const priorityTemplate = (rowData: Submission) => {
    const option = priorityOptions.find(opt => opt.value === rowData.priority);
    return (
      <Badge 
        value={option?.label} 
        style={{ backgroundColor: option?.color }}
      />
    );
  };

  const typeTemplate = (rowData: Submission) => {
    const option = contentTypeOptions.find(opt => opt.value === rowData.type);
    return (
      <div className="flex align-items-center gap-2">
        <i className={option?.icon} />
        <span>{option?.label}</span>
      </div>
    );
  };

  const tagsTemplate = (rowData: Submission) => (
    <div className="flex flex-wrap gap-1">
      {rowData.tags.slice(0, 2).map(tag => (
        <Chip key={tag} label={tag} className="text-xs" />
      ))}
      {rowData.tags.length > 2 && (
        <Chip label={`+${rowData.tags.length - 2} more`} className="text-xs p-chip-outlined" />
      )}
    </div>
  );

  const progressTemplate = (rowData: Submission) => {
    if (rowData.status === SubmissionStatus.PENDING) {
      return <span className="text-color-secondary">Waiting to start</span>;
    }
    
    if (rowData.status === SubmissionStatus.FAILED) {
      return <span className="text-red-500">Failed</span>;
    }
    
    if (rowData.status === SubmissionStatus.CANCELLED) {
      return <span className="text-color-secondary">Cancelled</span>;
    }
    
    return (
      <div>
        <div className="flex justify-content-between align-items-center mb-1">
          <span className="text-sm">{rowData.progressPercentage}%</span>
          {rowData.totalUrls > 0 && (
            <span className="text-xs text-color-secondary">
              {rowData.processedUrls}/{rowData.totalUrls}
            </span>
          )}
        </div>
        <ProgressBar 
          value={rowData.progressPercentage} 
          style={{ height: '6px' }}
          showValue={false}
        />
        {rowData.estimatedCompletion && rowData.status === SubmissionStatus.PROCESSING && (
          <div className="text-xs text-color-secondary mt-1">
            ETA: {rowData.estimatedCompletion.toLocaleTimeString()}
          </div>
        )}
      </div>
    );
  };

  const actionsTemplate = (rowData: Submission) => (
    <div className="flex gap-1">
      <Button 
        icon="pi pi-eye" 
        size="small" 
        text 
        tooltip="View Details"
        onClick={() => navigate(`/protection/submissions/${rowData.id}`)}
      />
      {rowData.status === SubmissionStatus.PROCESSING && (
        <Button 
          icon="pi pi-times" 
          size="small" 
          text 
          tooltip="Cancel"
          onClick={() => cancelSubmission(rowData.id)}
        />
      )}
      {rowData.status === SubmissionStatus.FAILED && (
        <Button 
          icon="pi pi-refresh" 
          size="small" 
          text 
          tooltip="Retry"
          onClick={() => retrySubmission(rowData.id)}
        />
      )}
      {[SubmissionStatus.COMPLETED, SubmissionStatus.FAILED, SubmissionStatus.CANCELLED].includes(rowData.status) && (
        <Button 
          icon="pi pi-trash" 
          size="small" 
          text 
          tooltip="Delete"
          onClick={() => deleteSubmission(rowData.id)}
        />
      )}
    </div>
  );

  const timestampTemplate = (rowData: Submission) => (
    <div className="text-sm">
      <div>{rowData.createdAt.toLocaleDateString()}</div>
      <div className="text-color-secondary text-xs">{rowData.createdAt.toLocaleTimeString()}</div>
    </div>
  );

  if (loading) {
    return (
      <div className="grid">
        <div className="col-12">
          <Skeleton width="100%" height="400px" className="mb-4" />
          <Skeleton width="100%" height="300px" />
        </div>
      </div>
    );
  }

  return (
    <div className="grid">
      <Toast ref={toast} position="top-right" />
      
      {/* Header */}
      <div className="col-12">
        <div className="flex flex-column md:flex-row md:justify-content-between md:align-items-center mb-4 gap-3">
          <div>
            <h2 className="m-0 text-900">Content Submissions</h2>
            <p className="text-600 m-0 mt-1">Submit URLs and content for monitoring and protection</p>
          </div>
          <div className="flex gap-2 align-items-center">
            <Button 
              label="View All Profiles" 
              icon="pi pi-user" 
              outlined 
              size="small"
              onClick={() => navigate('/protection/profiles')}
            />
            <Button 
              label="View Reports" 
              icon="pi pi-chart-bar" 
              outlined 
              size="small"
              onClick={() => navigate('/reports')}
            />
          </div>
        </div>
      </div>

      {/* Submission Form */}
      <div className="col-12 lg:col-8">
        <Card title="Submit Content for Monitoring" className="mb-4">
          <div className="grid formgrid p-fluid">
            {/* Basic Information */}
            <div className="col-12">
              <div className="field">
                <label htmlFor="title" className="block text-900 font-medium mb-2">
                  Submission Title *
                </label>
                <InputText
                  id="title"
                  value={form.title}
                  onChange={(e) => handleInputChange('title', e.target.value)}
                  placeholder="Enter a descriptive title for this submission"
                  className={validationErrors.title ? 'p-invalid' : ''}
                />
                {validationErrors.title && (
                  <small className="p-error">{validationErrors.title}</small>
                )}
              </div>
            </div>

            <div className="col-12 md:col-6">
              <div className="field">
                <label htmlFor="type" className="block text-900 font-medium mb-2">
                  Content Type
                </label>
                <Dropdown
                  id="type"
                  value={form.type}
                  onChange={(e: DropdownChangeEvent) => handleInputChange('type', e.value)}
                  options={contentTypeOptions}
                  optionLabel="label"
                  optionValue="value"
                  placeholder="Select content type"
                />
              </div>
            </div>

            <div className="col-12 md:col-6">
              <div className="field">
                <label htmlFor="priority" className="block text-900 font-medium mb-2">
                  Priority Level
                </label>
                <Dropdown
                  id="priority"
                  value={form.priority}
                  onChange={(e: DropdownChangeEvent) => handleInputChange('priority', e.value)}
                  options={priorityOptions}
                  optionLabel="label"
                  optionValue="value"
                  placeholder="Select priority"
                />
              </div>
            </div>

            <div className="col-12 md:col-6">
              <div className="field">
                <label htmlFor="category" className="block text-900 font-medium mb-2">
                  Category
                </label>
                <Dropdown
                  id="category"
                  value={form.category}
                  onChange={(e: DropdownChangeEvent) => handleInputChange('category', e.value)}
                  options={categoryOptions}
                  optionLabel="label"
                  optionValue="value"
                  placeholder="Select category"
                />
              </div>
            </div>

            <div className="col-12 md:col-6">
              <div className="field">
                <label htmlFor="tags" className="block text-900 font-medium mb-2">
                  Tags
                </label>
                <MultiSelect
                  id="tags"
                  value={form.tags}
                  onChange={(e: MultiSelectChangeEvent) => handleInputChange('tags', e.value)}
                  options={commonTags}
                  optionLabel="label"
                  optionValue="value"
                  placeholder="Select relevant tags"
                  display="chip"
                  maxSelectedLabels={3}
                />
              </div>
            </div>

            {/* Content Submission Tabs */}
            <div className="col-12">
              <Divider />
              <TabView activeIndex={activeTab} onTabChange={(e) => setActiveTab(e.index)}>
                {/* Single URL Tab */}
                <TabPanel header="Single URL" leftIcon="pi pi-link">
                  <div className="field">
                    <label htmlFor="singleUrl" className="block text-900 font-medium mb-2">
                      URL to Monitor *
                    </label>
                    <div className="p-inputgroup">
                      <span className="p-inputgroup-addon">
                        <i className="pi pi-link" />
                      </span>
                      <InputText
                        id="singleUrl"
                        value={form.singleUrl}
                        onChange={(e) => handleInputChange('singleUrl', e.target.value)}
                        placeholder="https://example.com/content-to-protect"
                        className={validationErrors.singleUrl ? 'p-invalid' : ''}
                      />
                      <Button
                        icon="pi pi-eye"
                        tooltip="Preview URL"
                        disabled={!form.singleUrl || !validateUrl(form.singleUrl)}
                        onClick={() => window.open(form.singleUrl, '_blank')}
                      />
                    </div>
                    {validationErrors.singleUrl && (
                      <small className="p-error">{validationErrors.singleUrl}</small>
                    )}
                    <small className="text-color-secondary">
                      Enter the URL of content you want to monitor for unauthorized use
                    </small>
                  </div>
                </TabPanel>

                {/* Bulk URLs Tab */}
                <TabPanel header="Bulk URLs" leftIcon="pi pi-list">
                  <div className="field">
                    <label htmlFor="bulkUrls" className="block text-900 font-medium mb-2">
                      URLs to Monitor * <small className="text-color-secondary">(one per line)</small>
                    </label>
                    <InputTextarea
                      id="bulkUrls"
                      value={form.bulkUrls}
                      onChange={(e) => handleInputChange('bulkUrls', e.target.value)}
                      rows={8}
                      placeholder={`https://example.com/image1.jpg\nhttps://example.com/video1.mp4\nhttps://social-media.com/profile\n...`}
                      className={validationErrors.bulkUrls ? 'p-invalid' : ''}
                    />
                    {validationErrors.bulkUrls && (
                      <small className="p-error">{validationErrors.bulkUrls}</small>
                    )}
                    <div className="flex justify-content-between align-items-center mt-2">
                      <small className="text-color-secondary">
                        Enter multiple URLs separated by new lines. CSV upload also supported.
                      </small>
                      {form.bulkUrls && (
                        <Badge 
                          value={`${form.bulkUrls.split('\n').filter(url => url.trim()).length} URLs`} 
                          severity="info" 
                        />
                      )}
                    </div>
                  </div>

                  <div className="field">
                    <Button
                      label="Upload CSV File"
                      icon="pi pi-upload"
                      outlined
                      size="small"
                      onClick={() => {
                        const input = document.createElement('input');
                        input.type = 'file';
                        input.accept = '.csv';
                        input.onchange = (e) => {
                          const file = (e.target as HTMLInputElement).files?.[0];
                          if (file) {
                            const reader = new FileReader();
                            reader.onload = (event) => {
                              const csv = event.target?.result as string;
                              const lines = csv.split('\n').map(line => line.trim()).filter(line => line);
                              handleInputChange('bulkUrls', lines.join('\n'));
                              showToast('success', 'CSV Imported', `${lines.length} URLs imported`);
                            };
                            reader.readAsText(file);
                          }
                        };
                        input.click();
                      }}
                    />
                  </div>
                </TabPanel>

                {/* File Upload Tab */}
                <TabPanel header="File Upload" leftIcon="pi pi-upload">
                  <div className="field">
                    <label className="block text-900 font-medium mb-2">
                      Upload Content Files * <small className="text-color-secondary">(Images, Videos, Documents)</small>
                    </label>
                    <FileUpload
                      ref={fileUploadRef}
                      mode="advanced"
                      multiple
                      accept="image/*,video/*,.pdf,.doc,.docx"
                      maxFileSize={50000000} // 50MB
                      onUpload={handleFileUpload}
                      auto={false}
                      customUpload
                      chooseLabel="Select Files"
                      uploadLabel="Add to Submission"
                      cancelLabel="Clear"
                      emptyTemplate={
                        <div className="text-center p-4">
                          <div className="text-6xl text-color-secondary mb-3">
                            <i className="pi pi-cloud-upload" />
                          </div>
                          <p className="m-0 text-color-secondary">
                            Drag and drop files here or click to browse
                          </p>
                          <p className="text-xs text-color-secondary mt-2">
                            Supported: Images (JPG, PNG, GIF), Videos (MP4, AVI, MOV), Documents (PDF, DOC, DOCX)
                          </p>
                        </div>
                      }
                      className={validationErrors.files ? 'p-invalid' : ''}
                    />
                    {validationErrors.files && (
                      <small className="p-error">{validationErrors.files}</small>
                    )}
                  </div>

                  {/* Selected Files Display */}
                  {form.files.length > 0 && (
                    <div className="field">
                      <label className="block text-900 font-medium mb-2">
                        Selected Files ({form.files.length})
                      </label>
                      <div className="border-1 border-300 border-round p-3">
                        {form.files.map((file, index) => (
                          <div key={index} className="flex justify-content-between align-items-center mb-2 last:mb-0">
                            <div className="flex align-items-center gap-2">
                              <i className="pi pi-file" />
                              <span className="font-medium">{file.name}</span>
                              <Badge 
                                value={`${(file.size / 1024 / 1024).toFixed(1)} MB`} 
                                severity="info"
                              />
                            </div>
                            <Button
                              icon="pi pi-times"
                              size="small"
                              text
                              severity="danger"
                              tooltip="Remove file"
                              onClick={() => removeFile(index)}
                            />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </TabPanel>
              </TabView>
            </div>

            {/* Additional Options */}
            <div className="col-12">
              <Divider />
              <div className="field">
                <label htmlFor="description" className="block text-900 font-medium mb-2">
                  Description
                </label>
                <InputTextarea
                  id="description"
                  value={form.description}
                  onChange={(e) => handleInputChange('description', e.target.value)}
                  rows={3}
                  placeholder="Describe the content and why it needs protection (optional)"
                />
              </div>
            </div>

            <div className="col-12 md:col-6">
              <div className="field-checkbox">
                <InputSwitch
                  id="autoMonitoring"
                  checked={form.autoMonitoring}
                  onChange={(e) => handleInputChange('autoMonitoring', e.value)}
                />
                <label htmlFor="autoMonitoring" className="ml-2">
                  Enable automatic monitoring
                </label>
                <small className="text-color-secondary block mt-1">
                  Continuously scan for this content across platforms
                </small>
              </div>
            </div>

            <div className="col-12 md:col-6">
              <div className="field-checkbox">
                <InputSwitch
                  id="notifyOnInfringement"
                  checked={form.notifyOnInfringement}
                  onChange={(e) => handleInputChange('notifyOnInfringement', e.value)}
                />
                <label htmlFor="notifyOnInfringement" className="ml-2">
                  Notify on infringement detection
                </label>
                <small className="text-color-secondary block mt-1">
                  Get email alerts when potential infringements are found
                </small>
              </div>
            </div>

            {/* Submit Button */}
            <div className="col-12">
              <Divider />
              <div className="flex justify-content-end gap-2">
                <Button
                  label="Clear Form"
                  icon="pi pi-times"
                  outlined
                  onClick={() => {
                    setForm({
                      title: '',
                      type: ContentType.URLS,
                      priority: PriorityLevel.NORMAL,
                      singleUrl: '',
                      bulkUrls: '',
                      tags: [],
                      category: '',
                      description: '',
                      autoMonitoring: true,
                      notifyOnInfringement: true,
                      files: []
                    });
                    setValidationErrors({});
                    setActiveTab(0);
                  }}
                />
                <Button
                  label="Submit for Monitoring"
                  icon="pi pi-check"
                  loading={uploading}
                  onClick={handleSubmit}
                />
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Quick Actions Sidebar */}
      <div className="col-12 lg:col-4">
        <Card title="Quick Actions" className="mb-4">
          <div className="flex flex-column gap-3">
            <Button
              label="Monitor Social Profile"
              icon="pi pi-user-plus"
              outlined
              className="justify-content-start"
              onClick={() => {
                setForm(prev => ({
                  ...prev,
                  title: 'Social Media Profile Protection',
                  type: ContentType.URLS,
                  category: 'social',
                  tags: ['impersonation', 'social'],
                  priority: PriorityLevel.HIGH
                }));
                setActiveTab(0);
              }}
            />
            <Button
              label="Protect Image Portfolio"
              icon="pi pi-image"
              outlined
              className="justify-content-start"
              onClick={() => {
                setForm(prev => ({
                  ...prev,
                  title: 'Photography Portfolio Protection',
                  type: ContentType.IMAGES,
                  category: 'photography',
                  tags: ['copyright', 'photography'],
                  priority: PriorityLevel.NORMAL
                }));
                setActiveTab(2);
              }}
            />
            <Button
              label="E-commerce Product Monitor"
              icon="pi pi-shopping-cart"
              outlined
              className="justify-content-start"
              onClick={() => {
                setForm(prev => ({
                  ...prev,
                  title: 'E-commerce Product Protection',
                  type: ContentType.URLS,
                  category: 'ecommerce',
                  tags: ['piracy', 'ecommerce'],
                  priority: PriorityLevel.NORMAL
                }));
                setActiveTab(1);
              }}
            />
            <Divider />
            <div className="text-center">
              <div className="text-500 text-sm mb-2">Need help?</div>
              <Button
                label="View Guide"
                icon="pi pi-question-circle"
                link
                size="small"
                onClick={() => navigate('/help/submissions')}
              />
            </div>
          </div>
        </Card>

        {/* Usage Stats */}
        <Card title="Submission Stats" className="mb-4">
          <div className="grid">
            <div className="col-6">
              <div className="text-center">
                <div className="text-2xl font-bold text-900">{submissions.length}</div>
                <div className="text-sm text-color-secondary">Total</div>
              </div>
            </div>
            <div className="col-6">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {submissions.filter(s => s.status === SubmissionStatus.ACTIVE || s.status === SubmissionStatus.PROCESSING).length}
                </div>
                <div className="text-sm text-color-secondary">Active</div>
              </div>
            </div>
            <div className="col-6">
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {submissions.filter(s => s.status === SubmissionStatus.COMPLETED).length}
                </div>
                <div className="text-sm text-color-secondary">Completed</div>
              </div>
            </div>
            <div className="col-6">
              <div className="text-center">
                <div className="text-2xl font-bold text-red-600">
                  {submissions.filter(s => s.status === SubmissionStatus.FAILED).length}
                </div>
                <div className="text-sm text-color-secondary">Failed</div>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Submissions History */}
      <div className="col-12">
        <Panel
          header="Submission History"
          toggleable
          className="mt-4"
          headerTemplate={(options) => (
            <div className="flex justify-content-between align-items-center w-full">
              <span className="font-bold text-lg">{options.titleElement}</span>
              <div className="flex gap-2">
                <Button
                  label="Refresh"
                  icon="pi pi-refresh"
                  link
                  size="small"
                  onClick={() => window.location.reload()}
                />
                {options.togglerElement}
              </div>
            </div>
          )}
        >
          <DataTable
            value={submissions}
            paginator
            rows={10}
            rowsPerPageOptions={[5, 10, 25]}
            size="small"
            showGridlines
            emptyMessage="No submissions found"
            sortField="createdAt"
            sortOrder={-1}
          >
            <Column
              field="title"
              header="Title"
              style={{ width: '20%' }}
              sortable
              body={(rowData) => (
                <div>
                  <div className="font-medium">{rowData.title}</div>
                  {rowData.description && (
                    <div className="text-sm text-color-secondary text-overflow-ellipsis">
                      {rowData.description.length > 50 
                        ? `${rowData.description.substring(0, 50)}...` 
                        : rowData.description}
                    </div>
                  )}
                </div>
              )}
            />
            <Column
              field="type"
              header="Type"
              body={typeTemplate}
              style={{ width: '10%' }}
            />
            <Column
              field="priority"
              header="Priority"
              body={priorityTemplate}
              style={{ width: '10%' }}
              sortable
            />
            <Column
              field="status"
              header="Status"
              body={statusTemplate}
              style={{ width: '15%' }}
              sortable
            />
            <Column
              header="Progress"
              body={progressTemplate}
              style={{ width: '15%' }}
            />
            <Column
              field="tags"
              header="Tags"
              body={tagsTemplate}
              style={{ width: '15%' }}
            />
            <Column
              field="createdAt"
              header="Created"
              body={timestampTemplate}
              style={{ width: '10%' }}
              sortable
            />
            <Column
              body={actionsTemplate}
              style={{ width: '5%' }}
            />
          </DataTable>
        </Panel>
      </div>

      {/* Help Messages */}
      {submissions.length === 0 && !loading && (
        <div className="col-12">
          <Message
            severity="info"
            text="No submissions yet. Use the form above to submit your first content for monitoring and protection."
          />
        </div>
      )}
    </div>
  );
};

export default Submissions;