import React, { useState } from 'react';
import {
  Box,
  TextField,
  Button,
  Grid,
  Typography,
  Alert,
  Divider,
} from '@mui/material';
import { Save, Cancel } from '@mui/icons-material';
import { useForm, Controller } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useSnackbar } from 'notistack';
import { apiService } from '@services/api';
import { useAuth } from '@hooks/useAuth';
import { User, ProfileUpdateData } from '@types/index';

// Validation schema
const profileSchema = yup.object().shape({
  firstName: yup
    .string()
    .min(2, 'First name must be at least 2 characters')
    .required('First name is required'),
  lastName: yup
    .string()
    .min(2, 'Last name must be at least 2 characters')
    .required('Last name is required'),
  email: yup
    .string()
    .email('Please enter a valid email address')
    .required('Email is required'),
});

interface ProfileFormProps {
  user: User;
  avatarPreview: string | null;
}

const ProfileForm: React.FC<ProfileFormProps> = ({ user, avatarPreview }) => {
  const { updateUser } = useAuth();
  const queryClient = useQueryClient();
  const { enqueueSnackbar } = useSnackbar();
  const [isEditing, setIsEditing] = useState(false);

  const {
    control,
    handleSubmit,
    formState: { errors, isDirty },
    reset,
  } = useForm<ProfileUpdateData>({
    resolver: yupResolver(profileSchema),
    defaultValues: {
      firstName: user.firstName,
      lastName: user.lastName,
      email: user.email,
    },
  });

  const updateProfileMutation = useMutation({
    mutationFn: (data: ProfileUpdateData) => {
      // Include avatar file if preview exists
      if (avatarPreview && typeof avatarPreview === 'string') {
        // Convert base64 to File object
        fetch(avatarPreview)
          .then(res => res.blob())
          .then(blob => {
            const file = new File([blob], 'avatar.jpg', { type: 'image/jpeg' });
            return apiService.updateProfile({ ...data, avatar: file });
          });
      }
      return apiService.updateProfile(data);
    },
    onSuccess: (response) => {
      const updatedUser = response.data;
      updateUser(updatedUser);
      queryClient.setQueryData(['user-profile'], updatedUser);
      
      enqueueSnackbar('Profile updated successfully', { variant: 'success' });
      setIsEditing(false);
    },
    onError: (error: any) => {
      enqueueSnackbar(
        error.response?.data?.message || 'Failed to update profile',
        { variant: 'error' }
      );
    },
  });

  const onSubmit = async (data: ProfileUpdateData) => {
    updateProfileMutation.mutate(data);
  };

  const handleCancel = () => {
    reset();
    setIsEditing(false);
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h6" fontWeight="600">
          Personal Information
        </Typography>
        {!isEditing && (
          <Button
            variant="outlined"
            onClick={() => setIsEditing(true)}
          >
            Edit Profile
          </Button>
        )}
      </Box>

      <form onSubmit={handleSubmit(onSubmit)}>
        <Grid container spacing={3}>
          <Grid item xs={12} sm={6}>
            <Controller
              name="firstName"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  fullWidth
                  label="First Name"
                  disabled={!isEditing}
                  error={!!errors.firstName}
                  helperText={errors.firstName?.message}
                />
              )}
            />
          </Grid>

          <Grid item xs={12} sm={6}>
            <Controller
              name="lastName"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  fullWidth
                  label="Last Name"
                  disabled={!isEditing}
                  error={!!errors.lastName}
                  helperText={errors.lastName?.message}
                />
              )}
            />
          </Grid>

          <Grid item xs={12}>
            <Controller
              name="email"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  fullWidth
                  label="Email Address"
                  type="email"
                  disabled={!isEditing}
                  error={!!errors.email}
                  helperText={errors.email?.message}
                />
              )}
            />
          </Grid>
        </Grid>

        {isEditing && (
          <>
            <Divider sx={{ my: 3 }} />
            
            <Box display="flex" justifyContent="flex-end" gap={2}>
              <Button
                variant="outlined"
                onClick={handleCancel}
                startIcon={<Cancel />}
              >
                Cancel
              </Button>
              
              <Button
                type="submit"
                variant="contained"
                disabled={!isDirty || updateProfileMutation.isPending}
                startIcon={
                  updateProfileMutation.isPending ? 
                  <div className="loading-spinner" /> : 
                  <Save />
                }
              >
                {updateProfileMutation.isPending ? 'Saving...' : 'Save Changes'}
              </Button>
            </Box>
          </>
        )}
      </form>

      {/* Account Information (Read-only) */}
      <Divider sx={{ my: 4 }} />
      
      <Typography variant="h6" fontWeight="600" gutterBottom>
        Account Information
      </Typography>
      
      <Grid container spacing={3}>
        <Grid item xs={12} sm={6}>
          <TextField
            fullWidth
            label="User ID"
            value={user.id}
            disabled
            helperText="Your unique user identifier"
          />
        </Grid>
        
        <Grid item xs={12} sm={6}>
          <TextField
            fullWidth
            label="Account Type"
            value={`${user.subscription} (${user.role})`}
            disabled
            helperText="Your current subscription and role"
          />
        </Grid>
        
        <Grid item xs={12} sm={6}>
          <TextField
            fullWidth
            label="Member Since"
            value={new Date(user.createdAt).toLocaleDateString()}
            disabled
            helperText="When you joined ContentGuard"
          />
        </Grid>
        
        <Grid item xs={12} sm={6}>
          <TextField
            fullWidth
            label="Last Active"
            value={new Date(user.lastActive).toLocaleDateString()}
            disabled
            helperText="Your last login date"
          />
        </Grid>
      </Grid>

      {/* Upgrade Notice for Free Users */}
      {user.subscription === 'free' && (
        <Alert severity="info" sx={{ mt: 3 }}>
          <Typography variant="body2" gutterBottom>
            Upgrade to Pro for advanced features
          </Typography>
          <Typography variant="body2" color="textSecondary">
            Get unlimited monitoring, priority support, and advanced analytics
          </Typography>
          <Button
            size="small"
            variant="contained"
            sx={{ mt: 1 }}
            onClick={() => window.location.href = '/upgrade'}
          >
            Upgrade Now
          </Button>
        </Alert>
      )}
    </Box>
  );
};

export default ProfileForm;