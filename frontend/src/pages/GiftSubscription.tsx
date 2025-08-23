import React, { useState, useEffect } from 'react';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { InputText } from 'primereact/inputtext';
import { Dropdown } from 'primereact/dropdown';
import { InputTextarea } from 'primereact/inputtextarea';
import { Divider } from 'primereact/divider';
import { Message } from 'primereact/message';
import { ProgressSpinner } from 'primereact/progressspinner';
import { Dialog } from 'primereact/dialog';
import { Badge } from 'primereact/badge';
import { Panel } from 'primereact/panel';
import './GiftSubscription.css';

interface SubscriptionPlan {
    value: string;
    label: string;
    monthlyPrice: number;
    yearlyPrice: number;
    features: string[];
    limits: {
        maxProtectedProfiles: number;
        maxMonthlyScans: number;
        maxTakedownRequests: number;
    };
}

interface BillingInterval {
    value: string;
    label: string;
    discount?: string;
}

interface GiftPurchaseData {
    recipientEmail: string;
    recipientName: string;
    plan: string;
    billingInterval: string;
    personalMessage: string;
    customSenderName: string;
}

interface PriceInfo {
    basePrice: number;
    discountAmount: number;
    finalPrice: number;
    currency: string;
    plan: string;
    interval: string;
}

const GiftSubscription: React.FC = () => {
    const [step, setStep] = useState(1);
    const [loading, setLoading] = useState(false);
    const [formData, setFormData] = useState<GiftPurchaseData>({
        recipientEmail: '',
        recipientName: '',
        plan: 'basic',
        billingInterval: 'monthly',
        personalMessage: '',
        customSenderName: ''
    });
    const [priceInfo, setPriceInfo] = useState<PriceInfo | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<any>(null);
    const [showPaymentDialog, setShowPaymentDialog] = useState(false);

    const subscriptionPlans: SubscriptionPlan[] = [
        {
            value: 'basic',
            label: 'Basic Plan',
            monthlyPrice: 49,
            yearlyPrice: 490,
            features: [
                'AI-powered face recognition',
                'Basic support',
                'Standard takedown templates'
            ],
            limits: {
                maxProtectedProfiles: 1,
                maxMonthlyScans: 1000,
                maxTakedownRequests: 50
            }
        },
        {
            value: 'professional',
            label: 'Professional Plan',
            monthlyPrice: 99,
            yearlyPrice: 990,
            features: [
                'AI-powered face recognition',
                'Priority support',
                'Custom branding',
                'Full API access',
                'Advanced analytics'
            ],
            limits: {
                maxProtectedProfiles: 5,
                maxMonthlyScans: 10000,
                maxTakedownRequests: 500
            }
        }
    ];

    const billingIntervals: BillingInterval[] = [
        { value: 'monthly', label: 'Monthly' },
        { value: 'yearly', label: 'Yearly', discount: '2 months free' }
    ];

    const selectedPlan = subscriptionPlans.find(plan => plan.value === formData.plan);
    const selectedInterval = billingIntervals.find(interval => interval.value === formData.billingInterval);

    // Fetch pricing information when plan or interval changes
    useEffect(() => {
        if (formData.plan && formData.billingInterval) {
            fetchPricing();
        }
    }, [formData.plan, formData.billingInterval]);

    const fetchPricing = async () => {
        try {
            const response = await fetch(
                `/api/v1/billing/gifts/pricing?plan=${formData.plan}&interval=${formData.billingInterval}`
            );
            const data = await response.json();
            
            if (data.success) {
                setPriceInfo(data.pricing);
            }
        } catch (error) {
            console.error('Error fetching pricing:', error);
        }
    };

    const handleInputChange = (field: keyof GiftPurchaseData, value: string) => {
        setFormData(prev => ({
            ...prev,
            [field]: value
        }));
        setError(null);
    };

    const validateStep1 = (): boolean => {
        if (!formData.recipientEmail) {
            setError('Recipient email is required');
            return false;
        }
        
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(formData.recipientEmail)) {
            setError('Please enter a valid email address');
            return false;
        }

        return true;
    };

    const validateStep2 = (): boolean => {
        if (!formData.plan || !formData.billingInterval) {
            setError('Please select a plan and billing interval');
            return false;
        }
        return true;
    };

    const handleNext = () => {
        setError(null);
        
        if (step === 1 && !validateStep1()) return;
        if (step === 2 && !validateStep2()) return;
        
        setStep(prev => prev + 1);
    };

    const handleBack = () => {
        setStep(prev => prev - 1);
        setError(null);
    };

    const handlePurchase = async () => {
        setLoading(true);
        setError(null);

        try {
            const response = await fetch('/api/v1/gifts/purchase', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify({
                    recipient_email: formData.recipientEmail,
                    recipient_name: formData.recipientName || null,
                    plan: formData.plan,
                    billing_interval: formData.billingInterval,
                    personal_message: formData.personalMessage || null,
                    custom_sender_name: formData.customSenderName || null,
                    use_checkout: true,
                    success_url: `${window.location.origin}/gift/success`,
                    cancel_url: `${window.location.origin}/gift/cancel`
                })
            });

            const data = await response.json();

            if (data.success) {
                if (data.checkout_url) {
                    // Redirect to Stripe Checkout
                    window.location.href = data.checkout_url;
                } else {
                    setSuccess(data);
                    setShowPaymentDialog(true);
                }
            } else {
                setError(data.message || 'Failed to create gift subscription');
            }
        } catch (error) {
            console.error('Error purchasing gift:', error);
            setError('Failed to process gift purchase. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const renderStep1 = () => (
        <Card title="Gift Recipient Information" className="gift-step-card">
            <div className="field">
                <label htmlFor="recipientEmail" className="block text-900 font-medium mb-2">
                    Recipient Email Address *
                </label>
                <InputText
                    id="recipientEmail"
                    value={formData.recipientEmail}
                    onChange={(e) => handleInputChange('recipientEmail', e.target.value)}
                    placeholder="Enter recipient's email address"
                    className="w-full"
                />
            </div>

            <div className="field">
                <label htmlFor="recipientName" className="block text-900 font-medium mb-2">
                    Recipient Name (Optional)
                </label>
                <InputText
                    id="recipientName"
                    value={formData.recipientName}
                    onChange={(e) => handleInputChange('recipientName', e.target.value)}
                    placeholder="Enter recipient's name"
                    className="w-full"
                />
            </div>

            <div className="field">
                <label htmlFor="customSenderName" className="block text-900 font-medium mb-2">
                    Custom Sender Name (Optional)
                </label>
                <InputText
                    id="customSenderName"
                    value={formData.customSenderName}
                    onChange={(e) => handleInputChange('customSenderName', e.target.value)}
                    placeholder="How you'd like to appear to the recipient"
                    className="w-full"
                />
                <small className="text-600">
                    Leave blank to use your account name
                </small>
            </div>
        </Card>
    );

    const renderStep2 = () => (
        <Card title="Choose Subscription Plan" className="gift-step-card">
            <div className="grid">
                {subscriptionPlans.map((plan) => (
                    <div key={plan.value} className="col-12 md:col-6">
                        <Card 
                            className={`plan-card ${formData.plan === plan.value ? 'selected' : ''}`}
                            onClick={() => handleInputChange('plan', plan.value)}
                        >
                            <div className="flex justify-content-between align-items-center mb-3">
                                <h4 className="m-0">{plan.label}</h4>
                                {formData.plan === plan.value && (
                                    <Badge value="Selected" severity="success" />
                                )}
                            </div>
                            
                            <div className="pricing mb-3">
                                <div className="text-2xl font-bold text-primary">
                                    ${formData.billingInterval === 'yearly' ? plan.yearlyPrice : plan.monthlyPrice}
                                    <span className="text-sm font-normal text-600">
                                        /{formData.billingInterval === 'yearly' ? 'year' : 'month'}
                                    </span>
                                </div>
                                {formData.billingInterval === 'yearly' && (
                                    <div className="text-green-500 text-sm">
                                        Save ${(plan.monthlyPrice * 12) - plan.yearlyPrice}
                                    </div>
                                )}
                            </div>

                            <Divider />

                            <div className="features">
                                <h5>Features:</h5>
                                <ul className="list-none p-0">
                                    {plan.features.map((feature, index) => (
                                        <li key={index} className="flex align-items-center mb-2">
                                            <i className="pi pi-check text-green-500 mr-2"></i>
                                            {feature}
                                        </li>
                                    ))}
                                </ul>
                            </div>

                            <Divider />

                            <div className="limits">
                                <h5>Limits:</h5>
                                <ul className="list-none p-0 text-sm">
                                    <li>• {plan.limits.maxProtectedProfiles} protected profile{plan.limits.maxProtectedProfiles > 1 ? 's' : ''}</li>
                                    <li>• {plan.limits.maxMonthlyScans.toLocaleString()} monthly scans</li>
                                    <li>• {plan.limits.maxTakedownRequests} takedown requests/month</li>
                                </ul>
                            </div>
                        </Card>
                    </div>
                ))}
            </div>

            <div className="field mt-4">
                <label className="block text-900 font-medium mb-2">
                    Billing Interval
                </label>
                <div className="flex gap-3">
                    {billingIntervals.map((interval) => (
                        <div 
                            key={interval.value}
                            className={`interval-option ${formData.billingInterval === interval.value ? 'selected' : ''}`}
                            onClick={() => handleInputChange('billingInterval', interval.value)}
                        >
                            <div className="flex align-items-center">
                                <span className="font-medium">{interval.label}</span>
                                {interval.discount && (
                                    <Badge value={interval.discount} severity="info" className="ml-2" />
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </Card>
    );

    const renderStep3 = () => (
        <Card title="Personal Message (Optional)" className="gift-step-card">
            <div className="field">
                <label htmlFor="personalMessage" className="block text-900 font-medium mb-2">
                    Add a personal message for the recipient
                </label>
                <InputTextarea
                    id="personalMessage"
                    value={formData.personalMessage}
                    onChange={(e) => handleInputChange('personalMessage', e.target.value)}
                    placeholder="Write a personal message to accompany your gift..."
                    rows={5}
                    className="w-full"
                    maxLength={1000}
                />
                <small className="text-600">
                    {formData.personalMessage.length}/1000 characters
                </small>
            </div>
        </Card>
    );

    const renderReview = () => (
        <Card title="Review Your Gift" className="gift-step-card">
            <div className="grid">
                <div className="col-12 md:col-8">
                    <Panel header="Gift Details" className="mb-3">
                        <div className="field">
                            <strong>Recipient:</strong> {formData.recipientEmail}
                            {formData.recipientName && ` (${formData.recipientName})`}
                        </div>
                        
                        <div className="field">
                            <strong>Plan:</strong> {selectedPlan?.label}
                        </div>
                        
                        <div className="field">
                            <strong>Billing:</strong> {selectedInterval?.label}
                        </div>
                        
                        {formData.customSenderName && (
                            <div className="field">
                                <strong>Sender Name:</strong> {formData.customSenderName}
                            </div>
                        )}
                        
                        {formData.personalMessage && (
                            <div className="field">
                                <strong>Personal Message:</strong>
                                <div className="bg-gray-50 p-3 border-round mt-2">
                                    {formData.personalMessage}
                                </div>
                            </div>
                        )}
                    </Panel>
                </div>

                <div className="col-12 md:col-4">
                    <Panel header="Order Summary" className="order-summary">
                        {priceInfo && (
                            <>
                                <div className="flex justify-content-between mb-2">
                                    <span>Subtotal:</span>
                                    <span>${(priceInfo.basePrice / 100).toFixed(2)}</span>
                                </div>
                                
                                {priceInfo.discountAmount > 0 && (
                                    <div className="flex justify-content-between mb-2 text-green-500">
                                        <span>Discount:</span>
                                        <span>-${(priceInfo.discountAmount / 100).toFixed(2)}</span>
                                    </div>
                                )}
                                
                                <Divider />
                                
                                <div className="flex justify-content-between text-xl font-bold">
                                    <span>Total:</span>
                                    <span>${(priceInfo.finalPrice / 100).toFixed(2)}</span>
                                </div>
                                
                                <div className="text-sm text-600 mt-2">
                                    Gift expires in 90 days if not redeemed
                                </div>
                            </>
                        )}
                    </Panel>
                </div>
            </div>
        </Card>
    );

    const renderStepIndicator = () => (
        <div className="step-indicator mb-4">
            <div className="flex align-items-center justify-content-center">
                {[1, 2, 3, 4].map((stepNumber) => (
                    <React.Fragment key={stepNumber}>
                        <div className={`step ${step >= stepNumber ? 'active' : ''}`}>
                            {step > stepNumber ? (
                                <i className="pi pi-check"></i>
                            ) : (
                                stepNumber
                            )}
                        </div>
                        {stepNumber < 4 && <div className="step-connector"></div>}
                    </React.Fragment>
                ))}
            </div>
            <div className="flex justify-content-center mt-2">
                <div className="step-labels">
                    <span className={step === 1 ? 'active' : ''}>Recipient</span>
                    <span className={step === 2 ? 'active' : ''}>Plan</span>
                    <span className={step === 3 ? 'active' : ''}>Message</span>
                    <span className={step === 4 ? 'active' : ''}>Review</span>
                </div>
            </div>
        </div>
    );

    return (
        <div className="gift-subscription-container">
            <div className="max-w-4xl mx-auto">
                <div className="text-center mb-4">
                    <h1 className="text-4xl font-bold text-900 mb-2">
                        🎁 Gift a Subscription
                    </h1>
                    <p className="text-xl text-600">
                        Give the gift of content protection to someone you care about
                    </p>
                </div>

                {renderStepIndicator()}

                {error && (
                    <Message severity="error" text={error} className="mb-4" />
                )}

                <div className="step-content">
                    {step === 1 && renderStep1()}
                    {step === 2 && renderStep2()}
                    {step === 3 && renderStep3()}
                    {step === 4 && renderReview()}
                </div>

                <div className="flex justify-content-between mt-4">
                    <Button
                        label="Back"
                        icon="pi pi-chevron-left"
                        onClick={handleBack}
                        disabled={step === 1 || loading}
                        severity="secondary"
                    />
                    
                    {step < 4 ? (
                        <Button
                            label="Next"
                            icon="pi pi-chevron-right"
                            iconPos="right"
                            onClick={handleNext}
                            disabled={loading}
                        />
                    ) : (
                        <Button
                            label={loading ? "Processing..." : "Purchase Gift"}
                            icon={loading ? "pi pi-spin pi-spinner" : "pi pi-credit-card"}
                            onClick={handlePurchase}
                            disabled={loading}
                            className="gift-purchase-btn"
                        />
                    )}
                </div>
            </div>

            <Dialog
                header="Gift Purchase Successful!"
                visible={showPaymentDialog}
                onHide={() => setShowPaymentDialog(false)}
                modal
                className="gift-success-dialog"
            >
                {success && (
                    <div className="text-center">
                        <i className="pi pi-check-circle text-6xl text-green-500 mb-3"></i>
                        <h3>Gift Sent Successfully!</h3>
                        <p>
                            Your gift subscription has been sent to <strong>{formData.recipientEmail}</strong>
                        </p>
                        <p>
                            Gift Code: <strong>{success.gift_code}</strong>
                        </p>
                        <div className="mt-4">
                            <Button
                                label="View My Gifts"
                                onClick={() => window.location.href = '/billing?tab=gifts'}
                                className="mr-2"
                            />
                            <Button
                                label="Send Another Gift"
                                onClick={() => {
                                    setShowPaymentDialog(false);
                                    setSuccess(null);
                                    setStep(1);
                                    setFormData({
                                        recipientEmail: '',
                                        recipientName: '',
                                        plan: 'basic',
                                        billingInterval: 'monthly',
                                        personalMessage: '',
                                        customSenderName: ''
                                    });
                                }}
                                severity="secondary"
                            />
                        </div>
                    </div>
                )}
            </Dialog>
        </div>
    );
};

export default GiftSubscription;