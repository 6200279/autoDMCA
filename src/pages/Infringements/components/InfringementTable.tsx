import React, { useState } from 'react';
import {
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
  Avatar,
  Box,
  Typography,
  Link,
  Tooltip,
  CircularProgress,
} from '@mui/material';
import {
  MoreVert,
  OpenInNew,
  Block,
  Check,
  Schedule,
  Error,
  Visibility,
  YouTube,
  Instagram,
  Facebook,
} from '@mui/icons-material';
import { formatDistanceToNow } from 'date-fns';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useSnackbar } from 'notistack';
import { apiService } from '@services/api';
import { Infringement, PaginatedResponse } from '@types/index';
import { statusColors } from '@/theme';

interface InfringementTableProps {
  data?: PaginatedResponse<Infringement>;
  isLoading: boolean;
  page: number;
  onPageChange: (page: number) => void;
  onRefresh: () => void;
}

const getPlatformIcon = (platform: string) => {
  switch (platform.toLowerCase()) {
    case 'youtube':
      return YouTube;
    case 'instagram':
      return Instagram;
    case 'facebook':
      return Facebook;
    default:
      return OpenInNew;
  }
};

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'removed':
      return Check;
    case 'failed':
      return Error;
    case 'pending':
      return Schedule;
    case 'reviewing':
      return Visibility;
    default:
      return Block;
  }
};

const InfringementTable: React.FC<InfringementTableProps> = ({
  data,
  isLoading,
  page,
  onPageChange,
  onRefresh,
}) => {
  const queryClient = useQueryClient();
  const { enqueueSnackbar } = useSnackbar();
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedInfringement, setSelectedInfringement] = useState<Infringement | null>(null);

  const updateStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      apiService.updateInfringementStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['infringements'] });
      enqueueSnackbar('Status updated successfully', { variant: 'success' });
      handleMenuClose();
    },
    onError: () => {
      enqueueSnackbar('Failed to update status', { variant: 'error' });
    },
  });

  const deleteInfringementMutation = useMutation({
    mutationFn: (id: string) => apiService.deleteInfringement(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['infringements'] });
      enqueueSnackbar('Infringement deleted successfully', { variant: 'success' });
      handleMenuClose();
    },
    onError: () => {
      enqueueSnackbar('Failed to delete infringement', { variant: 'error' });
    },
  });

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, infringement: Infringement) => {
    setAnchorEl(event.currentTarget);
    setSelectedInfringement(infringement);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setSelectedInfringement(null);
  };

  const handleStatusUpdate = (status: string) => {
    if (selectedInfringement) {
      updateStatusMutation.mutate({ id: selectedInfringement.id, status });
    }
  };

  const handleDelete = () => {
    if (selectedInfringement) {
      deleteInfringementMutation.mutate(selectedInfringement.id);
    }
  };

  if (isLoading && !data) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (!data?.data?.length) {
    return (
      <Box textAlign="center" py={8}>
        <Typography variant="h6" color="textSecondary" gutterBottom>
          No infringements found
        </Typography>
        <Typography variant="body2" color="textSecondary">
          Try adjusting your filters or search terms
        </Typography>
      </Box>
    );
  }

  return (
    <>
      <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Content</TableCell>
              <TableCell>Platform</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Confidence</TableCell>
              <TableCell>Detected</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {data.data.map((infringement) => {
              const PlatformIcon = getPlatformIcon(infringement.platform);
              const StatusIcon = getStatusIcon(infringement.status);
              const timeAgo = formatDistanceToNow(new Date(infringement.detectedAt), { addSuffix: true });

              return (
                <TableRow
                  key={infringement.id}
                  hover
                  sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
                >
                  <TableCell>
                    <Box>
                      <Link
                        href={infringement.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        sx={{
                          textDecoration: 'none',
                          color: 'primary.main',
                          fontWeight: 500,
                          '&:hover': { textDecoration: 'underline' },
                        }}
                      >
                        {infringement.url.length > 50
                          ? `${infringement.url.substring(0, 50)}...`
                          : infringement.url}
                      </Link>
                      {infringement.originalContent && (
                        <Typography variant="caption" display="block" color="textSecondary">
                          {infringement.originalContent.title}
                        </Typography>
                      )}
                    </Box>
                  </TableCell>

                  <TableCell>
                    <Box display="flex" alignItems="center" gap={1}>
                      <Avatar sx={{ width: 24, height: 24, bgcolor: 'primary.main' }}>
                        <PlatformIcon sx={{ fontSize: 14 }} />
                      </Avatar>
                      <Typography variant="body2" textTransform="capitalize">
                        {infringement.platform}
                      </Typography>
                    </Box>
                  </TableCell>

                  <TableCell>
                    <Chip
                      icon={<StatusIcon sx={{ fontSize: 16 }} />}
                      label={infringement.status}
                      size="small"
                      sx={{
                        backgroundColor: `${statusColors[infringement.status as keyof typeof statusColors]}20`,
                        color: statusColors[infringement.status as keyof typeof statusColors],
                        border: `1px solid ${statusColors[infringement.status as keyof typeof statusColors]}40`,
                        textTransform: 'capitalize',
                        fontWeight: 600,
                      }}
                    />
                  </TableCell>

                  <TableCell>
                    <Box display="flex" alignItems="center" gap={1}>
                      <Typography variant="body2" fontWeight="600">
                        {Math.round(infringement.confidence * 100)}%
                      </Typography>
                      <Box
                        sx={{
                          width: 40,
                          height: 4,
                          bgcolor: 'grey.200',
                          borderRadius: 2,
                          overflow: 'hidden',
                        }}
                      >
                        <Box
                          sx={{
                            width: `${infringement.confidence * 100}%`,
                            height: '100%',
                            bgcolor: infringement.confidence > 0.7 ? 'success.main' : 
                                   infringement.confidence > 0.5 ? 'warning.main' : 'error.main',
                          }}
                        />
                      </Box>
                    </Box>
                  </TableCell>

                  <TableCell>
                    <Tooltip title={new Date(infringement.detectedAt).toLocaleString()}>
                      <Typography variant="body2" color="textSecondary">
                        {timeAgo}
                      </Typography>
                    </Tooltip>
                  </TableCell>

                  <TableCell>
                    <IconButton
                      onClick={(e) => handleMenuOpen(e, infringement)}
                      size="small"
                    >
                      <MoreVert />
                    </IconButton>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>

      <TablePagination
        rowsPerPageOptions={[20]}
        component="div"
        count={data.pagination.total}
        rowsPerPage={20}
        page={page - 1}
        onPageChange={(_, newPage) => onPageChange(newPage + 1)}
      />

      {/* Action Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
        PaperProps={{
          sx: { minWidth: 180 }
        }}
      >
        <MenuItem onClick={() => handleStatusUpdate('pending')}>
          <ListItemIcon>
            <Schedule fontSize="small" />
          </ListItemIcon>
          <ListItemText>Mark as Pending</ListItemText>
        </MenuItem>
        
        <MenuItem onClick={() => handleStatusUpdate('reviewing')}>
          <ListItemIcon>
            <Visibility fontSize="small" />
          </ListItemIcon>
          <ListItemText>Start Review</ListItemText>
        </MenuItem>
        
        <MenuItem onClick={() => handleStatusUpdate('removed')}>
          <ListItemIcon>
            <Check fontSize="small" />
          </ListItemIcon>
          <ListItemText>Mark as Removed</ListItemText>
        </MenuItem>
        
        <MenuItem onClick={() => handleStatusUpdate('failed')}>
          <ListItemIcon>
            <Error fontSize="small" />
          </ListItemIcon>
          <ListItemText>Mark as Failed</ListItemText>
        </MenuItem>
        
        <MenuItem onClick={handleDelete} sx={{ color: 'error.main' }}>
          <ListItemIcon>
            <Block fontSize="small" sx={{ color: 'error.main' }} />
          </ListItemIcon>
          <ListItemText>Delete</ListItemText>
        </MenuItem>
      </Menu>
    </>
  );
};

export default InfringementTable;