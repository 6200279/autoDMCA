import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  CardHeader,
  Box,
  Typography,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  ListItemAvatar,
  Avatar,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  Chip,
  CircularProgress
} from '@mui/material';
import {
  CreditCard,
  Add,
  Delete,
  Star,
  AccountBalance
} from '@mui/icons-material';
import { loadStripe } from '@stripe/stripe-js';
import {
  Elements,
  CardElement,
  useStripe,
  useElements
} from '@stripe/react-stripe-js';

import { billingApi } from '../../services/api';

interface PaymentMethodsProps {
  onRefresh: () => void;
}

// Initialize Stripe
const stripePromise = loadStripe(process.env.REACT_APP_STRIPE_PUBLISHABLE_KEY || '');

const PaymentMethods: React.FC<PaymentMethodsProps> = ({ onRefresh }) => {
  const [paymentMethods, setPaymentMethods] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [selectedPaymentMethod, setSelectedPaymentMethod] = useState<any>(null);

  const fetchPaymentMethods = async () => {
    try {
      setLoading(true);
      const response = await billingApi.getPaymentMethods();
      setPaymentMethods(response.data);
    } catch (error) {
      console.error('Failed to fetch payment methods:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPaymentMethods();
  }, []);

  const handleDeletePaymentMethod = async () => {
    if (!selectedPaymentMethod) return;

    try {
      await billingApi.removePaymentMethod(selectedPaymentMethod.id);
      setDeleteConfirmOpen(false);
      setSelectedPaymentMethod(null);
      fetchPaymentMethods();
      onRefresh();
    } catch (error) {
      console.error('Failed to delete payment method:', error);
    }
  };

  const getCardBrandIcon = (brand: string) => {
    switch (brand?.toLowerCase()) {
      case 'visa':
        return '💳';
      case 'mastercard':
        return '💳';
      case 'amex':
        return '💳';
      case 'discover':
        return '💳';
      default:
        return '💳';
    }
  };

  const formatExpiryDate = (month: number, year: number) => {
    return `${month.toString().padStart(2, '0')}/${year.toString().slice(-2)}`;
  };

  return (
    <>
      <Card>
        <CardHeader
          title="Payment Methods"
          action={
            <Button
              startIcon={<Add />}
              onClick={() => setAddModalOpen(true)}
              variant="outlined"
              size="small"
            >
              Add Card
            </Button>
          }
        />
        <CardContent>
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
              <CircularProgress />
            </Box>
          ) : paymentMethods.length === 0 ? (
            <Alert severity="info">
              No payment methods added yet. Add a card to manage your subscription.
            </Alert>
          ) : (
            <List disablePadding>
              {paymentMethods.map((method) => (
                <ListItem key={method.id} divider>
                  <ListItemAvatar>
                    <Avatar sx={{ bgcolor: 'primary.main' }}>
                      {method.type === 'card' ? (
                        <CreditCard />
                      ) : (
                        <AccountBalance />
                      )}
                    </Avatar>
                  </ListItemAvatar>
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="body1">
                          {method.cardBrand?.toUpperCase()} •••• {method.cardLast4}
                        </Typography>
                        {method.isDefault && (
                          <Chip
                            label="Default"
                            size="small"
                            color="primary"
                            icon={<Star />}
                          />
                        )}
                      </Box>
                    }
                    secondary={
                      method.type === 'card' ? (
                        `Expires ${formatExpiryDate(method.cardExpMonth, method.cardExpYear)}`
                      ) : (
                        `${method.bankName} •••• ${method.bankLast4}`
                      )
                    }
                  />
                  <ListItemSecondaryAction>
                    <IconButton
                      edge="end"
                      onClick={() => {
                        setSelectedPaymentMethod(method);
                        setDeleteConfirmOpen(true);
                      }}
                      disabled={method.isDefault}
                    >
                      <Delete />
                    </IconButton>
                  </ListItemSecondaryAction>
                </ListItem>
              ))}
            </List>
          )}
        </CardContent>
      </Card>

      {/* Add Payment Method Modal */}
      <Elements stripe={stripePromise}>
        <AddPaymentMethodModal
          open={addModalOpen}
          onClose={() => setAddModalOpen(false)}
          onSuccess={() => {
            setAddModalOpen(false);
            fetchPaymentMethods();
            onRefresh();
          }}
        />
      </Elements>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteConfirmOpen}
        onClose={() => setDeleteConfirmOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Remove Payment Method</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to remove this payment method?
          </Typography>
          {selectedPaymentMethod && (
            <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
              <Typography variant="body2">
                <strong>
                  {selectedPaymentMethod.cardBrand?.toUpperCase()} •••• {selectedPaymentMethod.cardLast4}
                </strong>
              </Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteConfirmOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleDeletePaymentMethod} color="error">
            Remove
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

// Add Payment Method Modal Component
interface AddPaymentMethodModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const AddPaymentMethodModal: React.FC<AddPaymentMethodModalProps> = ({
  open,
  onClose,
  onSuccess
}) => {
  const stripe = useStripe();
  const elements = useElements();
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    if (!stripe || !elements) {
      return;
    }

    const cardElement = elements.getElement(CardElement);
    if (!cardElement) {
      return;
    }

    setProcessing(true);
    setError(null);

    try {
      // Create setup intent
      const { data: setupIntentData } = await billingApi.createSetupIntent({
        usage: 'off_session'
      });

      // Confirm setup intent
      const { setupIntent, error: stripeError } = await stripe.confirmCardSetup(
        setupIntentData.clientSecret,
        {
          payment_method: {
            card: cardElement,
          }
        }
      );

      if (stripeError) {
        setError(stripeError.message || 'An error occurred');
        return;
      }

      if (setupIntent && setupIntent.payment_method) {
        // Add payment method to backend
        await billingApi.addPaymentMethod({
          paymentMethodId: setupIntent.payment_method.id,
          setAsDefault: false
        });

        onSuccess();
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to add payment method');
    } finally {
      setProcessing(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <form onSubmit={handleSubmit}>
        <DialogTitle>Add Payment Method</DialogTitle>
        <DialogContent>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Enter your card details below. This card will be securely stored for future payments.
            </Typography>

            <Box
              sx={{
                mt: 2,
                p: 2,
                border: 1,
                borderColor: 'divider',
                borderRadius: 1,
                '& .StripeElement': {
                  padding: '12px 0',
                },
                '& .StripeElement--focus': {
                  borderColor: 'primary.main',
                },
              }}
            >
              <CardElement
                options={{
                  style: {
                    base: {
                      fontSize: '16px',
                      color: '#424770',
                      '::placeholder': {
                        color: '#aab7c4',
                      },
                    },
                  },
                }}
              />
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose} disabled={processing}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="contained"
            disabled={!stripe || processing}
            startIcon={processing ? <CircularProgress size={16} /> : <Add />}
          >
            Add Card
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};

export default PaymentMethods;