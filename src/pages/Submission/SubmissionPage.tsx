import React, { useState } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Alert,
  Tab,
  Tabs,
} from '@mui/material';
import {
  CloudUpload,
  List,
  History,
} from '@mui/icons-material';
import URLSubmissionForm from './components/URLSubmissionForm';
import BulkUpload from './components/BulkUpload';
import SubmissionHistory from './components/SubmissionHistory';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => (
  <div
    role="tabpanel"
    hidden={value !== index}
    id={`submission-tabpanel-${index}`}
    aria-labelledby={`submission-tab-${index}`}
  >
    {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
  </div>
);

const SubmissionPage: React.FC = () => {
  const [currentTab, setCurrentTab] = useState(0);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
  };

  return (
    <Box>
      {/* Page Header */}
      <Box mb={3}>
        <Typography variant="h4" component="h1" gutterBottom fontWeight="600">
          Submit Content
        </Typography>
        <Typography variant="body1" color="textSecondary">
          Submit URLs for protection monitoring or report infringements
        </Typography>
      </Box>

      {/* Information Alert */}
      <Alert severity="info" sx={{ mb: 3 }}>
        <Typography variant="body2" gutterBottom>
          <strong>How it works:</strong>
        </Typography>
        <Typography variant="body2" component="div">
          • Submit URLs of your original content for monitoring<br/>
          • Our AI will scan for unauthorized copies across platforms<br/>
          • Receive notifications when infringements are detected<br/>
          • Automated takedown requests can be sent on your behalf
        </Typography>
      </Alert>

      {/* Main Content Card */}
      <Card>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs
            value={currentTab}
            onChange={handleTabChange}
            aria-label="submission tabs"
          >
            <Tab
              icon={<CloudUpload />}
              label="Single URL"
              id="submission-tab-0"
              aria-controls="submission-tabpanel-0"
            />
            <Tab
              icon={<List />}
              label="Bulk Upload"
              id="submission-tab-1"
              aria-controls="submission-tabpanel-1"
            />
            <Tab
              icon={<History />}
              label="History"
              id="submission-tab-2"
              aria-controls="submission-tabpanel-2"
            />
          </Tabs>
        </Box>

        <CardContent>
          <TabPanel value={currentTab} index={0}>
            <URLSubmissionForm />
          </TabPanel>
          
          <TabPanel value={currentTab} index={1}>
            <BulkUpload />
          </TabPanel>
          
          <TabPanel value={currentTab} index={2}>
            <SubmissionHistory />
          </TabPanel>
        </CardContent>
      </Card>

      {/* Help Section */}
      <Grid container spacing={3} sx={{ mt: 2 }}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom fontWeight="600">
                Supported Platforms
              </Typography>
              <Typography variant="body2" color="textSecondary" paragraph>
                We monitor content across major platforms including:
              </Typography>
              <Box component="ul" sx={{ pl: 2, m: 0 }}>
                <li>YouTube</li>
                <li>Instagram</li>
                <li>TikTok</li>
                <li>Facebook</li>
                <li>Twitter</li>
                <li>And many more...</li>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom fontWeight="600">
                Content Types
              </Typography>
              <Typography variant="body2" color="textSecondary" paragraph>
                We can protect various types of content:
              </Typography>
              <Box component="ul" sx={{ pl: 2, m: 0 }}>
                <li>Videos and animations</li>
                <li>Images and artwork</li>
                <li>Music and audio</li>
                <li>Written content</li>
                <li>Brand assets</li>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default SubmissionPage;