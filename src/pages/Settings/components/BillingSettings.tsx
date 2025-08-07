import React, { useState } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
} from '@mui/material';
import {
  CreditCard,
  Receipt,
  Upgrade,
  Download,
  Check,
  Star,
} from '@mui/icons-material';
import { useAuth } from '@hooks/useAuth';

// Mock billing data
const mockInvoices = [
  {
    id: 'INV-2024-001',
    date: '2024-01-01',
    amount: 29.99,
    status: 'paid',
    plan: 'Pro Monthly',
  },
  {
    id: 'INV-2023-012',
    date: '2023-12-01',
    amount: 29.99,
    status: 'paid',
    plan: 'Pro Monthly',
  },
  {
    id: 'INV-2023-011',
    date: '2023-11-01',
    amount: 29.99,
    status: 'paid',
    plan: 'Pro Monthly',
  },
];

const plans = [
  {
    name: 'Free',
    price: 0,
    period: 'Forever',
    features: [
      '5 URLs monitored',
      'Basic detection',
      'Email notifications',
      'Community support',
    ],
    current: false,
  },
  {
    name: 'Pro',
    price: 29.99,
    period: 'per month',
    features: [
      '100 URLs monitored',
      'Advanced AI detection',
      'Real-time alerts',
      'Automated takedowns',
      'Priority support',
      'Detailed analytics',
    ],
    current: true,
    popular: true,
  },
  {
    name: 'Enterprise',
    price: 99.99,
    period: 'per month',
    features: [
      'Unlimited URLs',
      'Custom AI models',
      'API access',
      'Dedicated support',
      'White-label options',
      'Advanced integrations',
      'SLA guarantees',
    ],
    current: false,
  },
];

const BillingSettings: React.FC = () => {
  const { user } = useAuth();
  const [upgradeDialog, setUpgradeDialog] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null);

  const handleUpgrade = (planName: string) => {
    setSelectedPlan(planName);
    setUpgradeDialog(true);
  };

  const handleDownloadInvoice = (invoiceId: string) => {
    // In a real app, this would download the actual invoice
    console.log('Downloading invoice:', invoiceId);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'paid':
        return 'success';
      case 'pending':
        return 'warning';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  return (
    <Box>
      <Typography variant="h6" gutterBottom fontWeight="600">
        Billing & Subscription
      </Typography>
      
      <Typography variant="body2" color="textSecondary" paragraph>
        Manage your subscription, billing information, and invoices.
      </Typography>

      <Grid container spacing={3}>
        {/* Current Plan */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="subtitle1" fontWeight="600" gutterBottom>
                Current Plan
              </Typography>
              
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Box>
                  <Typography variant="h5" fontWeight="600">
                    {user?.subscription === 'free' ? 'Free Plan' : 'Pro Plan'}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    {user?.subscription === 'free' 
                      ? 'Basic content protection' 
                      : 'Advanced protection with automated takedowns'
                    }
                  </Typography>
                </Box>
                
                {user?.subscription === 'free' && (
                  <Button
                    variant="contained"
                    startIcon={<Upgrade />}
                    onClick={() => handleUpgrade('Pro')}
                  >
                    Upgrade Now
                  </Button>
                )}
              </Box>

              {user?.subscription !== 'free' && (
                <Alert severity="info" sx={{ mt: 2 }}>
                  Your next billing cycle starts on January 15, 2024. 
                  You can cancel or modify your subscription at any time.
                </Alert>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Available Plans */}
        <Grid item xs={12}>
          <Typography variant="subtitle1" fontWeight="600" gutterBottom>
            Available Plans
          </Typography>
          
          <Grid container spacing={2}>
            {plans.map((plan) => (
              <Grid item xs={12} md={4} key={plan.name}>
                <Card
                  sx={{
                    position: 'relative',
                    height: '100%',
                    border: plan.current ? 2 : 1,
                    borderColor: plan.current ? 'primary.main' : 'divider',
                  }}
                >
                  {plan.popular && (
                    <Chip
                      label="Most Popular"
                      color="primary"
                      size="small"
                      icon={<Star />}
                      sx={{
                        position: 'absolute',
                        top: -8,
                        left: '50%',
                        transform: 'translateX(-50%)',
                      }}
                    />
                  )}
                  
                  <CardContent sx={{ textAlign: 'center', height: '100%', display: 'flex', flexDirection: 'column' }}>
                    <Typography variant="h5" fontWeight="600" gutterBottom>
                      {plan.name}
                    </Typography>
                    
                    <Typography variant="h3" fontWeight="700" color="primary">
                      ${plan.price}
                    </Typography>
                    
                    <Typography variant="body2" color="textSecondary" gutterBottom>
                      {plan.period}
                    </Typography>

                    <List sx={{ flex: 1, py: 2 }}>
                      {plan.features.map((feature, index) => (
                        <ListItem key={index} sx={{ py: 0.5 }}>
                          <ListItemIcon sx={{ minWidth: 32 }}>
                            <Check color="primary" fontSize="small" />
                          </ListItemIcon>
                          <ListItemText
                            primary={feature}
                            primaryTypographyProps={{ variant: 'body2' }}
                          />
                        </ListItem>
                      ))}
                    </List>

                    {plan.current ? (
                      <Chip label="Current Plan" color="primary" />
                    ) : (
                      <Button
                        variant={plan.popular ? 'contained' : 'outlined'}
                        onClick={() => handleUpgrade(plan.name)}
                        fullWidth
                      >
                        {plan.price === 0 ? 'Downgrade' : 'Upgrade'}
                      </Button>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Grid>

        {/* Billing History */}
        {user?.subscription !== 'free' && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                  <Typography variant="subtitle1" fontWeight="600">
                    Billing History
                  </Typography>
                  <Button
                    variant="outlined"
                    startIcon={<Receipt />}
                    size="small"
                  >
                    View All
                  </Button>
                </Box>

                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Invoice</TableCell>
                        <TableCell>Date</TableCell>
                        <TableCell>Plan</TableCell>
                        <TableCell>Amount</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell>Action</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {mockInvoices.map((invoice) => (
                        <TableRow key={invoice.id}>
                          <TableCell>{invoice.id}</TableCell>
                          <TableCell>
                            {new Date(invoice.date).toLocaleDateString()}
                          </TableCell>
                          <TableCell>{invoice.plan}</TableCell>
                          <TableCell>${invoice.amount}</TableCell>
                          <TableCell>
                            <Chip
                              label={invoice.status}
                              size="small"
                              color={getStatusColor(invoice.status) as any}
                              sx={{ textTransform: 'capitalize' }}
                            />
                          </TableCell>
                          <TableCell>
                            <Button
                              size="small"
                              startIcon={<Download />}
                              onClick={() => handleDownloadInvoice(invoice.id)}
                            >
                              Download
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Payment Method */}
        {user?.subscription !== 'free' && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="subtitle1" fontWeight="600" gutterBottom>
                  Payment Method
                </Typography>
                
                <Box display="flex" alignItems="center" gap={2}>
                  <CreditCard color="primary" />
                  <Box>
                    <Typography variant="body2" fontWeight="500">
                      •••• •••• •••• 4242
                    </Typography>
                    <Typography variant="caption" color="textSecondary">
                      Expires 12/2025
                    </Typography>
                  </Box>
                  <Button variant="outlined" size="small" sx={{ ml: 'auto' }}>
                    Update
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>

      {/* Upgrade Dialog */}
      <Dialog open={upgradeDialog} onClose={() => setUpgradeDialog(false)}>
        <DialogTitle>
          Upgrade to {selectedPlan} Plan
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" gutterBottom>
            You're about to upgrade to the {selectedPlan} plan. This will give you access to:
          </Typography>
          
          {selectedPlan && (
            <List>
              {plans.find(p => p.name === selectedPlan)?.features.map((feature, index) => (
                <ListItem key={index}>
                  <ListItemIcon>
                    <Check color="primary" />
                  </ListItemIcon>
                  <ListItemText primary={feature} />
                </ListItem>
              ))}
            </List>
          )}
          
          <Alert severity="info" sx={{ mt: 2 }}>
            Your new plan will be active immediately, and you'll be charged pro-rata for the current billing period.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUpgradeDialog(false)}>
            Cancel
          </Button>
          <Button variant="contained" onClick={() => setUpgradeDialog(false)}>
            Confirm Upgrade
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default BillingSettings;