import React, { useState } from 'react';
import {
  Box,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Typography,
  Grid,
  Alert,
  Paper,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Add,
  Delete,
  CloudUpload,
  Link as LinkIcon,
  Info,
} from '@mui/icons-material';
import { useForm, Controller, useFieldArray } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useSnackbar } from 'notistack';
import { apiService } from '@services/api';
import { ManualSubmission } from '@types/index';

// Validation schema
const submissionSchema = yup.object().shape({
  urls: yup
    .array()
    .of(
      yup.object().shape({
        url: yup
          .string()
          .url('Please enter a valid URL')
          .required('URL is required'),
      })
    )
    .min(1, 'At least one URL is required')
    .max(10, 'Maximum 10 URLs allowed'),
  contentType: yup
    .string()
    .oneOf(['video', 'image', 'audio', 'text'], 'Invalid content type')
    .required('Content type is required'),
  priority: yup
    .string()
    .oneOf(['low', 'medium', 'high'], 'Invalid priority level')
    .required('Priority is required'),
  description: yup
    .string()
    .max(500, 'Description must be less than 500 characters'),
  originalContentUrl: yup
    .string()
    .url('Please enter a valid URL'),
});

interface FormData {
  urls: { url: string }[];
  contentType: 'video' | 'image' | 'audio' | 'text';
  priority: 'low' | 'medium' | 'high';
  description?: string;
  originalContentUrl?: string;
}

const contentTypeOptions = [
  { value: 'video', label: 'Video' },
  { value: 'image', label: 'Image' },
  { value: 'audio', label: 'Audio' },
  { value: 'text', label: 'Text' },
];

const priorityOptions = [
  { value: 'low', label: 'Low', color: 'default' as const },
  { value: 'medium', label: 'Medium', color: 'warning' as const },
  { value: 'high', label: 'High', color: 'error' as const },
];

const URLSubmissionForm: React.FC = () => {
  const queryClient = useQueryClient();
  const { enqueueSnackbar } = useSnackbar();
  const [submissionSuccess, setSubmissionSuccess] = useState(false);

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors },
    watch,
  } = useForm<FormData>({
    resolver: yupResolver(submissionSchema),
    defaultValues: {
      urls: [{ url: '' }],
      contentType: 'video',
      priority: 'medium',
      description: '',
      originalContentUrl: '',
    },
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'urls',
  });

  const submitUrlsMutation = useMutation({
    mutationFn: (data: ManualSubmission) => apiService.submitUrls(data),
    onSuccess: (response) => {
      enqueueSnackbar('URLs submitted successfully for monitoring', { 
        variant: 'success' 
      });
      setSubmissionSuccess(true);
      reset();
      queryClient.invalidateQueries({ queryKey: ['submissions'] });
      
      // Reset success message after 5 seconds
      setTimeout(() => setSubmissionSuccess(false), 5000);
    },
    onError: (error: any) => {
      enqueueSnackbar(
        error.response?.data?.message || 'Failed to submit URLs',
        { variant: 'error' }
      );
    },
  });

  const onSubmit = (data: FormData) => {
    const submission: ManualSubmission = {
      urls: data.urls.map(item => item.url),
      contentType: data.contentType,
      priority: data.priority,
      description: data.description,
      originalContentUrl: data.originalContentUrl,
    };

    submitUrlsMutation.mutate(submission);
  };

  const addUrlField = () => {
    if (fields.length < 10) {
      append({ url: '' });
    }
  };

  const removeUrlField = (index: number) => {
    if (fields.length > 1) {
      remove(index);
    }
  };

  const selectedPriority = watch('priority');
  const selectedPriorityOption = priorityOptions.find(opt => opt.value === selectedPriority);

  return (
    <Box>
      <Typography variant="h6" gutterBottom fontWeight="600">
        Submit URLs for Monitoring
      </Typography>
      
      <Typography variant="body2" color="textSecondary" paragraph>
        Add URLs of your original content to start monitoring for unauthorized copies.
      </Typography>

      {submissionSuccess && (
        <Alert severity="success" sx={{ mb: 3 }}>
          <Typography variant="body2" gutterBottom>
            <strong>Submission successful!</strong>
          </Typography>
          <Typography variant="body2">
            Your URLs have been added to our monitoring system. You'll receive notifications 
            when potential infringements are detected.
          </Typography>
        </Alert>
      )}

      <form onSubmit={handleSubmit(onSubmit)}>
        <Grid container spacing={3}>
          {/* URL Fields */}
          <Grid item xs={12}>
            <Box display="flex" alignItems="center" gap={1} mb={2}>
              <LinkIcon color="action" />
              <Typography variant="subtitle1" fontWeight="600">
                Content URLs
              </Typography>
              <Tooltip title="Add the URLs of your original content that you want to protect">
                <IconButton size="small">
                  <Info fontSize="small" />
                </IconButton>
              </Tooltip>
            </Box>

            {fields.map((field, index) => (
              <Paper 
                key={field.id} 
                sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}
                variant="outlined"
              >
                <Box display="flex" alignItems="flex-start" gap={2}>
                  <Controller
                    name={`urls.${index}.url`}
                    control={control}
                    render={({ field }) => (
                      <TextField
                        {...field}
                        fullWidth
                        label={`URL ${index + 1}`}
                        placeholder="https://example.com/your-content"
                        error={!!errors.urls?.[index]?.url}
                        helperText={errors.urls?.[index]?.url?.message}
                        size="small"
                      />
                    )}
                  />
                  
                  {fields.length > 1 && (
                    <IconButton
                      onClick={() => removeUrlField(index)}
                      color="error"
                      size="small"
                    >
                      <Delete />
                    </IconButton>
                  )}
                </Box>
              </Paper>
            ))}

            {fields.length < 10 && (
              <Button
                variant="outlined"
                startIcon={<Add />}
                onClick={addUrlField}
                size="small"
                sx={{ mb: 2 }}
              >
                Add Another URL
              </Button>
            )}
          </Grid>

          {/* Content Type */}
          <Grid item xs={12} sm={6}>
            <Controller
              name="contentType"
              control={control}
              render={({ field }) => (
                <FormControl fullWidth>
                  <InputLabel>Content Type</InputLabel>
                  <Select
                    {...field}
                    label="Content Type"
                    error={!!errors.contentType}
                  >
                    {contentTypeOptions.map((option) => (
                      <MenuItem key={option.value} value={option.value}>
                        {option.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              )}
            />
            {errors.contentType && (
              <Typography variant="caption" color="error" sx={{ mt: 0.5, display: 'block' }}>
                {errors.contentType.message}
              </Typography>
            )}
          </Grid>

          {/* Priority */}
          <Grid item xs={12} sm={6}>
            <Controller
              name="priority"
              control={control}
              render={({ field }) => (
                <FormControl fullWidth>
                  <InputLabel>Priority Level</InputLabel>
                  <Select
                    {...field}
                    label="Priority Level"
                    error={!!errors.priority}
                  >
                    {priorityOptions.map((option) => (
                      <MenuItem key={option.value} value={option.value}>
                        <Box display="flex" alignItems="center" gap={1}>
                          {option.label}
                          <Chip
                            label={option.label}
                            size="small"
                            color={option.color}
                            sx={{ minWidth: 60 }}
                          />
                        </Box>
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              )}
            />
            {errors.priority && (
              <Typography variant="caption" color="error" sx={{ mt: 0.5, display: 'block' }}>
                {errors.priority.message}
              </Typography>
            )}
          </Grid>

          {/* Original Content URL */}
          <Grid item xs={12}>
            <Controller
              name="originalContentUrl"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  fullWidth
                  label="Original Content URL (Optional)"
                  placeholder="https://your-website.com/original-content"
                  error={!!errors.originalContentUrl}
                  helperText={
                    errors.originalContentUrl?.message || 
                    "Link to where your original content is hosted (helps with verification)"
                  }
                />
              )}
            />
          </Grid>

          {/* Description */}
          <Grid item xs={12}>
            <Controller
              name="description"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  fullWidth
                  multiline
                  rows={3}
                  label="Description (Optional)"
                  placeholder="Describe your content and any specific concerns..."
                  error={!!errors.description}
                  helperText={errors.description?.message}
                />
              )}
            />
          </Grid>

          {/* Submit Button */}
          <Grid item xs={12}>
            <Box display="flex" justifyContent="space-between" alignItems="center">
              <Box>
                {selectedPriorityOption && (
                  <Chip
                    label={`${selectedPriorityOption.label} Priority`}
                    color={selectedPriorityOption.color}
                    variant="outlined"
                  />
                )}
              </Box>
              
              <Button
                type="submit"
                variant="contained"
                size="large"
                startIcon={
                  submitUrlsMutation.isPending ? 
                  <div className="loading-spinner" /> : 
                  <CloudUpload />
                }
                disabled={submitUrlsMutation.isPending}
                sx={{ minWidth: 160 }}
              >
                {submitUrlsMutation.isPending ? 'Submitting...' : 'Submit URLs'}
              </Button>
            </Box>
          </Grid>
        </Grid>
      </form>
    </Box>
  );
};

export default URLSubmissionForm;