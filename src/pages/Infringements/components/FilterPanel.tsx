import React from 'react';
import {
  Card,
  CardContent,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  OutlinedInput,
  Box,
  Typography,
  TextField,
} from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { InfringementFilter } from '@types/index';

interface FilterPanelProps {
  filters: InfringementFilter;
  onFiltersChange: (filters: InfringementFilter) => void;
}

const statusOptions = [
  { value: 'detected', label: 'Detected' },
  { value: 'pending', label: 'Pending' },
  { value: 'reviewing', label: 'Reviewing' },
  { value: 'removed', label: 'Removed' },
  { value: 'failed', label: 'Failed' },
];

const platformOptions = [
  { value: 'youtube', label: 'YouTube' },
  { value: 'instagram', label: 'Instagram' },
  { value: 'tiktok', label: 'TikTok' },
  { value: 'facebook', label: 'Facebook' },
  { value: 'twitter', label: 'Twitter' },
  { value: 'twitch', label: 'Twitch' },
];

const contentTypeOptions = [
  { value: 'video', label: 'Video' },
  { value: 'image', label: 'Image' },
  { value: 'audio', label: 'Audio' },
  { value: 'text', label: 'Text' },
];

const FilterPanel: React.FC<FilterPanelProps> = ({ filters, onFiltersChange }) => {
  const handleMultiSelectChange = (
    field: keyof InfringementFilter,
    value: string[]
  ) => {
    onFiltersChange({ ...filters, [field]: value });
  };

  const handleDateRangeChange = (field: 'start' | 'end', date: Date | null) => {
    if (!date) {
      const { dateRange, ...newFilters } = filters;
      onFiltersChange(newFilters);
      return;
    }

    const currentRange = filters.dateRange || { start: new Date(), end: new Date() };
    onFiltersChange({
      ...filters,
      dateRange: {
        ...currentRange,
        [field]: date,
      },
    });
  };

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom fontWeight="600">
          Filters
        </Typography>
        
        <Grid container spacing={3}>
          {/* Status Filter */}
          <Grid item xs={12} md={3}>
            <FormControl fullWidth size="small">
              <InputLabel>Status</InputLabel>
              <Select
                multiple
                value={filters.status || []}
                onChange={(e) => handleMultiSelectChange('status', e.target.value as string[])}
                input={<OutlinedInput label="Status" />}
                renderValue={(selected) => (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {selected.map((value) => (
                      <Chip
                        key={value}
                        label={statusOptions.find(opt => opt.value === value)?.label}
                        size="small"
                      />
                    ))}
                  </Box>
                )}
              >
                {statusOptions.map((option) => (
                  <MenuItem key={option.value} value={option.value}>
                    {option.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          {/* Platform Filter */}
          <Grid item xs={12} md={3}>
            <FormControl fullWidth size="small">
              <InputLabel>Platform</InputLabel>
              <Select
                multiple
                value={filters.platform || []}
                onChange={(e) => handleMultiSelectChange('platform', e.target.value as string[])}
                input={<OutlinedInput label="Platform" />}
                renderValue={(selected) => (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {selected.map((value) => (
                      <Chip
                        key={value}
                        label={platformOptions.find(opt => opt.value === value)?.label}
                        size="small"
                      />
                    ))}
                  </Box>
                )}
              >
                {platformOptions.map((option) => (
                  <MenuItem key={option.value} value={option.value}>
                    {option.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          {/* Content Type Filter */}
          <Grid item xs={12} md={3}>
            <FormControl fullWidth size="small">
              <InputLabel>Content Type</InputLabel>
              <Select
                multiple
                value={filters.contentType || []}
                onChange={(e) => handleMultiSelectChange('contentType', e.target.value as string[])}
                input={<OutlinedInput label="Content Type" />}
                renderValue={(selected) => (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {selected.map((value) => (
                      <Chip
                        key={value}
                        label={contentTypeOptions.find(opt => opt.value === value)?.label}
                        size="small"
                      />
                    ))}
                  </Box>
                )}
              >
                {contentTypeOptions.map((option) => (
                  <MenuItem key={option.value} value={option.value}>
                    {option.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          {/* Date Range Filters */}
          <Grid item xs={12} md={3}>
            <LocalizationProvider dateAdapter={AdapterDateFns}>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <DatePicker
                  label="From Date"
                  value={filters.dateRange?.start || null}
                  onChange={(date) => handleDateRangeChange('start', date)}
                  slotProps={{
                    textField: {
                      size: 'small',
                      fullWidth: true,
                    },
                  }}
                />
                <DatePicker
                  label="To Date"
                  value={filters.dateRange?.end || null}
                  onChange={(date) => handleDateRangeChange('end', date)}
                  slotProps={{
                    textField: {
                      size: 'small',
                      fullWidth: true,
                    },
                  }}
                />
              </Box>
            </LocalizationProvider>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
};

export default FilterPanel;