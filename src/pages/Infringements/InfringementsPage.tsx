import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  TextField,
  InputAdornment,
  Chip,
  Grid,
  Alert,
} from '@mui/material';
import {
  Search,
  FilterList,
  Refresh,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { useWebSocket } from '@hooks/useWebSocket';
import { apiService } from '@services/api';
import { InfringementFilter } from '@types/index';
import InfringementTable from './components/InfringementTable';
import FilterPanel from './components/FilterPanel';
import StatusSummary from './components/StatusSummary';

const InfringementsPage: React.FC = () => {
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<InfringementFilter>({});
  const [searchQuery, setSearchQuery] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  
  const limit = 20;

  // Fetch infringements with pagination and filters
  const {
    data: infringementsData,
    isLoading,
    refetch,
    error,
  } = useQuery({
    queryKey: ['infringements', page, filters],
    queryFn: () => apiService.getInfringements(page, limit, filters),
    keepPreviousData: true,
  });

  // Set up WebSocket for real-time updates
  useWebSocket({
    onInfringementDetected: (data) => {
      refetch();
    },
    onStatusUpdate: (data) => {
      refetch();
    },
    enableNotifications: true,
  });

  // Handle search
  useEffect(() => {
    const delayedSearch = setTimeout(() => {
      setFilters(prev => ({ ...prev, searchQuery }));
      setPage(1);
    }, 500);

    return () => clearTimeout(delayedSearch);
  }, [searchQuery]);

  const handleFilterChange = (newFilters: InfringementFilter) => {
    setFilters(newFilters);
    setPage(1);
  };

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
  };

  const handleClearFilters = () => {
    setFilters({});
    setSearchQuery('');
    setPage(1);
  };

  const activeFilterCount = Object.values(filters).filter(
    value => value && (Array.isArray(value) ? value.length > 0 : true)
  ).length;

  return (
    <Box>
      {/* Page Header */}
      <Box mb={3}>
        <Typography variant="h4" component="h1" gutterBottom fontWeight="600">
          Infringements
        </Typography>
        <Typography variant="body1" color="textSecondary">
          Monitor and manage detected content violations
        </Typography>
      </Box>

      {/* Status Summary */}
      <Box mb={3}>
        <StatusSummary />
      </Box>

      {/* Search and Filter Bar */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                placeholder="Search by URL, platform, or description..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Search color="action" />
                    </InputAdornment>
                  ),
                }}
                variant="outlined"
                size="small"
              />
            </Grid>
            
            <Grid item xs={12} md={6}>
              <Box display="flex" justifyContent="flex-end" gap={1}>
                <Button
                  variant={showFilters ? "contained" : "outlined"}
                  startIcon={<FilterList />}
                  onClick={() => setShowFilters(!showFilters)}
                  color={activeFilterCount > 0 ? "primary" : "inherit"}
                >
                  Filters
                  {activeFilterCount > 0 && (
                    <Chip
                      label={activeFilterCount}
                      size="small"
                      sx={{ ml: 1, height: 20 }}
                    />
                  )}
                </Button>
                
                <Button
                  variant="outlined"
                  startIcon={<Refresh />}
                  onClick={() => refetch()}
                >
                  Refresh
                </Button>
                
                {activeFilterCount > 0 && (
                  <Button
                    variant="text"
                    onClick={handleClearFilters}
                    color="secondary"
                  >
                    Clear All
                  </Button>
                )}
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Filter Panel */}
      {showFilters && (
        <Box mb={3}>
          <FilterPanel
            filters={filters}
            onFiltersChange={handleFilterChange}
          />
        </Box>
      )}

      {/* Active Filters Display */}
      {activeFilterCount > 0 && (
        <Box mb={2}>
          <Box display="flex" flexWrap="wrap" gap={1}>
            {filters.status?.map(status => (
              <Chip
                key={status}
                label={`Status: ${status}`}
                onDelete={() => {
                  const newStatus = filters.status?.filter(s => s !== status);
                  handleFilterChange({ ...filters, status: newStatus });
                }}
                color="primary"
                variant="outlined"
                size="small"
              />
            ))}
            {filters.platform?.map(platform => (
              <Chip
                key={platform}
                label={`Platform: ${platform}`}
                onDelete={() => {
                  const newPlatforms = filters.platform?.filter(p => p !== platform);
                  handleFilterChange({ ...filters, platform: newPlatforms });
                }}
                color="primary"
                variant="outlined"
                size="small"
              />
            ))}
            {filters.contentType?.map(type => (
              <Chip
                key={type}
                label={`Type: ${type}`}
                onDelete={() => {
                  const newTypes = filters.contentType?.filter(t => t !== type);
                  handleFilterChange({ ...filters, contentType: newTypes });
                }}
                color="primary"
                variant="outlined"
                size="small"
              />
            ))}
          </Box>
        </Box>
      )}

      {/* Error Display */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          Failed to load infringements. Please try again.
        </Alert>
      )}

      {/* Infringements Table */}
      <Card>
        <InfringementTable
          data={infringementsData}
          isLoading={isLoading}
          page={page}
          onPageChange={handlePageChange}
          onRefresh={refetch}
        />
      </Card>
    </Box>
  );
};

export default InfringementsPage;