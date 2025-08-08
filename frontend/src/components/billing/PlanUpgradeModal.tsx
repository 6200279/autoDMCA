import React, { useState, useEffect } from 'react';
import { Dialog } from 'primereact/dialog';
import { Button } from 'primereact/button';
import { Card } from 'primereact/card';
import { InputSwitch } from 'primereact/inputswitch';
import { Message } from 'primereact/message';
import { Tag } from 'primereact/tag';
import { ProgressSpinner } from 'primereact/progressspinner';

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
      visible={open}
      onHide={onClose}
      style={{ width: '90vw', maxWidth: '1200px', minHeight: '70vh' }}
      header={
        <div className="flex justify-between items-center w-full">
          <h2 className="text-xl font-semibold">
            {currentPlan ? 'Change Subscription Plan' : 'Choose Your Plan'}
          </h2>
        </div>
      }
      className="p-dialog-maximized"
    >
      <div className="p-6">
        {loading ? (
          <div className="flex justify-center p-8">
            <ProgressSpinner />
          </div>
        ) : (
          <>
            {error && (
              <Message 
                severity="error" 
                text={error}
                className="mb-6"
              />
            )}

            {/* Billing Toggle */}
            <div className="mb-8 text-center">
              <div className="flex items-center justify-center gap-4">
                <span>Monthly billing</span>
                <InputSwitch
                  checked={isYearly}
                  onChange={(e) => setIsYearly(e.value)}
                />
                <span>Annual billing</span>
                <Tag 
                  value="Save up to 17%" 
                  severity="success" 
                />
              </div>
            </div>

            {/* Plans Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {plans.map((plan) => {
                const features = getPlanFeatures(plan);
                const price = getPrice(plan);
                const savings = getSavings(plan);
                const isCurrent = isCurrentPlan(plan.plan);
                const isDowngradeOption = isDowngrade(plan.plan);

                return (
                  <div key={plan.plan} className="relative">
                    <Card
                      className={`h-full cursor-pointer transition-all hover:shadow-lg ${
                        selectedPlan === plan.plan 
                          ? 'border-2 border-blue-500' 
                          : 'border border-gray-200'
                      }`}
                      onClick={() => setSelectedPlan(plan.plan)}
                    >
                      {/* Popular Badge */}
                      {plan.plan === 'professional' && (
                        <div className="absolute -top-3 left-1/2 transform -translate-x-1/2 z-10">
                          <Tag
                            value="Most Popular"
                            icon="pi pi-star"
                            severity="info"
                          />
                        </div>
                      )}

                      <div className="p-6 h-full flex flex-col">
                        {/* Plan Header */}
                        <div className="text-center mb-6">
                          <h3 className="text-xl font-semibold mb-2">
                            {plan.name}
                          </h3>
                          <p className="text-gray-600 text-sm mb-4">
                            {plan.description}
                          </p>

                          {/* Current Plan Badge */}
                          {isCurrent && (
                            <Tag
                              value="Current Plan"
                              severity="success"
                              className="mb-4"
                            />
                          )}

                          {/* Pricing */}
                          <div className="mb-4">
                            <span className="text-3xl font-bold">
                              ${price}
                            </span>
                            <span className="text-lg text-gray-600 ml-1">
                              /{isYearly ? 'year' : 'month'}
                            </span>
                          </div>

                          {/* Savings */}
                          {isYearly && savings > 0 && (
                            <p className="text-sm text-green-600 font-medium">
                              Save ${savings}/year
                            </p>
                          )}
                        </div>

                        <hr className="my-4" />

                        {/* Features List */}
                        <div className="space-y-3 flex-grow">
                          {features.map((feature, index) => (
                            <div key={index} className="flex items-center gap-3">
                              <i className={`${
                                feature.included 
                                  ? 'pi pi-check text-green-500' 
                                  : 'pi pi-times text-gray-400'
                              }`}></i>
                              <span className={`text-sm ${
                                feature.included 
                                  ? 'text-gray-900' 
                                  : 'text-gray-400 line-through'
                              }`}>
                                {feature.name}
                              </span>
                            </div>
                          ))}
                        </div>

                        {/* Action Button */}
                        <div className="mt-6">
                          {isCurrent ? (
                            <Button
                              label="Current Plan"
                              icon="pi pi-check"
                              disabled
                              outlined
                              className="w-full"
                            />
                          ) : (
                            <Button
                              label={`${isDowngradeOption ? 'Downgrade' : 'Upgrade'} to ${plan.name}`}
                              icon={
                                upgrading 
                                  ? "pi pi-spin pi-spinner"
                                  : isDowngradeOption 
                                    ? "pi pi-arrow-down" 
                                    : "pi pi-arrow-up"
                              }
                              onClick={() => handleUpgrade(plan.plan)}
                              disabled={upgrading}
                              severity={isDowngradeOption ? "warning" : "info"}
                              className={`w-full ${selectedPlan === plan.plan ? '' : 'p-button-outlined'}`}
                            />
                          )}
                        </div>
                      </div>
                    </Card>
                  </div>
                );
              })}
            </div>

            {/* Additional Information */}
            <div className="mt-8 p-4 bg-gray-50 rounded">
              <p className="text-sm text-gray-600">
                <strong>Note:</strong> Plan changes take effect immediately. 
                {currentPlan && ' You will be charged or credited prorated amounts based on the remaining time in your current billing cycle.'}
                {!currentPlan && ' You can cancel anytime before your trial ends.'}
              </p>
            </div>
          </>
        )}
      </div>
    </Dialog>
  );
};

export default PlanUpgradeModal;