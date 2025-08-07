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
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Chip,
  Paper,
} from '@mui/material';
import {
  Add,
  ContentCopy,
  Delete,
  Visibility,
  VisibilityOff,
  Code,
  Key,
} from '@mui/icons-material';
import { useSnackbar } from 'notistack';
import { useAuth } from '@hooks/useAuth';

interface APIKey {
  id: string;
  name: string;
  key: string;
  permissions: string[];
  created: string;
  lastUsed?: string;
  active: boolean;
}

const mockAPIKeys: APIKey[] = [
  {
    id: '1',
    name: 'Production API',
    key: 'cg_live_1234567890abcdef1234567890abcdef',
    permissions: ['read', 'write'],
    created: '2024-01-01',
    lastUsed: '2024-01-10',
    active: true,
  },
  {
    id: '2',
    name: 'Development Testing',
    key: 'cg_test_abcdef1234567890abcdef1234567890',
    permissions: ['read'],
    created: '2024-01-05',
    active: true,
  },
];

const APISettings: React.FC = () => {
  const { user } = useAuth();
  const { enqueueSnackbar } = useSnackbar();
  const [apiKeys, setApiKeys] = useState<APIKey[]>(mockAPIKeys);
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [createDialog, setCreateDialog] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');

  const handleCopyKey = (key: string) => {
    navigator.clipboard.writeText(key);
    enqueueSnackbar('API key copied to clipboard', { variant: 'success' });
  };

  const toggleKeyVisibility = (keyId: string) => {
    setShowKeys(prev => ({ ...prev, [keyId]: !prev[keyId] }));
  };

  const handleCreateKey = () => {
    if (!newKeyName.trim()) {
      enqueueSnackbar('Please enter a name for the API key', { variant: 'warning' });
      return;
    }

    const newKey: APIKey = {
      id: Date.now().toString(),
      name: newKeyName,
      key: `cg_live_${Math.random().toString(36).substring(2, 34)}`,
      permissions: ['read', 'write'],
      created: new Date().toISOString().split('T')[0],
      active: true,
    };

    setApiKeys(prev => [...prev, newKey]);
    setCreateDialog(false);
    setNewKeyName('');
    enqueueSnackbar('API key created successfully', { variant: 'success' });
  };

  const handleDeleteKey = (keyId: string) => {
    setApiKeys(prev => prev.filter(key => key.id !== keyId));
    enqueueSnackbar('API key deleted', { variant: 'success' });
  };

  const maskKey = (key: string) => {
    return key.substring(0, 12) + '•'.repeat(20) + key.substring(key.length - 4);
  };

  if (user?.subscription === 'free') {
    return (
      <Box>
        <Typography variant="h6" gutterBottom fontWeight="600">
          API Access
        </Typography>
        
        <Alert severity="info" sx={{ mb: 3 }}>
          <Typography variant="body2" gutterBottom>
            <strong>API access is available for Pro and Enterprise plans.</strong>
          </Typography>
          <Typography variant="body2">
            Upgrade your plan to access our powerful API for automated content protection and monitoring.
          </Typography>
          <Button
            variant="contained"
            size="small"
            sx={{ mt: 2 }}
            onClick={() => window.location.href = '/settings?tab=3'}
          >
            Upgrade Now
          </Button>
        </Alert>

        <Card>
          <CardContent>
            <Typography variant="subtitle1" fontWeight="600" gutterBottom>
              API Features (Available with Upgrade)
            </Typography>
            
            <Box component="ul" sx={{ pl: 2 }}>
              <li>Submit URLs programmatically</li>
              <li>Retrieve infringement data</li>
              <li>Automate takedown processes</li>
              <li>Real-time webhook notifications</li>
              <li>Bulk operations</li>
              <li>Custom integrations</li>
            </Box>
          </CardContent>
        </Card>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h6" gutterBottom fontWeight="600">
        API Access
      </Typography>
      
      <Typography variant="body2" color="textSecondary" paragraph>
        Manage your API keys and access tokens for programmatic access to ContentGuard.
      </Typography>

      <Grid container spacing={3}>
        {/* API Keys */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="subtitle1" fontWeight="600">
                  API Keys
                </Typography>
                <Button
                  variant="contained"
                  startIcon={<Add />}
                  onClick={() => setCreateDialog(true)}
                >
                  Create New Key
                </Button>
              </Box>

              {apiKeys.length === 0 ? (
                <Alert severity="info">
                  No API keys created yet. Create your first API key to get started.
                </Alert>
              ) : (
                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Name</TableCell>
                        <TableCell>Key</TableCell>
                        <TableCell>Permissions</TableCell>
                        <TableCell>Created</TableCell>
                        <TableCell>Last Used</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell>Actions</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {apiKeys.map((apiKey) => (
                        <TableRow key={apiKey.id}>
                          <TableCell>{apiKey.name}</TableCell>
                          <TableCell>
                            <Box display="flex" alignItems="center" gap={1}>
                              <Typography variant="body2" fontFamily="monospace">
                                {showKeys[apiKey.id] ? apiKey.key : maskKey(apiKey.key)}
                              </Typography>
                              <IconButton
                                size="small"
                                onClick={() => toggleKeyVisibility(apiKey.id)}
                              >
                                {showKeys[apiKey.id] ? <VisibilityOff /> : <Visibility />}
                              </IconButton>
                              <IconButton
                                size="small"
                                onClick={() => handleCopyKey(apiKey.key)}
                              >
                                <ContentCopy />
                              </IconButton>
                            </Box>
                          </TableCell>
                          <TableCell>
                            <Box display="flex" gap={0.5}>
                              {apiKey.permissions.map(permission => (
                                <Chip
                                  key={permission}
                                  label={permission}
                                  size="small"
                                  variant="outlined"
                                />
                              ))}
                            </Box>
                          </TableCell>
                          <TableCell>
                            {new Date(apiKey.created).toLocaleDateString()}
                          </TableCell>
                          <TableCell>
                            {apiKey.lastUsed 
                              ? new Date(apiKey.lastUsed).toLocaleDateString()
                              : 'Never'
                            }
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={apiKey.active ? 'Active' : 'Inactive'}
                              color={apiKey.active ? 'success' : 'default'}
                              size="small"
                            />
                          </TableCell>
                          <TableCell>
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() => handleDeleteKey(apiKey.id)}
                            >
                              <Delete />
                            </IconButton>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* API Documentation */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="subtitle1" fontWeight="600" gutterBottom>
                API Documentation
              </Typography>
              
              <Typography variant="body2" color="textSecondary" paragraph>
                Get started with our RESTful API to integrate ContentGuard into your applications.
              </Typography>

              <Paper sx={{ p: 2, bgcolor: 'grey.50', mb: 2 }}>
                <Typography variant="body2" fontFamily="monospace" gutterBottom>
                  Base URL: https://api.contentguard.com/v1
                </Typography>
                <Typography variant="body2" fontFamily="monospace">
                  Authentication: Bearer {apiKeys[0]?.key || 'YOUR_API_KEY'}
                </Typography>
              </Paper>

              <Box display="flex" gap={2}>
                <Button
                  variant="outlined"
                  startIcon={<Code />}
                  onClick={() => window.open('/docs/api', '_blank')}
                >
                  View Documentation
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<Key />}
                  onClick={() => window.open('/docs/authentication', '_blank')}
                >
                  Authentication Guide
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Rate Limits */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="subtitle1" fontWeight="600" gutterBottom>
                Rate Limits
              </Typography>
              
              <Grid container spacing={2}>
                <Grid item xs={12} sm={4}>
                  <Box textAlign="center">
                    <Typography variant="h4" fontWeight="700" color="primary">
                      1,000
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      Requests per hour
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Box textAlign="center">
                    <Typography variant="h4" fontWeight="700" color="primary">
                      10,000
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      Requests per day
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Box textAlign="center">
                    <Typography variant="h4" fontWeight="700" color="success.main">
                      0.2%
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      Current usage
                    </Typography>
                  </Box>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Create API Key Dialog */}
      <Dialog open={createDialog} onClose={() => setCreateDialog(false)}>
        <DialogTitle>Create New API Key</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="textSecondary" gutterBottom>
            Give your API key a descriptive name to help you identify its purpose.
          </Typography>
          
          <TextField
            autoFocus
            margin="dense"
            label="API Key Name"
            fullWidth
            variant="outlined"
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
            placeholder="e.g., Production Integration"
          />
          
          <Alert severity="warning" sx={{ mt: 2 }}>
            <Typography variant="body2">
              Keep your API key secure! It will only be shown once after creation.
            </Typography>
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialog(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreateKey}>
            Create Key
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default APISettings;