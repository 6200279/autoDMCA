import React, { useState } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  TextField,
  Grid,
  Alert,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  Lock,
  Security,
  Smartphone,
  Computer,
  Delete,
  Add,
  Visibility,
  VisibilityOff,
} from '@mui/icons-material';
import { useForm, Controller } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { useMutation } from '@tanstack/react-query';
import { useSnackbar } from 'notistack';
import { apiService } from '@services/api';

// Mock data for active sessions
const activeSessions = [
  {
    id: '1',
    device: 'Chrome on Windows',
    location: 'New York, NY',
    lastActive: '2024-01-15T10:30:00Z',
    current: true,
    icon: Computer,
  },
  {
    id: '2',
    device: 'iPhone Safari',
    location: 'New York, NY',
    lastActive: '2024-01-14T15:20:00Z',
    current: false,
    icon: Smartphone,
  },
];

// Password change schema
const passwordSchema = yup.object().shape({
  currentPassword: yup
    .string()
    .required('Current password is required'),
  newPassword: yup
    .string()
    .min(8, 'Password must be at least 8 characters')
    .matches(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/, 'Password must contain uppercase, lowercase, and number')
    .required('New password is required'),
  confirmPassword: yup
    .string()
    .oneOf([yup.ref('newPassword')], 'Passwords must match')
    .required('Please confirm your password'),
});

interface PasswordFormData {
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
}

const SecuritySettings: React.FC = () => {
  const { enqueueSnackbar } = useSnackbar();
  const [showPasswords, setShowPasswords] = useState({
    current: false,
    new: false,
    confirm: false,
  });
  const [twoFactorDialog, setTwoFactorDialog] = useState(false);

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<PasswordFormData>({
    resolver: yupResolver(passwordSchema),
    defaultValues: {
      currentPassword: '',
      newPassword: '',
      confirmPassword: '',
    },
  });

  const changePasswordMutation = useMutation({
    mutationFn: (data: PasswordFormData) => {
      // This would be an actual API call
      return new Promise((resolve) => {
        setTimeout(() => resolve({ success: true }), 1000);
      });
    },
    onSuccess: () => {
      enqueueSnackbar('Password changed successfully', { variant: 'success' });
      reset();
    },
    onError: () => {
      enqueueSnackbar('Failed to change password', { variant: 'error' });
    },
  });

  const terminateSessionMutation = useMutation({
    mutationFn: (sessionId: string) => {
      // This would be an actual API call
      return new Promise((resolve) => {
        setTimeout(() => resolve({ success: true }), 500);
      });
    },
    onSuccess: () => {
      enqueueSnackbar('Session terminated successfully', { variant: 'success' });
    },
    onError: () => {
      enqueueSnackbar('Failed to terminate session', { variant: 'error' });
    },
  });

  const onSubmit = (data: PasswordFormData) => {
    changePasswordMutation.mutate(data);
  };

  const togglePasswordVisibility = (field: keyof typeof showPasswords) => {
    setShowPasswords(prev => ({
      ...prev,
      [field]: !prev[field],
    }));
  };

  const handleTerminateSession = (sessionId: string) => {
    terminateSessionMutation.mutate(sessionId);
  };

  return (
    <Box>
      <Typography variant="h6" fontWeight="600" gutterBottom>
        Security Settings
      </Typography>

      {/* Password Change Section */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="subtitle1" fontWeight="600" gutterBottom>
            Change Password
          </Typography>
          
          <form onSubmit={handleSubmit(onSubmit)}>
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <Controller
                  name="currentPassword"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      fullWidth
                      label="Current Password"
                      type={showPasswords.current ? 'text' : 'password'}
                      error={!!errors.currentPassword}
                      helperText={errors.currentPassword?.message}
                      InputProps={{
                        endAdornment: (
                          <IconButton
                            onClick={() => togglePasswordVisibility('current')}
                            edge="end"
                          >
                            {showPasswords.current ? <VisibilityOff /> : <Visibility />}
                          </IconButton>
                        ),
                      }}
                    />
                  )}
                />
              </Grid>

              <Grid item xs={12} sm={6}>
                <Controller
                  name="newPassword"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      fullWidth
                      label="New Password"
                      type={showPasswords.new ? 'text' : 'password'}
                      error={!!errors.newPassword}
                      helperText={errors.newPassword?.message}
                      InputProps={{
                        endAdornment: (
                          <IconButton
                            onClick={() => togglePasswordVisibility('new')}
                            edge="end"
                          >
                            {showPasswords.new ? <VisibilityOff /> : <Visibility />}
                          </IconButton>
                        ),
                      }}
                    />
                  )}
                />
              </Grid>

              <Grid item xs={12} sm={6}>
                <Controller
                  name="confirmPassword"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      fullWidth
                      label="Confirm New Password"
                      type={showPasswords.confirm ? 'text' : 'password'}
                      error={!!errors.confirmPassword}
                      helperText={errors.confirmPassword?.message}
                      InputProps={{
                        endAdornment: (
                          <IconButton
                            onClick={() => togglePasswordVisibility('confirm')}
                            edge="end"
                          >
                            {showPasswords.confirm ? <VisibilityOff /> : <Visibility />}
                          </IconButton>
                        ),
                      }}
                    />
                  )}
                />
              </Grid>
            </Grid>

            <Box mt={2}>
              <Button
                type="submit"
                variant="contained"
                startIcon={changePasswordMutation.isPending ? 
                  <div className="loading-spinner" /> : <Lock />}
                disabled={changePasswordMutation.isPending}
              >
                {changePasswordMutation.isPending ? 'Changing...' : 'Change Password'}
              </Button>
            </Box>
          </form>
        </CardContent>
      </Card>

      {/* Two-Factor Authentication */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Box>
              <Typography variant="subtitle1" fontWeight="600" gutterBottom>
                Two-Factor Authentication
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Add an extra layer of security to your account
              </Typography>
            </Box>
            <Button
              variant="outlined"
              startIcon={<Security />}
              onClick={() => setTwoFactorDialog(true)}
            >
              Enable 2FA
            </Button>
          </Box>

          <Alert severity="info">
            Two-factor authentication is not currently enabled for your account.
            We recommend enabling it for enhanced security.
          </Alert>
        </CardContent>
      </Card>

      {/* Active Sessions */}
      <Card>
        <CardContent>
          <Typography variant="subtitle1" fontWeight="600" gutterBottom>
            Active Sessions
          </Typography>
          <Typography variant="body2" color="textSecondary" mb={2}>
            Manage devices that are currently signed in to your account
          </Typography>

          <List>
            {activeSessions.map((session, index) => {
              const Icon = session.icon;
              const lastActive = new Date(session.lastActive).toLocaleDateString();

              return (
                <React.Fragment key={session.id}>
                  <ListItem>
                    <ListItemIcon>
                      <Icon />
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Box display="flex" alignItems="center" gap={1}>
                          {session.device}
                          {session.current && (
                            <Typography
                              variant="caption"
                              sx={{
                                bgcolor: 'success.main',
                                color: 'white',
                                px: 1,
                                py: 0.25,
                                borderRadius: 1,
                                fontSize: '0.7rem',
                              }}
                            >
                              Current
                            </Typography>
                          )}
                        </Box>
                      }
                      secondary={`${session.location} • Last active: ${lastActive}`}
                    />
                    {!session.current && (
                      <ListItemSecondaryAction>
                        <IconButton
                          edge="end"
                          onClick={() => handleTerminateSession(session.id)}
                          color="error"
                        >
                          <Delete />
                        </IconButton>
                      </ListItemSecondaryAction>
                    )}
                  </ListItem>
                  {index < activeSessions.length - 1 && <Divider />}
                </React.Fragment>
              );
            })}
          </List>

          <Box mt={2}>
            <Button
              variant="outlined"
              color="error"
              onClick={() => {
                // Terminate all other sessions
                activeSessions
                  .filter(session => !session.current)
                  .forEach(session => handleTerminateSession(session.id));
              }}
            >
              Terminate All Other Sessions
            </Button>
          </Box>
        </CardContent>
      </Card>

      {/* Two-Factor Setup Dialog */}
      <Dialog
        open={twoFactorDialog}
        onClose={() => setTwoFactorDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Enable Two-Factor Authentication</DialogTitle>
        <DialogContent>
          <Alert severity="info" sx={{ mb: 2 }}>
            Two-factor authentication setup would be implemented here with QR code
            and backup codes generation.
          </Alert>
          <Typography variant="body2">
            This feature is coming soon. You'll be able to set up 2FA using
            authenticator apps like Google Authenticator or Authy.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setTwoFactorDialog(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default SecuritySettings;