import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { InputText } from 'primereact/inputtext';
import { Message } from 'primereact/message';
import { ProgressSpinner } from 'primereact/progressspinner';
import { Dialog } from 'primereact/dialog';
import { Badge } from 'primereact/badge';
import { Panel } from 'primereact/panel';
import { Divider } from 'primereact/divider';
import './GiftRedemption.css';

interface GiftInfo {
    id: number;
    giver_email: string;
    giver_name: string;
    recipient_email: string;
    recipient_name?: string;
    plan: string;
    billing_interval: string;
    amount: number;
    currency: string;
    status: string;
    gift_code: string;
    personal_message?: string;
    custom_sender_name?: string;
    expires_at: string;
    created_at: string;
}

interface GiftStatusResponse {
    success: boolean;
    exists: boolean;
    gift?: GiftInfo;
    can_be_redeemed: boolean;
    days_until_expiry?: number;
    error_message?: string;
}

interface RedemptionResponse {
    success: boolean;
    subscription_id?: number;
    plan?: string;
    billing_interval?: string;
    message: string;
    error_code?: string;
}

const GiftRedemption: React.FC = () => {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const [giftCode, setGiftCode] = useState(searchParams.get('code') || '');
    const [loading, setLoading] = useState(false);
    const [checking, setChecking] = useState(false);
    const [giftInfo, setGiftInfo] = useState<GiftInfo | null>(null);
    const [giftStatus, setGiftStatus] = useState<GiftStatusResponse | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<RedemptionResponse | null>(null);
    const [showSuccessDialog, setShowSuccessDialog] = useState(false);

    // Check gift status when component mounts or code changes
    useEffect(() => {
        if (giftCode && giftCode.length >= 16) {
            checkGiftStatus();
        }
    }, []);

    const formatGiftCode = (code: string): string => {
        // Remove all non-alphanumeric characters and convert to uppercase
        const clean = code.replace(/[^A-Z0-9]/g, '').toUpperCase();
        
        // Add dashes every 4 characters
        return clean.replace(/(.{4})/g, '$1-').replace(/-$/, '');
    };

    const handleCodeChange = (value: string) => {
        const formatted = formatGiftCode(value);
        setGiftCode(formatted);
        setError(null);
        setGiftStatus(null);
        setGiftInfo(null);
    };

    const checkGiftStatus = async () => {
        if (!giftCode || giftCode.length < 16) {
            setError('Please enter a valid gift code');
            return;
        }

        setChecking(true);
        setError(null);

        try {
            const response = await fetch('/api/v1/gifts/status', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    gift_code: giftCode
                })
            });

            const data: GiftStatusResponse = await response.json();

            if (data.success) {
                setGiftStatus(data);
                if (data.gift) {
                    setGiftInfo(data.gift);
                }
                
                if (!data.exists) {
                    setError('Gift code not found. Please check the code and try again.');
                } else if (!data.can_be_redeemed) {
                    setError(data.error_message || 'This gift code cannot be redeemed.');
                }
            } else {
                setError('Failed to check gift status. Please try again.');
            }
        } catch (error) {
            console.error('Error checking gift status:', error);
            setError('Failed to check gift status. Please try again.');
        } finally {
            setChecking(false);
        }
    };

    const redeemGift = async () => {
        if (!giftStatus?.can_be_redeemed) {
            setError('This gift cannot be redeemed');
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const token = localStorage.getItem('token');
            if (!token) {
                setError('Please log in to redeem your gift');
                // Redirect to login with return URL
                navigate(`/login?redirect=${encodeURIComponent(`/gift/redeem?code=${giftCode}`)}`);
                return;
            }

            const response = await fetch('/api/v1/gifts/redeem', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    gift_code: giftCode
                })
            });

            const data: RedemptionResponse = await response.json();

            if (data.success) {
                setSuccess(data);
                setShowSuccessDialog(true);
            } else {
                setError(data.message || 'Failed to redeem gift. Please try again.');
            }
        } catch (error) {
            console.error('Error redeeming gift:', error);
            setError('Failed to redeem gift. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const getPlanDisplayName = (plan: string): string => {
        return plan.charAt(0).toUpperCase() + plan.slice(1) + ' Plan';
    };

    const getIntervalDisplayName = (interval: string): string => {
        return interval.charAt(0).toUpperCase() + interval.slice(1);
    };

    const getStatusBadge = (status: string) => {
        switch (status) {
            case 'pending':
                return <Badge value="Ready to Redeem" severity="success" />;
            case 'redeemed':
                return <Badge value="Redeemed" severity="info" />;
            case 'expired':
                return <Badge value="Expired" severity="danger" />;
            case 'cancelled':
                return <Badge value="Cancelled" severity="warning" />;
            default:
                return <Badge value={status} />;
        }
    };

    const formatDate = (dateString: string): string => {
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    };

    const renderGiftCodeInput = () => (
        <Card title="🎁 Redeem Your Gift Subscription" className="gift-input-card">
            <div className="text-center mb-4">
                <p className="text-lg text-600">
                    Enter your gift code below to redeem your free subscription
                </p>
            </div>

            <div className="field">
                <label htmlFor="giftCode" className="block text-900 font-medium mb-2">
                    Gift Code
                </label>
                <div className="flex gap-2">
                    <InputText
                        id="giftCode"
                        value={giftCode}
                        onChange={(e) => handleCodeChange(e.target.value)}
                        placeholder="XXXX-XXXX-XXXX-XXXX"
                        className="flex-1 gift-code-input"
                        maxLength={19}
                    />
                    <Button
                        label="Check"
                        icon={checking ? "pi pi-spin pi-spinner" : "pi pi-search"}
                        onClick={checkGiftStatus}
                        disabled={checking || !giftCode || giftCode.length < 16}
                    />
                </div>
                <small className="text-600">
                    Enter the 16-character gift code you received
                </small>
            </div>
        </Card>
    );

    const renderGiftDetails = () => {
        if (!giftInfo || !giftStatus) return null;

        return (
            <Card title="Gift Details" className="gift-details-card">
                <div className="grid">
                    <div className="col-12 md:col-8">
                        <div className="gift-info">
                            <div className="flex justify-content-between align-items-center mb-3">
                                <h3 className="m-0">Subscription Gift</h3>
                                {getStatusBadge(giftInfo.status)}
                            </div>

                            <div className="gift-details-grid">
                                <div className="detail-item">
                                    <span className="label">From:</span>
                                    <span className="value">
                                        {giftInfo.custom_sender_name || giftInfo.giver_name}
                                    </span>
                                </div>

                                <div className="detail-item">
                                    <span className="label">Plan:</span>
                                    <span className="value">
                                        {getPlanDisplayName(giftInfo.plan)}
                                    </span>
                                </div>

                                <div className="detail-item">
                                    <span className="label">Billing:</span>
                                    <span className="value">
                                        {getIntervalDisplayName(giftInfo.billing_interval)}
                                    </span>
                                </div>

                                <div className="detail-item">
                                    <span className="label">Value:</span>
                                    <span className="value">
                                        ${giftInfo.amount.toFixed(2)} {giftInfo.currency}
                                    </span>
                                </div>

                                <div className="detail-item">
                                    <span className="label">Expires:</span>
                                    <span className="value">
                                        {formatDate(giftInfo.expires_at)}
                                        {giftStatus.days_until_expiry !== undefined && (
                                            <span className="ml-2 text-orange-500">
                                                ({giftStatus.days_until_expiry} days left)
                                            </span>
                                        )}
                                    </span>
                                </div>
                            </div>

                            {giftInfo.personal_message && (
                                <>
                                    <Divider />
                                    <div className="personal-message">
                                        <h4>Personal Message:</h4>
                                        <div className="message-content">
                                            "{giftInfo.personal_message}"
                                        </div>
                                    </div>
                                </>
                            )}
                        </div>
                    </div>

                    <div className="col-12 md:col-4">
                        <Panel header="Plan Features" className="features-panel">
                            <div className="plan-features">
                                {giftInfo.plan === 'basic' && (
                                    <ul>
                                        <li>• 1 Protected Profile</li>
                                        <li>• 1,000 Monthly Scans</li>
                                        <li>• 50 Takedown Requests</li>
                                        <li>• AI Face Recognition</li>
                                        <li>• Basic Support</li>
                                    </ul>
                                )}
                                {giftInfo.plan === 'professional' && (
                                    <ul>
                                        <li>• 5 Protected Profiles</li>
                                        <li>• 10,000 Monthly Scans</li>
                                        <li>• 500 Takedown Requests</li>
                                        <li>• AI Face Recognition</li>
                                        <li>• Priority Support</li>
                                        <li>• Custom Branding</li>
                                        <li>• Full API Access</li>
                                    </ul>
                                )}
                            </div>
                        </Panel>
                    </div>
                </div>

                {giftStatus.can_be_redeemed && (
                    <div className="text-center mt-4">
                        <Button
                            label={loading ? "Redeeming..." : "Redeem Gift"}
                            icon={loading ? "pi pi-spin pi-spinner" : "pi pi-gift"}
                            onClick={redeemGift}
                            disabled={loading}
                            className="redeem-button"
                            size="large"
                        />
                    </div>
                )}
            </Card>
        );
    };

    const renderSuccessDialog = () => (
        <Dialog
            header="🎉 Gift Redeemed Successfully!"
            visible={showSuccessDialog}
            onHide={() => setShowSuccessDialog(false)}
            modal
            className="success-dialog"
        >
            {success && (
                <div className="text-center">
                    <i className="pi pi-check-circle text-6xl text-green-500 mb-3"></i>
                    <h3>Welcome to your new subscription!</h3>
                    <p className="text-lg mb-3">
                        You've successfully redeemed your {getPlanDisplayName(success.plan || '')} subscription.
                    </p>
                    <p className="text-600 mb-4">
                        Your subscription is now active and ready to use.
                    </p>
                    <div className="flex justify-content-center gap-3">
                        <Button
                            label="Go to Dashboard"
                            icon="pi pi-home"
                            onClick={() => navigate('/dashboard')}
                        />
                        <Button
                            label="View Subscription"
                            icon="pi pi-credit-card"
                            onClick={() => navigate('/billing')}
                            severity="secondary"
                        />
                    </div>
                </div>
            )}
        </Dialog>
    );

    return (
        <div className="gift-redemption-container">
            <div className="max-w-3xl mx-auto">
                <div className="text-center mb-4">
                    <h1 className="text-4xl font-bold text-900 mb-2">
                        Redeem Your Gift
                    </h1>
                    <p className="text-xl text-600">
                        Activate your free subscription with your gift code
                    </p>
                </div>

                {error && (
                    <Message severity="error" text={error} className="mb-4" />
                )}

                {renderGiftCodeInput()}

                {giftInfo && renderGiftDetails()}

                {renderSuccessDialog()}

                <div className="help-section mt-4">
                    <Card>
                        <div className="text-center">
                            <h4>Need Help?</h4>
                            <p className="text-600 mb-3">
                                If you're having trouble redeeming your gift code, here are some common solutions:
                            </p>
                            <ul className="text-left max-w-md mx-auto">
                                <li>• Make sure you've entered the code exactly as received</li>
                                <li>• Check that the code hasn't expired</li>
                                <li>• Ensure you're logged into the correct account</li>
                                <li>• Verify the code hasn't already been redeemed</li>
                            </ul>
                            <div className="mt-3">
                                <Button
                                    label="Contact Support"
                                    icon="pi pi-envelope"
                                    onClick={() => window.location.href = 'mailto:support@autodmca.com'}
                                    severity="secondary"
                                    size="small"
                                />
                            </div>
                        </div>
                    </Card>
                </div>
            </div>
        </div>
    );
};

export default GiftRedemption;