import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { useDropzone } from 'react-dropzone';
import { Card } from 'primereact/card';
import { TabView, TabPanel } from 'primereact/tabview';
import { Button } from 'primereact/button';
import { InputText } from 'primereact/inputtext';
import { InputTextarea } from 'primereact/inputtextarea';
import { Dropdown } from 'primereact/dropdown';
import { FileUpload } from 'primereact/fileupload';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Tag } from 'primereact/tag';
import { Badge } from 'primereact/badge';
import { ProgressBar } from 'primereact/progressbar';
import { Toast } from 'primereact/toast';
import { Message } from 'primereact/message';
import { Panel } from 'primereact/panel';
import { Divider } from 'primereact/divider';
import { InputSwitch } from 'primereact/inputswitch';
import { Chips } from 'primereact/chips';
import { ConfirmDialog, confirmDialog } from 'primereact/confirmdialog';
import { Dialog } from 'primereact/dialog';

import { submissionApi, profileApi } from '../services/api';
import { 
  Submission, 
  CreateSubmission, 
  BulkSubmission,
  ContentType, 
  PriorityLevel, 
  SubmissionStatus,
  UrlValidationResult,
  ProtectedProfile
} from '../types/api';

// Form validation schema with proper typing
const submissionSchema = yup.object({
  title: yup.string().required('Title is required').min(3, 'Title must be at least 3 characters'),
  type: yup.string().oneOf(Object.values(ContentType), 'Invalid content type').required('Content type is required'),
  priority: yup.string().oneOf(Object.values(PriorityLevel), 'Invalid priority level').required('Priority level is required'),
  description: yup.string().optional(),
  category: yup.string().optional(),
  tags: yup.array().of(yup.string()).optional(),
  urls: yup.array().of(yup.string().url('Invalid URL format')).when('type', {
    is: ContentType.URLS,
    then: (schema) => schema.min(1, 'At least one URL is required for URL submissions').required(),
    otherwise: (schema) => schema.optional()
  }),
  profile_id: yup.number().positive('Invalid profile ID').optional(),
  auto_monitoring: yup.boolean().optional(),
  notify_on_infringement: yup.boolean().optional(),
});

interface SubmissionFormData {
  title: string;
  type: ContentType;
  priority: PriorityLevel;
  description?: string;
  category?: string;
  tags?: string[];
  urls?: string[];
  profile_id?: number;
  auto_monitoring?: boolean;
  notify_on_infringement?: boolean;
}

const Submissions: React.FC = () => {
  const toast = useRef<Toast>(null);
  const fileUploadRef = useRef<FileUpload>(null);
  
  // State management
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(false);
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [profiles, setProfiles] = useState<ProtectedProfile[]>([]);
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [bulkUrls, setBulkUrls] = useState('');
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [validationResults, setValidationResults] = useState<UrlValidationResult[]>([]);
  const [uploadProgress, setUploadProgress] = useState<{ [key: string]: number }>({});
  const [showProgressDialog, setShowProgressDialog] = useState(false);
  const [currentSubmission, setCurrentSubmission] = useState<Submission | null>(null);

  // Form setup with proper typing
  const { control, handleSubmit, reset, watch, setValue, formState: { errors, isValid } } = useForm<SubmissionFormData>({
    resolver: yupResolver(submissionSchema),
    defaultValues: {
      title: '',
      type: ContentType.IMAGES,
      priority: PriorityLevel.NORMAL,
      description: '',
      category: '',
      tags: [],
      urls: [],
      auto_monitoring: true,
      notify_on_infringement: true,
    },
    mode: 'onChange'
  });

  const watchedType: ContentType = watch('type');

  // Dropzone configuration
  const onDrop = useCallback((acceptedFiles: File[]) => {
    setUploadedFiles(prev => [...prev, ...acceptedFiles]);
    showToast('success', 'Files Added', `${acceptedFiles.length} files added successfully`);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'],
      'video/*': ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv'],
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx']
    },
    multiple: true,
    maxSize: 100 * 1024 * 1024, // 100MB
  });

  // Options for dropdowns
  const contentTypeOptions = [
    { label: 'Images', value: ContentType.IMAGES, icon: 'pi-image' },
    { label: 'Videos', value: ContentType.VIDEOS, icon: 'pi-video' },
    { label: 'Documents', value: ContentType.DOCUMENTS, icon: 'pi-file' },
    { label: 'URLs', value: ContentType.URLS, icon: 'pi-link' }
  ];

  const priorityOptions = [
    { label: 'Normal', value: PriorityLevel.NORMAL, icon: 'pi-circle', severity: 'secondary' },
    { label: 'High', value: PriorityLevel.HIGH, icon: 'pi-exclamation-triangle', severity: 'warning' },
    { label: 'Urgent', value: PriorityLevel.URGENT, icon: 'pi-exclamation-circle', severity: 'danger' }
  ];

  const categoryOptions = [
    { label: 'Photography', value: 'photography' },
    { label: 'Artwork', value: 'artwork' },
    { label: 'Music', value: 'music' },
    { label: 'Video Content', value: 'video_content' },
    { label: 'Written Content', value: 'written_content' },
    { label: 'Brand Assets', value: 'brand_assets' },
    { label: 'Software', value: 'software' },
    { label: 'Other', value: 'other' }
  ];

  // Utility functions
  const showToast = (severity: 'success' | 'info' | 'warn' | 'error', summary: string, detail: string) => {
    toast.current?.show({ severity, summary, detail, life: 5000 });
  };

  const getStatusSeverity = (status: SubmissionStatus): "success" | "secondary" | "info" | "warning" | "danger" => {
    switch (status) {
      case SubmissionStatus.COMPLETED: return 'success';
      case SubmissionStatus.ACTIVE: return 'info';
      case SubmissionStatus.PROCESSING: return 'warning';
      case SubmissionStatus.FAILED: return 'danger';
      case SubmissionStatus.CANCELLED: return 'secondary';
      default: return 'secondary';
    }
  };

  // Data fetching
  const fetchSubmissions = async () => {
    try {
      setLoading(true);
      const response = await submissionApi.getSubmissions();
      setSubmissions(response.data.items || response.data);
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch submissions';
      showToast('error', 'Error', errorMessage);
      console.error('Error fetching submissions:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchProfiles = async () => {
    try {
      const response = await profileApi.getProfiles();
      setProfiles(response.data.items || response.data);
    } catch (error: unknown) {
      console.error('Error fetching profiles:', error);
    }
  };

  // Form submission handlers
  const handleFileSubmission = async (data: SubmissionFormData) => {
    if (uploadedFiles.length === 0) {
      showToast('warn', 'Warning', 'Please select files to upload');
      return;
    }

    try {
      setLoading(true);
      setShowProgressDialog(true);
      
      // Upload files first
      const uploadResponse = await submissionApi.uploadFiles(uploadedFiles);
      const fileUrls = uploadResponse.data.file_urls || [];

      // Create submission
      const submissionData: CreateSubmission = {
        ...data,
        urls: fileUrls,
      };

      const response = await submissionApi.createSubmission(submissionData);
      setCurrentSubmission(response.data);
      
      showToast('success', 'Success', 'Files submitted successfully');
      setUploadedFiles([]);
      reset();
      fetchSubmissions();
    } catch (error: unknown) {
      const errorMessage = (error as any)?.response?.data?.detail || 'Failed to submit files';
      showToast('error', 'Error', errorMessage);
      console.error('Error submitting files:', error);
    } finally {
      setLoading(false);
      setShowProgressDialog(false);
    }
  };

  const handleUrlSubmission = async (data: SubmissionFormData) => {
    if (!bulkUrls.trim()) {
      showToast('warn', 'Warning', 'Please enter URLs to submit');
      return;
    }

    const urls = bulkUrls.split('\n').filter(url => url.trim());
    
    if (urls.length === 0) {
      showToast('warn', 'Warning', 'Please enter valid URLs');
      return;
    }

    try {
      setLoading(true);
      
      // Validate URLs first
      const validationResponse = await submissionApi.validateUrls(urls);
      const validUrls = validationResponse.data.filter((result: UrlValidationResult) => result.is_valid);
      
      if (validUrls.length === 0) {
        showToast('warn', 'Warning', 'No valid URLs found');
        return;
      }

      // Create submission
      const submissionData: CreateSubmission = {
        ...data,
        urls: validUrls.map((result: UrlValidationResult) => result.url),
      };

      const response = await submissionApi.createSubmission(submissionData);
      
      showToast('success', 'Success', `${validUrls.length} URLs submitted successfully`);
      setBulkUrls('');
      setValidationResults([]);
      reset();
      fetchSubmissions();
    } catch (error: unknown) {
      const errorMessage = (error as any)?.response?.data?.detail || 'Failed to submit URLs';
      showToast('error', 'Error', errorMessage);
      console.error('Error submitting URLs:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleBatchSubmission = async (data: SubmissionFormData) => {
    if (!csvFile) {
      showToast('warn', 'Warning', 'Please select a CSV file');
      return;
    }

    try {
      setLoading(true);
      
      // Parse CSV file (simplified - in production would use a proper CSV parser)
      const csvText = await csvFile.text();
      const lines = csvText.split('\n').filter(line => line.trim());
      const headers = lines[0].split(',');
      
      const submissions: CreateSubmission[] = lines.slice(1).map(line => {
        const values = line.split(',');
        return {
          title: values[0] || data.title,
          type: (values[1] as ContentType) || data.type,
          priority: (values[2] as PriorityLevel) || data.priority,
          urls: [values[3]].filter(Boolean),
          description: values[4] || data.description,
          category: values[5] || data.category,
          auto_monitoring: data.auto_monitoring,
          notify_on_infringement: data.notify_on_infringement,
        };
      });

      const bulkData: BulkSubmission = {
        submissions,
        apply_to_all: {
          category: data.category,
          tags: data.tags,
          priority: data.priority,
          auto_monitoring: data.auto_monitoring,
          notify_on_infringement: data.notify_on_infringement,
        }
      };

      const response = await submissionApi.bulkCreate(bulkData);
      
      showToast('success', 'Success', `${submissions.length} submissions created successfully`);
      setCsvFile(null);
      reset();
      fetchSubmissions();
    } catch (error: unknown) {
      const errorMessage = (error as any)?.response?.data?.detail || 'Failed to process batch submission';
      showToast('error', 'Error', errorMessage);
      console.error('Error processing batch:', error);
    } finally {
      setLoading(false);
    }
  };

  const onSubmit = (data: SubmissionFormData) => {
    switch (activeTab) {
      case 0: // File Upload
        handleFileSubmission(data);
        break;
      case 1: // URL Submission
        handleUrlSubmission(data);
        break;
      case 2: // Batch Import
        handleBatchSubmission(data);
        break;
    }
  };

  const validateUrls = async () => {
    if (!bulkUrls.trim()) return;
    
    const urls = bulkUrls.split('\n').filter(url => url.trim());
    
    try {
      setLoading(true);
      const response = await submissionApi.validateUrls(urls);
      setValidationResults(response.data);
      
      const validCount = response.data.filter((result: UrlValidationResult) => result.is_valid).length;
      showToast('info', 'Validation Complete', `${validCount} of ${urls.length} URLs are valid`);
    } catch (error: unknown) {
      showToast('error', 'Error', 'Failed to validate URLs');
    } finally {
      setLoading(false);
    }
  };

  const removeFile = (index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const retrySubmission = async (id: string) => {
    try {
      await submissionApi.retrySubmission(id);
      showToast('success', 'Success', 'Submission retry initiated');
      fetchSubmissions();
    } catch (error: unknown) {
      showToast('error', 'Error', 'Failed to retry submission');
    }
  };

  const cancelSubmission = async (id: string) => {
    confirmDialog({
      message: 'Are you sure you want to cancel this submission?',
      header: 'Confirm Cancellation',
      icon: 'pi pi-exclamation-triangle',
      acceptClassName: 'p-button-danger',
      accept: async () => {
        try {
          await submissionApi.cancelSubmission(id);
          showToast('success', 'Success', 'Submission cancelled');
          fetchSubmissions();
        } catch (error: unknown) {
          showToast('error', 'Error', 'Failed to cancel submission');
        }
      }
    });
  };

  // Effects
  useEffect(() => {
    fetchSubmissions();
    fetchProfiles();
  }, []);

  // Column templates for DataTable
  const statusBodyTemplate = (submission: Submission) => (
    <Tag 
      value={submission.status} 
      severity={getStatusSeverity(submission.status)}
      icon={submission.status === SubmissionStatus.PROCESSING ? 'pi pi-spin pi-spinner' : undefined}
    />
  );

  const progressBodyTemplate = (submission: Submission) => (
    <div className="flex align-items-center gap-2">
      <ProgressBar 
        value={submission.progress_percentage} 
        className="w-full"
        style={{ height: '0.5rem' }}
      />
      <span className="text-sm font-medium">{submission.progress_percentage}%</span>
    </div>
  );

  const actionsBodyTemplate = (submission: Submission) => (
    <div className="flex gap-2">
      {submission.status === SubmissionStatus.FAILED && (
        <Button
          icon="pi pi-refresh"
          size="small"
          severity="warning"
          tooltip="Retry submission"
          onClick={() => retrySubmission(submission.id)}
        />
      )}
      {[SubmissionStatus.PENDING, SubmissionStatus.PROCESSING].includes(submission.status) && (
        <Button
          icon="pi pi-times"
          size="small"
          severity="danger"
          tooltip="Cancel submission"
          onClick={() => cancelSubmission(submission.id)}
        />
      )}
    </div>
  );

  const typeBodyTemplate = (submission: Submission) => {
    const typeOption = contentTypeOptions.find(opt => opt.value === submission.type);
    return (
      <div className="flex align-items-center gap-2">
        <i className={`${typeOption?.icon} text-primary`}></i>
        <span>{typeOption?.label}</span>
      </div>
    );
  };

  return (
    <>
      <Toast ref={toast} />
      <ConfirmDialog />

      <div className="surface-ground px-4 py-8 md:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-column md:flex-row md:align-items-center md:justify-content-between mb-6">
            <div>
              <h1 className="text-4xl font-bold text-900 m-0">Content Submissions</h1>
              <p className="text-700 text-lg mt-2 mb-0">
                Upload and submit content for protection monitoring
              </p>
            </div>
            <Button 
              label="View History" 
              icon="pi pi-history" 
              outlined 
              onClick={() => setActiveTab(3)}
            />
          </div>

          <TabView activeIndex={activeTab} onTabChange={(e) => setActiveTab(e.index)}>
            {/* File Upload Tab */}
            <TabPanel header="File Upload" leftIcon="pi pi-cloud-upload mr-2">
              <div className="grid">
                <div className="col-12 lg:col-8">
                  <Card title="Upload Files" className="mb-4">
                    <div className="mb-4">
                      <div 
                        {...getRootProps()} 
                        className={`border-2 border-dashed border-300 border-round p-6 text-center cursor-pointer transition-colors ${
                          isDragActive ? 'border-primary-500 surface-100' : 'hover:border-400'
                        }`}
                      >
                        <input {...getInputProps()} />
                        <i className="pi pi-cloud-upload text-6xl text-400 mb-3 block"></i>
                        <p className="text-700 text-xl mb-2">
                          {isDragActive ? 'Drop files here' : 'Drag & drop files here'}
                        </p>
                        <p className="text-600 mb-3">or click to browse</p>
                        <p className="text-500 text-sm m-0">
                          Supported: Images, Videos, Documents (Max: 100MB each)
                        </p>
                      </div>
                    </div>

                    {uploadedFiles.length > 0 && (
                      <div className="mb-4">
                        <h4 className="text-lg font-semibold mb-3">Selected Files ({uploadedFiles.length})</h4>
                        <div className="max-h-20rem overflow-y-auto">
                          {uploadedFiles.map((file, index) => (
                            <div key={index} className="flex justify-content-between align-items-center p-2 border-round hover:surface-100 mb-2">
                              <div className="flex align-items-center gap-2">
                                <i className="pi pi-file text-primary"></i>
                                <span className="font-medium">{file.name}</span>
                                <Badge value={`${(file.size / 1024 / 1024).toFixed(2)} MB`} severity="info" />
                              </div>
                              <Button
                                icon="pi pi-times"
                                size="small"
                                text
                                severity="danger"
                                onClick={() => removeFile(index)}
                              />
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </Card>
                </div>

                <div className="col-12 lg:col-4">
                  <Card title="Submission Details">
                    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-column gap-4">
                      <div className="field">
                        <label htmlFor="title" className="block text-900 font-medium mb-2">
                          Title *
                        </label>
                        <Controller
                          name="title"
                          control={control}
                          render={({ field }) => (
                            <InputText
                              {...field}
                              id="title"
                              placeholder="Enter submission title"
                              className={`w-full ${errors.title ? 'p-invalid' : ''}`}
                            />
                          )}
                        />
                        {errors.title && <small className="p-error">{errors.title.message}</small>}
                      </div>

                      <div className="field">
                        <label htmlFor="type" className="block text-900 font-medium mb-2">
                          Content Type *
                        </label>
                        <Controller
                          name="type"
                          control={control}
                          render={({ field }) => (
                            <Dropdown
                              {...field}
                              id="type"
                              options={contentTypeOptions}
                              placeholder="Select content type"
                              className="w-full"
                              itemTemplate={(option) => (
                                <div className="flex align-items-center gap-2">
                                  <i className={option.icon}></i>
                                  <span>{option.label}</span>
                                </div>
                              )}
                            />
                          )}
                        />
                      </div>

                      <div className="field">
                        <label htmlFor="priority" className="block text-900 font-medium mb-2">
                          Priority *
                        </label>
                        <Controller
                          name="priority"
                          control={control}
                          render={({ field }) => (
                            <Dropdown
                              {...field}
                              id="priority"
                              options={priorityOptions}
                              placeholder="Select priority"
                              className="w-full"
                              itemTemplate={(option) => (
                                <div className="flex align-items-center gap-2">
                                  <i className={option.icon}></i>
                                  <span>{option.label}</span>
                                </div>
                              )}
                            />
                          )}
                        />
                      </div>

                      <div className="field">
                        <label htmlFor="category" className="block text-900 font-medium mb-2">
                          Category
                        </label>
                        <Controller
                          name="category"
                          control={control}
                          render={({ field }) => (
                            <Dropdown
                              {...field}
                              id="category"
                              options={categoryOptions}
                              placeholder="Select category"
                              className="w-full"
                              emptyMessage="No categories found"
                            />
                          )}
                        />
                      </div>

                      <div className="field">
                        <label htmlFor="tags" className="block text-900 font-medium mb-2">
                          Tags
                        </label>
                        <Controller
                          name="tags"
                          control={control}
                          render={({ field }) => (
                            <Chips
                              {...field}
                              id="tags"
                              placeholder="Add tags"
                              className="w-full"
                              separator=","
                            />
                          )}
                        />
                      </div>

                      <div className="field">
                        <label htmlFor="description" className="block text-900 font-medium mb-2">
                          Description
                        </label>
                        <Controller
                          name="description"
                          control={control}
                          render={({ field }) => (
                            <InputTextarea
                              {...field}
                              id="description"
                              rows={3}
                              placeholder="Optional description"
                              className="w-full"
                            />
                          )}
                        />
                      </div>

                      {profiles.length > 0 && (
                        <div className="field">
                          <label htmlFor="profile_id" className="block text-900 font-medium mb-2">
                            Protected Profile
                          </label>
                          <Controller
                            name="profile_id"
                            control={control}
                            render={({ field }) => (
                              <Dropdown
                                {...field}
                                id="profile_id"
                                options={profiles.map(p => ({ label: p.name, value: p.id }))}
                                placeholder="Select profile (optional)"
                                className="w-full"
                                emptyMessage="No profiles found"
                              />
                            )}
                          />
                        </div>
                      )}

                      <Divider />

                      <div className="field flex align-items-center gap-3">
                        <Controller
                          name="auto_monitoring"
                          control={control}
                          render={({ field }) => (
                            <InputSwitch 
                              {...field} 
                              checked={field.value}
                              inputId="auto_monitoring"
                            />
                          )}
                        />
                        <label htmlFor="auto_monitoring" className="font-medium">
                          Enable auto-monitoring
                        </label>
                      </div>

                      <div className="field flex align-items-center gap-3">
                        <Controller
                          name="notify_on_infringement"
                          control={control}
                          render={({ field }) => (
                            <InputSwitch 
                              {...field} 
                              checked={field.value}
                              inputId="notify_on_infringement"
                            />
                          )}
                        />
                        <label htmlFor="notify_on_infringement" className="font-medium">
                          Notify on infringements
                        </label>
                      </div>

                      <Button
                        type="submit"
                        label="Submit Files"
                        icon="pi pi-upload"
                        loading={loading}
                        disabled={uploadedFiles.length === 0 || !isValid}
                        className="w-full"
                      />
                    </form>
                  </Card>
                </div>
              </div>
            </TabPanel>

            {/* URL Submission Tab */}
            <TabPanel header="URL Submission" leftIcon="pi pi-link mr-2">
              <div className="grid">
                <div className="col-12 lg:col-8">
                  <Card title="Bulk URL Submission" className="mb-4">
                    <div className="field mb-4">
                      <label htmlFor="bulk-urls" className="block text-900 font-medium mb-2">
                        URLs (one per line) *
                      </label>
                      <InputTextarea
                        id="bulk-urls"
                        value={bulkUrls}
                        onChange={(e) => setBulkUrls(e.target.value)}
                        rows={10}
                        placeholder="https://example.com/image1.jpg&#10;https://example.com/image2.jpg&#10;https://example.com/video1.mp4"
                        className="w-full font-mono"
                      />
                      <small className="text-500 block mt-2">
                        Enter one URL per line. Supported: Direct links to images, videos, or documents.
                      </small>
                    </div>

                    <div className="flex gap-2 mb-4">
                      <Button
                        label="Validate URLs"
                        icon="pi pi-check"
                        outlined
                        onClick={validateUrls}
                        disabled={!bulkUrls.trim() || loading}
                        loading={loading}
                      />
                    </div>

                    {validationResults.length > 0 && (
                      <div className="mb-4">
                        <h4 className="text-lg font-semibold mb-3">Validation Results</h4>
                        <div className="max-h-20rem overflow-y-auto">
                          {validationResults.map((result, index) => (
                            <div key={index} className="flex justify-content-between align-items-center p-3 border-1 border-300 border-round mb-2">
                              <div className="flex flex-column gap-1">
                                <span className="font-medium text-sm">{result.url}</span>
                                <span className="text-600 text-xs">{result.domain}</span>
                                {result.error_message && (
                                  <span className="text-red-500 text-xs">{result.error_message}</span>
                                )}
                              </div>
                              <Tag 
                                value={result.is_valid ? 'Valid' : 'Invalid'} 
                                severity={result.is_valid ? 'success' : 'danger'}
                              />
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </Card>
                </div>

                <div className="col-12 lg:col-4">
                  <Card title="URL Submission Details">
                    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-column gap-4">
                      <div className="field">
                        <label htmlFor="url-title" className="block text-900 font-medium mb-2">
                          Title *
                        </label>
                        <Controller
                          name="title"
                          control={control}
                          render={({ field }) => (
                            <InputText
                              {...field}
                              id="url-title"
                              placeholder="Enter submission title"
                              className={`w-full ${errors.title ? 'p-invalid' : ''}`}
                            />
                          )}
                        />
                        {errors.title && <small className="p-error">{errors.title.message}</small>}
                      </div>

                      <div className="field">
                        <label htmlFor="url-priority" className="block text-900 font-medium mb-2">
                          Priority *
                        </label>
                        <Controller
                          name="priority"
                          control={control}
                          render={({ field }) => (
                            <Dropdown
                              {...field}
                              id="url-priority"
                              options={priorityOptions}
                              placeholder="Select priority"
                              className="w-full"
                              itemTemplate={(option) => (
                                <div className="flex align-items-center gap-2">
                                  <i className={option.icon}></i>
                                  <span>{option.label}</span>
                                </div>
                              )}
                            />
                          )}
                        />
                      </div>

                      <div className="field">
                        <label htmlFor="url-category" className="block text-900 font-medium mb-2">
                          Category
                        </label>
                        <Controller
                          name="category"
                          control={control}
                          render={({ field }) => (
                            <Dropdown
                              {...field}
                              id="url-category"
                              options={categoryOptions}
                              placeholder="Select category"
                              className="w-full"
                            />
                          )}
                        />
                      </div>

                      <div className="field">
                        <label htmlFor="url-description" className="block text-900 font-medium mb-2">
                          Description
                        </label>
                        <Controller
                          name="description"
                          control={control}
                          render={({ field }) => (
                            <InputTextarea
                              {...field}
                              id="url-description"
                              rows={3}
                              placeholder="Optional description"
                              className="w-full"
                            />
                          )}
                        />
                      </div>

                      <Divider />

                      <div className="field flex align-items-center gap-3">
                        <Controller
                          name="auto_monitoring"
                          control={control}
                          render={({ field }) => (
                            <InputSwitch 
                              {...field} 
                              checked={field.value}
                              inputId="url_auto_monitoring"
                            />
                          )}
                        />
                        <label htmlFor="url_auto_monitoring" className="font-medium">
                          Enable auto-monitoring
                        </label>
                      </div>

                      <Button
                        type="submit"
                        label="Submit URLs"
                        icon="pi pi-send"
                        loading={loading}
                        disabled={!bulkUrls.trim() || !isValid}
                        className="w-full"
                      />
                    </form>
                  </Card>
                </div>
              </div>
            </TabPanel>

            {/* Batch Import Tab */}
            <TabPanel header="Batch Import" leftIcon="pi pi-upload mr-2">
              <div className="grid">
                <div className="col-12 lg:col-8">
                  <Card title="CSV Batch Import" className="mb-4">
                    <Message severity="info" text="Upload a CSV file with columns: title, type, priority, url, description, category" className="mb-4" />
                    
                    <div className="field mb-4">
                      <label htmlFor="csv-file" className="block text-900 font-medium mb-2">
                        CSV File *
                      </label>
                      <FileUpload
                        mode="basic"
                        accept=".csv"
                        maxFileSize={10000000} // 10MB
                        customUpload
                        uploadHandler={(e) => setCsvFile(e.files[0])}
                        chooseLabel="Choose CSV File"
                        className="w-full"
                        id="csv-file"
                      />
                      {csvFile && (
                        <div className="flex align-items-center gap-2 mt-2">
                          <i className="pi pi-file-excel text-green-500"></i>
                          <span className="font-medium">{csvFile.name}</span>
                          <Badge value={`${(csvFile.size / 1024).toFixed(2)} KB`} severity="info" />
                        </div>
                      )}
                    </div>

                    <Panel header="CSV Format Example" className="mb-4" collapsed>
                      <div className="font-mono text-sm bg-gray-50 p-3 border-round">
                        title,type,priority,url,description,category<br/>
                        "My Image 1",images,normal,"https://example.com/image1.jpg","First image",photography<br/>
                        "My Video 1",videos,high,"https://example.com/video1.mp4","Important video",video_content<br/>
                        "Document 1",documents,urgent,"https://example.com/doc1.pdf","Critical document",written_content
                      </div>
                    </Panel>
                  </Card>
                </div>

                <div className="col-12 lg:col-4">
                  <Card title="Batch Settings">
                    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-column gap-4">
                      <div className="field">
                        <label htmlFor="batch-title" className="block text-900 font-medium mb-2">
                          Batch Title *
                        </label>
                        <Controller
                          name="title"
                          control={control}
                          render={({ field }) => (
                            <InputText
                              {...field}
                              id="batch-title"
                              placeholder="Enter batch title"
                              className={`w-full ${errors.title ? 'p-invalid' : ''}`}
                            />
                          )}
                        />
                        {errors.title && <small className="p-error">{errors.title.message}</small>}
                      </div>

                      <div className="field">
                        <label htmlFor="batch-priority" className="block text-900 font-medium mb-2">
                          Default Priority *
                        </label>
                        <Controller
                          name="priority"
                          control={control}
                          render={({ field }) => (
                            <Dropdown
                              {...field}
                              id="batch-priority"
                              options={priorityOptions}
                              placeholder="Select default priority"
                              className="w-full"
                              itemTemplate={(option) => (
                                <div className="flex align-items-center gap-2">
                                  <i className={option.icon}></i>
                                  <span>{option.label}</span>
                                </div>
                              )}
                            />
                          )}
                        />
                      </div>

                      <div className="field">
                        <label htmlFor="batch-category" className="block text-900 font-medium mb-2">
                          Default Category
                        </label>
                        <Controller
                          name="category"
                          control={control}
                          render={({ field }) => (
                            <Dropdown
                              {...field}
                              id="batch-category"
                              options={categoryOptions}
                              placeholder="Select default category"
                              className="w-full"
                            />
                          )}
                        />
                      </div>

                      <Divider />

                      <div className="field flex align-items-center gap-3">
                        <Controller
                          name="auto_monitoring"
                          control={control}
                          render={({ field }) => (
                            <InputSwitch 
                              {...field} 
                              checked={field.value}
                              inputId="batch_auto_monitoring"
                            />
                          )}
                        />
                        <label htmlFor="batch_auto_monitoring" className="font-medium">
                          Enable auto-monitoring for all
                        </label>
                      </div>

                      <Button
                        type="submit"
                        label="Process Batch"
                        icon="pi pi-cog"
                        loading={loading}
                        disabled={!csvFile || !isValid}
                        className="w-full"
                      />
                    </form>
                  </Card>
                </div>
              </div>
            </TabPanel>

            {/* Submission History Tab */}
            <TabPanel header="History" leftIcon="pi pi-history mr-2">
              <Card>
                <DataTable 
                  value={submissions} 
                  loading={loading}
                  paginator 
                  rows={10}
                  rowsPerPageOptions={[5, 10, 25, 50]}
                  paginatorTemplate="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport RowsPerPageDropdown"
                  currentPageReportTemplate="Showing {first} to {last} of {totalRecords} submissions"
                  emptyMessage="No submissions found"
                  sortMode="multiple"
                  removableSort
                  className="p-datatable-gridlines"
                >
                  <Column 
                    field="title" 
                    header="Title" 
                    sortable 
                    className="font-medium"
                  />
                  <Column 
                    field="type" 
                    header="Type" 
                    body={typeBodyTemplate}
                    sortable
                  />
                  <Column 
                    field="status" 
                    header="Status" 
                    body={statusBodyTemplate}
                    sortable
                  />
                  <Column 
                    field="progress_percentage" 
                    header="Progress" 
                    body={progressBodyTemplate}
                  />
                  <Column 
                    field="total_urls" 
                    header="Items" 
                    sortable
                    body={(submission) => (
                      <Badge value={submission.total_urls} severity="info" />
                    )}
                  />
                  <Column 
                    field="created_at" 
                    header="Created" 
                    sortable
                    body={(submission) => new Date(submission.created_at).toLocaleDateString()}
                  />
                  <Column 
                    header="Actions" 
                    body={actionsBodyTemplate}
                    style={{ width: '8rem' }}
                  />
                </DataTable>
              </Card>
            </TabPanel>
          </TabView>
        </div>
      </div>

      {/* Progress Dialog */}
      <Dialog
        header="Processing Submission"
        visible={showProgressDialog}
        onHide={() => setShowProgressDialog(false)}
        closable={false}
        style={{ width: '400px' }}
        modal
      >
        <div className="flex flex-column align-items-center gap-4 py-4">
          <i className="pi pi-spin pi-spinner text-4xl text-primary"></i>
          <p className="text-center text-lg font-medium">
            Uploading and processing your files...
          </p>
          {currentSubmission && (
            <div className="w-full">
              <div className="flex justify-content-between mb-2">
                <span>Progress</span>
                <span>{currentSubmission.progress_percentage}%</span>
              </div>
              <ProgressBar value={currentSubmission.progress_percentage} />
            </div>
          )}
          <p className="text-center text-sm text-600 m-0">
            Please wait while we process your submission. This may take a few moments.
          </p>
        </div>
      </Dialog>
    </>
  );
};

export default Submissions;