import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  Grid,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Switch,
  FormControlLabel,
  Alert,
  Chip,
  CircularProgress,
  Divider
} from '@mui/material';
import {
  Check,
  Star,
  Close,
  TrendingUp
} from '@mui/icons-material';

import { billingApi } from '../../services/api';

interface PlanUpgradeModalProps {
  open: boolean;
  onClose: () => void;
  currentPlan?: string;
  onUpgradeComplete: () => void;
}

interface PlanFeature {
  name: string;
  included: boolean;
}

interface Plan {
  plan: string;
  name: string;
  description: string;
  monthlyPrice: number;
  yearlyPrice: number;
  yearlyDiscount: number;
  maxProtectedProfiles: number;
  maxMonthlyScans: number;
  maxTakedownRequests: number;
  aiFaceRecognition: boolean;
  prioritySupport: boolean;
  customBranding: boolean;
  apiAccess: boolean;
  bulkOperations?: boolean;
  advancedAnalytics?: boolean;
  popular?: boolean;
}

const PlanUpgradeModal: React.FC<PlanUpgradeModalProps> = ({
  open,
  onClose,
  currentPlan,
  onUpgradeComplete
}) => {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [upgrading, setUpgrading] = useState(false);
  const [isYearly, setIsYearly] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  const fetchPlans = async () => {
    try {
      setLoading(true);
      const response = await billingApi.getSubscriptionPlans();
      setPlans(response.data);
    } catch (err) {
      console.error('Failed to fetch plans:', err);
      setError('Failed to load subscription plans');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      fetchPlans();
    }
  }, [open]);

  const handleUpgrade = async (planId: string) => {
    setUpgrading(true);
    setError(null);

    try {
      if (currentPlan) {
        // Update existing subscription
        await billingApi.updateSubscription({
          plan: planId,
          interval: isYearly ? 'year' : 'month'
        });
      } else {
        // Create new subscription
        await billingApi.createSubscription({
          plan: planId,
          interval: isYearly ? 'year' : 'month'
        });
      }

      onUpgradeComplete();
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to upgrade subscription');
    } finally {
      setUpgrading(false);
    }
  };

  const getPlanFeatures = (plan: Plan): PlanFeature[] => [
    { name: `${plan.maxProtectedProfiles} Protected Profile${plan.maxProtectedProfiles > 1 ? 's' : ''}`, included: true },
    { name: `${plan.maxMonthlyScans} Monthly Scans`, included: true },
    { name: `${plan.maxTakedownRequests} Takedown Requests`, included: true },
    { name: 'AI Face Recognition', included: plan.aiFaceRecognition },
    { name: 'Priority Support', included: plan.prioritySupport },
    { name: 'Custom Branding', included: plan.customBranding },
    { name: 'API Access', included: plan.apiAccess },
    { name: 'Bulk Operations', included: plan.bulkOperations || false },
    { name: 'Advanced Analytics', included: plan.advancedAnalytics || false }
  ];

  const getPrice = (plan: Plan) => {
    return isYearly ? plan.yearlyPrice : plan.monthlyPrice;
  };

  const getSavings = (plan: Plan) => {
    if (!isYearly) return 0;
    const monthlyTotal = plan.monthlyPrice * 12;
    return monthlyTotal - plan.yearlyPrice;
  };

  const isCurrentPlan = (planId: string) => {
    return currentPlan === planId;
  };

  const isDowngrade = (planId: string) => {
    if (!currentPlan) return false;
    
    const planHierarchy = { 'basic': 1, 'professional': 2, 'enterprise': 3 };
    const currentLevel = planHierarchy[currentPlan as keyof typeof planHierarchy] || 0;
    const targetLevel = planHierarchy[planId as keyof typeof planHierarchy] || 0;
    
    return targetLevel < currentLevel;
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="lg"
      fullWidth
      PaperProps={{
        sx: { minHeight: '70vh' }
      }}
    >
      <DialogTitle>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h5">
            {currentPlan ? 'Change Subscription Plan' : 'Choose Your Plan'}
          </Typography>
          <Button onClick={onClose} sx={{ minWidth: 'auto', p: 1 }}>
            <Close />
          </Button>
        </Box>
      </DialogTitle>

      <DialogContent>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <>
            {error && (
              <Alert severity="error" sx={{ mb: 3 }}>
                {error}
              </Alert>
            )}

            {/* Billing Toggle */}
            <Box sx={{ mb: 4, textAlign: 'center' }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={isYearly}
                    onChange={(e) => setIsYearly(e.target.checked)}
                    color="primary"
                  />
                }
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography>Annual billing</Typography>
                    <Chip label="Save up to 17%" color="success" size="small" />
                  </Box>
                }
              />
            </Box>

            {/* Plans Grid */}
            <Grid container spacing={3}>
              {plans.map((plan) => {
                const features = getPlanFeatures(plan);
                const price = getPrice(plan);
                const savings = getSavings(plan);
                const isCurrent = isCurrentPlan(plan.plan);
                const isDowngradeOption = isDowngrade(plan.plan);

                return (
                  <Grid item xs={12} md={6} key={plan.plan}>
                    <Card
                      sx={{
                        height: '100%',
                        display: 'flex',
                        flexDirection: 'column',
                        position: 'relative',
                        border: selectedPlan === plan.plan ? 2 : 1,
                        borderColor: selectedPlan === plan.plan ? 'primary.main' : 'divider',
                        '&:hover': {
                          borderColor: 'primary.main',
                          cursor: 'pointer'
                        }
                      }}
                      onClick={() => setSelectedPlan(plan.plan)}
                    >
                      {/* Popular Badge */}
                      {plan.plan === 'professional' && (
                        <Box
                          sx={{
                            position: 'absolute',
                            top: -10,
                            left: '50%',
                            transform: 'translateX(-50%)',
                            zIndex: 1
                          }}
                        >
                          <Chip
                            label="Most Popular"
                            color="primary"
                            size="small"
                            icon={<Star />}
                          />
                        </Box>
                      )}

                      <CardContent sx={{ flexGrow: 1, p: 3 }}>
                        {/* Plan Header */}
                        <Box sx={{ textAlign: 'center', mb: 3 }}>
                          <Typography variant="h5" gutterBottom>
                            {plan.name}
                          </Typography>
                          <Typography variant="body2" color="text.secondary" paragraph>
                            {plan.description}
                          </Typography>

                          {/* Current Plan Badge */}
                          {isCurrent && (
                            <Chip
                              label="Current Plan"
                              color="success"
                              size="small"
                              sx={{ mb: 2 }}
                            />
                          )}

                          {/* Pricing */}
                          <Box sx={{ mb: 2 }}>
                            <Typography variant="h3" component="span" sx={{ fontWeight: 'bold' }}>
                              ${price}
                            </Typography>
                            <Typography variant="h6" component="span" color="text.secondary">
                              /{isYearly ? 'year' : 'month'}
                            </Typography>
                          </Box>

                          {/* Savings */}
                          {isYearly && savings > 0 && (
                            <Typography variant="body2" color="success.main">
                              Save ${savings}/year
                            </Typography>
                          )}
                        </Box>

                        <Divider sx={{ my: 2 }} />

                        {/* Features List */}
                        <List dense>
                          {features.map((feature, index) => (
                            <ListItem key={index} sx={{ px: 0 }}>
                              <ListItemIcon sx={{ minWidth: 32 }}>
                                {feature.included ? (
                                  <Check color="success" />
                                ) : (
                                  <Close color="disabled" />
                                )}
                              </ListItemIcon>
                              <ListItemText
                                primary={feature.name}
                                sx={{
                                  opacity: feature.included ? 1 : 0.5,
                                  textDecoration: feature.included ? 'none' : 'line-through'
                                }}
                              />
                            </ListItem>
                          ))}
                        </List>

                        {/* Action Button */}
                        <Box sx={{ mt: 'auto', pt: 3 }}>
                          {isCurrent ? (
                            <Button
                              fullWidth
                              variant="outlined"
                              disabled
                              startIcon={<Check />}
                            >
                              Current Plan
                            </Button>
                          ) : (
                            <Button
                              fullWidth
                              variant={selectedPlan === plan.plan ? 'contained' : 'outlined'}
                              color={isDowngradeOption ? 'warning' : 'primary'}
                              onClick={() => handleUpgrade(plan.plan)}
                              disabled={upgrading}
                              startIcon={
                                upgrading ? (
                                  <CircularProgress size={16} />
                                ) : isDowngradeOption ? (
                                  <TrendingUp sx={{ transform: 'rotate(180deg)' }} />
                                ) : (
                                  <TrendingUp />
                                )
                              }
                            >
                              {isDowngradeOption ? 'Downgrade' : 'Upgrade'} to {plan.name}
                            </Button>
                          )}
                        </Box>
                      </CardContent>
                    </Card>
                  </Grid>
                );
              })}
            </Grid>

            {/* Additional Information */}
            <Box sx={{ mt: 4, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
              <Typography variant="body2" color="text.secondary">
                <strong>Note:</strong> Plan changes take effect immediately. 
                {currentPlan && ' You will be charged or credited prorated amounts based on the remaining time in your current billing cycle.'}
                {!currentPlan && ' You can cancel anytime before your trial ends.'}
              </Typography>
            </Box>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default PlanUpgradeModal;