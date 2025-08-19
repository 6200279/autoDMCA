# API Keys Setup Guide - Content Protection Platform

This guide provides step-by-step instructions for obtaining and configuring all external API keys required for the Content Protection Platform.

## Overview
The platform integrates with multiple external services for content scanning, payment processing, and notifications. Each service requires API keys and configuration.

---

## 1. Google Custom Search API

**Purpose**: Search the web for leaked content and infringement detection

### Setup Steps:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing project
3. Enable the Custom Search API:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Custom Search API"
   - Click "Enable"

4. Create API credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "API Key"
   - Copy the API key (GOOGLE_API_KEY)

5. Create Custom Search Engine:
   - Go to [Google Custom Search](https://cse.google.com/)
   - Click "Add" to create new search engine
   - Enter "*" for sites to search (entire web)
   - Create the search engine
   - Copy the Search Engine ID (GOOGLE_CUSTOM_SEARCH_ID)

### Environment Variables:
```bash
GOOGLE_API_KEY=AIzaSy...your-api-key
GOOGLE_CUSTOM_SEARCH_ID=your-search-engine-id
```

### Pricing:
- Free: 100 searches/day
- Paid: $5 per 1,000 queries (up to 10k/day)

---

## 2. Microsoft Bing Web Search API

**Purpose**: Additional search engine coverage for content detection

### Setup Steps:
1. Go to [Azure Portal](https://portal.azure.com/)
2. Create a new "Bing Search v7" resource:
   - Search for "Bing Search v7" in the marketplace
   - Click "Create"
   - Choose subscription and resource group
   - Select pricing tier (F1 for free tier)
   - Create the resource

3. Get API key:
   - Go to your Bing Search resource
   - Navigate to "Keys and Endpoint"
   - Copy Key 1 (BING_API_KEY)

### Environment Variables:
```bash
BING_API_KEY=your-bing-api-key
```

### Pricing:
- Free: 1,000 transactions/month
- S1: $7 per 1,000 transactions

---

## 3. Stripe Payment Processing

**Purpose**: Handle subscription billing and payment processing

### Setup Steps:
1. Go to [Stripe Dashboard](https://dashboard.stripe.com/)
2. Create account or login
3. Get API keys:
   - Navigate to "Developers" > "API keys"
   - Copy "Publishable key" (STRIPE_PUBLISHABLE_KEY)
   - Copy "Secret key" (STRIPE_SECRET_KEY)

4. Set up webhooks:
   - Go to "Developers" > "Webhooks"
   - Click "Add endpoint"
   - Enter your webhook URL: `https://api.yourdomain.com/webhooks/stripe`
   - Select events: `invoice.payment_succeeded`, `customer.subscription.updated`, `customer.subscription.deleted`
   - Copy the webhook signing secret (STRIPE_WEBHOOK_SECRET)

### Environment Variables:
```bash
STRIPE_SECRET_KEY=sk_live_your-secret-key  # Use sk_test_ for testing
STRIPE_PUBLISHABLE_KEY=pk_live_your-publishable-key
STRIPE_WEBHOOK_SECRET=whsec_your-webhook-secret
```

### Test Mode:
Use test keys for development:
```bash
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
```

---

## 4. Email Service (SMTP)

**Purpose**: Send notifications, DMCA notices, and transactional emails

### Option A: Gmail SMTP (Recommended for small-scale)

1. Enable 2-factor authentication on your Gmail account
2. Generate App Password:
   - Go to Google Account settings
   - Security > App passwords
   - Generate password for "Mail"
   - Use this as SMTP_PASSWORD

### Environment Variables:
```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-16-char-app-password
EMAIL_FROM_NAME=Content Protection Platform
EMAIL_FROM_ADDRESS=noreply@yourdomain.com
```

### Option B: SendGrid (Recommended for production)

1. Go to [SendGrid](https://sendgrid.com/)
2. Create account and verify domain
3. Create API key:
   - Go to Settings > API Keys
   - Create API key with "Full Access"

### Environment Variables:
```bash
SMTP_SERVER=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=your-sendgrid-api-key
EMAIL_FROM_NAME=Content Protection Platform
EMAIL_FROM_ADDRESS=noreply@yourdomain.com
```

---

## 5. Twitter/X API

**Purpose**: Monitor Twitter for impersonation and content theft

### Setup Steps:
1. Go to [Twitter Developer Portal](https://developer.twitter.com/)
2. Apply for developer account
3. Create a new app
4. Generate API keys:
   - API Key and Secret
   - Access Token and Secret

### Environment Variables:
```bash
TWITTER_API_KEY=your-api-key
TWITTER_API_SECRET=your-api-secret
TWITTER_ACCESS_TOKEN=your-access-token
TWITTER_ACCESS_TOKEN_SECRET=your-access-token-secret
```

### Pricing:
- Basic: $100/month (up to 10,000 tweets/month)
- Pro: $5,000/month (up to 1M tweets/month)

---

## 6. Facebook/Meta API

**Purpose**: Monitor Facebook and Instagram for content theft

### Setup Steps:
1. Go to [Facebook Developers](https://developers.facebook.com/)
2. Create app for "Business"
3. Add Instagram Basic Display and Facebook Login products
4. Get App ID and App Secret

### Environment Variables:
```bash
FACEBOOK_APP_ID=your-app-id
FACEBOOK_APP_SECRET=your-app-secret
```

### Instagram Access:
For Instagram monitoring, you'll need to implement OAuth flow to get user access tokens.

---

## 7. WhoisXML API

**Purpose**: WHOIS lookups for domain information in DMCA processing

### Setup Steps:
1. Go to [WhoisXML API](https://whoisxmlapi.com/)
2. Sign up for free account
3. Get API key from dashboard

### Environment Variables:
```bash
WHOIS_API_KEY=your-whois-api-key
```

### Pricing:
- Free: 1,000 requests/month
- Paid: Starting at $99/month for 10,000 requests

---

## 8. Cloudflare API (Optional)

**Purpose**: DNS management and CDN integration

### Setup Steps:
1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. Add your domain to Cloudflare
3. Get API key:
   - Go to "My Profile" > "API Tokens"
   - Create token with Zone:Edit permissions

### Environment Variables:
```bash
CLOUDFLARE_API_KEY=your-api-key
CLOUDFLARE_ZONE_ID=your-zone-id
```

---

## 9. Monitoring Services (Optional)

### Sentry Error Tracking

1. Go to [Sentry.io](https://sentry.io/)
2. Create project
3. Get DSN from project settings

```bash
REACT_APP_SENTRY_DSN=https://your-dsn@sentry.io/project-id
```

### Google Analytics

1. Go to [Google Analytics](https://analytics.google.com/)
2. Create property
3. Get Tracking ID

```bash
REACT_APP_GOOGLE_ANALYTICS_ID=GA-XXXXXXXXX
```

---

## API Key Security Best Practices

### 1. Environment Variables
- Never commit API keys to version control
- Use environment variables for all sensitive data
- Rotate keys regularly (quarterly)

### 2. Key Restrictions
- Restrict API keys by IP address when possible
- Limit key permissions to minimum required
- Monitor API key usage for anomalies

### 3. Testing vs Production
- Use separate API keys for testing and production
- Test with staging/sandbox environments when available
- Validate all integrations before going live

---

## Configuration Validation

After setting up all API keys, run the validation script:

```bash
# Test API connectivity
./scripts/validate-production.sh

# Test individual services
curl -X POST "https://api.yourdomain.com/test/google-search"
curl -X POST "https://api.yourdomain.com/test/bing-search"
curl -X POST "https://api.yourdomain.com/test/email"
curl -X POST "https://api.yourdomain.com/test/stripe"
```

---

## Cost Estimation

### Monthly API Costs (Estimated)
- Google Custom Search: $50-200 (10k-40k searches)
- Bing Search API: $35-140 (5k-20k searches)
- Stripe: 2.9% + $0.30 per transaction
- SendGrid: $15-80 (40k-100k emails)
- Twitter API: $100-500 (basic to pro tier)
- WhoisXML: $99-299 (10k-50k lookups)

**Total Monthly: $300-1,200** (depending on usage)

### Free Tier Limitations
- Suitable for testing and small-scale deployments
- Monitor usage to avoid service interruptions
- Upgrade to paid tiers before reaching limits

---

## Support Contacts

For API-specific issues:
- **Google APIs**: [Google Cloud Support](https://cloud.google.com/support/)
- **Microsoft APIs**: [Azure Support](https://azure.microsoft.com/support/)
- **Stripe**: [Stripe Support](https://support.stripe.com/)
- **Twitter**: [Twitter Developer Support](https://developer.twitter.com/support)
- **Facebook**: [Facebook Developer Support](https://developers.facebook.com/support/)

For platform integration issues:
- Technical Support: support@contentprotection.com
- Documentation: https://docs.contentprotection.com

---

**Last Updated**: $(date)
**Version**: 1.0.0