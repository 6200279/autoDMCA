# Social Media Protection Management Screen - Comprehensive Design Specification

## 1. Screen Overview & Purpose

### Primary Function
The Social Media Protection Management screen serves as the central hub for monitoring, detecting, and managing content infringements across major social media platforms. It provides platform-specific tools, real-time monitoring capabilities, and automated protection workflows tailored to each social media platform's unique characteristics and APIs.

### User Goals
- Monitor content across multiple social media platforms simultaneously
- Set up platform-specific detection rules and algorithms
- Manage social media account connections and permissions
- Track platform-specific takedown success rates and response times
- Configure automated responses and escalation workflows
- Analyze social media protection performance and trends

### Business Context
This screen is essential for content creators, influencers, and agencies who need specialized protection for social media content. Each platform has unique content formats, APIs, user behaviors, and takedown procedures, requiring tailored protection strategies and monitoring approaches.

## 2. Layout Architecture

### Primary Layout Structure
```
┌─────────────────────────────────────────────────────────────────┐
│ Header: "Social Media Protection" + [Platform Status] [Sync All]│
│ Subtitle: "Real-time monitoring across social platforms"       │
├─────────────────────────────────────────────────────────────────┤
│ [IG: Connected] [TT: Pending] [YT: Active] [TW: Disconnected]   │
├─────────────────────────────────────────────────────────────────┤
│ ┌─ Platform Overview ─┐┌─ Active Monitoring ─┐┌─ Analytics ─┐    │
│ │ Instagram    [✓]    ││ Real-time Feeds      ││ Platform    │    │
│ │ • 15K followers     ││ ┌─────────────────┐  ││ Performance │    │
│ │ • 847 posts         ││ │ @user reposted  │  ││ [Chart]     │    │
│ │ • Last scan: 2m ago ││ │ your content    │  ││             │    │
│ │ [Configure] [Scan]  ││ │ [Instagram] 3m  │  ││ Success     │    │
│ │                     ││ │ [View] [Report] │  ││ Rates       │    │
│ │ TikTok       [!]    ││ └─────────────────┘  ││ [Table]     │    │
│ │ • Setup required    ││ [Load More Alerts]   ││             │    │
│ │ [Connect Account]   ││                      ││             │    │
│ └─────────────────────┘└──────────────────────┘└─────────────┘    │
└─────────────────────────────────────────────────────────────────┘

Platform Configuration Modal:
┌─────────────────────────────────┐
│ ✕ Configure Instagram Protection│
├─────────────────────────────────┤
│ Account Connection:             │
│ • @username [Connected ✓]      │
│ • Permissions: Read, Report     │
│ [Reconnect] [Test Connection]   │
│                                 │
│ Monitoring Settings:            │
│ ☑ Monitor reposts              │
│ ☑ Track hashtag usage          │
│ ☑ Detect story mentions        │
│ ☑ Scan comments for links      │
│                                 │
│ Detection Sensitivity:          │
│ High ●●●○○ Balanced            │
│                                 │
│ Auto-Actions:                   │
│ ☑ Auto-report obvious theft    │
│ ☐ Auto-comment with warning    │
│ ☑ Notify user immediately      │
│                                 │
│ [Save Settings] [Cancel]        │
│ [Advanced Options...]           │
└─────────────────────────────────┘
```

### Tab Structure
- **Tab 1**: Platform Overview (connection status and quick actions)
- **Tab 2**: Real-time Monitoring (live detection feeds and alerts)
- **Tab 3**: Protection Analytics (performance metrics and insights)
- **Tab 4**: Platform Settings (configuration and automation rules)

### Grid System
- **Desktop**: Three-column layout (platform list, monitoring feed, analytics sidebar)
- **Tablet**: Two-column with collapsible sidebar
- **Mobile**: Single column with tabbed navigation

### Responsive Breakpoints
- **Large (1200px+)**: Full three-column dashboard layout
- **Medium (768-1199px)**: Two-column with collapsible third column
- **Small (576-767px)**: Single column with tab navigation
- **Extra Small (<576px)**: Mobile-optimized single column cards

## 3. Visual Design System

### Color Palette
```css
/* Platform Brand Colors */
--instagram-primary: #E4405F
--instagram-gradient: linear-gradient(45deg, #f09433 0%,#e6683c 25%,#dc2743 50%,#cc2366 75%,#bc1888 100%)
--tiktok-primary: #000000
--tiktok-accent: #ff0050
--youtube-primary: #FF0000
--youtube-secondary: #282828
--twitter-primary: #1DA1F2
--twitter-secondary: #14171A
--facebook-primary: #1877F2
--facebook-secondary: #42A5F5
--linkedin-primary: #0A66C2
--snapchat-primary: #FFFC00
--pinterest-primary: #BD081C
--reddit-primary: #FF4500

/* Connection Status Colors */
--status-connected: #10b981 (emerald-500)
--status-pending: #f59e0b (amber-500)
--status-error: #ef4444 (red-500)
--status-disconnected: #6b7280 (gray-500)
--status-syncing: #3b82f6 (blue-500)

/* Alert Colors */
--alert-urgent: #dc2626 (red-600)
--alert-high: #f59e0b (amber-500)
--alert-medium: #3b82f6 (blue-500)
--alert-low: #10b981 (emerald-500)

/* Background Colors */
--surface-ground: #ffffff
--surface-section: #f8fafc
--surface-card: #ffffff
--surface-overlay: rgba(0,0,0,0.6)

/* Monitoring Feed Colors */
--feed-background: #f8fafc (gray-50)
--feed-item-hover: #f1f5f9 (slate-100)
--feed-border: #e2e8f0 (slate-200)
--feed-timestamp: #64748b (slate-500)
```

### Typography
```css
/* Headers */
.page-title: 28px/1.2 'Inter', weight-700, color-gray-900
.page-subtitle: 14px/1.5 'Inter', weight-400, color-gray-600
.platform-name: 18px/1.3 'Inter', weight-600, color-gray-900
.section-title: 16px/1.3 'Inter', weight-600, color-gray-800

/* Platform Cards */
.platform-status: 14px/1.3 'Inter', weight-500, color-themed
.platform-stats: 12px/1.2 'Inter', weight-400, color-gray-600
.connection-label: 11px/1.2 'Inter', weight-600, uppercase, color-white
.sync-timestamp: 11px/1.2 'Inter', weight-400, color-gray-500

/* Monitoring Feed */
.feed-title: 14px/1.4 'Inter', weight-600, color-gray-900
.feed-platform: 12px/1.2 'Inter', weight-500, color-white
.feed-description: 13px/1.4 'Inter', weight-400, color-gray-700
.feed-timestamp: 11px/1.2 'Inter', weight-400, color-gray-500
.feed-action: 12px/1.3 'Inter', weight-500, color-themed

/* Configuration Modal */
.config-section: 16px/1.3 'Inter', weight-600, color-gray-800
.config-label: 14px/1.3 'Inter', weight-500, color-gray-700
.config-description: 12px/1.4 'Inter', weight-400, color-gray-600
.config-value: 13px/1.3 'Inter', weight-500, color-gray-900
```

### Spacing System
```css
/* Component Spacing */
--spacing-xs: 4px
--spacing-sm: 8px
--spacing-md: 16px
--spacing-lg: 24px
--spacing-xl: 32px
--spacing-2xl: 48px

/* Layout Spacing */
--container-padding: 24px
--section-gap: 32px
--platform-card-padding: 20px
--feed-item-padding: 16px
--modal-padding: 24px
--status-badge-padding: 4px 8px
```

## 4. Interactive Components Breakdown

### Platform Connection Cards
**Purpose**: Visual overview of each social media platform's connection status

**Card Structure**:
```
┌─────────────────────────────────┐
│ [IG Logo] Instagram       [✓]   │
│ @username                       │
│ • 15.2K followers               │
│ • 847 posts monitored           │
│ • Last scan: 2 minutes ago      │
│ [Configure] [Scan Now]          │
└─────────────────────────────────┘
```

**Connection States**:
- **Connected**: Green checkmark, live data, all actions available
- **Pending**: Amber warning, partial data, limited actions
- **Error**: Red alert, error message, troubleshooting actions
- **Disconnected**: Gray status, setup prompt, connection wizard
- **Syncing**: Blue indicator, progress animation, current activity

**Interactive Features**:
- **Real-time Status**: Live connection status updates
- **Quick Actions**: Immediate scan, configuration, reconnection
- **Platform Branding**: Authentic platform colors and logos
- **Statistics Display**: Follower counts, post counts, scan frequency
- **Error Handling**: Clear error messages with resolution steps

### Real-time Monitoring Feed
**Purpose**: Live stream of detected infringements and platform activity

**Feed Item Structure**:
```
┌─────────────────────────────────┐
│ 🚨 [IG] High Priority Alert     │
│ @suspicious_user reposted your  │
│ content without permission      │
│ Original: instagram.com/p/xyz   │
│ Infringing: instagram.com/p/abc │
│ Detected: 3 minutes ago         │
│ [View Details] [Report Now]     │
│ [Mark False Positive]           │
└─────────────────────────────────┘
```

**Alert Types**:
- **Repost Detection**: Direct content reposts without permission
- **Story Mentions**: Content shared in stories without credit
- **Hashtag Abuse**: Unauthorized use of branded hashtags
- **Comment Spam**: Links to pirated content in comments
- **Profile Impersonation**: Fake profiles using creator's content
- **Bio Link Theft**: Unauthorized links in user bios

**Real-time Features**:
- **WebSocket Updates**: Live feed updates without page refresh
- **Priority Sorting**: High-priority alerts appear first
- **Batch Actions**: Select multiple alerts for bulk processing
- **Auto-refresh**: Configurable refresh intervals
- **Filtering**: Filter by platform, alert type, priority level

### Platform Configuration Modal
**Purpose**: Comprehensive settings for each social media platform

**Configuration Sections**:
1. **Account Connection**:
   - OAuth connection management
   - Permission scope settings
   - Connection testing tools
   - Multiple account support

2. **Monitoring Settings**:
   - Content type selection (posts, stories, reels, etc.)
   - Hashtag monitoring configuration
   - Keyword and phrase tracking
   - Geographic monitoring settings

3. **Detection Sensitivity**:
   - AI similarity thresholds
   - False positive filtering
   - Detection algorithm selection
   - Custom rule creation

4. **Auto-Actions**:
   - Automated reporting settings
   - Response templates
   - Escalation workflows
   - Notification preferences

5. **Advanced Options**:
   - API rate limiting
   - Scan frequency settings
   - Data retention policies
   - Integration webhooks

### Analytics Dashboard Component
**Purpose**: Platform-specific performance metrics and insights

**Analytics Sections**:
1. **Platform Performance**:
   - Detection success rates per platform
   - Response time comparisons
   - Content type vulnerability analysis
   - Geographic infringement patterns

2. **Trend Analysis**:
   - Infringement volume trends
   - Platform-specific seasonal patterns
   - Hashtag usage analytics
   - Viral content tracking

3. **Success Metrics**:
   - Takedown success rates by platform
   - Average response times
   - False positive rates
   - User engagement protection

**Interactive Charts**:
- **Line Charts**: Infringement trends over time
- **Bar Charts**: Platform comparison metrics
- **Pie Charts**: Content type distribution
- **Heatmaps**: Geographic infringement patterns
- **Progress Bars**: Platform-specific success rates

### Automated Workflow Builder
**Purpose**: Create platform-specific automated protection workflows

**Workflow Components**:
- **Triggers**: Detection events that start workflows
- **Conditions**: Rules to filter and prioritize actions
- **Actions**: Automated responses and notifications
- **Escalations**: Multi-step protection processes
- **Notifications**: User and team alert configurations

**Workflow Templates**:
- **Instagram Story Protection**: Auto-report story reposts
- **TikTok Duet Monitoring**: Track unauthorized duets/stitches
- **Twitter Thread Protection**: Monitor thread screenshots
- **YouTube Short Detection**: Cross-platform short video monitoring
- **Multi-platform Campaign**: Coordinated protection across platforms

## 5. Interaction Patterns & User Flows

### Platform Connection Flow
1. **Platform Selection**: User chooses social media platform to connect
2. **OAuth Initiation**: Redirect to platform authentication
3. **Permission Grant**: User grants required permissions
4. **Account Verification**: System verifies account access and permissions
5. **Configuration Setup**: Initial monitoring settings configuration
6. **Test Scan**: Perform initial scan to verify connectivity
7. **Monitoring Activation**: Platform monitoring becomes active

### Alert Response Flow
1. **Alert Detection**: System detects potential infringement
2. **Priority Assessment**: Algorithm assigns priority level
3. **User Notification**: Real-time alert delivered to user
4. **Alert Review**: User reviews detection details and evidence
5. **Action Selection**: Choose response (report, ignore, escalate)
6. **Platform Reporting**: Automated or manual report submission
7. **Status Tracking**: Monitor platform response and resolution
8. **Follow-up Actions**: Escalation if needed, documentation

### Configuration Management Flow
1. **Platform Selection**: Choose platform to configure
2. **Settings Review**: Review current configuration settings
3. **Modification**: Update monitoring rules, sensitivity, actions
4. **Testing**: Test new settings with sample content
5. **Validation**: Ensure settings work as expected
6. **Deployment**: Apply new configuration to live monitoring
7. **Monitoring**: Track performance of new settings
8. **Optimization**: Fine-tune based on results

### Multi-platform Campaign Flow
1. **Campaign Creation**: Define protection campaign scope
2. **Platform Selection**: Choose participating platforms
3. **Rule Configuration**: Set platform-specific detection rules
4. **Content Definition**: Define protected content sets
5. **Workflow Setup**: Create automated response workflows
6. **Launch**: Activate cross-platform monitoring
7. **Management**: Monitor campaign performance across platforms
8. **Optimization**: Adjust settings based on effectiveness

## 6. Content Strategy & Messaging

### Primary Headings
- **Page Title**: "Social Media Protection"
- **Page Subtitle**: "Real-time monitoring across social platforms"
- **Section Titles**: "Platform Overview", "Active Monitoring", "Protection Analytics", "Configuration"

### Platform Status Labels
```javascript
const platformStatusLabels = {
  'connected': 'Connected',
  'pending': 'Pending Setup',
  'error': 'Connection Error',
  'disconnected': 'Not Connected',
  'syncing': 'Syncing...',
  'rate_limited': 'Rate Limited',
  'maintenance': 'Platform Maintenance'
};

const platformStatusDescriptions = {
  'connected': 'Actively monitoring for infringements',
  'pending': 'Waiting for account connection approval',
  'error': 'Unable to connect - check permissions',
  'disconnected': 'Click to connect this platform',
  'syncing': 'Updating data from platform',
  'rate_limited': 'Waiting for API rate limit reset',
  'maintenance': 'Platform temporarily unavailable'
};
```

### Alert Priority Labels
```javascript
const alertPriorityLabels = {
  'urgent': 'URGENT',
  'high': 'HIGH',
  'medium': 'MEDIUM',
  'low': 'LOW',
  'info': 'INFO'
};

const alertTypeLabels = {
  'repost': 'Content Repost',
  'story_share': 'Story Share',
  'hashtag_abuse': 'Hashtag Misuse',
  'comment_spam': 'Comment Spam',
  'profile_impersonation': 'Profile Impersonation',
  'bio_link_theft': 'Bio Link Theft',
  'viral_spread': 'Viral Spread Alert'
};
```

### Platform-specific Action Labels
```javascript
const platformActions = {
  'instagram': {
    'report_post': 'Report Post to Instagram',
    'report_story': 'Report Story to Instagram',
    'report_profile': 'Report Profile to Instagram',
    'dm_user': 'Send Direct Message',
    'comment_warning': 'Post Warning Comment'
  },
  'tiktok': {
    'report_video': 'Report Video to TikTok',
    'report_profile': 'Report Profile to TikTok',
    'report_duet': 'Report Duet/Stitch',
    'message_user': 'Send Private Message'
  },
  'youtube': {
    'copyright_claim': 'File Copyright Claim',
    'report_video': 'Report Video to YouTube',
    'report_channel': 'Report Channel',
    'community_strike': 'Request Community Strike'
  },
  'twitter': {
    'dmca_report': 'File DMCA Report',
    'report_tweet': 'Report Tweet',
    'report_profile': 'Report Profile',
    'reply_warning': 'Reply with Warning'
  }
};
```

### Configuration Form Labels
```javascript
const configurationLabels = {
  monitoring: {
    posts: 'Monitor regular posts',
    stories: 'Monitor stories/temporary content',
    reels: 'Monitor short-form videos',
    comments: 'Scan comments for infringing links',
    hashtags: 'Track branded hashtag usage',
    mentions: 'Monitor account mentions',
    direct_messages: 'Scan direct messages (if permitted)'
  },
  sensitivity: {
    very_high: 'Very High (90%+ similarity)',
    high: 'High (80%+ similarity)',
    balanced: 'Balanced (70%+ similarity)',
    low: 'Low (60%+ similarity)',
    custom: 'Custom threshold'
  },
  actions: {
    auto_report: 'Automatically report obvious theft',
    auto_message: 'Send automated warning messages',
    notify_immediately: 'Send immediate notifications',
    escalate_viral: 'Auto-escalate viral infringements',
    create_evidence: 'Automatically capture evidence'
  }
};
```

### Toast Messages
```javascript
const toastMessages = {
  success: {
    platformConnected: 'Successfully connected to {platform}',
    scanCompleted: '{platform} scan completed - {count} items checked',
    reportSubmitted: 'Report submitted to {platform} successfully',
    configurationSaved: '{platform} configuration updated',
    alertDismissed: 'Alert marked as resolved',
    bulkActionCompleted: '{count} alerts processed successfully'
  },
  error: {
    connectionFailed: 'Failed to connect to {platform}',
    scanFailed: 'Scan failed for {platform} - {error}',
    reportFailed: 'Failed to submit report to {platform}',
    configurationFailed: 'Failed to save {platform} configuration',
    rateLimited: '{platform} rate limit reached - try again later',
    permissionDenied: 'Insufficient permissions for {platform}'
  },
  warning: {
    connectionExpired: '{platform} connection expired - please reconnect',
    rateLimitApproaching: 'Approaching {platform} rate limit',
    maintenanceMode: '{platform} is currently in maintenance mode',
    lowSensitivity: 'Low sensitivity may miss some infringements'
  },
  info: {
    scanStarted: 'Starting {platform} scan...',
    newAlert: 'New {priority} priority alert from {platform}',
    configurationTest: 'Testing {platform} configuration...',
    syncInProgress: 'Syncing data from {platform}...'
  }
};
```

## 7. Data Structure & Content Types

### Platform Connection Data Model
```typescript
interface PlatformConnection {
  id: string;                       // Connection ID
  platform: SocialMediaPlatform;   // Platform identifier
  status: ConnectionStatus;         // Current connection status
  account_info: {
    username: string;               // Platform username
    display_name: string;           // Display name
    follower_count: number;         // Follower count
    following_count: number;        // Following count
    post_count: number;            // Total posts
    verified: boolean;             // Verification status
    profile_image_url?: string;     // Profile picture URL
    bio?: string;                  // Profile biography
  };
  permissions: PlatformPermission[]; // Granted permissions
  oauth_token?: string;             // OAuth access token
  refresh_token?: string;           // OAuth refresh token
  token_expires_at?: Date;          // Token expiration
  last_sync: Date;                  // Last synchronization
  created_at: Date;                 // Connection creation
  updated_at: Date;                 // Last update
  settings: PlatformSettings;       // Platform-specific settings
  statistics: PlatformStatistics;   // Performance metrics
}
```

### Social Media Platform Enumeration
```typescript
enum SocialMediaPlatform {
  INSTAGRAM = 'instagram',
  TIKTOK = 'tiktok',
  YOUTUBE = 'youtube',
  TWITTER = 'twitter',
  FACEBOOK = 'facebook',
  LINKEDIN = 'linkedin',
  SNAPCHAT = 'snapchat',
  PINTEREST = 'pinterest',
  REDDIT = 'reddit'
}
```

### Connection Status Enumeration
```typescript
enum ConnectionStatus {
  CONNECTED = 'connected',
  PENDING = 'pending',
  ERROR = 'error',
  DISCONNECTED = 'disconnected',
  SYNCING = 'syncing',
  RATE_LIMITED = 'rate_limited',
  MAINTENANCE = 'maintenance',
  EXPIRED = 'expired'
}
```

### Platform Alert Data Model
```typescript
interface PlatformAlert {
  id: string;                       // Alert ID
  platform: SocialMediaPlatform;   // Source platform
  type: AlertType;                  // Alert classification
  priority: AlertPriority;          // Priority level
  status: AlertStatus;              // Processing status
  detected_at: Date;                // Detection timestamp
  
  // Content Information
  infringing_content: {
    url: string;                    // Infringing content URL
    platform_id: string;           // Platform-specific ID
    content_type: string;           // Type (post, story, video, etc.)
    description?: string;           // Content description
    author: {
      username: string;             // Author username
      display_name: string;         // Author display name
      follower_count?: number;      // Author followers
    };
    engagement: {
      likes?: number;               // Like count
      comments?: number;            // Comment count
      shares?: number;              // Share count
      views?: number;               // View count
    };
    created_at: Date;              // Content creation date
  };
  
  // Original Content Reference
  original_content: {
    url: string;                    // Original content URL
    title?: string;                 // Original title
    creator: string;                // Original creator
    created_at: Date;              // Original creation date
  };
  
  // Detection Details
  detection: {
    similarity_score: number;       // Similarity percentage (0-100)
    detection_method: string;       // Detection algorithm used
    confidence_level: number;       // Confidence score (0-100)
    false_positive_probability: number; // False positive likelihood
  };
  
  // Response Information
  response?: {
    action_taken: string;           // Action performed
    platform_response?: string;    // Platform response
    success: boolean;               // Action success status
    response_time?: number;         // Response time in minutes
    responded_at: Date;            // Response timestamp
  };
  
  // User Actions
  user_actions: UserAction[];       // Actions taken by user
  notes?: string;                   // User notes
  tags?: string[];                  // User-defined tags
}
```

### Platform Settings Data Model
```typescript
interface PlatformSettings {
  monitoring: {
    enabled: boolean;               // Monitoring enabled
    content_types: ContentType[];   // Monitored content types
    keywords: string[];             // Tracked keywords
    hashtags: string[];             // Tracked hashtags
    users: string[];                // Monitored users
    geographic_regions?: string[];  // Geographic restrictions
  };
  
  detection: {
    similarity_threshold: number;   // Similarity threshold (0-100)
    algorithm: DetectionAlgorithm;  // Detection algorithm
    false_positive_filter: boolean; // Enable false positive filtering
    custom_rules: CustomRule[];     // Custom detection rules
  };
  
  automation: {
    auto_report: boolean;           // Auto-report obvious theft
    auto_message: boolean;          // Send automated messages
    auto_escalate: boolean;         // Auto-escalate high priority
    notification_threshold: AlertPriority; // Notification threshold
    workflow_templates: WorkflowTemplate[]; // Automated workflows
  };
  
  api: {
    rate_limit_buffer: number;      // API rate limit buffer
    scan_frequency: ScanFrequency;  // Scan frequency
    retry_attempts: number;         // Retry failed requests
    timeout: number;                // Request timeout (seconds)
  };
}
```

### Platform Statistics Data Model
```typescript
interface PlatformStatistics {
  // Detection Metrics
  total_scans: number;              // Total scans performed
  total_alerts: number;             // Total alerts generated
  alerts_by_priority: {
    urgent: number;
    high: number;
    medium: number;
    low: number;
  };
  
  // Performance Metrics
  detection_accuracy: number;       // Overall accuracy percentage
  false_positive_rate: number;      // False positive rate
  average_response_time: number;    // Average platform response time
  success_rate: number;             // Takedown success rate
  
  // Time-based Statistics
  daily_metrics: DailyMetric[];     // Daily performance data
  weekly_trends: WeeklyTrend[];     // Weekly trend analysis
  monthly_summaries: MonthlySummary[]; // Monthly summaries
  
  // Content Analysis
  content_type_distribution: {      // Content type breakdown
    [key in ContentType]: number;
  };
  geographic_distribution: {        // Geographic spread
    [country: string]: number;
  };
  
  // Updated Tracking
  last_calculated: Date;            // Last statistics update
  next_calculation: Date;           // Next scheduled update
}
```

## 8. Accessibility Requirements

### Keyboard Navigation
- **Tab Order**: Platform cards → Monitoring feed → Analytics → Configuration
- **Platform Cards**: Tab through cards, Enter to configure, Space to scan
- **Monitoring Feed**: Arrow keys for navigation, Enter for actions
- **Modals**: Tab through form fields, Escape to close

### Screen Reader Support
```html
<!-- Platform Connection Cards -->
<div role="region" aria-labelledby="platform-overview">
  <h2 id="platform-overview">Platform Connections</h2>
  <div 
    role="button" 
    tabindex="0"
    aria-label="Instagram - Connected - 15,200 followers - Last scan 2 minutes ago"
    aria-describedby="instagram-details"
  >
    <div id="instagram-details" class="sr-only">
      Platform: Instagram, Status: Connected, Account: @username, 
      Monitoring 847 posts, High detection sensitivity enabled
    </div>
  </div>
</div>

<!-- Real-time Monitoring Feed -->
<div role="log" aria-live="polite" aria-label="Live monitoring alerts">
  <div role="article" aria-labelledby="alert-1-title">
    <h3 id="alert-1-title">High priority Instagram alert</h3>
    <p aria-describedby="alert-1-details">
      Content repost detected from @suspicious_user
    </p>
    <div id="alert-1-details" class="sr-only">
      Detected 3 minutes ago, 95% similarity score, 
      Infringing post has 245 likes and 12 comments
    </div>
    <div role="group" aria-label="Alert actions">
      <button aria-label="View detailed information for this alert">View Details</button>
      <button aria-label="Report this infringement to Instagram">Report Now</button>
    </div>
  </div>
</div>

<!-- Configuration Modal -->
<dialog role="dialog" aria-labelledby="config-title" aria-modal="true">
  <h2 id="config-title">Configure Instagram Protection</h2>
  
  <fieldset>
    <legend>Monitoring Settings</legend>
    <div role="group" aria-labelledby="content-types">
      <span id="content-types">Content types to monitor:</span>
      <label>
        <input type="checkbox" checked aria-describedby="posts-help" />
        Monitor regular posts
      </label>
      <div id="posts-help" class="sr-only">
        Scans all posted images and videos for unauthorized reposts
      </div>
    </div>
  </fieldset>
  
  <div role="slider" aria-valuenow="80" aria-valuemin="0" aria-valuemax="100" 
       aria-label="Detection sensitivity: 80 percent">
    <span class="sr-only">
      Current sensitivity level: High - Will detect content with 80% or greater similarity
    </span>
  </div>
</dialog>

<!-- Platform Status Announcements -->
<div role="status" aria-live="assertive" aria-atomic="true">
  Instagram connection restored - monitoring resumed
</div>
```

### WCAG Compliance Features
- **Color Contrast**: All platform brand colors adjusted to meet WCAG AA standards
- **Focus Indicators**: High-visibility focus rings on all interactive elements
- **Error Handling**: Clear error messages with suggested resolution steps
- **Alternative Text**: Descriptive labels for platform logos and status indicators
- **Semantic Markup**: Proper heading hierarchy and landmark roles
- **Live Regions**: Real-time announcements for status changes and new alerts

### Responsive Accessibility
- **Touch Targets**: Minimum 44px×44px on mobile for all interactive elements
- **Zoom Support**: Interface remains fully functional at 200% zoom
- **Motion Preferences**: Respect prefers-reduced-motion for animations
- **High Contrast**: Enhanced borders and contrast in high contrast mode

## 9. Performance Considerations

### Real-time Updates Optimization
- **WebSocket Connections**: Efficient real-time alert delivery
- **Connection Pooling**: Shared connections across platform APIs
- **Rate Limit Management**: Intelligent API rate limiting
- **Data Compression**: Compressed data transfer for mobile users
- **Selective Updates**: Only update changed data, not full refreshes

### Platform API Integration
```typescript
// Rate-limited API client
class PlatformApiClient {
  private rateLimiter: RateLimiter;
  private cache: LRUCache;
  
  async makeRequest(endpoint: string, params: any) {
    // Check rate limits
    await this.rateLimiter.acquire();
    
    // Check cache first
    const cacheKey = this.generateCacheKey(endpoint, params);
    const cached = this.cache.get(cacheKey);
    
    if (cached && !this.isCacheExpired(cached)) {
      return cached.data;
    }
    
    // Make API request with retry logic
    const response = await this.requestWithRetry(endpoint, params);
    
    // Update cache
    this.cache.set(cacheKey, {
      data: response,
      timestamp: Date.now()
    });
    
    return response;
  }
}
```

### Component Performance
```typescript
// Memoized platform card component
const PlatformCard = memo(({ platform, connection }: Props) => {
  const lastScanFormatted = useMemo(() => 
    formatRelativeTime(connection.last_sync),
    [connection.last_sync]
  );
  
  return (
    <Card className="platform-card">
      <PlatformHeader platform={platform} status={connection.status} />
      <PlatformStats connection={connection} />
      <PlatformActions platform={platform} onAction={handleAction} />
    </Card>
  );
});

// Virtualized alert feed for high-volume platforms
const AlertFeed = ({ alerts }: { alerts: PlatformAlert[] }) => {
  return (
    <FixedSizeList
      height={600}
      itemCount={alerts.length}
      itemSize={120}
      itemData={alerts}
    >
      {AlertItem}
    </FixedSizeList>
  );
};
```

### Bundle Size Optimization
- **Platform-specific Code Splitting**: Load only connected platform code
- **Lazy Loading**: Load configuration modals on demand
- **Tree Shaking**: Remove unused platform API clients
- **Asset Optimization**: Optimized platform logos and icons

## 10. Error Handling & Edge Cases

### Platform API Error Handling
```typescript
const handlePlatformError = (error: PlatformApiError, platform: string) => {
  switch (error.type) {
    case 'RATE_LIMITED':
      updatePlatformStatus(platform, 'rate_limited');
      scheduleRetry(platform, error.retryAfter);
      showToast('warning', 'Rate Limited', `${platform} rate limit reached`);
      break;
      
    case 'TOKEN_EXPIRED':
      updatePlatformStatus(platform, 'expired');
      showReconnectionPrompt(platform);
      break;
      
    case 'PERMISSION_DENIED':
      updatePlatformStatus(platform, 'error');
      showPermissionError(platform, error.requiredPermissions);
      break;
      
    case 'PLATFORM_MAINTENANCE':
      updatePlatformStatus(platform, 'maintenance');
      showMaintenanceNotice(platform, error.estimatedDuration);
      break;
      
    case 'ACCOUNT_SUSPENDED':
      updatePlatformStatus(platform, 'error');
      showAccountSuspensionError(platform);
      break;
      
    default:
      updatePlatformStatus(platform, 'error');
      showGenericError(platform, error.message);
  }
};
```

### Connection Recovery Strategies
```typescript
// Automatic reconnection with exponential backoff
class ConnectionManager {
  private retryAttempts = new Map<string, number>();
  private maxRetries = 5;
  
  async attemptReconnection(platform: string) {
    const attempts = this.retryAttempts.get(platform) || 0;
    
    if (attempts >= this.maxRetries) {
      this.showManualReconnectionRequired(platform);
      return;
    }
    
    const delay = Math.pow(2, attempts) * 1000; // Exponential backoff
    await new Promise(resolve => setTimeout(resolve, delay));
    
    try {
      await this.reconnectPlatform(platform);
      this.retryAttempts.delete(platform);
      this.showReconnectionSuccess(platform);
    } catch (error) {
      this.retryAttempts.set(platform, attempts + 1);
      this.scheduleNextRetry(platform);
    }
  }
}
```

### Data Validation and Sanitization
```typescript
// Platform data validation
const validatePlatformData = (data: any, platform: string): ValidationResult => {
  const schema = platformSchemas[platform];
  
  try {
    const validated = schema.parse(data);
    return { valid: true, data: validated };
  } catch (error) {
    console.error(`${platform} data validation failed:`, error);
    return { 
      valid: false, 
      error: `Invalid data format from ${platform}`,
      details: error.issues 
    };
  }
};
```

### Edge Cases
- **Multiple Account Management**: Handle multiple accounts per platform
- **Platform Policy Changes**: Adapt to changing platform APIs and policies
- **Cross-platform Content**: Handle content that appears on multiple platforms
- **High-volume Creators**: Scale for creators with millions of posts
- **Regional Restrictions**: Handle geo-blocked content and regional differences

## 11. Integration Points

### Social Media Platform APIs
```typescript
// Platform API service registry
const platformApis = {
  instagram: new InstagramBusinessApi({
    clientId: process.env.INSTAGRAM_CLIENT_ID,
    clientSecret: process.env.INSTAGRAM_CLIENT_SECRET,
    redirectUri: process.env.INSTAGRAM_REDIRECT_URI
  }),
  
  tiktok: new TikTokBusinessApi({
    clientKey: process.env.TIKTOK_CLIENT_KEY,
    clientSecret: process.env.TIKTOK_CLIENT_SECRET
  }),
  
  youtube: new YouTubeDataApi({
    apiKey: process.env.YOUTUBE_API_KEY,
    clientId: process.env.YOUTUBE_CLIENT_ID
  }),
  
  twitter: new TwitterApi({
    bearerToken: process.env.TWITTER_BEARER_TOKEN,
    clientId: process.env.TWITTER_CLIENT_ID,
    clientSecret: process.env.TWITTER_CLIENT_SECRET
  })
};
```

### WebSocket Real-time Updates
```typescript
// Real-time platform updates
useEffect(() => {
  const ws = new WebSocket(process.env.REACT_APP_WS_URL);
  
  ws.onmessage = (event) => {
    const update = JSON.parse(event.data);
    
    switch (update.type) {
      case 'platform_status_change':
        updatePlatformStatus(update.platform, update.status);
        break;
        
      case 'new_alert':
        addAlert(update.alert);
        showAlertNotification(update.alert);
        break;
        
      case 'scan_completed':
        updateScanResults(update.platform, update.results);
        break;
        
      case 'rate_limit_warning':
        showRateLimitWarning(update.platform, update.remaining);
        break;
    }
  };
  
  return () => ws.close();
}, []);
```

### Backend API Integration
```typescript
// Social media protection API service
const socialMediaApi = {
  // Platform management
  getPlatformConnections: () => 
    GET('/api/social-media/platforms'),
    
  connectPlatform: (platform: string, authCode: string) => 
    POST(`/api/social-media/platforms/${platform}/connect`, { authCode }),
    
  disconnectPlatform: (platform: string) => 
    DELETE(`/api/social-media/platforms/${platform}`),
    
  // Monitoring and alerts
  getAlerts: (params?: {
    platform?: string;
    priority?: string;
    status?: string;
    limit?: number;
  }) => GET('/api/social-media/alerts', { params }),
  
  processAlert: (alertId: string, action: string) => 
    POST(`/api/social-media/alerts/${alertId}/process`, { action }),
    
  // Configuration
  updatePlatformSettings: (platform: string, settings: PlatformSettings) => 
    PUT(`/api/social-media/platforms/${platform}/settings`, settings),
    
  // Analytics
  getPlatformAnalytics: (platform?: string, dateRange?: DateRange) => 
    GET('/api/social-media/analytics', { 
      params: { platform, ...dateRange } 
    }),
    
  // Scanning
  triggerScan: (platform: string, scope?: ScanScope) => 
    POST(`/api/social-media/platforms/${platform}/scan`, { scope })
};
```

## 12. Technical Implementation Notes

### State Management Architecture
```typescript
// Social media protection state
interface SocialMediaState {
  // Platform connections
  platforms: Record<SocialMediaPlatform, PlatformConnection>;
  connectionStatus: Record<SocialMediaPlatform, ConnectionStatus>;
  
  // Monitoring feed
  alerts: PlatformAlert[];
  alertFilters: AlertFilters;
  feedLoading: boolean;
  
  // Analytics
  analytics: PlatformAnalytics;
  analyticsLoading: boolean;
  
  // Configuration
  platformSettings: Record<SocialMediaPlatform, PlatformSettings>;
  activeConfigModal: SocialMediaPlatform | null;
  
  // UI state
  selectedTab: number;
  selectedAlerts: string[];
  searchQuery: string;
}

// Actions
const socialMediaSlice = createSlice({
  name: 'socialMedia',
  initialState,
  reducers: {
    updatePlatformStatus: (state, action) => {
      const { platform, status } = action.payload;
      state.connectionStatus[platform] = status;
    },
    addAlert: (state, action) => {
      state.alerts.unshift(action.payload);
    },
    updatePlatformSettings: (state, action) => {
      const { platform, settings } = action.payload;
      state.platformSettings[platform] = settings;
    }
  }
});
```

### Platform-specific Components
```typescript
// Platform-specific configuration components
const platformComponents = {
  instagram: lazy(() => import('./platforms/InstagramConfig')),
  tiktok: lazy(() => import('./platforms/TikTokConfig')),
  youtube: lazy(() => import('./platforms/YouTubeConfig')),
  twitter: lazy(() => import('./platforms/TwitterConfig'))
};

// Dynamic platform component loading
const PlatformConfigModal = ({ platform, onClose }: Props) => {
  const PlatformComponent = platformComponents[platform];
  
  if (!PlatformComponent) {
    return <GenericPlatformConfig platform={platform} onClose={onClose} />;
  }
  
  return (
    <Suspense fallback={<ConfigurationSkeleton />}>
      <PlatformComponent onClose={onClose} />
    </Suspense>
  );
};
```

### OAuth Flow Implementation
```typescript
// Platform OAuth flow
const usePlatformOAuth = (platform: SocialMediaPlatform) => {
  const [isConnecting, setIsConnecting] = useState(false);
  
  const initiateConnection = useCallback(async () => {
    setIsConnecting(true);
    
    try {
      // Get OAuth URL from backend
      const { authUrl, state } = await socialMediaApi.getOAuthUrl(platform);
      
      // Store state for verification
      sessionStorage.setItem(`${platform}_oauth_state`, state);
      
      // Redirect to platform OAuth
      window.location.href = authUrl;
    } catch (error) {
      setIsConnecting(false);
      handleOAuthError(error, platform);
    }
  }, [platform]);
  
  return { initiateConnection, isConnecting };
};
```

## 13. Future Enhancements

### Phase 2 Features
- **AI-Powered Detection**: Advanced machine learning for improved accuracy
- **Cross-Platform Correlation**: Link related infringements across platforms
- **Advanced Automation**: Complex multi-step automated workflows
- **Team Collaboration**: Multi-user platform management
- **White-Label Solutions**: Platform management for agencies

### Phase 3 Features
- **Emerging Platform Support**: TikTok competitors, new social platforms
- **Advanced Analytics**: Predictive analytics and trend forecasting
- **API Access**: Public API for third-party integrations
- **Mobile Application**: Native mobile app for platform management
- **Blockchain Integration**: Immutable proof of content ownership

### Platform-Specific Enhancements
- **Instagram**: Reels monitoring, IGTV protection, Shopping integration
- **TikTok**: Sound/music detection, effect monitoring, brand challenge tracking
- **YouTube**: Shorts protection, Community post monitoring, Live stream alerts
- **Twitter**: Spaces monitoring, Fleet protection (if returned), Thread protection
- **Emerging Platforms**: BeReal, Clubhouse, Discord, Twitch integration

This comprehensive specification provides complete guidance for implementing a professional-grade Social Media Protection Management screen with real-time monitoring, multi-platform integration, and advanced automation capabilities.