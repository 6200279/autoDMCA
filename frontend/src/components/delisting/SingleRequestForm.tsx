import React, { useState } from 'react';
import { Card } from 'primereact/card';
import { InputText } from 'primereact/inputtext';
import { InputTextarea } from 'primereact/inputtextarea';
import { Dropdown } from 'primereact/dropdown';
import { MultiSelect } from 'primereact/multiselect';
import { Button } from 'primereact/button';
import { Message } from 'primereact/message';
import { ProgressSpinner } from 'primereact/progressspinner';
import { classNames } from 'primereact/utils';
import { Controller, useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { searchEngineDelistingApi } from '../../services/api';
import type { 
  SingleDelistingFormData, 
  SearchEngine, 
  DelistingPriority 
} from '../../types/delisting';

interface SingleRequestFormProps {
  onSuccess?: (requestId: string) => void;
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
  url: yup
    .string()
    .required('URL is required')
    .url('Please enter a valid URL')
    .matches(
      /^https?:\/\/.+/,
      'URL must start with http:// or https://'
    ),
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

const SingleRequestForm: React.FC<SingleRequestFormProps> = ({
  onSuccess,
  onError
}) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null);

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors }
  } = useForm<SingleDelistingFormData>({
    resolver: yupResolver(validationSchema),
    defaultValues: {
      url: '',
      originalContentUrl: '',
      reason: 'Copyright infringement - unauthorized distribution',
      evidenceUrl: '',
      priority: 'normal',
      searchEngines: ['google', 'bing'],
      profileId: ''
    }
  });

  const onSubmit = async (data: SingleDelistingFormData) => {
    setIsSubmitting(true);
    setSubmitError(null);
    setSubmitSuccess(null);

    try {
      const response = await searchEngineDelistingApi.submitDelistingRequest({
        url: data.url,
        originalContentUrl: data.originalContentUrl || undefined,
        reason: data.reason,
        evidenceUrl: data.evidenceUrl || undefined,
        priority: data.priority,
        searchEngines: data.searchEngines,
        profileId: data.profileId || undefined
      });

      setSubmitSuccess(
        `Request submitted successfully! Request ID: ${response.data.id}`
      );
      
      if (onSuccess) {
        onSuccess(response.data.id);
      }
      
      // Reset form after successful submission
      reset();
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 
                          error.message || 
                          'Failed to submit delisting request';
      setSubmitError(errorMessage);
      
      if (onError) {
        onError(errorMessage);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const getFormErrorMessage = (name: keyof SingleDelistingFormData) => {
    return errors[name] && <small className="p-error">{errors[name]?.message}</small>;
  };

  return (
    <Card 
      title="Submit Single URL for Delisting"
      className="single-request-form"
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

        {/* URL Field */}
        <div className="field">
          <label htmlFor="url" className="font-semibold">
            Infringing URL *
          </label>
          <Controller
            name="url"
            control={control}
            render={({ field, fieldState }) => (
              <InputText
                id={field.name}
                {...field}
                placeholder="https://example.com/infringing-content"
                className={classNames({ 'p-invalid': fieldState.error })}
              />
            )}
          />
          {getFormErrorMessage('url')}
        </div>

        {/* Original Content URL Field */}
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
          <small className="text-600">
            URL where the original, authorized content is hosted
          </small>
        </div>

        {/* Search Engines Selection */}
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

        {/* Priority Selection */}
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

        {/* Reason Field */}
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
                placeholder="Describe why this content should be delisted..."
                className={classNames({ 'p-invalid': fieldState.error })}
              />
            )}
          />
          {getFormErrorMessage('reason')}
        </div>

        {/* Evidence URL Field */}
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
          <small className="text-600">
            Optional URL containing evidence of ownership or infringement
          </small>
        </div>

        <div className="flex justify-content-between gap-2 mt-4">
          <Button
            type="button"
            label="Clear Form"
            icon="pi pi-times"
            severity="secondary"
            outlined
            onClick={() => reset()}
            disabled={isSubmitting}
          />
          
          <Button
            type="submit"
            label="Submit Request"
            icon={isSubmitting ? 'pi pi-spin pi-spinner' : 'pi pi-send'}
            disabled={isSubmitting}
            className="flex-1"
          />
        </div>

        {isSubmitting && (
          <div className="flex align-items-center justify-content-center mt-3">
            <ProgressSpinner size="20px" className="mr-2" />
            <span className="text-600">Submitting delisting request...</span>
          </div>
        )}
      </form>
    </Card>
  );
};

export default SingleRequestForm;