import React, { useState } from 'react';
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  Avatar,
  Button,
  Alert,
  Tab,
  Tabs,
} from '@mui/material';
import {
  Person,
  Security,
  Notifications,
  CameraAlt,
} from '@mui/icons-material';
import { useAuth } from '@hooks/useAuth';
import ProfileForm from './components/ProfileForm';
import SecuritySettings from './components/SecuritySettings';
import NotificationSettings from './components/NotificationSettings';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index, ...other }) => (
  <div
    role="tabpanel"
    hidden={value !== index}
    id={`profile-tabpanel-${index}`}
    aria-labelledby={`profile-tab-${index}`}
    {...other}
  >
    {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
  </div>
);

const ProfilePage: React.FC = () => {
  const { user } = useAuth();
  const [currentTab, setCurrentTab] = useState(0);
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
  };

  const handleAvatarChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        setAvatarPreview(e.target?.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  if (!user) {
    return (
      <Box>
        <Alert severity="error">
          Unable to load profile information. Please try refreshing the page.
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      {/* Page Header */}
      <Box mb={4}>
        <Typography variant="h4" component="h1" gutterBottom fontWeight="600">
          Profile
        </Typography>
        <Typography variant="body1" color="textSecondary">
          Manage your account information and preferences
        </Typography>
      </Box>

      <Grid container spacing={3}>
        {/* Profile Summary Card */}
        <Grid item xs={12} lg={4}>
          <Card>
            <CardContent sx={{ textAlign: 'center', py: 4 }}>
              <Box sx={{ position: 'relative', display: 'inline-block', mb: 3 }}>
                <Avatar
                  src={avatarPreview || user.avatar}
                  sx={{
                    width: 120,
                    height: 120,
                    fontSize: '2rem',
                    fontWeight: 600,
                    bgcolor: 'primary.main',
                  }}
                >
                  {user.firstName?.[0]}{user.lastName?.[0]}
                </Avatar>
                
                <input
                  accept="image/*"
                  style={{ display: 'none' }}
                  id="avatar-upload"
                  type="file"
                  onChange={handleAvatarChange}
                />
                <label htmlFor="avatar-upload">
                  <Button
                    component="span"
                    size="small"
                    variant="contained"
                    sx={{
                      position: 'absolute',
                      bottom: 0,
                      right: 0,
                      borderRadius: '50%',
                      minWidth: 36,
                      width: 36,
                      height: 36,
                      p: 0,
                    }}
                  >
                    <CameraAlt fontSize="small" />
                  </Button>
                </label>
              </Box>
              
              <Typography variant="h5" fontWeight="600" gutterBottom>
                {user.firstName} {user.lastName}
              </Typography>
              
              <Typography variant="body2" color="textSecondary" gutterBottom>
                {user.email}
              </Typography>
              
              <Box display="flex" justifyContent="center" gap={1} mt={2}>
                <Button
                  variant="contained"
                  size="small"
                  color={user.subscription === 'pro' ? 'success' : 'primary'}
                  sx={{ textTransform: 'capitalize' }}
                >
                  {user.subscription} Plan
                </Button>
                
                <Button
                  variant="outlined"
                  size="small"
                  color={user.role === 'admin' ? 'secondary' : 'primary'}
                  sx={{ textTransform: 'capitalize' }}
                >
                  {user.role}
                </Button>
              </Box>

              <Box mt={3}>
                <Typography variant="body2" color="textSecondary">
                  Member since {new Date(user.createdAt).toLocaleDateString()}
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  Last active {new Date(user.lastActive).toLocaleDateString()}
                </Typography>
              </Box>
            </CardContent>
          </Card>

          {/* Quick Stats */}
          <Card sx={{ mt: 2 }}>
            <CardContent>
              <Typography variant="h6" fontWeight="600" gutterBottom>
                Quick Stats
              </Typography>
              
              <Box display="flex" justifyContent="space-between" mb={1}>
                <Typography variant="body2" color="textSecondary">
                  Content Protected
                </Typography>
                <Typography variant="body2" fontWeight="600">
                  142 items
                </Typography>
              </Box>
              
              <Box display="flex" justifyContent="space-between" mb={1}>
                <Typography variant="body2" color="textSecondary">
                  Infringements Detected
                </Typography>
                <Typography variant="body2" fontWeight="600" color="error">
                  24 this month
                </Typography>
              </Box>
              
              <Box display="flex" justifyContent="space-between">
                <Typography variant="body2" color="textSecondary">
                  Success Rate
                </Typography>
                <Typography variant="body2" fontWeight="600" color="success.main">
                  96%
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Settings Tabs */}
        <Grid item xs={12} lg={8}>
          <Card>
            <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
              <Tabs
                value={currentTab}
                onChange={handleTabChange}
                aria-label="profile settings tabs"
              >
                <Tab
                  icon={<Person />}
                  label="Personal Info"
                  id="profile-tab-0"
                  aria-controls="profile-tabpanel-0"
                />
                <Tab
                  icon={<Security />}
                  label="Security"
                  id="profile-tab-1"
                  aria-controls="profile-tabpanel-1"
                />
                <Tab
                  icon={<Notifications />}
                  label="Notifications"
                  id="profile-tab-2"
                  aria-controls="profile-tabpanel-2"
                />
              </Tabs>
            </Box>

            <CardContent>
              <TabPanel value={currentTab} index={0}>
                <ProfileForm user={user} avatarPreview={avatarPreview} />
              </TabPanel>
              
              <TabPanel value={currentTab} index={1}>
                <SecuritySettings />
              </TabPanel>
              
              <TabPanel value={currentTab} index={2}>
                <NotificationSettings />
              </TabPanel>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default ProfilePage;