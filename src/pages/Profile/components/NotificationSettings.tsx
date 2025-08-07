import React, { useState } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  FormControlLabel,
  Switch,
  Grid,
  Button,
  Divider,
  Alert,
} from '@mui/material';
import { Save } from '@mui/icons-material';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useSnackbar } from 'notistack';
import { apiService } from '@services/api';
import { AccountSettings } from '@types/index';

const NotificationSettings: React.FC = () => {
  const { enqueueSnackbar } = useSnackbar();

  // Fetch current notification settings
  const { data: settingsData, isLoading } = useQuery({
    queryKey: ['account-settings'],
    queryFn: () => apiService.getAccountSettings(),
  });

  // Default settings if API call fails
  const [settings, setSettings] = useState<AccountSettings>({
    notifications: {
      email: true,
      push: true,
      sms: false,
    },
    monitoring: {
      autoTakedown: false,
      sensitivity: 'medium',
      platforms: ['youtube', 'instagram'],
    },
    privacy: {
      profileVisible: false,
      shareAnalytics: false,
    },
  });

  React.useEffect(() => {
    if (settingsData?.data) {
      setSettings(settingsData.data);
    }
  }, [settingsData]);

  const updateSettingsMutation = useMutation({
    mutationFn: (newSettings: AccountSettings) => 
      apiService.updateAccountSettings(newSettings),
    onSuccess: () => {
      enqueueSnackbar('Notification settings saved', { variant: 'success' });
    },
    onError: () => {
      enqueueSnackbar('Failed to save settings', { variant: 'error' });
    },
  });

  const handleNotificationChange = (type: keyof AccountSettings['notifications']) => {
    setSettings(prev => ({
      ...prev,
      notifications: {
        ...prev.notifications,
        [type]: !prev.notifications[type],
      },
    }));
  };

  const handleMonitoringChange = (setting: keyof AccountSettings['monitoring'], value: any) => {
    setSettings(prev => ({
      ...prev,
      monitoring: {
        ...prev.monitoring,
        [setting]: value,
      },
    }));
  };

  const handlePrivacyChange = (setting: keyof AccountSettings['privacy']) => {
    setSettings(prev => ({
      ...prev,
      privacy: {
        ...prev.privacy,
        [setting]: !prev.privacy[setting],
      },
    }));
  };

  const handleSave = () => {
    updateSettingsMutation.mutate(settings);
  };

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
        <div className="loading-spinner" />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h6" fontWeight="600" gutterBottom>
        Notification Preferences
      </Typography>

      {/* Email Notifications */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="subtitle1" fontWeight="600" gutterBottom>
            Email Notifications
          </Typography>
          
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.notifications.email}
                    onChange={() => handleNotificationChange('email')}
                  />
                }
                label={
                  <Box>
                    <Typography variant="body2" fontWeight="500">
                      Email Notifications
                    </Typography>
                    <Typography variant="caption" color="textSecondary">
                      Receive email alerts for important events
                    </Typography>
                  </Box>
                }
              />
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Push Notifications */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="subtitle1" fontWeight="600" gutterBottom>
            Push Notifications
          </Typography>
          
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.notifications.push}
                    onChange={() => handleNotificationChange('push')}
                  />
                }
                label={
                  <Box>
                    <Typography variant="body2" fontWeight="500">
                      Browser Push Notifications
                    </Typography>
                    <Typography variant="caption" color="textSecondary">
                      Get instant notifications in your browser
                    </Typography>
                  </Box>
                }
              />
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* SMS Notifications */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="subtitle1" fontWeight="600" gutterBottom>
            SMS Notifications
          </Typography>
          
          <Alert severity="info" sx={{ mb: 2 }}>
            SMS notifications are available for Pro and Enterprise plans only.
          </Alert>
          
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.notifications.sms}
                    onChange={() => handleNotificationChange('sms')}
                    disabled={true} // Disabled for demo
                  />
                }
                label={
                  <Box>
                    <Typography variant="body2" fontWeight="500">
                      SMS Alerts
                    </Typography>
                    <Typography variant="caption" color="textSecondary">
                      Critical alerts via SMS (Pro plan required)
                    </Typography>
                  </Box>
                }
              />
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Monitoring Settings */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="subtitle1" fontWeight="600" gutterBottom>
            Monitoring Preferences
          </Typography>
          
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.monitoring.autoTakedown}
                    onChange={() => handleMonitoringChange('autoTakedown', !settings.monitoring.autoTakedown)}
                  />
                }
                label={
                  <Box>
                    <Typography variant="body2" fontWeight="500">
                      Automatic Takedown Requests
                    </Typography>
                    <Typography variant="caption" color="textSecondary">
                      Automatically send DMCA requests for high-confidence matches
                    </Typography>
                  </Box>
                }
              />
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Privacy Settings */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="subtitle1" fontWeight="600" gutterBottom>
            Privacy Settings
          </Typography>
          
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.privacy.profileVisible}
                    onChange={() => handlePrivacyChange('profileVisible')}
                  />
                }
                label={
                  <Box>
                    <Typography variant="body2" fontWeight="500">
                      Public Profile
                    </Typography>
                    <Typography variant="caption" color="textSecondary">
                      Make your profile visible to other users
                    </Typography>
                  </Box>
                }
              />
            </Grid>
            
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.privacy.shareAnalytics}
                    onChange={() => handlePrivacyChange('shareAnalytics')}
                  />
                }
                label={
                  <Box>
                    <Typography variant="body2" fontWeight="500">
                      Share Anonymous Analytics
                    </Typography>
                    <Typography variant="caption" color="textSecondary">
                      Help improve our service by sharing usage data
                    </Typography>
                  </Box>
                }
              />
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <Divider sx={{ my: 3 }} />

      {/* Save Button */}
      <Box display="flex" justifyContent="flex-end">
        <Button
          variant="contained"
          startIcon={updateSettingsMutation.isPending ? 
            <div className="loading-spinner" /> : <Save />}
          onClick={handleSave}
          disabled={updateSettingsMutation.isPending}
        >
          {updateSettingsMutation.isPending ? 'Saving...' : 'Save Settings'}
        </Button>
      </Box>
    </Box>
  );
};

export default NotificationSettings;