import React, { useState, useCallback } from 'react';
import {
  Box,
  Typography,
  Button,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  IconButton,
  Alert,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Grid,
} from '@mui/material';
import {
  CloudUpload,
  Description,
  Delete,
  Download,
  Check,
  Warning,
} from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';
import { useForm, Controller } from 'react-hook-form';
import { useMutation } from '@tanstack/react-query';
import { useSnackbar } from 'notistack';

interface BulkUploadForm {
  contentType: 'video' | 'image' | 'audio' | 'text';
  priority: 'low' | 'medium' | 'high';
  description?: string;
}

interface UploadedFile {
  file: File;
  urls: string[];
  status: 'pending' | 'processing' | 'completed' | 'error';
  error?: string;
}

const BulkUpload: React.FC = () => {
  const { enqueueSnackbar } = useSnackbar();
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);

  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<BulkUploadForm>({
    defaultValues: {
      contentType: 'video',
      priority: 'medium',
      description: '',
    },
  });

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles = acceptedFiles.map(file => ({
      file,
      urls: [],
      status: 'pending' as const,
    }));
    
    setUploadedFiles(prev => [...prev, ...newFiles]);
    
    // Process files to extract URLs
    newFiles.forEach((fileData, index) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const content = e.target?.result as string;
        const urls = extractUrlsFromContent(content);
        
        setUploadedFiles(prev =>
          prev.map((f, i) => {
            if (f.file.name === fileData.file.name) {
              return {
                ...f,
                urls,
                status: urls.length > 0 ? 'completed' : 'error',
                error: urls.length === 0 ? 'No valid URLs found in file' : undefined,
              };
            }
            return f;
          })
        );
      };
      reader.readAsText(fileData.file);
    });
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/plain': ['.txt'],
      'text/csv': ['.csv'],
      'application/json': ['.json'],
    },
    multiple: true,
    maxSize: 5 * 1024 * 1024, // 5MB
  });

  const extractUrlsFromContent = (content: string): string[] => {
    // Simple URL extraction - in a real app, this would be more sophisticated
    const urlRegex = /(https?:\/\/[^\s\n,]+)/g;
    const matches = content.match(urlRegex) || [];
    return matches.filter(url => {
      try {
        new URL(url);
        return true;
      } catch {
        return false;
      }
    });
  };

  const removeFile = (fileName: string) => {
    setUploadedFiles(prev => prev.filter(f => f.file.name !== fileName));
  };

  const processBulkSubmission = useMutation({
    mutationFn: async (data: BulkUploadForm) => {
      setIsProcessing(true);
      
      // Simulate API call for bulk submission
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      const allUrls = uploadedFiles.flatMap(f => f.urls);
      
      // Here you would make actual API calls
      return { submittedUrls: allUrls.length };
    },
    onSuccess: (result) => {
      enqueueSnackbar(
        `Successfully submitted ${result.submittedUrls} URLs for monitoring`,
        { variant: 'success' }
      );
      setUploadedFiles([]);
      setIsProcessing(false);
    },
    onError: () => {
      enqueueSnackbar('Failed to process bulk submission', { variant: 'error' });
      setIsProcessing(false);
    },
  });

  const onSubmit = (data: BulkUploadForm) => {
    if (uploadedFiles.length === 0) {
      enqueueSnackbar('Please upload at least one file', { variant: 'warning' });
      return;
    }

    const validFiles = uploadedFiles.filter(f => f.status === 'completed');
    if (validFiles.length === 0) {
      enqueueSnackbar('No valid files with URLs found', { variant: 'warning' });
      return;
    }

    processBulkSubmission.mutate(data);
  };

  const downloadTemplate = () => {
    const template = `# ContentGuard Bulk Upload Template
# Add one URL per line
# Lines starting with # are comments and will be ignored

https://example.com/your-video-1
https://example.com/your-video-2
https://example.com/your-video-3

# You can also include descriptions after URLs (separated by a comma)
https://example.com/your-video-4, My important video content
`;

    const blob = new Blob([template], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'contentguard-bulk-template.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const totalUrls = uploadedFiles.reduce((sum, file) => sum + file.urls.length, 0);
  const validFiles = uploadedFiles.filter(f => f.status === 'completed').length;

  return (
    <Box>
      <Typography variant="h6" gutterBottom fontWeight="600">
        Bulk URL Upload
      </Typography>
      
      <Typography variant="body2" color="textSecondary" paragraph>
        Upload files containing multiple URLs for batch processing. Supported formats: TXT, CSV, JSON.
      </Typography>

      <Grid container spacing={3}>
        {/* File Upload Area */}
        <Grid item xs={12}>
          <Paper
            {...getRootProps()}
            sx={{
              p: 3,
              textAlign: 'center',
              border: '2px dashed',
              borderColor: isDragActive ? 'primary.main' : 'grey.300',
              bgcolor: isDragActive ? 'primary.50' : 'grey.50',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              '&:hover': {
                borderColor: 'primary.main',
                bgcolor: 'primary.50',
              },
            }}
          >
            <input {...getInputProps()} />
            <CloudUpload sx={{ fontSize: 48, color: 'grey.400', mb: 2 }} />
            
            {isDragActive ? (
              <Typography variant="body1" color="primary">
                Drop the files here...
              </Typography>
            ) : (
              <>
                <Typography variant="body1" gutterBottom>
                  Drag & drop files here, or click to select
                </Typography>
                <Typography variant="body2" color="textSecondary" gutterBottom>
                  Supports TXT, CSV, and JSON files (max 5MB each)
                </Typography>
                <Button variant="outlined" sx={{ mt: 1 }}>
                  Choose Files
                </Button>
              </>
            )}
          </Paper>

          <Box display="flex" justifyContent="space-between" alignItems="center" mt={2}>
            <Button
              variant="text"
              startIcon={<Download />}
              onClick={downloadTemplate}
              size="small"
            >
              Download Template
            </Button>
            
            {totalUrls > 0 && (
              <Typography variant="body2" color="textSecondary">
                {totalUrls} URLs found in {validFiles} file{validFiles !== 1 ? 's' : ''}
              </Typography>
            )}
          </Box>
        </Grid>

        {/* Uploaded Files List */}
        {uploadedFiles.length > 0 && (
          <Grid item xs={12}>
            <Typography variant="subtitle1" gutterBottom fontWeight="600">
              Uploaded Files
            </Typography>
            
            <Paper variant="outlined">
              <List>
                {uploadedFiles.map((fileData, index) => (
                  <ListItem key={index}>
                    <ListItemIcon>
                      {fileData.status === 'completed' && <Check color="success" />}
                      {fileData.status === 'error' && <Warning color="error" />}
                      {fileData.status === 'pending' && <Description color="action" />}
                    </ListItemIcon>
                    
                    <ListItemText
                      primary={fileData.file.name}
                      secondary={
                        fileData.status === 'completed'
                          ? `${fileData.urls.length} URLs found`
                          : fileData.status === 'error'
                          ? fileData.error
                          : 'Processing...'
                      }
                    />
                    
                    <IconButton
                      edge="end"
                      onClick={() => removeFile(fileData.file.name)}
                      size="small"
                    >
                      <Delete />
                    </IconButton>
                  </ListItem>
                ))}
              </List>
            </Paper>
          </Grid>
        )}

        {/* Form Fields */}
        {uploadedFiles.length > 0 && (
          <>
            <Grid item xs={12} sm={6}>
              <Controller
                name="contentType"
                control={control}
                render={({ field }) => (
                  <FormControl fullWidth>
                    <InputLabel>Content Type</InputLabel>
                    <Select {...field} label="Content Type">
                      <MenuItem value="video">Video</MenuItem>
                      <MenuItem value="image">Image</MenuItem>
                      <MenuItem value="audio">Audio</MenuItem>
                      <MenuItem value="text">Text</MenuItem>
                    </Select>
                  </FormControl>
                )}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <Controller
                name="priority"
                control={control}
                render={({ field }) => (
                  <FormControl fullWidth>
                    <InputLabel>Priority Level</InputLabel>
                    <Select {...field} label="Priority Level">
                      <MenuItem value="low">Low</MenuItem>
                      <MenuItem value="medium">Medium</MenuItem>
                      <MenuItem value="high">High</MenuItem>
                    </Select>
                  </FormControl>
                )}
              />
            </Grid>

            <Grid item xs={12}>
              <Controller
                name="description"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    fullWidth
                    multiline
                    rows={2}
                    label="Batch Description (Optional)"
                    placeholder="Describe this batch of content..."
                  />
                )}
              />
            </Grid>

            {/* Submit Section */}
            <Grid item xs={12}>
              {validFiles > 0 && (
                <Alert severity="info" sx={{ mb: 2 }}>
                  Ready to submit {totalUrls} URLs from {validFiles} file{validFiles !== 1 ? 's' : ''} 
                  for monitoring.
                </Alert>
              )}
              
              <Box display="flex" justifyContent="flex-end">
                <Button
                  variant="contained"
                  size="large"
                  onClick={handleSubmit(onSubmit)}
                  disabled={isProcessing || validFiles === 0}
                  startIcon={
                    isProcessing ? 
                    <div className="loading-spinner" /> : 
                    <CloudUpload />
                  }
                >
                  {isProcessing ? 'Processing...' : `Submit ${totalUrls} URLs`}
                </Button>
              </Box>
            </Grid>
          </>
        )}
      </Grid>
    </Box>
  );
};

export default BulkUpload;