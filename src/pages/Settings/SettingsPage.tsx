import React, { useState } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Tab,
  Tabs,
  Alert,
} from '@mui/material';
import {
  Settings,
  Security,
  Notifications,
  Payment,
  Api,
  Shield,
} from '@mui/icons-material';
import GeneralSettings from './components/GeneralSettings';
import SecuritySettings from './components/SecuritySettings';
import NotificationSettings from './components/NotificationSettings';
import BillingSettings from './components/BillingSettings';
import APISettings from './components/APISettings';
import PrivacySettings from './components/PrivacySettings';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => (
  <div
    role="tabpanel"
    hidden={value !== index}
    id={`settings-tabpanel-${index}`}
    aria-labelledby={`settings-tab-${index}`}
  >
    {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
  </div>
);

const SettingsPage: React.FC = () => {
  const [currentTab, setCurrentTab] = useState(0);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
  };

  const tabItems = [
    { label: 'General', icon: Settings, component: GeneralSettings },
    { label: 'Security', icon: Security, component: SecuritySettings },
    { label: 'Notifications', icon: Notifications, component: NotificationSettings },
    { label: 'Billing', icon: Payment, component: BillingSettings },
    { label: 'API Access', icon: Api, component: APISettings },
    { label: 'Privacy', icon: Shield, component: PrivacySettings },
  ];

  return (
    <Box>
      {/* Page Header */}
      <Box mb={3}>
        <Typography variant="h4" component="h1" gutterBottom fontWeight="600">
          Settings
        </Typography>
        <Typography variant="body1" color="textSecondary">
          Manage your account preferences and configuration
        </Typography>
      </Box>

      {/* Beta Notice */}
      <Alert severity="info" sx={{ mb: 3 }}>
        <Typography variant="body2">
          <strong>Settings Management:</strong> Configure your ContentGuard experience. 
          Changes are automatically saved and synced across all your devices.
        </Typography>
      </Alert>

      {/* Settings Container */}
      <Grid container spacing={3}>
        {/* Navigation Tabs */}
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent sx={{ p: 0 }}>
              <Tabs
                orientation="vertical"
                variant="scrollable"
                value={currentTab}
                onChange={handleTabChange}
                sx={{
                  borderRight: 1,
                  borderColor: 'divider',
                  '& .MuiTabs-flexContainer': {
                    alignItems: 'stretch',
                  },
                  '& .MuiTab-root': {
                    minHeight: 60,
                    alignItems: 'flex-start',
                    justifyContent: 'flex-start',
                    textAlign: 'left',
                    px: 3,
                    py: 2,
                  },
                }}
              >
                {tabItems.map((item, index) => {
                  const Icon = item.icon;
                  return (
                    <Tab
                      key={index}
                      icon={<Icon sx={{ mr: 2 }} />}
                      label={item.label}
                      id={`settings-tab-${index}`}
                      aria-controls={`settings-tabpanel-${index}`}
                      iconPosition="start"
                    />
                  );
                })}
              </Tabs>
            </CardContent>
          </Card>
        </Grid>

        {/* Settings Content */}
        <Grid item xs={12} md={9}>
          <Card>
            <CardContent>
              {tabItems.map((item, index) => {
                const Component = item.component;
                return (
                  <TabPanel key={index} value={currentTab} index={index}>
                    <Component />
                  </TabPanel>
                );
              })}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default SettingsPage;