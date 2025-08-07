import React, { useState } from 'react';
import {
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Chip,
  IconButton,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Alert,
  CircularProgress,
  Paper,
  TextField,
  InputAdornment,
} from '@mui/material';
import {
  MoreVert,
  Visibility,
  Delete,
  Refresh,
  Search,
} from '@mui/icons-material';
import { formatDistanceToNow } from 'date-fns';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSnackbar } from 'notistack';
import { apiService } from '@services/api';

interface Submission {
  id: string;
  urls: string[];
  contentType: string;
  priority: string;
  status: 'processing' | 'completed' | 'failed';
  submittedAt: string;
  processedAt?: string;
  description?: string;
  detectedCount: number;
}

const SubmissionHistory: React.FC = () => {
  const queryClient = useQueryClient();
  const { enqueueSnackbar } = useSnackbar();
  const [page, setPage] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedSubmission, setSelectedSubmission] = useState<Submission | null>(null);

  const {
    data: submissionsData,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['submissions', page + 1, searchQuery],
    queryFn: () => apiService.getSubmissions(page + 1, 10),
  });

  const deleteSubmissionMutation = useMutation({
    mutationFn: (id: string) => {
      // This would be the actual API call
      return new Promise((resolve) => {
        setTimeout(() => resolve({ success: true }), 1000);
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['submissions'] });
      enqueueSnackbar('Submission deleted successfully', { variant: 'success' });
      handleMenuClose();
    },
    onError: () => {
      enqueueSnackbar('Failed to delete submission', { variant: 'error' });
    },
  });

  // Mock data for demo purposes
  const mockSubmissions: Submission[] = [
    {
      id: '1',
      urls: ['https://youtube.com/watch?v=abc123', 'https://vimeo.com/123456'],
      contentType: 'video',
      priority: 'high',
      status: 'completed',
      submittedAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
      processedAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000 + 30 * 60 * 1000).toISOString(),
      description: 'Music video content batch',
      detectedCount: 3,
    },
    {
      id: '2',
      urls: ['https://instagram.com/p/abc123'],
      contentType: 'image',
      priority: 'medium',
      status: 'processing',
      submittedAt: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
      description: 'Brand logo monitoring',
      detectedCount: 0,
    },
    {
      id: '3',
      urls: ['https://soundcloud.com/track/123'],
      contentType: 'audio',
      priority: 'low',
      status: 'failed',
      submittedAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
      processedAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000 + 10 * 60 * 1000).toISOString(),
      description: 'Podcast episode protection',
      detectedCount: 0,
    },
  ];

  const submissions = submissionsData?.data || mockSubmissions;

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, submission: Submission) => {
    setAnchorEl(event.currentTarget);
    setSelectedSubmission(submission);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setSelectedSubmission(null);
  };

  const handleDelete = () => {
    if (selectedSubmission) {
      deleteSubmissionMutation.mutate(selectedSubmission.id);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'processing':
        return 'warning';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'error';
      case 'medium':
        return 'warning';
      case 'low':
        return 'default';
      default:
        return 'default';
    }
  };

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="300px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h6" fontWeight="600">
          Submission History
        </Typography>
        
        <IconButton onClick={() => refetch()}>
          <Refresh />
        </IconButton>
      </Box>

      {/* Search Bar */}
      <Box mb={3}>
        <TextField
          fullWidth
          placeholder="Search by description or content type..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Search color="action" />
              </InputAdornment>
            ),
          }}
          size="small"
        />
      </Box>

      {submissions.length === 0 ? (
        <Alert severity="info">
          No submissions found. Submit some URLs to start monitoring your content.
        </Alert>
      ) : (
        <Paper variant="outlined">
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>URLs</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Priority</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Detected</TableCell>
                  <TableCell>Submitted</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {submissions.map((submission) => (
                  <TableRow key={submission.id} hover>
                    <TableCell>
                      <Box>
                        <Typography variant="body2" fontWeight="500">
                          {submission.urls.length} URL{submission.urls.length !== 1 ? 's' : ''}
                        </Typography>
                        {submission.description && (
                          <Typography variant="caption" color="textSecondary">
                            {submission.description}
                          </Typography>
                        )}
                      </Box>
                    </TableCell>

                    <TableCell>
                      <Chip
                        label={submission.contentType}
                        size="small"
                        variant="outlined"
                        sx={{ textTransform: 'capitalize' }}
                      />
                    </TableCell>

                    <TableCell>
                      <Chip
                        label={submission.priority}
                        size="small"
                        color={getPriorityColor(submission.priority) as any}
                        sx={{ textTransform: 'capitalize' }}
                      />
                    </TableCell>

                    <TableCell>
                      <Chip
                        label={submission.status}
                        size="small"
                        color={getStatusColor(submission.status) as any}
                        sx={{ textTransform: 'capitalize' }}
                      />
                    </TableCell>

                    <TableCell>
                      <Typography 
                        variant="body2" 
                        fontWeight="600"
                        color={submission.detectedCount > 0 ? 'error.main' : 'text.secondary'}
                      >
                        {submission.detectedCount}
                      </Typography>
                    </TableCell>

                    <TableCell>
                      <Typography variant="body2">
                        {formatDistanceToNow(new Date(submission.submittedAt), { addSuffix: true })}
                      </Typography>
                      {submission.processedAt && (
                        <Typography variant="caption" color="textSecondary" display="block">
                          Processed {formatDistanceToNow(new Date(submission.processedAt), { addSuffix: true })}
                        </Typography>
                      )}
                    </TableCell>

                    <TableCell>
                      <IconButton
                        onClick={(e) => handleMenuOpen(e, submission)}
                        size="small"
                      >
                        <MoreVert />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>

          <TablePagination
            rowsPerPageOptions={[10]}
            component="div"
            count={submissions.length}
            rowsPerPage={10}
            page={page}
            onPageChange={(_, newPage) => setPage(newPage)}
          />
        </Paper>
      )}

      {/* Action Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
        PaperProps={{
          sx: { minWidth: 160 }
        }}
      >
        <MenuItem onClick={() => {
          // View details action
          handleMenuClose();
        }}>
          <ListItemIcon>
            <Visibility fontSize="small" />
          </ListItemIcon>
          <ListItemText>View Details</ListItemText>
        </MenuItem>
        
        <MenuItem onClick={handleDelete} sx={{ color: 'error.main' }}>
          <ListItemIcon>
            <Delete fontSize="small" sx={{ color: 'error.main' }} />
          </ListItemIcon>
          <ListItemText>Delete</ListItemText>
        </MenuItem>
      </Menu>
    </Box>
  );
};

export default SubmissionHistory;