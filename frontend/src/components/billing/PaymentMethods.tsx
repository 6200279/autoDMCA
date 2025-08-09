import React, { useState, useEffect } from 'react';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { Dialog } from 'primereact/dialog';
import { Message } from 'primereact/message';
import { Tag } from 'primereact/tag';
import { ProgressSpinner } from 'primereact/progressspinner';
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

  // const getCardBrandIcon = (brand: string) => {
  //   switch (brand?.toLowerCase()) {
  //     case 'visa':
  //       return '💳';
  //     case 'mastercard':
  //       return '💳';
  //     case 'amex':
  //       return '💳';
  //     case 'discover':
  //       return '💳';
  //     default:
  //       return '💳';
  //   }
  // };

  const formatExpiryDate = (month: number, year: number) => {
    return `${month.toString().padStart(2, '0')}/${year.toString().slice(-2)}`;
  };

  return (
    <>
      <Card className="p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Payment Methods</h2>
          <Button
            label="Add Card"
            icon="pi pi-plus"
            onClick={() => setAddModalOpen(true)}
            outlined
            size="small"
          />
        </div>
        
        {loading ? (
          <div className="flex justify-center p-4">
            <ProgressSpinner />
          </div>
        ) : paymentMethods.length === 0 ? (
          <Message 
            severity="info" 
            text="No payment methods added yet. Add a card to manage your subscription." 
          />
        ) : (
          <div className="space-y-4">
            {paymentMethods.map((method) => (
              <div key={method.id} className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-blue-500 rounded-full flex items-center justify-center text-white">
                    <i className={method.type === 'card' ? 'pi pi-credit-card' : 'pi pi-building'}></i>
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">
                        {method.cardBrand?.toUpperCase()} •••• {method.cardLast4}
                      </span>
                      {method.isDefault && (
                        <Tag
                          value="Default"
                          icon="pi pi-star"
                          severity="info"
                        />
                      )}
                    </div>
                    <p className="text-sm text-gray-600">
                      {method.type === 'card' ? (
                        `Expires ${formatExpiryDate(method.cardExpMonth, method.cardExpYear)}`
                      ) : (
                        `${method.bankName} •••• ${method.bankLast4}`
                      )}
                    </p>
                  </div>
                </div>
                <Button
                  icon="pi pi-trash"
                  onClick={() => {
                    setSelectedPaymentMethod(method);
                    setDeleteConfirmOpen(true);
                  }}
                  disabled={method.isDefault}
                  severity="danger"
                  outlined
                  size="small"
                />
              </div>
            ))}
          </div>
        )}
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
        header="Remove Payment Method"
        visible={deleteConfirmOpen}
        onHide={() => setDeleteConfirmOpen(false)}
        style={{ width: '450px' }}
        footer={
          <div className="flex justify-end gap-2">
            <Button 
              label="Cancel" 
              outlined
              onClick={() => setDeleteConfirmOpen(false)}
            />
            <Button 
              label="Remove" 
              onClick={handleDeletePaymentMethod} 
              severity="danger" 
            />
          </div>
        }
      >
        <p className="mb-4">
          Are you sure you want to remove this payment method?
        </p>
        {selectedPaymentMethod && (
          <div className="mt-4 p-3 bg-gray-50 rounded">
            <p className="font-medium text-sm">
              {selectedPaymentMethod.cardBrand?.toUpperCase()} •••• {selectedPaymentMethod.cardLast4}
            </p>
          </div>
        )}
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
          paymentMethodId: (setupIntent.payment_method as any).id,
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
    <Dialog 
      header="Add Payment Method" 
      visible={open} 
      onHide={onClose} 
      style={{ width: '500px' }}
      footer={
        <div className="flex justify-end gap-2">
          <Button 
            label="Cancel" 
            outlined
            onClick={onClose} 
            disabled={processing}
          />
          <Button
            label="Add Card"
            icon={processing ? "pi pi-spin pi-spinner" : "pi pi-plus"}
            disabled={!stripe || processing}
            onClick={handleSubmit}
          />
        </div>
      }
    >
      <form onSubmit={handleSubmit}>
        {error && (
          <Message 
            severity="error" 
            text={error}
            className="mb-4"
          />
        )}

        <div className="mt-4">
          <p className="text-sm text-gray-600 mb-4">
            Enter your card details below. This card will be securely stored for future payments.
          </p>

          <div className="mt-4 p-4 border border-gray-200 rounded">
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
          </div>
        </div>
      </form>
    </Dialog>
  );
};

export default PaymentMethods;