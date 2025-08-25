import React, { useState, useRef } from 'react';
import { Card } from 'primereact/card';
import { InputText } from 'primereact/inputtext';
import { InputTextarea } from 'primereact/inputtextarea';
import { Dropdown } from 'primereact/dropdown';
import { MultiSelect } from 'primereact/multiselect';
import { Button } from 'primereact/button';
import { FileUpload, FileUploadHandlerEvent } from 'primereact/fileupload';
import { Message } from 'primereact/message';
import { ProgressSpinner } from 'primereact/progressspinner';
import { TabView, TabPanel } from 'primereact/tabview';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { classNames } from 'primereact/utils';
import { Controller, useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { searchEngineDelistingApi } from '../../services/api';
import type { 
  BatchDelistingFormData, 
  SearchEngine, 
  DelistingPriority 
} from '../../types/delisting';

interface BatchRequestFormProps {
  onSuccess?: (batchId: string) => void;
  onError?: (error: string) => void;
}

const searchEngineOptions = [
  { label: 'Google', value: 'google' as SearchEngine },
  { label: 'Bing', value: 'bing' as SearchEngine },
  { label: 'Yahoo', value: 'yahoo' as SearchEngine },
  { label: 'Yandex', value: 'yandex' as SearchEngine }
];

const priorityOptions = [
  { label: 'Low', value: 'low' as DelistingPriority },
  { label: 'Normal', value: 'normal' as DelistingPriority },
  { label: 'High', value: 'high' as DelistingPriority },
  { label: 'Urgent', value: 'urgent' as DelistingPriority }
];

const validationSchema = yup.object({
  urls: yup
    .array()
    .of(yup.string().url('Invalid URL').required('URL is required'))
    .min(1, 'At least one URL is required')
    .max(100, 'Maximum 100 URLs allowed per batch')
    .required('URLs are required'),
  originalContentUrl: yup
    .string()
    .url('Please enter a valid URL for original content')
    .nullable(),
  reason: yup
    .string()
    .required('Reason is required')
    .min(10, 'Reason must be at least 10 characters'),
  evidenceUrl: yup
    .string()
    .url('Please enter a valid evidence URL')
    .nullable(),
  priority: yup
    .string()
    .required('Priority is required')
    .oneOf(['low', 'normal', 'high', 'urgent'], 'Invalid priority'),
  searchEngines: yup
    .array()
    .of(yup.string().oneOf(['google', 'bing', 'yahoo', 'yandex']))
    .min(1, 'Please select at least one search engine')
    .required('Search engines are required')
});

const BatchRequestForm: React.FC<BatchRequestFormProps> = ({
  onSuccess,
  onError
}) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null);
  const [activeTabIndex, setActiveTabIndex] = useState(0);
  const [parsedUrls, setParsedUrls] = useState<string[]>([]);
  const fileUploadRef = useRef<FileUpload>(null);

  const {
    control,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors }
  } = useForm<BatchDelistingFormData>({
    resolver: yupResolver(validationSchema),
    defaultValues: {
      urls: [],
      originalContentUrl: '',
      reason: 'Copyright infringement - unauthorized distribution',
      evidenceUrl: '',
      priority: 'normal',
      searchEngines: ['google', 'bing'],
      profileId: ''
    }
  });

  const urls = watch('urls');

  const onSubmit = async (data: BatchDelistingFormData) => {
    setIsSubmitting(true);
    setSubmitError(null);
    setSubmitSuccess(null);

    try {
      const response = await searchEngineDelistingApi.submitBatchDelisting({
        urls: data.urls,
        originalContentUrl: data.originalContentUrl || undefined,
        reason: data.reason,
        evidenceUrl: data.evidenceUrl || undefined,
        priority: data.priority,
        searchEngines: data.searchEngines,
        profileId: data.profileId || undefined
      });

      setSubmitSuccess(
        `Batch submitted successfully! Batch ID: ${response.data.id} (${data.urls.length} URLs)`
      );
      
      if (onSuccess) {
        onSuccess(response.data.id);
      }
      
      // Reset form after successful submission
      reset();
      setParsedUrls([]);
      if (fileUploadRef.current) {
        fileUploadRef.current.clear();
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 
                          error.message || 
                          'Failed to submit batch delisting request';
      setSubmitError(errorMessage);
      
      if (onError) {
        onError(errorMessage);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFileUpload = (event: FileUploadHandlerEvent) => {
    const file = event.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const text = e.target?.result as string;
        const lines = text.split('\n')
          .map(line => line.trim())
          .filter(line => line && line.startsWith('http'))
          .slice(0, 100); // Limit to 100 URLs
        
        setParsedUrls(lines);
        setValue('urls', lines, { shouldValidate: true });
      };
      reader.readAsText(file);
    }
  };

  const handleManualUrlsChange = (urlText: string) => {
    const lines = urlText.split('\n')
      .map(line => line.trim())
      .filter(line => line)
      .slice(0, 100); // Limit to 100 URLs
    
    setParsedUrls(lines);
    setValue('urls', lines, { shouldValidate: true });
  };

  const removeUrl = (index: number) => {
    const newUrls = [...urls];
    newUrls.splice(index, 1);
    setValue('urls', newUrls, { shouldValidate: true });
    setParsedUrls(newUrls);
  };

  const getFormErrorMessage = (name: keyof BatchDelistingFormData) => {
    return errors[name] && <small className="p-error">{errors[name]?.message}</small>;
  };

  const urlTemplate = `# CSV Template for Batch URL Delisting
# One URL per line, or use CSV format with headers
# Examples:

https://example1.com/infringing-content
https://example2.com/unauthorized-copy
https://pirate-site.com/stolen-content

# Or CSV format:
# url,priority,reason
# https://example1.com/content1,high,Copyright infringement
# https://example2.com/content2,normal,Unauthorized distribution`;

  return (
    <Card 
      title="Submit Batch URLs for Delisting"
      className="batch-request-form"
    >
      <form onSubmit={handleSubmit(onSubmit)} className="p-fluid">
        {submitError && (
          <Message 
            severity="error" 
            text={submitError} 
            className="w-full mb-4"
          />
        )}
        
        {submitSuccess && (
          <Message 
            severity="success" 
            text={submitSuccess} 
            className="w-full mb-4"
          />
        )}

        {/* URL Input Section */}
        <div className="field">
          <label className="font-semibold mb-2 block">
            URLs to Delist * (Maximum 100 URLs)
          </label>
          
          <TabView 
            activeIndex={activeTabIndex} 
            onTabChange={(e) => setActiveTabIndex(e.index)}
          >
            <TabPanel header="Upload CSV File" leftIcon="pi pi-upload mr-2">
              <FileUpload
                ref={fileUploadRef}
                mode="basic"
                name="csvFile"
                accept=".csv,.txt"
                maxFileSize={1000000}
                onUpload={handleFileUpload}
                auto
                chooseLabel="Choose CSV File"
                className="mb-3"
              />
              <Message 
                severity="info" 
                text="Upload a CSV file with one URL per line, or use the template format below"
                className="mb-3"
              />
              <pre className="bg-gray-50 p-3 border-round text-sm overflow-auto">
                {urlTemplate}
              </pre>
            </TabPanel>
            
            <TabPanel header="Manual Entry" leftIcon="pi pi-edit mr-2">
              <InputTextarea
                placeholder="Enter URLs (one per line)&#10;https://example1.com/content1&#10;https://example2.com/content2&#10;https://example3.com/content3"
                rows={6}
                className="mb-3"
                onChange={(e) => handleManualUrlsChange(e.target.value)}
              />
            </TabPanel>
          </TabView>

          {/* URLs Preview */}
          {urls.length > 0 && (
            <div className="mt-3">
              <label className="font-semibold block mb-2">
                URLs to Process ({urls.length}/100)
              </label>
              <DataTable
                value={urls.map((url, index) => ({ id: index, url }))}
                scrollable
                scrollHeight="200px"
                className="border-round"
              >
                <Column 
                  field="url" 
                  header="URL"
                  body={(rowData) => (
                    <span className="text-sm">{rowData.url}</span>
                  )}
                />
                <Column
                  header="Actions"
                  style={{ width: '80px' }}
                  body={(rowData) => (
                    <Button
                      icon="pi pi-times"
                      size="small"
                      severity="danger"
                      text
                      rounded
                      onClick={() => removeUrl(rowData.id)}
                    />
                  )}
                />
              </DataTable>
            </div>
          )}
          {getFormErrorMessage('urls')}
        </div>

        {/* Common Fields */}
        <div className="grid">
          <div className="col-12 md:col-6">
            <div className="field">
              <label htmlFor="originalContentUrl" className="font-semibold">
                Original Content URL
              </label>
              <Controller
                name="originalContentUrl"
                control={control}
                render={({ field, fieldState }) => (
                  <InputText
                    id={field.name}
                    {...field}
                    placeholder="https://yoursite.com/original-content"
                    className={classNames({ 'p-invalid': fieldState.error })}
                  />
                )}
              />
              {getFormErrorMessage('originalContentUrl')}
            </div>
          </div>

          <div className="col-12 md:col-6">
            <div className="field">
              <label htmlFor="evidenceUrl" className="font-semibold">
                Evidence URL
              </label>
              <Controller
                name="evidenceUrl"
                control={control}
                render={({ field, fieldState }) => (
                  <InputText
                    id={field.name}
                    {...field}
                    placeholder="https://evidence.example.com/proof"
                    className={classNames({ 'p-invalid': fieldState.error })}
                  />
                )}
              />
              {getFormErrorMessage('evidenceUrl')}
            </div>
          </div>
        </div>

        <div className="grid">
          <div className="col-12 md:col-6">
            <div className="field">
              <label htmlFor="searchEngines" className="font-semibold">
                Target Search Engines *
              </label>
              <Controller
                name="searchEngines"
                control={control}
                render={({ field, fieldState }) => (
                  <MultiSelect
                    id={field.name}
                    value={field.value}
                    onChange={field.onChange}
                    options={searchEngineOptions}
                    optionLabel="label"
                    optionValue="value"
                    placeholder="Select search engines"
                    className={classNames({ 'p-invalid': fieldState.error })}
                    display="chip"
                  />
                )}
              />
              {getFormErrorMessage('searchEngines')}
            </div>
          </div>

          <div className="col-12 md:col-6">
            <div className="field">
              <label htmlFor="priority" className="font-semibold">
                Priority *
              </label>
              <Controller
                name="priority"
                control={control}
                render={({ field, fieldState }) => (
                  <Dropdown
                    id={field.name}
                    value={field.value}
                    onChange={field.onChange}
                    options={priorityOptions}
                    optionLabel="label"
                    optionValue="value"
                    placeholder="Select priority level"
                    className={classNames({ 'p-invalid': fieldState.error })}
                  />
                )}
              />
              {getFormErrorMessage('priority')}
            </div>
          </div>
        </div>

        <div className="field">
          <label htmlFor="reason" className="font-semibold">
            Reason for Delisting *
          </label>
          <Controller
            name="reason"
            control={control}
            render={({ field, fieldState }) => (
              <InputTextarea
                id={field.name}
                {...field}
                rows={3}
                placeholder="Describe why these URLs should be delisted..."
                className={classNames({ 'p-invalid': fieldState.error })}
              />
            )}
          />
          {getFormErrorMessage('reason')}
        </div>

        <div className="flex justify-content-between gap-2 mt-4">
          <Button
            type="button"
            label="Clear Form"
            icon="pi pi-times"
            severity="secondary"
            outlined
            onClick={() => {
              reset();
              setParsedUrls([]);
              if (fileUploadRef.current) {
                fileUploadRef.current.clear();
              }
            }}
            disabled={isSubmitting}
          />
          
          <Button
            type="submit"
            label={`Submit Batch (${urls.length} URLs)`}
            icon={isSubmitting ? 'pi pi-spin pi-spinner' : 'pi pi-send'}
            disabled={isSubmitting || urls.length === 0}
            className="flex-1"
          />
        </div>

        {isSubmitting && (
          <div className="flex align-items-center justify-content-center mt-3">
            <ProgressSpinner size="20px" className="mr-2" />
            <span className="text-600">Submitting batch delisting request...</span>
          </div>
        )}
      </form>
    </Card>
  );
};

export default BatchRequestForm;