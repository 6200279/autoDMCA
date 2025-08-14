import React, { useState, useEffect, useRef, useCallback } from 'react';
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
import { Toast } from 'primereact/toast';
import { confirmDialog } from 'primereact/confirmdialog';
import { Chip } from 'primereact/chip';
import { InputSwitch } from 'primereact/inputswitch';
import { Skeleton } from 'primereact/skeleton';
import { Panel } from 'primereact/panel';
import { MultiSelect, MultiSelectChangeEvent } from 'primereact/multiselect';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { submissionApi } from '../services/api';
import { 
  ContentType, 
  PriorityLevel, 
  SubmissionStatus, 
  Submission, 
  CreateSubmission,
  UrlValidationResult,
  ApiResponse,
  PaginatedResponse 
} from '../types/api';

// Local submission form interface
export interface LocalSubmission extends Omit<Submission, 'created_at' | 'updated_at' | 'completed_at' | 'estimated_completion'> {
  createdAt: Date;
  updatedAt: Date;
  completedAt?: Date;
  estimatedCompletion?: Date;
  progressPercentage: number;
  files?: File[]; // Local files before upload
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

export interface FileUploadProgress {
  [key: string]: {
    progress: number;
    status: 'uploading' | 'completed' | 'failed';
    url?: string;
    error?: string;
  };
}

const Submissions: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const toast = useRef<Toast>(null);
  const fileUploadRef = useRef<FileUpload>(null);

  // State
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState(0);
  const [submissions, setSubmissions] = useState<LocalSubmission[]>([]);
  const [uploading, setUploading] = useState(false);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});
  const [fileUploadProgress, setFileUploadProgress] = useState<FileUploadProgress>({});
  const [urlValidationLoading, setUrlValidationLoading] = useState(false);
  const [pagination, setPagination] = useState({
    page: 1,
    per_page: 10,
    total: 0,
    pages: 0
  });
  const [filters, setFilters] = useState<{
    status?: SubmissionStatus;
    type?: ContentType;
    priority?: PriorityLevel;
    search?: string;
  }>({});

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

  // Fetch submissions from API
  const fetchSubmissions = useCallback(async () => {
    try {
      setLoading(true);
      const response = await submissionApi.getSubmissions({
        page: pagination.page,
        per_page: pagination.per_page,
        ...filters
      });
      
      const apiSubmissions = response.data as PaginatedResponse<Submission>;
      
      // Convert API format to local format
      const localSubmissions: LocalSubmission[] = apiSubmissions.items.map(sub => ({
        ...sub,
        user_id: sub.user_id,
        profile_id: sub.profile_id,
        progressPercentage: sub.progress_percentage,
        autoMonitoring: sub.auto_monitoring,
        notifyOnInfringement: sub.notify_on_infringement,
        createdAt: new Date(sub.created_at),
        updatedAt: new Date(sub.updated_at),
        completedAt: sub.completed_at ? new Date(sub.completed_at) : undefined,
        estimatedCompletion: sub.estimated_completion ? new Date(sub.estimated_completion) : undefined,
        totalUrls: sub.total_urls,
        processedUrls: sub.processed_urls,
        validUrls: sub.valid_urls,
        invalidUrls: sub.invalid_urls,
        errorMessage: sub.error_message
      }));
      
      setSubmissions(localSubmissions);
      setPagination(prev => ({
        ...prev,
        total: apiSubmissions.total,
        pages: apiSubmissions.pages
      }));
    } catch (error: any) {
      console.error('Failed to fetch submissions:', error);
      showToast('error', 'Failed to Load', getApiErrorMessage(error));
    } finally {
      setLoading(false);
    }
  }, [pagination.page, pagination.per_page, filters]);

  useEffect(() => {
    if (user?.id) {
      fetchSubmissions();
    }
  }, [user?.id, fetchSubmissions]);

  // Real-time progress polling for active submissions
  useEffect(() => {
    const activeSubmissions = submissions.filter(sub => 
      sub.status === SubmissionStatus.PROCESSING || sub.status === SubmissionStatus.PENDING
    );
    
    if (activeSubmissions.length === 0) return;
    
    const pollProgress = async () => {
      try {
        const progressPromises = activeSubmissions.map(async (sub) => {
          const response = await submissionApi.getSubmissionProgress(sub.id);
          return { id: sub.id, progress: response.data };
        });
        
        const progressResults = await Promise.allSettled(progressPromises);
        
        setSubmissions(prev => prev.map(sub => {
          const result = progressResults.find((r, i) => 
            r.status === 'fulfilled' && activeSubmissions[i].id === sub.id
          );
          
          if (result && result.status === 'fulfilled') {
            const progressData = result.value.progress;
            return {
              ...sub,
              progressPercentage: progressData.progress_percentage || sub.progressPercentage,
              status: progressData.status || sub.status,
              processedUrls: progressData.processed_urls || sub.processedUrls,
              validUrls: progressData.valid_urls || sub.validUrls,
              invalidUrls: progressData.invalid_urls || sub.invalidUrls,
              errorMessage: progressData.error_message || sub.errorMessage,
              updatedAt: new Date()
            };
          }
          
          return sub;
        }));
      } catch (error) {
        console.error('Failed to poll submission progress:', error);
      }
    };
    
    const interval = setInterval(pollProgress, 5000); // Poll every 5 seconds
    return () => clearInterval(interval);
  }, [submissions]);

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

  // Backend URL validation
  const validateUrlsWithBackend = async (urls: string[]): Promise<UrlValidationResult[]> => {
    try {
      setUrlValidationLoading(true);
      const response = await submissionApi.validateUrls(urls);
      return response.data as UrlValidationResult[];
    } catch (error: any) {
      console.error('URL validation failed:', error);
      showToast('error', 'Validation Failed', 'Could not validate URLs with backend');
      return urls.map(url => ({
        url,
        is_valid: validateUrl(url),
        domain: '',
        error_message: 'Backend validation unavailable'
      }));
    } finally {
      setUrlValidationLoading(false);
    }
  };

  const validateForm = async (): Promise<boolean> => {
    const errors: Record<string, string> = {};

    if (!form.title.trim()) {
      errors.title = 'Title is required';
    }

    let urlsToValidate: string[] = [];

    if (activeTab === 0) { // Single URL tab
      if (!form.singleUrl.trim()) {
        errors.singleUrl = 'URL is required';
      } else {
        urlsToValidate = [form.singleUrl];
      }
    } else if (activeTab === 1) { // Bulk URL tab
      if (!form.bulkUrls.trim()) {
        errors.bulkUrls = 'At least one URL is required';
      } else {
        urlsToValidate = form.bulkUrls.split('\n').map(url => url.trim()).filter(url => url);
      }
    } else if (activeTab === 2) { // File upload tab
      if (form.files.length === 0) {
        errors.files = 'At least one file is required';
      }
    }

    // Validate URLs with backend if we have URLs
    if (urlsToValidate.length > 0) {
      try {
        const validationResults = await validateUrlsWithBackend(urlsToValidate);
        const invalidResults = validationResults.filter(result => !result.is_valid);
        
        if (invalidResults.length > 0) {
          const invalidUrls = invalidResults.map(result => result.url);
          const errorKey = activeTab === 0 ? 'singleUrl' : 'bulkUrls';
          errors[errorKey] = `Invalid URLs: ${invalidUrls.slice(0, 3).join(', ')}${invalidUrls.length > 3 ? ` and ${invalidUrls.length - 3} more` : ''}`;
        }
      } catch (error) {
        // If backend validation fails, fall back to client-side validation
        const invalidUrls = urlsToValidate.filter(url => !validateUrl(url));
        if (invalidUrls.length > 0) {
          const errorKey = activeTab === 0 ? 'singleUrl' : 'bulkUrls';
          errors[errorKey] = `Invalid URLs found: ${invalidUrls.slice(0, 3).join(', ')}${invalidUrls.length > 3 ? '...' : ''}`;
        }
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

  const handleFileUpload = async (event: FileUploadUploadEvent) => {
    const uploadedFiles = Array.from(event.files) as File[];
    
    // Initialize progress tracking for each file
    const newProgress: FileUploadProgress = {};
    uploadedFiles.forEach(file => {
      newProgress[file.name] = { progress: 0, status: 'uploading' };
    });
    setFileUploadProgress(prev => ({ ...prev, ...newProgress }));
    
    try {
      // Upload files to backend storage
      const response = await submissionApi.uploadFiles(uploadedFiles);
      const uploadedFileUrls = response.data.file_urls || [];
      
      // Update progress to completed
      uploadedFiles.forEach((file, index) => {
        setFileUploadProgress(prev => ({
          ...prev,
          [file.name]: {
            progress: 100,
            status: 'completed',
            url: uploadedFileUrls[index]
          }
        }));
      });
      
      setForm(prev => ({ ...prev, files: [...prev.files, ...uploadedFiles] }));
      fileUploadRef.current?.clear();
      showToast('success', 'Files Uploaded', `${uploadedFiles.length} file(s) uploaded successfully`);
    } catch (error: any) {
      console.error('File upload failed:', error);
      
      // Update progress to failed
      uploadedFiles.forEach(file => {
        setFileUploadProgress(prev => ({
          ...prev,
          [file.name]: {
            progress: 0,
            status: 'failed',
            error: error.response?.data?.message || 'Upload failed'
          }
        }));
      });
      
      showToast('error', 'Upload Failed', 'Failed to upload files. Please try again.');
    }
  };

  const removeFile = (index: number) => {
    const fileToRemove = form.files[index];
    setForm(prev => ({
      ...prev,
      files: prev.files.filter((_, i) => i !== index)
    }));
    
    // Also remove from progress tracking
    if (fileToRemove) {
      setFileUploadProgress(prev => {
        const newProgress = { ...prev };
        delete newProgress[fileToRemove.name];
        return newProgress;
      });
    }
  };

  // Bulk URL validation helper
  const validateBulkUrls = async (urlText: string): Promise<{ valid: string[], invalid: string[] }> => {
    const urls = urlText.split('\n').map(url => url.trim()).filter(url => url);
    
    try {
      const validationResults = await validateUrlsWithBackend(urls);
      const valid = validationResults.filter(r => r.is_valid).map(r => r.url);
      const invalid = validationResults.filter(r => !r.is_valid).map(r => r.url);
      return { valid, invalid };
    } catch {
      // Fallback to client-side validation
      const valid = urls.filter(url => validateUrl(url));
      const invalid = urls.filter(url => !validateUrl(url));
      return { valid, invalid };
    }
  };

  // Helper to get API error message
  const getApiErrorMessage = (error: any): string => {
    if (error.response?.data?.message) return error.response.data.message;
    if (error.response?.data?.detail) return error.response.data.detail;
    if (error.response?.data?.error) return error.response.data.error;
    if (error.message) return error.message;
    return 'An unexpected error occurred';
  };

  const handleSubmit = async () => {
    const isValid = await validateForm();
    if (!isValid) {
      showToast('error', 'Validation Failed', 'Please fix the errors before submitting');
      return;
    }

    setUploading(true);
    
    try {
      let urls: string[] = [];
      
      if (activeTab === 0) {
        urls = [form.singleUrl];
      } else if (activeTab === 1) {
        urls = form.bulkUrls.split('\n').map(url => url.trim()).filter(url => url);
      }

      // First upload files if any
      let uploadedFileUrls: string[] = [];
      if (form.files.length > 0) {
        try {
          const fileResponse = await submissionApi.uploadFiles(form.files);
          uploadedFileUrls = fileResponse.data.file_urls || [];
        } catch (uploadError: any) {
          console.error('File upload failed:', uploadError);
          showToast('error', 'File Upload Failed', getApiErrorMessage(uploadError));
          return;
        }
      }

      // Create submission data
      const submissionData: CreateSubmission = {
        title: form.title,
        type: form.type,
        priority: form.priority,
        urls: urls.length > 0 ? urls : undefined,
        tags: form.tags.length > 0 ? form.tags : undefined,
        category: form.category || undefined,
        description: form.description || undefined,
        auto_monitoring: form.autoMonitoring,
        notify_on_infringement: form.notifyOnInfringement
      };

      // Submit to API
      const response = await submissionApi.createSubmission({
        ...submissionData,
        file_urls: uploadedFileUrls.length > 0 ? uploadedFileUrls : undefined
      });
      
      const newSubmission = response.data as Submission;
      
      // Convert to local format and add to list
      const localSubmission: LocalSubmission = {
        ...newSubmission,
        user_id: newSubmission.user_id,
        progressPercentage: newSubmission.progress_percentage,
        autoMonitoring: newSubmission.auto_monitoring,
        notifyOnInfringement: newSubmission.notify_on_infringement,
        createdAt: new Date(newSubmission.created_at),
        updatedAt: new Date(newSubmission.updated_at),
        completedAt: newSubmission.completed_at ? new Date(newSubmission.completed_at) : undefined,
        estimatedCompletion: newSubmission.estimated_completion ? new Date(newSubmission.estimated_completion) : undefined,
        totalUrls: newSubmission.total_urls,
        processedUrls: newSubmission.processed_urls,
        validUrls: newSubmission.valid_urls,
        invalidUrls: newSubmission.invalid_urls,
        errorMessage: newSubmission.error_message,
        files: form.files.length > 0 ? form.files : undefined
      };

      setSubmissions(prev => [localSubmission, ...prev]);
      
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
      setFileUploadProgress({});
      showToast('success', 'Submission Created', 'Your content has been submitted for monitoring');
    } catch (error: any) {
      console.error('Submission failed:', error);
      showToast('error', 'Submission Failed', getApiErrorMessage(error));
    } finally {
      setUploading(false);
    }
  };

  const cancelSubmission = async (submissionId: string) => {
    confirmDialog({
      message: 'Are you sure you want to cancel this submission?',
      header: 'Cancel Submission',
      icon: 'pi pi-exclamation-triangle',
      accept: async () => {
        try {
          await submissionApi.cancelSubmission(submissionId);
          
          setSubmissions(prev => 
            prev.map(sub => 
              sub.id === submissionId 
                ? { ...sub, status: SubmissionStatus.CANCELLED, progressPercentage: 0, updatedAt: new Date() }
                : sub
            )
          );
          showToast('info', 'Submission Cancelled', 'The submission has been cancelled');
        } catch (error: any) {
          console.error('Failed to cancel submission:', error);
          showToast('error', 'Cancel Failed', getApiErrorMessage(error));
        }
      }
    });
  };

  const retrySubmission = async (submissionId: string) => {
    try {
      await submissionApi.retrySubmission(submissionId);
      
      setSubmissions(prev => 
        prev.map(sub => 
          sub.id === submissionId 
            ? { ...sub, status: SubmissionStatus.PENDING, progressPercentage: 0, errorMessage: undefined, updatedAt: new Date() }
            : sub
        )
      );
      showToast('info', 'Submission Retried', 'The submission has been restarted');
    } catch (error: any) {
      console.error('Failed to retry submission:', error);
      showToast('error', 'Retry Failed', getApiErrorMessage(error));
    }
  };

  const deleteSubmission = async (submissionId: string) => {
    confirmDialog({
      message: 'Are you sure you want to delete this submission? This action cannot be undone.',
      header: 'Delete Submission',
      icon: 'pi pi-exclamation-triangle',
      accept: async () => {
        try {
          await submissionApi.deleteSubmission(submissionId);
          
          setSubmissions(prev => prev.filter(sub => sub.id !== submissionId));
          setPagination(prev => ({ ...prev, total: prev.total - 1 }));
          showToast('info', 'Submission Deleted', 'The submission has been removed');
        } catch (error: any) {
          console.error('Failed to delete submission:', error);
          showToast('error', 'Delete Failed', getApiErrorMessage(error));
        }
      }
    });
  };

  // Template functions for DataTable columns
  const statusTemplate = (rowData: LocalSubmission) => {
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

  const priorityTemplate = (rowData: LocalSubmission) => {
    const option = priorityOptions.find(opt => opt.value === rowData.priority);
    return (
      <Badge 
        value={option?.label} 
        style={{ backgroundColor: option?.color }}
      />
    );
  };

  const typeTemplate = (rowData: LocalSubmission) => {
    const option = contentTypeOptions.find(opt => opt.value === rowData.type);
    return (
      <div className="flex align-items-center gap-2">
        <i className={option?.icon} />
        <span>{option?.label}</span>
      </div>
    );
  };

  const tagsTemplate = (rowData: LocalSubmission) => (
    <div className="flex flex-wrap gap-1">
      {rowData.tags.slice(0, 2).map(tag => (
        <Chip key={tag} label={tag} className="text-xs" />
      ))}
      {rowData.tags.length > 2 && (
        <Chip label={`+${rowData.tags.length - 2} more`} className="text-xs p-chip-outlined" />
      )}
    </div>
  );

  const progressTemplate = (rowData: LocalSubmission) => {
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

  const actionsTemplate = (rowData: LocalSubmission) => (
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

  const timestampTemplate = (rowData: LocalSubmission) => (
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
                      loading={urlValidationLoading}
                      onClick={() => {
                        const input = document.createElement('input');
                        input.type = 'file';
                        input.accept = '.csv,.txt';
                        input.onchange = async (e) => {
                          const file = (e.target as HTMLInputElement).files?.[0];
                          if (file) {
                            try {
                              const reader = new FileReader();
                              reader.onload = async (event) => {
                                const content = event.target?.result as string;
                                const lines = content.split('\n').map(line => line.trim()).filter(line => line);
                                
                                // Validate URLs if they look like URLs
                                if (lines.length > 0) {
                                  const { valid, invalid } = await validateBulkUrls(lines.join('\n'));
                                  handleInputChange('bulkUrls', valid.join('\n'));
                                  
                                  if (invalid.length > 0) {
                                    showToast('warn', 'Some URLs Invalid', `${valid.length} valid URLs imported, ${invalid.length} invalid URLs ignored`);
                                  } else {
                                    showToast('success', 'CSV Imported', `${valid.length} URLs imported successfully`);
                                  }
                                }
                              };
                              reader.readAsText(file);
                            } catch (error) {
                              showToast('error', 'Import Failed', 'Could not read the file. Please check the format.');
                            }
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
                        {form.files.map((file, index) => {
                          const progress = fileUploadProgress[file.name];
                          return (
                            <div key={index} className="mb-3 last:mb-0">
                              <div className="flex justify-content-between align-items-center mb-2">
                                <div className="flex align-items-center gap-2">
                                  <i className={`pi ${progress?.status === 'completed' ? 'pi-check-circle' : progress?.status === 'failed' ? 'pi-times-circle' : 'pi-file'}`} 
                                     style={{ color: progress?.status === 'completed' ? 'green' : progress?.status === 'failed' ? 'red' : undefined }} />
                                  <span className="font-medium">{file.name}</span>
                                  <Badge 
                                    value={`${(file.size / 1024 / 1024).toFixed(1)} MB`} 
                                    severity="info"
                                  />
                                  {progress?.status === 'completed' && (
                                    <Badge value="Uploaded" severity="success" />
                                  )}
                                  {progress?.status === 'failed' && (
                                    <Badge value="Failed" severity="danger" />
                                  )}
                                </div>
                                <Button
                                  icon="pi pi-times"
                                  size="small"
                                  text
                                  severity="danger"
                                  tooltip="Remove file"
                                  onClick={() => removeFile(index)}
                                  disabled={progress?.status === 'uploading'}
                                />
                              </div>
                              {progress && progress.status === 'uploading' && (
                                <ProgressBar 
                                  value={progress.progress} 
                                  style={{ height: '4px' }}
                                  showValue={false}
                                />
                              )}
                              {progress?.error && (
                                <small className="p-error block mt-1">{progress.error}</small>
                              )}
                            </div>
                          );
                        })}
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
                  loading={uploading || urlValidationLoading}
                  disabled={uploading || urlValidationLoading || Object.values(fileUploadProgress).some(p => p.status === 'uploading')}
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
                <div className="text-2xl font-bold text-900">{pagination.total}</div>
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
          
          {loading && (
            <div className="mt-3 text-center">
              <small className="text-color-secondary">Loading latest statistics...</small>
            </div>
          )}
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
                  loading={loading}
                  onClick={() => fetchSubmissions()}
                />
                {options.togglerElement}
              </div>
            </div>
          )}
        >
          <DataTable
            value={submissions}
            paginator
            lazy
            first={(pagination.page - 1) * pagination.per_page}
            rows={pagination.per_page}
            totalRecords={pagination.total}
            rowsPerPageOptions={[5, 10, 25, 50]}
            size="small"
            showGridlines
            emptyMessage={loading ? "Loading submissions..." : "No submissions found"}
            sortField="createdAt"
            sortOrder={-1}
            loading={loading}
            onPage={(e) => {
              setPagination(prev => ({ ...prev, page: Math.floor(e.first / e.rows) + 1, per_page: e.rows }));
            }}
            globalFilterFields={['title', 'description', 'tags', 'category']}
            header={
              <div className="flex justify-content-between align-items-center">
                <div className="flex gap-2 align-items-center">
                  <InputText 
                    placeholder="Search submissions..."
                    value={filters.search || ''}
                    onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value || undefined }))}
                    className="w-20rem"
                  />
                  <Dropdown
                    value={filters.status}
                    onChange={(e) => setFilters(prev => ({ ...prev, status: e.value || undefined }))}
                    options={[
                      { label: 'All Status', value: undefined },
                      { label: 'Pending', value: SubmissionStatus.PENDING },
                      { label: 'Processing', value: SubmissionStatus.PROCESSING },
                      { label: 'Active', value: SubmissionStatus.ACTIVE },
                      { label: 'Completed', value: SubmissionStatus.COMPLETED },
                      { label: 'Failed', value: SubmissionStatus.FAILED },
                      { label: 'Cancelled', value: SubmissionStatus.CANCELLED }
                    ]}
                    placeholder="Filter by status"
                    showClear
                    className="w-12rem"
                  />
                  <Dropdown
                    value={filters.type}
                    onChange={(e) => setFilters(prev => ({ ...prev, type: e.value || undefined }))}
                    options={[
                      { label: 'All Types', value: undefined },
                      ...contentTypeOptions
                    ]}
                    placeholder="Filter by type"
                    showClear
                    className="w-10rem"
                  />
                </div>
                <div className="text-sm text-color-secondary">
                  Showing {((pagination.page - 1) * pagination.per_page) + 1} to {Math.min(pagination.page * pagination.per_page, pagination.total)} of {pagination.total} submissions
                </div>
              </div>
            }
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
      
      {/* Connection Status */}
      {loading && submissions.length === 0 && (
        <div className="col-12">
          <Message
            severity="info"
            text="Connecting to backend services and loading your submissions..."
          />
        </div>
      )}
    </div>
  );
};

export default Submissions;