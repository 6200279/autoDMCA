/**
 * Content Protection Platform - JavaScript/Node.js SDK Examples
 * Comprehensive examples for integrating with the Content Protection API using JavaScript
 */

const axios = require('axios');
const crypto = require('crypto');
const EventEmitter = require('events');

/**
 * Main SDK class for Content Protection Platform
 */
class ContentProtectionSDK extends EventEmitter {
    constructor(baseUrl = 'https://api.contentprotection.ai') {
        super();
        this.baseUrl = baseUrl;
        this.accessToken = null;
        this.refreshToken = null;
        this.tokenExpiresAt = null;
        
        // Create axios instance with interceptors
        this.client = axios.create({
            baseURL: baseUrl,
            timeout: 30000
        });
        
        this.setupInterceptors();
    }
    
    /**
     * Setup axios interceptors for automatic token refresh and error handling
     */
    setupInterceptors() {
        // Request interceptor for authentication
        this.client.interceptors.request.use(async (config) => {
            await this.refreshTokenIfNeeded();
            
            if (this.accessToken) {
                config.headers.Authorization = `Bearer ${this.accessToken}`;
            }
            
            return config;
        });
        
        // Response interceptor for error handling
        this.client.interceptors.response.use(
            (response) => response,
            async (error) => {
                const { response } = error;
                
                if (response?.status === 429) {
                    // Handle rate limiting
                    const retryAfter = parseInt(response.headers['x-ratelimit-retry-after']) || 60;
                    console.warn(`Rate limited. Waiting ${retryAfter} seconds...`);
                    
                    await this.sleep(retryAfter * 1000);
                    return this.client.request(error.config);
                }
                
                if (response?.status === 401 && this.refreshToken) {
                    // Token expired, try to refresh
                    try {
                        await this.refreshAccessToken();
                        return this.client.request(error.config);
                    } catch (refreshError) {
                        this.emit('authError', refreshError);
                        throw refreshError;
                    }
                }
                
                throw error;
            }
        );
    }
    
    /**
     * Authenticate with email and password
     */
    async authenticate(email, password, rememberMe = true) {
        try {
            const response = await this.client.post('/api/v1/auth/login', {
                email,
                password,
                remember_me: rememberMe
            });
            
            const { access_token, refresh_token, expires_in } = response.data;
            
            this.accessToken = access_token;
            this.refreshToken = refresh_token;
            
            // Calculate expiration with 5-minute buffer
            this.tokenExpiresAt = new Date(Date.now() + (expires_in - 300) * 1000);
            
            this.emit('authenticated', response.data);
            console.log('Authentication successful');
            
            return response.data;
        } catch (error) {
            this.emit('authError', error);
            throw this.handleError(error);
        }
    }
    
    /**
     * Refresh access token if needed
     */
    async refreshTokenIfNeeded() {
        if (this.tokenExpiresAt && new Date() >= this.tokenExpiresAt) {
            await this.refreshAccessToken();
        }
    }
    
    /**
     * Refresh access token using refresh token
     */
    async refreshAccessToken() {
        if (!this.refreshToken) {
            throw new Error('No refresh token available. Please re-authenticate.');
        }
        
        try {
            const response = await axios.post(`${this.baseUrl}/api/v1/auth/refresh`, {
                refresh_token: this.refreshToken
            });
            
            const { access_token, refresh_token, expires_in } = response.data;
            
            this.accessToken = access_token;
            this.refreshToken = refresh_token;
            this.tokenExpiresAt = new Date(Date.now() + (expires_in - 300) * 1000);
            
            console.log('Token refreshed successfully');
        } catch (error) {
            this.accessToken = null;
            this.refreshToken = null;
            this.tokenExpiresAt = null;
            throw error;
        }
    }
    
    /**
     * Handle API errors consistently
     */
    handleError(error) {
        const response = error.response;
        if (response) {
            const { status, data } = response;
            const errorData = data || {};
            
            switch (status) {
                case 400:
                    return new ValidationError(errorData.detail || 'Validation failed', errorData);
                case 401:
                    return new AuthenticationError(errorData.detail || 'Authentication required', errorData);
                case 403:
                    return new PermissionError(errorData.detail || 'Access denied', errorData);
                case 404:
                    return new NotFoundError(errorData.detail || 'Resource not found', errorData);
                case 429:
                    return new RateLimitError(errorData.detail || 'Rate limit exceeded', errorData);
                case 500:
                    return new ServerError(errorData.detail || 'Internal server error', errorData);
                default:
                    return new APIError(`HTTP ${status}: ${errorData.detail || 'Unknown error'}`, errorData);
            }
        }
        
        return error;
    }
    
    /**
     * Utility method for delays
     */
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

/**
 * Profile management class
 */
class ProfileManager {
    constructor(sdk) {
        this.sdk = sdk;
    }
    
    /**
     * Create a new protected profile
     */
    async create({ name, platform, username, keywords = [] }) {
        try {
            const response = await this.sdk.client.post('/api/v1/profiles', {
                name,
                platform,
                username,
                keywords,
                monitoring_enabled: true
            });
            
            return response.data;
        } catch (error) {
            throw this.sdk.handleError(error);
        }
    }
    
    /**
     * Upload reference content for AI signature generation
     */
    async uploadReferenceContent(profileId, imageUrls) {
        try {
            const response = await this.sdk.client.post('/api/v1/scanning/profile/signatures', {
                profile_id: profileId,
                image_urls: imageUrls.slice(0, 10) // Limit to 10 images
            });
            
            return response.data;
        } catch (error) {
            throw this.sdk.handleError(error);
        }
    }
    
    /**
     * Get profile details
     */
    async get(profileId) {
        try {
            const response = await this.sdk.client.get(`/api/v1/profiles/${profileId}`);
            return response.data;
        } catch (error) {
            throw this.sdk.handleError(error);
        }
    }
    
    /**
     * List all profiles
     */
    async list({ limit = 50, offset = 0 } = {}) {
        try {
            const response = await this.sdk.client.get('/api/v1/profiles', {
                params: { limit, offset }
            });
            return response.data;
        } catch (error) {
            throw this.sdk.handleError(error);
        }
    }
    
    /**
     * Update profile settings
     */
    async update(profileId, updates) {
        try {
            const response = await this.sdk.client.put(`/api/v1/profiles/${profileId}`, updates);
            return response.data;
        } catch (error) {
            throw this.sdk.handleError(error);
        }
    }
}

/**
 * Scanning operations class
 */
class ScanningManager {
    constructor(sdk) {
        this.sdk = sdk;
    }
    
    /**
     * Trigger manual scan for unauthorized content
     */
    async triggerManualScan(profileId) {
        try {
            const response = await this.sdk.client.post('/api/v1/scanning/scan/manual', null, {
                params: { profile_id: profileId }
            });
            
            return response.data;
        } catch (error) {
            throw this.sdk.handleError(error);
        }
    }
    
    /**
     * Scan specific URL for content matches
     */
    async scanUrl(url, profileId) {
        try {
            const response = await this.sdk.client.post('/api/v1/scanning/scan/url', null, {
                params: { url, profile_id: profileId }
            });
            
            return response.data;
        } catch (error) {
            throw this.sdk.handleError(error);
        }
    }
    
    /**
     * Get scan job status
     */
    async getScanStatus(jobId) {
        try {
            const response = await this.sdk.client.get(`/api/v1/scanning/scan/status/${jobId}`);
            return response.data;
        } catch (error) {
            throw this.sdk.handleError(error);
        }
    }
    
    /**
     * Wait for scan completion with progress monitoring
     */
    async waitForScanCompletion(jobId, timeout = 300000) { // 5 minutes default
        return new Promise((resolve, reject) => {
            const startTime = Date.now();
            const interval = 30000; // Check every 30 seconds
            
            const checkStatus = async () => {
                try {
                    if (Date.now() - startTime > timeout) {
                        reject(new Error(`Scan ${jobId} did not complete within timeout`));
                        return;
                    }
                    
                    const status = await this.getScanStatus(jobId);
                    
                    // Emit progress event
                    this.sdk.emit('scanProgress', { jobId, status });
                    
                    if (status.status === 'completed') {
                        this.sdk.emit('scanCompleted', { jobId, results: status.results });
                        resolve(status);
                    } else if (status.status === 'failed') {
                        const error = new Error(`Scan ${jobId} failed: ${status.error || 'Unknown error'}`);
                        this.sdk.emit('scanFailed', { jobId, error });
                        reject(error);
                    } else {
                        // Still in progress, check again later
                        setTimeout(checkStatus, interval);
                    }
                } catch (error) {
                    reject(error);
                }
            };
            
            checkStatus();
        });
    }
    
    /**
     * Get scanning history
     */
    async getHistory({ profileId, limit = 50, offset = 0 } = {}) {
        try {
            const params = { limit, offset };
            if (profileId) params.profile_id = profileId;
            
            const response = await this.sdk.client.get('/api/v1/scanning/scan/history', { params });
            return response.data;
        } catch (error) {
            throw this.sdk.handleError(error);
        }
    }
    
    /**
     * Configure automated scanning schedule
     */
    async configureSchedule(profileId, { frequency = 'daily', time = '02:00', platforms = ['google', 'bing'] }) {
        try {
            const response = await this.sdk.client.post('/api/v1/scanning/scan/schedule', {
                profile_id: profileId,
                schedule: {
                    frequency,
                    time,
                    platforms
                }
            });
            
            return response.data;
        } catch (error) {
            throw this.sdk.handleError(error);
        }
    }
}

/**
 * Infringement management class
 */
class InfringementManager {
    constructor(sdk) {
        this.sdk = sdk;
    }
    
    /**
     * List detected infringements with filters
     */
    async list({ profileId, status, minConfidence = 0.0, limit = 50, offset = 0 } = {}) {
        try {
            const params = { limit, offset };
            
            if (profileId) params.profile_id = profileId;
            if (status) params.status = status;
            if (minConfidence > 0) params.min_confidence = minConfidence;
            
            const response = await this.sdk.client.get('/api/v1/infringements', { params });
            return response.data;
        } catch (error) {
            throw this.sdk.handleError(error);
        }
    }
    
    /**
     * Get detailed infringement information
     */
    async get(infringementId) {
        try {
            const response = await this.sdk.client.get(`/api/v1/infringements/${infringementId}`);
            return response.data;
        } catch (error) {
            throw this.sdk.handleError(error);
        }
    }
    
    /**
     * Update infringement status
     */
    async updateStatus(infringementId, status, notes = null) {
        try {
            const data = { status };
            if (notes) data.notes = notes;
            
            const response = await this.sdk.client.put(`/api/v1/infringements/${infringementId}`, data);
            return response.data;
        } catch (error) {
            throw this.sdk.handleError(error);
        }
    }
    
    /**
     * Process multiple infringements in bulk
     */
    async bulkProcess(infringementIds, action, options = {}) {
        try {
            const response = await this.sdk.client.post('/api/v1/infringements/bulk', {
                infringement_ids: infringementIds,
                action,
                ...options
            });
            
            return response.data;
        } catch (error) {
            throw this.sdk.handleError(error);
        }
    }
}

/**
 * DMCA takedown management class
 */
class TakedownManager {
    constructor(sdk) {
        this.sdk = sdk;
    }
    
    /**
     * Submit DMCA takedown request
     */
    async submit(infringementId, { urgency = 'normal', additionalInfo, templateId } = {}) {
        try {
            const data = {
                infringement_id: infringementId,
                urgency
            };
            
            if (additionalInfo) data.additional_info = additionalInfo;
            if (templateId) data.template_id = templateId;
            
            const response = await this.sdk.client.post('/api/v1/takedowns', data);
            return response.data;
        } catch (error) {
            throw this.sdk.handleError(error);
        }
    }
    
    /**
     * Get takedown request status
     */
    async getStatus(takedownId) {
        try {
            const response = await this.sdk.client.get(`/api/v1/takedowns/${takedownId}`);
            return response.data;
        } catch (error) {
            throw this.sdk.handleError(error);
        }
    }
    
    /**
     * List takedown requests with filters
     */
    async list({ status, platform, limit = 50, offset = 0 } = {}) {
        try {
            const params = { limit, offset };
            
            if (status) params.status = status;
            if (platform) params.platform = platform;
            
            const response = await this.sdk.client.get('/api/v1/takedowns', { params });
            return response.data;
        } catch (error) {
            throw this.sdk.handleError(error);
        }
    }
    
    /**
     * Cancel pending takedown request
     */
    async cancel(takedownId, reason) {
        try {
            const response = await this.sdk.client.post(`/api/v1/takedowns/${takedownId}/cancel`, {
                reason
            });
            return response.data;
        } catch (error) {
            throw this.sdk.handleError(error);
        }
    }
}

/**
 * Webhook management class
 */
class WebhookManager {
    constructor(sdk) {
        this.sdk = sdk;
    }
    
    /**
     * Create webhook endpoint
     */
    async create(url, events, secret = null) {
        try {
            const data = { url, events };
            if (secret) data.secret = secret;
            
            const response = await this.sdk.client.post('/api/v1/webhooks', data);
            return response.data;
        } catch (error) {
            throw this.sdk.handleError(error);
        }
    }
    
    /**
     * List configured webhooks
     */
    async list() {
        try {
            const response = await this.sdk.client.get('/api/v1/webhooks');
            return response.data;
        } catch (error) {
            throw this.sdk.handleError(error);
        }
    }
    
    /**
     * Delete webhook
     */
    async delete(webhookId) {
        try {
            const response = await this.sdk.client.delete(`/api/v1/webhooks/${webhookId}`);
            return response.data;
        } catch (error) {
            throw this.sdk.handleError(error);
        }
    }
    
    /**
     * Verify webhook signature for security
     */
    static verifySignature(payload, signature, secret) {
        const expectedSignature = crypto
            .createHmac('sha256', secret)
            .update(payload)
            .digest('hex');
        
        return crypto.timingSafeEqual(
            Buffer.from(`sha256=${expectedSignature}`),
            Buffer.from(signature)
        );
    }
}

/**
 * Main API client that combines all managers
 */
class ContentProtectionClient extends ContentProtectionSDK {
    constructor(baseUrl) {
        super(baseUrl);
        
        // Initialize all managers
        this.profiles = new ProfileManager(this);
        this.scanning = new ScanningManager(this);
        this.infringements = new InfringementManager(this);
        this.takedowns = new TakedownManager(this);
        this.webhooks = new WebhookManager(this);
    }
}

// Custom error classes
class APIError extends Error {
    constructor(message, errorData = {}) {
        super(message);
        this.name = 'APIError';
        this.errorData = errorData;
    }
}

class ValidationError extends APIError {
    constructor(message, errorData) {
        super(message, errorData);
        this.name = 'ValidationError';
    }
}

class AuthenticationError extends APIError {
    constructor(message, errorData) {
        super(message, errorData);
        this.name = 'AuthenticationError';
    }
}

class PermissionError extends APIError {
    constructor(message, errorData) {
        super(message, errorData);
        this.name = 'PermissionError';
    }
}

class NotFoundError extends APIError {
    constructor(message, errorData) {
        super(message, errorData);
        this.name = 'NotFoundError';
    }
}

class RateLimitError extends APIError {
    constructor(message, errorData) {
        super(message, errorData);
        this.name = 'RateLimitError';
    }
}

class ServerError extends APIError {
    constructor(message, errorData) {
        super(message, errorData);
        this.name = 'ServerError';
    }
}

/**
 * Complete example workflow
 */
async function exampleWorkflow() {
    try {
        // Initialize client
        const client = new ContentProtectionClient();
        
        // Set up event listeners
        client.on('authenticated', (data) => {
            console.log('🔐 Authentication successful');
        });
        
        client.on('scanProgress', ({ jobId, status }) => {
            console.log(`📊 Scan ${jobId} status: ${status.status}`);
        });
        
        client.on('scanCompleted', ({ jobId, results }) => {
            console.log(`✅ Scan ${jobId} completed with ${results.infringements_found} matches`);
        });
        
        // Authenticate
        await client.authenticate('creator@example.com', 'secure_password');
        
        // Create profile
        console.log('📝 Creating protected profile...');
        const profile = await client.profiles.create({
            name: 'Content Creator',
            platform: 'onlyfans',
            username: 'creator_username',
            keywords: ['creator name', 'username', 'exclusive content']
        });
        
        console.log(`✅ Profile created with ID: ${profile.id}`);
        
        // Upload reference content
        console.log('📸 Uploading reference content...');
        const referenceImages = [
            'https://example.com/reference1.jpg',
            'https://example.com/reference2.jpg'
        ];
        
        const signatures = await client.profiles.uploadReferenceContent(profile.id, referenceImages);
        console.log(`✅ Generated ${signatures.signatures_generated.face_encodings} face encodings`);
        
        // Configure monitoring
        console.log('⏰ Configuring scan schedule...');
        await client.scanning.configureSchedule(profile.id, {
            frequency: 'daily',
            time: '02:00',
            platforms: ['google', 'bing', 'social_media']
        });
        
        // Trigger manual scan
        console.log('🔍 Triggering manual scan...');
        const scanResult = await client.scanning.triggerManualScan(profile.id);
        console.log(`✅ Scan initiated with job ID: ${scanResult.job_id}`);
        
        // Wait for scan completion
        console.log('⏳ Waiting for scan to complete...');
        const finalStatus = await client.scanning.waitForScanCompletion(scanResult.job_id);
        
        // Process infringements
        console.log('🚨 Processing detected infringements...');
        const infringements = await client.infringements.list({
            profileId: profile.id,
            status: 'detected',
            minConfidence: 0.8
        });
        
        for (const infringement of infringements.items) {
            const confidence = infringement.confidence_score;
            const url = infringement.url;
            
            console.log(`🎯 Found infringement at ${url} (confidence: ${confidence.toFixed(2)})`);
            
            if (confidence > 0.9) {
                // High confidence - submit takedown immediately
                const takedown = await client.takedowns.submit(infringement.id, {
                    urgency: 'high',
                    additionalInfo: 'High-confidence match found through AI analysis'
                });
                console.log(`📨 Takedown submitted: ${takedown.id}`);
            } else if (confidence > 0.8) {
                // Medium confidence - mark for manual review
                await client.infringements.updateStatus(
                    infringement.id,
                    'pending_review',
                    'Medium confidence - requires manual verification'
                );
            }
        }
        
        // Set up webhooks
        console.log('🔗 Setting up webhooks...');
        const webhook = await client.webhooks.create(
            'https://your-app.com/webhooks/contentprotection',
            ['scan.completed', 'infringement.detected', 'takedown.status_changed'],
            'your-webhook-secret'
        );
        console.log(`✅ Webhook created: ${webhook.id}`);
        
        console.log('🎉 Setup complete! Your content is now being protected.');
        
    } catch (error) {
        console.error('❌ Error:', error.message);
        
        if (error instanceof AuthenticationError) {
            console.error('Please check your credentials and try again.');
        } else if (error instanceof RateLimitError) {
            console.error('Rate limit exceeded. Please wait before making more requests.');
        } else if (error instanceof ValidationError) {
            console.error('Validation failed:', error.errorData);
        }
    }
}

// Express.js webhook handler example
const express = require('express');
const app = express();

app.use(express.raw({ type: 'application/json' }));

app.post('/webhooks/contentprotection', (req, res) => {
    const signature = req.headers['x-contentprotection-signature'];
    const payload = req.body.toString();
    const secret = process.env.WEBHOOK_SECRET;
    
    // Verify signature
    if (!WebhookManager.verifySignature(payload, signature, secret)) {
        return res.status(401).send('Invalid signature');
    }
    
    const event = JSON.parse(payload);
    
    switch (event.event) {
        case 'scan.completed':
            console.log(`Scan completed for profile ${event.data.profile_id}`);
            // Handle scan completion
            break;
            
        case 'infringement.detected':
            console.log(`New infringement detected: ${event.data.url}`);
            // Handle new infringement
            break;
            
        case 'takedown.status_changed':
            console.log(`Takedown ${event.data.takedown_id} status changed to ${event.data.new_status}`);
            // Handle takedown status change
            break;
    }
    
    res.status(200).send('OK');
});

// Export everything
module.exports = {
    ContentProtectionClient,
    ContentProtectionSDK,
    ProfileManager,
    ScanningManager,
    InfringementManager,
    TakedownManager,
    WebhookManager,
    // Error classes
    APIError,
    ValidationError,
    AuthenticationError,
    PermissionError,
    NotFoundError,
    RateLimitError,
    ServerError
};

// Run example if called directly
if (require.main === module) {
    exampleWorkflow().catch(console.error);
}