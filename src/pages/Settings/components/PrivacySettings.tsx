import React, { useState } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  FormControlLabel,
  Switch,
  Button,
  Grid,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  Divider,
} from '@mui/material';
import {
  Shield,
  Download,
  Delete,
  Warning,
} from '@mui/icons-material';
import { useMutation } from '@tanstack/react-query';
import { useSnackbar } from 'notistack';

interface PrivacySettingsData {
  profileVisible: boolean;
  shareAnalytics: boolean;
  marketingEmails: boolean;
  thirdPartyIntegrations: boolean;
  dataRetention: boolean;
  activityLogging: boolean;
}

const PrivacySettings: React.FC = () => {
  const { enqueueSnackbar } = useSnackbar();
  const [deleteDialog, setDeleteDialog] = useState(false);
  const [exportDialog, setExportDialog] = useState(false);
  
  const [settings, setSettings] = useState<PrivacySettingsData>({
    profileVisible: false,
    shareAnalytics: false,
    marketingEmails: true,
    thirdPartyIntegrations: false,
    dataRetention: true,
    activityLogging: true,
  });

  const saveSettingsMutation = useMutation({
    mutationFn: (data: PrivacySettingsData) => {
      return new Promise((resolve) => {
        setTimeout(() => resolve({ success: true }), 1000);
      });
    },
    onSuccess: () => {
      enqueueSnackbar('Privacy settings saved successfully', { variant: 'success' });
    },
    onError: () => {
      enqueueSnackbar('Failed to save settings', { variant: 'error' });
    },
  });

  const exportDataMutation = useMutation({
    mutationFn: () => {
      return new Promise((resolve) => {
        setTimeout(() => resolve({ downloadUrl: 'https://example.com/export.zip' }), 2000);
      });
    },
    onSuccess: () => {
      enqueueSnackbar('Data export initiated. You\'ll receive a download link via email.', { variant: 'success' });
      setExportDialog(false);
    },
    onError: () => {
      enqueueSnackbar('Failed to export data', { variant: 'error' });
    },
  });

  const deleteAccountMutation = useMutation({
    mutationFn: () => {
      return new Promise((resolve) => {
        setTimeout(() => resolve({ success: true }), 2000);
      });
    },
    onSuccess: () => {
      enqueueSnackbar('Account deletion initiated. You have 30 days to cancel.', { variant: 'info' });
      setDeleteDialog(false);
    },
    onError: () => {
      enqueueSnackbar('Failed to delete account', { variant: 'error' });
    },
  });

  const handleChange = (field: keyof PrivacySettingsData) => {
    setSettings(prev => ({ ...prev, [field]: !prev[field] }));
  };

  const handleSave = () => {
    saveSettingsMutation.mutate(settings);
  };

  const handleExportData = () => {
    exportDataMutation.mutate();
  };

  const handleDeleteAccount = () => {
    deleteAccountMutation.mutate();
  };

  return (
    <Box>
      <Typography variant="h6" gutterBottom fontWeight="600">
        Privacy & Data
      </Typography>
      
      <Typography variant="body2" color="textSecondary" paragraph>
        Control how your data is collected, used, and shared by ContentGuard.
      </Typography>

      <Grid container spacing={3}>
        {/* Privacy Controls */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="subtitle1" fontWeight="600" gutterBottom>
                Privacy Controls
              </Typography>
              
              <Box display="flex" flexDirection="column" gap={2}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.profileVisible}
                      onChange={() => handleChange('profileVisible')}
                    />
                  }
                  label={
                    <Box>
                      <Typography variant="body2" fontWeight="500">
                        Public Profile
                      </Typography>
                      <Typography variant="caption" color="textSecondary">
                        Make your profile visible to other ContentGuard users
                      </Typography>
                    </Box>
                  }
                />

                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.shareAnalytics}
                      onChange={() => handleChange('shareAnalytics')}
                    />
                  }
                  label={
                    <Box>
                      <Typography variant="body2" fontWeight="500">
                        Share Anonymous Analytics
                      </Typography>
                      <Typography variant="caption" color="textSecondary">
                        Help improve ContentGuard by sharing anonymous usage data
                      </Typography>
                    </Box>
                  }
                />

                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.marketingEmails}
                      onChange={() => handleChange('marketingEmails')}
                    />
                  }
                  label={
                    <Box>
                      <Typography variant="body2" fontWeight="500">
                        Marketing Emails
                      </Typography>
                      <Typography variant="caption" color="textSecondary">
                        Receive emails about new features, tips, and promotions
                      </Typography>
                    </Box>
                  }
                />

                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.thirdPartyIntegrations}
                      onChange={() => handleChange('thirdPartyIntegrations')}
                    />
                  }
                  label={
                    <Box>
                      <Typography variant="body2" fontWeight="500">
                        Third-party Integrations
                      </Typography>
                      <Typography variant="caption" color="textSecondary">
                        Allow ContentGuard to connect with external services
                      </Typography>
                    </Box>
                  }
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Data Management */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="subtitle1" fontWeight="600" gutterBottom>
                Data Management
              </Typography>
              
              <Box display="flex" flexDirection="column" gap={2}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.dataRetention}
                      onChange={() => handleChange('dataRetention')}
                    />
                  }
                  label={
                    <Box>
                      <Typography variant="body2" fontWeight="500">
                        Extended Data Retention
                      </Typography>
                      <Typography variant="caption" color="textSecondary">
                        Keep historical data longer for improved detection accuracy
                      </Typography>
                    </Box>
                  }
                />

                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.activityLogging}
                      onChange={() => handleChange('activityLogging')}
                    />
                  }
                  label={
                    <Box>
                      <Typography variant="body2" fontWeight="500">
                        Activity Logging
                      </Typography>
                      <Typography variant="caption" color="textSecondary">
                        Log account activity for security and audit purposes
                      </Typography>
                    </Box>
                  }
                />
              </Box>

              <Button
                variant="contained"
                startIcon={saveSettingsMutation.isPending ? 
                  <div className="loading-spinner" /> : <Shield />}
                onClick={handleSave}
                disabled={saveSettingsMutation.isPending}
                sx={{ mt: 2 }}
              >
                {saveSettingsMutation.isPending ? 'Saving...' : 'Save Privacy Settings'}
              </Button>
            </CardContent>
          </Card>
        </Grid>

        {/* Data Export */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="subtitle1" fontWeight="600" gutterBottom>
                Data Export
              </Typography>
              
              <Typography variant="body2" color="textSecondary" paragraph>
                Download a copy of all your data stored in ContentGuard, including submissions, 
                infringements, and account information.
              </Typography>

              <Button
                variant="outlined"
                startIcon={<Download />}
                onClick={() => setExportDialog(true)}
              >
                Request Data Export
              </Button>
            </CardContent>
          </Card>
        </Grid>

        {/* Account Deletion */}
        <Grid item xs={12}>
          <Card sx={{ borderColor: 'error.main', borderWidth: 1 }}>
            <CardContent>
              <Typography variant="subtitle1" fontWeight="600" gutterBottom color="error">
                Delete Account
              </Typography>
              
              <Alert severity="warning" sx={{ mb: 2 }}>
                <Typography variant="body2">
                  <strong>Warning:</strong> This action cannot be undone. All your data, 
                  monitoring settings, and subscription will be permanently deleted.
                </Typography>
              </Alert>

              <Button
                variant="outlined"
                color="error"
                startIcon={<Delete />}
                onClick={() => setDeleteDialog(true)}
              >
                Delete My Account
              </Button>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Data Export Dialog */}
      <Dialog open={exportDialog} onClose={() => setExportDialog(false)}>
        <DialogTitle>Export Your Data</DialogTitle>
        <DialogContent>
          <Typography variant="body2" gutterBottom>
            We'll prepare a comprehensive export of your ContentGuard data including:
          </Typography>
          
          <List>
            <ListItem>
              <ListItemText primary="Account information and profile" />
            </ListItem>
            <ListItem>
              <ListItemText primary="All submitted URLs and monitoring settings" />
            </ListItem>
            <ListItem>
              <ListItemText primary="Detected infringements and their status" />
            </ListItem>
            <ListItem>
              <ListItemText primary="Activity logs and usage history" />
            </ListItem>
            <ListItem>
              <ListItemText primary="Billing and subscription information" />
            </ListItem>
          </List>

          <Alert severity="info" sx={{ mt: 2 }}>
            The export process may take up to 24 hours for large datasets. 
            You'll receive a secure download link via email.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setExportDialog(false)}>
            Cancel
          </Button>
          <Button 
            variant="contained" 
            onClick={handleExportData}
            disabled={exportDataMutation.isPending}
          >
            {exportDataMutation.isPending ? 'Processing...' : 'Start Export'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Account Deletion Dialog */}
      <Dialog open={deleteDialog} onClose={() => setDeleteDialog(false)}>
        <DialogTitle sx={{ color: 'error.main' }}>
          <Warning sx={{ mr: 1 }} />
          Delete Account
        </DialogTitle>
        <DialogContent>
          <Alert severity="error" sx={{ mb: 2 }}>
            <Typography variant="body2" gutterBottom>
              <strong>This action is irreversible!</strong>
            </Typography>
            <Typography variant="body2">
              Once deleted, you will lose access to all your data, monitoring, and protection services.
            </Typography>
          </Alert>

          <Typography variant="body2" gutterBottom>
            Account deletion will:
          </Typography>
          
          <List>
            <ListItem>
              <ListItemText 
                primary="Permanently delete all your content monitoring" 
                secondary="Your protected URLs will no longer be monitored"
              />
            </ListItem>
            <ListItem>
              <ListItemText 
                primary="Remove all infringement data and history" 
                secondary="Past detections and takedown records will be lost"
              />
            </ListItem>
            <ListItem>
              <ListItemText 
                primary="Cancel your subscription immediately" 
                secondary="No refunds will be issued for remaining subscription time"
              />
            </ListItem>
            <ListItem>
              <ListItemText 
                primary="Delete your account profile and settings" 
                secondary="You'll need to create a new account to use ContentGuard again"
              />
            </ListItem>
          </List>

          <Alert severity="info" sx={{ mt: 2 }}>
            You have 30 days to cancel the deletion by contacting support. 
            After 30 days, the deletion will be final.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialog(false)}>
            Keep My Account
          </Button>
          <Button 
            variant="contained" 
            color="error"
            onClick={handleDeleteAccount}
            disabled={deleteAccountMutation.isPending}
          >
            {deleteAccountMutation.isPending ? 'Deleting...' : 'Yes, Delete My Account'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default PrivacySettings;