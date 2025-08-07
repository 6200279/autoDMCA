import React, { useState } from 'react';
import {
  Box,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Switch,
  Button,
  Grid,
  Divider,
  Alert,
  Card,
  CardContent,
} from '@mui/material';
import { Save } from '@mui/icons-material';
import { useMutation } from '@tanstack/react-query';
import { useSnackbar } from 'notistack';

interface GeneralSettingsData {
  language: string;
  timezone: string;
  dateFormat: string;
  theme: string;
  autoRefresh: boolean;
  compactMode: boolean;
  showHelpTips: boolean;
}

const GeneralSettings: React.FC = () => {
  const { enqueueSnackbar } = useSnackbar();
  
  const [settings, setSettings] = useState<GeneralSettingsData>({
    language: 'en',
    timezone: 'UTC',
    dateFormat: 'MM/dd/yyyy',
    theme: 'light',
    autoRefresh: true,
    compactMode: false,
    showHelpTips: true,
  });

  const saveSettingsMutation = useMutation({
    mutationFn: (data: GeneralSettingsData) => {
      // Simulate API call
      return new Promise((resolve) => {
        setTimeout(() => resolve({ success: true }), 1000);
      });
    },
    onSuccess: () => {
      enqueueSnackbar('General settings saved successfully', { variant: 'success' });
    },
    onError: () => {
      enqueueSnackbar('Failed to save settings', { variant: 'error' });
    },
  });

  const handleChange = (field: keyof GeneralSettingsData, value: any) => {
    setSettings(prev => ({ ...prev, [field]: value }));
  };

  const handleSave = () => {
    saveSettingsMutation.mutate(settings);
  };

  return (
    <Box>
      <Typography variant="h6" gutterBottom fontWeight="600">
        General Settings
      </Typography>
      
      <Typography variant="body2" color="textSecondary" paragraph>
        Customize your ContentGuard experience with these general preferences.
      </Typography>

      <Grid container spacing={3}>
        {/* Localization Settings */}
        <Grid item xs={12}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="subtitle1" fontWeight="600" gutterBottom>
                Localization
              </Typography>
              
              <Grid container spacing={2}>
                <Grid item xs={12} sm={4}>
                  <FormControl fullWidth>
                    <InputLabel>Language</InputLabel>
                    <Select
                      value={settings.language}
                      label="Language"
                      onChange={(e) => handleChange('language', e.target.value)}
                    >
                      <MenuItem value="en">English</MenuItem>
                      <MenuItem value="es">Español</MenuItem>
                      <MenuItem value="fr">Français</MenuItem>
                      <MenuItem value="de">Deutsch</MenuItem>
                      <MenuItem value="it">Italiano</MenuItem>
                      <MenuItem value="pt">Português</MenuItem>
                      <MenuItem value="zh">中文</MenuItem>
                      <MenuItem value="ja">日本語</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>

                <Grid item xs={12} sm={4}>
                  <FormControl fullWidth>
                    <InputLabel>Timezone</InputLabel>
                    <Select
                      value={settings.timezone}
                      label="Timezone"
                      onChange={(e) => handleChange('timezone', e.target.value)}
                    >
                      <MenuItem value="UTC">UTC (Coordinated Universal Time)</MenuItem>
                      <MenuItem value="EST">EST (Eastern Standard Time)</MenuItem>
                      <MenuItem value="PST">PST (Pacific Standard Time)</MenuItem>
                      <MenuItem value="GMT">GMT (Greenwich Mean Time)</MenuItem>
                      <MenuItem value="CET">CET (Central European Time)</MenuItem>
                      <MenuItem value="JST">JST (Japan Standard Time)</MenuItem>
                      <MenuItem value="AEST">AEST (Australian Eastern Time)</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>

                <Grid item xs={12} sm={4}>
                  <FormControl fullWidth>
                    <InputLabel>Date Format</InputLabel>
                    <Select
                      value={settings.dateFormat}
                      label="Date Format"
                      onChange={(e) => handleChange('dateFormat', e.target.value)}
                    >
                      <MenuItem value="MM/dd/yyyy">MM/dd/yyyy (US)</MenuItem>
                      <MenuItem value="dd/MM/yyyy">dd/MM/yyyy (EU)</MenuItem>
                      <MenuItem value="yyyy-MM-dd">yyyy-MM-dd (ISO)</MenuItem>
                      <MenuItem value="dd MMM yyyy">dd MMM yyyy</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Appearance Settings */}
        <Grid item xs={12}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="subtitle1" fontWeight="600" gutterBottom>
                Appearance
              </Typography>
              
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth>
                    <InputLabel>Theme</InputLabel>
                    <Select
                      value={settings.theme}
                      label="Theme"
                      onChange={(e) => handleChange('theme', e.target.value)}
                    >
                      <MenuItem value="light">Light</MenuItem>
                      <MenuItem value="dark">Dark</MenuItem>
                      <MenuItem value="system">Follow System</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
              </Grid>

              <Box mt={2}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.compactMode}
                      onChange={(e) => handleChange('compactMode', e.target.checked)}
                    />
                  }
                  label={
                    <Box>
                      <Typography variant="body2" fontWeight="500">
                        Compact Mode
                      </Typography>
                      <Typography variant="caption" color="textSecondary">
                        Use smaller spacing and condensed layouts
                      </Typography>
                    </Box>
                  }
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Behavior Settings */}
        <Grid item xs={12}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="subtitle1" fontWeight="600" gutterBottom>
                Behavior
              </Typography>
              
              <Box display="flex" flexDirection="column" gap={2}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.autoRefresh}
                      onChange={(e) => handleChange('autoRefresh', e.target.checked)}
                    />
                  }
                  label={
                    <Box>
                      <Typography variant="body2" fontWeight="500">
                        Auto-refresh Data
                      </Typography>
                      <Typography variant="caption" color="textSecondary">
                        Automatically refresh dashboard and statistics every 30 seconds
                      </Typography>
                    </Box>
                  }
                />

                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.showHelpTips}
                      onChange={(e) => handleChange('showHelpTips', e.target.checked)}
                    />
                  }
                  label={
                    <Box>
                      <Typography variant="body2" fontWeight="500">
                        Show Help Tips
                      </Typography>
                      <Typography variant="caption" color="textSecondary">
                        Display helpful tooltips and guidance throughout the app
                      </Typography>
                    </Box>
                  }
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Performance Settings */}
        <Grid item xs={12}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="subtitle1" fontWeight="600" gutterBottom>
                Performance
              </Typography>
              
              <Alert severity="info" sx={{ mb: 2 }}>
                <Typography variant="body2">
                  Performance settings help optimize ContentGuard for your device and connection.
                </Typography>
              </Alert>
              
              <Box display="flex" flexDirection="column" gap={1}>
                <Typography variant="body2">
                  <strong>Current Status:</strong>
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  • Auto-refresh: {settings.autoRefresh ? 'Enabled' : 'Disabled'}
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  • Compact mode: {settings.compactMode ? 'Enabled' : 'Disabled'}
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  • Real-time updates: Active
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Save Button */}
        <Grid item xs={12}>
          <Divider sx={{ my: 2 }} />
          
          <Box display="flex" justifyContent="flex-end">
            <Button
              variant="contained"
              startIcon={saveSettingsMutation.isPending ? 
                <div className="loading-spinner" /> : <Save />}
              onClick={handleSave}
              disabled={saveSettingsMutation.isPending}
            >
              {saveSettingsMutation.isPending ? 'Saving...' : 'Save General Settings'}
            </Button>
          </Box>
        </Grid>
      </Grid>
    </Box>
  );
};

export default GeneralSettings;