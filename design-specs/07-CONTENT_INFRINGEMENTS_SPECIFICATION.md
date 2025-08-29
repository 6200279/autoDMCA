# Content Infringements Detection Screen - Comprehensive Design Specification

## 1. Screen Overview & Purpose

### Primary Function
The Content Infringements Detection screen is the central monitoring hub for detecting, reviewing, and managing content infringements across multiple platforms. It leverages AI-powered content matching to identify unauthorized use of protected content and provides tools for efficient takedown management.

### User Goals
- Monitor real-time infringement detection across platforms
- Review and validate detected infringements
- Manage bulk takedown operations efficiently
- Track removal success rates and response times
- Analyze platform performance and detection trends
- Export infringement data for legal proceedings

### Business Context
This screen is critical for content protection agencies, creators, and legal teams who need to actively monitor and respond to content theft. It serves as the primary interface for AI-powered detection results and takedown workflow management.

## 2. Layout Architecture

### Primary Layout Structure
```
┌─────────────────────────────────────────────────────────────────┐
│ Header: "Infringement Detection" + Date Range Filter           │
│ Subtitle: "Monitor and manage detected content infringements"   │
├─────────────────────────────────────────────────────────────────┤
│ [Total: 125] [Pending: 23] [Review: 8] [Removed: 67] [Rate: 85%]│
├─────────────────────────────────────────────────────────────────┤
│ ┌─ Infringements List ─┐┌─── Analytics ───┐                    │
│ │ [Bulk] [Mark False]  ││                  │                    │
│ │ [Export] | [Search🔍]││ Detection Trends │ Status Distribution│
│ │ ☑│Thumbnail│Status   ││ [Chart Area]     │ [Doughnut Chart]  │
│ │ ☑│"Title"  │PENDING  ││                  │                   │
│ │  │Platform │95% conf.││                  │ Platform          │
│ │  │2h ago   │[Actions]││                  │ Performance       │
│ └─────────────────────┘│                  │ [Table]           │
│                         │                  │                   │
└─────────────────────────────────────────────────────────────────┘

Details Overlay:
┌─────────────────────────────────┐
│ ✕ "Unauthorized Content..."     │ 
├─────────────────────────────────┤
│ [Thumbnail] │ Status: PENDING   │
│ [Preview]   │ Confidence: 95%   │
│             │ Platform: Instagram│
│             │ Detected: 2h ago   │
│ Description: "Original content  │
│ reposted without permission..." │
│ Tags: [exact-match][high-conf] │
│ [Open URL] [Send Takedown]     │
└─────────────────────────────────┘
```

### Tab Structure
- **Tab 1**: Infringements List (primary data table)
- **Tab 2**: Analytics (charts and performance metrics)

### Grid System
- **Desktop**: Full-width table with fixed sidebar for filters
- **Tablet**: Horizontal scrollable table with collapsible columns
- **Mobile**: Card-based layout with priority information

### Responsive Breakpoints
- **Large (1200px+)**: Full table with all columns and sidebar analytics
- **Medium (768-1199px)**: Hide metadata columns, maintain core data
- **Small (576-767px)**: Card layout with essential information
- **Extra Small (<576px)**: Single column cards with action sheets

## 3. Visual Design System

### Color Palette
```css
/* Status Colors */
--status-pending: #f59e0b (amber-500) 
--status-under-review: #3b82f6 (blue-500)
--status-takedown-sent: #06b6d4 (cyan-500)
--status-removed: #10b981 (emerald-500) 
--status-rejected: #ef4444 (red-500)
--status-false-positive: #6b7280 (gray-500)

/* Confidence Colors */
--confidence-high: #10b981 (90%+, green-600)
--confidence-medium: #f59e0b (70-89%, amber-600)
--confidence-low: #ef4444 (<70%, red-600)

/* Background Colors */
--surface-ground: #ffffff
--surface-section: #f8fafc
--surface-card: #ffffff
--surface-overlay: rgba(0,0,0,0.6)

/* Chart Colors */
--chart-primary: #6366f1 (indigo-500)
--chart-secondary: #10b981 (emerald-500)
--chart-accent: #f59e0b (amber-500)
--chart-danger: #ef4444 (red-500)
--chart-info: #3b82f6 (blue-500)
--chart-neutral: #6b7280 (gray-500)

/* Platform Badge Colors */
--instagram-color: #E4405F
--tiktok-color: #000000
--onlyfans-color: #00AFF0
--twitter-color: #1DA1F2
--youtube-color: #FF0000
--reddit-color: #FF4500
--telegram-color: #0088CC
```

### Typography
```css
/* Headers */
.page-title: 28px/1.2 'Inter', weight-700, color-gray-900
.page-subtitle: 14px/1.5 'Inter', weight-400, color-gray-600
.section-title: 20px/1.3 'Inter', weight-600, color-gray-900
.stat-title: 12px/1.2 'Inter', weight-500, color-gray-600
.stat-value: 24px/1.1 'Inter', weight-700, color-themed

/* Table Content */
.infringement-title: 14px/1.4 'Inter', weight-600, color-gray-900
.infringement-desc: 12px/1.3 'Inter', weight-400, color-gray-600
.platform-label: 12px/1.2 'Inter', weight-500, color-white
.confidence-value: 14px/1.2 'Inter', weight-700, color-themed
.similarity-label: 12px/1.2 'Inter', weight-400, color-gray-600

/* Form Elements */
.filter-label: 13px/1.3 'Inter', weight-500, color-gray-700
.search-input: 14px/1.4 'Inter', weight-400, color-gray-900
.button-label: 14px/1.3 'Inter', weight-500, color-themed
.tooltip-text: 12px/1.2 'Inter', weight-400, color-gray-800
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
--card-padding: 20px
--table-cell-padding: 12px 16px
--stats-card-padding: 16px
--overlay-padding: 24px
```

## 4. Interactive Components Breakdown

### Statistics Dashboard Cards
**Purpose**: Real-time overview of infringement detection metrics

**Card Structure**:
- **Total Detections**: Overall count with trend indicator
- **Pending Action**: Urgent items requiring attention (amber highlight)
- **Under Review**: Items in manual review process (blue highlight)
- **Successfully Removed**: Successful takedowns (green highlight)  
- **Success Rate**: Calculated percentage with visual indicator
- **Average Response Time**: Time-based metric in hours

**Visual States**:
- **Default**: Clean card with centered metrics
- **Hover**: Subtle elevation increase with shadow enhancement
- **Loading**: Skeleton placeholders with shimmer effect
- **Empty**: Zero state with muted styling

### Tabbed Interface Component
**Purpose**: Organize infringements list and analytics views

**Tab 1 - Infringements List**:
- Primary data table with all detected infringements
- Bulk action toolbar with selection-dependent buttons
- Real-time updates with WebSocket integration
- Advanced filtering and search capabilities

**Tab 2 - Analytics**:
- Detection trends chart (line/area chart)
- Status distribution (doughnut chart)
- Platform performance comparison table
- Time-based analytics with date range filtering

### Data Table Component (Enhanced)
**Purpose**: Display comprehensive infringement data with advanced features

**Column Structure**:
1. **Selection**: Multi-select checkboxes for bulk operations
2. **Content**: Thumbnail preview with title and platform
3. **Status**: Color-coded status tags with icons
4. **Confidence**: Percentage with color coding and similarity
5. **Platform**: Branded platform badges
6. **Profile**: Associated creator profile information
7. **Detected**: Relative and absolute timestamps
8. **Actions**: Context-specific action buttons

**Advanced Features**:
- **Multi-column sorting**: Sort by multiple criteria
- **Advanced filtering**: Platform, status, confidence, date ranges
- **Global search**: Full-text search across all fields
- **Export functionality**: CSV export with selected columns
- **Real-time updates**: Live data updates via WebSocket

### Content Preview Component
**Purpose**: Visual content comparison for validation

**Structure**:
- **Thumbnail Display**: 60x60px preview with click-to-expand
- **Original Comparison**: Side-by-side view in overlay
- **Metadata Display**: View counts, likes, duration information
- **Zoom and Pan**: Full-screen preview with manipulation controls

**Interaction States**:
- **Hover**: Subtle scale animation (1.05x)
- **Loading**: Skeleton with shimmer animation
- **Error**: Fallback icon with retry option
- **Preview**: Modal overlay with image manipulation

### Confidence Meter Component
**Purpose**: Visual confidence and similarity scoring

**Display Format**:
```
┌─────────────┐
│    95%      │ <- Main confidence score (color-coded)
│  98% similar│ <- Similarity percentage (smaller)
└─────────────┘
```

**Color Coding**:
- **High (90%+)**: Green text (#10b981)
- **Medium (70-89%)**: Amber text (#f59e0b) 
- **Low (<70%)**: Red text (#ef4444)

### Action Button Groups
**Purpose**: Context-specific actions per infringement

**Button Types**:
- **View Details**: Eye icon, opens detailed overlay
- **Open URL**: External link icon, opens in new tab
- **Send Takedown**: Send icon, initiates takedown process
- **Mark False Positive**: X icon, marks as false positive

**States**:
- **Default**: Subtle text buttons with icons
- **Hover**: Background color change with icon animation
- **Disabled**: Grayed out for unavailable actions
- **Loading**: Spinner replacement during action execution

### Bulk Action Toolbar
**Purpose**: Efficient multi-item operations

**Action Buttons**:
- **Bulk Takedown**: Enabled only when eligible items selected
- **Mark False Positives**: Mass false positive marking
- **Export Selected**: Export filtered selection to CSV
- **Advanced Filters**: Toggle advanced filtering panel

**Selection Logic**:
- Buttons enable/disable based on selection and status
- Clear visual feedback for selection count
- Progress indicators for bulk operations

## 5. Interaction Patterns & User Flows

### Infringement Review Flow
1. **Discovery**: User sees new infringement in real-time updates
2. **Initial Review**: Click on thumbnail or title to view details
3. **Validation**: Compare original vs detected content in overlay
4. **Decision**: Choose between takedown, false positive, or further review
5. **Action**: Execute chosen action with confirmation
6. **Tracking**: Monitor status changes in real-time

### Bulk Operation Flow
1. **Selection**: User selects multiple infringements via checkboxes
2. **Action Choice**: Click appropriate bulk action button
3. **Validation**: System shows eligible items and confirms action
4. **Confirmation**: User confirms bulk operation with details
5. **Execution**: Batch processing with progress indication
6. **Results**: Summary of successful/failed operations

### Filtering and Search Flow
1. **Search Input**: User types in global search field
2. **Real-time Results**: Table filters immediately as user types
3. **Advanced Filters**: User opens advanced filter panel
4. **Criteria Selection**: Choose platform, status, confidence, date ranges
5. **Application**: Filters combine with search for refined results
6. **Clear/Reset**: Easy option to clear all filters

### Analytics Review Flow
1. **Tab Switch**: User clicks Analytics tab
2. **Data Loading**: Charts and tables load with current data
3. **Time Range**: User selects different date ranges
4. **Platform Analysis**: Review platform-specific performance
5. **Trend Identification**: Identify patterns in detection trends
6. **Export**: Generate reports for external analysis

## 6. Content Strategy & Messaging

### Primary Headings
- **Page Title**: "Infringement Detection"  
- **Page Subtitle**: "Monitor and manage detected content infringements"
- **Tab Headers**: "Infringements List", "Analytics"
- **Section Titles**: "Detection Trends", "Status Distribution", "Platform Performance"

### Status Labels
```javascript
const statusLabels = {
  'pending': 'Pending Review',
  'under_review': 'Under Review', 
  'takedown_sent': 'Takedown Sent',
  'removed': 'Successfully Removed',
  'rejected': 'Takedown Rejected',
  'false_positive': 'False Positive'
};
```

### Action Button Labels
- **Primary Actions**: "Send Takedown", "Mark as False Positive", "View Details"
- **Bulk Actions**: "Bulk Takedown", "Mark False Positives", "Export Selected"
- **Navigation**: "Open URL", "View Original", "Compare Content"

### Statistics Labels
```javascript
const statsLabels = {
  total: 'Total Detections',
  pending: 'Pending Action',
  underReview: 'Under Review', 
  removed: 'Successfully Removed',
  successRate: 'Success Rate',
  avgResponseTime: 'Avg Response Time'
};
```

### Toast Messages
```javascript
const toastMessages = {
  success: {
    takedownSent: 'Takedown request sent successfully',
    bulkTakedown: '{count} takedown requests sent successfully',
    markedFalsePositive: 'Marked as false positive',
    dataExported: 'Infringement data exported to CSV'
  },
  error: {
    takedownFailed: 'Failed to send takedown request',
    bulkOperationFailed: 'Bulk operation failed',
    loadingFailed: 'Failed to load infringement data',
    exportFailed: 'Failed to export data'
  },
  info: {
    newInfringement: 'New infringement detected: {title}',
    statusUpdated: 'Infringement status updated',
    realTimeUpdate: 'Data updated in real-time'
  }
};
```

### Empty States
- **No Infringements**: "No infringements detected yet"
- **No Search Results**: "No infringements match your search criteria"
- **No Selection**: "Select infringements to perform bulk actions"
- **Loading**: "Loading infringement data..."

## 7. Data Structure & Content Types

### Infringement Data Model
```typescript
interface Infringement {
  id: string;
  title: string;                    // Human-readable infringement title
  description: string;              // Detailed description
  url: string;                      // URL of infringing content
  platform: string;                // Platform where content was found
  status: 'pending' | 'under_review' | 'takedown_sent' | 'removed' | 'rejected' | 'false_positive';
  confidence: number;               // AI confidence score (0-100)
  similarity: number;               // Content similarity score (0-100)
  profileId: string;                // Associated creator profile ID
  profileName: string;              // Creator profile name
  thumbnail: string;                // Preview image URL
  originalContent: string;          // Original content URL/reference
  detectedAt: Date;                 // Detection timestamp
  lastUpdated: Date;                // Last status update
  takedownRequestId?: string;       // Associated takedown request ID
  reportedBy: 'system' | 'user';    // Detection source
  tags: string[];                   // Classification tags
  metadata: {
    uploader?: string;              // Content uploader identifier
    viewCount?: number;             // View/impression count
    likeCount?: number;             // Engagement metrics
    commentCount?: number;          // Comment count
    duration?: number;              // Video/audio duration in seconds
    contentType: 'image' | 'video' | 'text' | 'audio';
  };
}
```

### Statistics Data Model
```typescript
interface InfringementStats {
  total: number;                    // Total infringements count
  pending: number;                  // Pending review count
  underReview: number;              // Under review count
  takedownSent: number;             // Takedown requests sent
  removed: number;                  // Successfully removed count
  rejected: number;                 // Rejected takedowns count
  falsePositive: number;            // False positives count
  avgResponseTime: number;          // Average response time in hours
  successRate: number;              // Success percentage (0-100)
}
```

### Platform Configuration
```typescript
const platformConfig = {
  'Instagram': { color: '#E4405F', icon: 'pi pi-instagram' },
  'TikTok': { color: '#000000', icon: 'pi pi-video' },
  'OnlyFans': { color: '#00AFF0', icon: 'pi pi-users' },
  'Twitter': { color: '#1DA1F2', icon: 'pi pi-twitter' },
  'YouTube': { color: '#FF0000', icon: 'pi pi-youtube' },
  'Reddit': { color: '#FF4500', icon: 'pi pi-reddit' },
  'Telegram': { color: '#0088CC', icon: 'pi pi-telegram' }
};
```

### Filter Configuration
```typescript
interface FilterConfig {
  global: { value: null, matchMode: FilterMatchMode.CONTAINS };
  title: { value: null, matchMode: FilterMatchMode.CONTAINS };
  platform: { value: null, matchMode: FilterMatchMode.IN };
  status: { value: null, matchMode: FilterMatchMode.IN };
  confidence: { value: null, matchMode: FilterMatchMode.GREATER_THAN_OR_EQUAL_TO };
  detectedAt: { 
    operator: FilterOperator.AND, 
    constraints: [{ value: null, matchMode: FilterMatchMode.DATE_IS }] 
  };
  profileName: { value: null, matchMode: FilterMatchMode.CONTAINS };
}
```

## 8. Accessibility Requirements

### Keyboard Navigation
- **Tab Order**: Header → Statistics → Tabs → Table → Actions → Overlays
- **Table Navigation**: Arrow keys for cell navigation, Enter to activate
- **Bulk Actions**: Space to select, Tab to navigate actions
- **Search**: Immediate focus with keyboard shortcut (Ctrl/Cmd + K)

### Screen Reader Support
```html
<!-- Statistics Cards -->
<div role="region" aria-labelledby="stats-heading">
  <h3 id="stats-heading" class="sr-only">Infringement Statistics</h3>
  <div role="group" aria-label="Total detections: 125">
    <div aria-describedby="total-desc">125</div>
    <div id="total-desc">Total Detections</div>
  </div>
</div>

<!-- Data Table -->
<table role="table" aria-label="Content Infringements">
  <thead>
    <tr role="row">
      <th role="columnheader" aria-sort="none">Content</th>
      <th role="columnheader" aria-sort="ascending">Status</th>
      <th role="columnheader" aria-sort="none">Confidence</th>
    </tr>
  </thead>
  <tbody>
    <tr role="row" aria-selected="false" aria-describedby="row-1-desc">
      <td role="gridcell">
        <img alt="Thumbnail for Unauthorized Content Distribution" />
        <div id="row-1-desc">Unauthorized Content Distribution on Instagram</div>
      </td>
      <td role="gridcell">
        <span aria-label="Status: Pending review">Pending</span>
      </td>
    </tr>
  </tbody>
</table>

<!-- Action Buttons -->
<button 
  aria-label="Send takedown request for Unauthorized Content Distribution"
  title="Send Takedown"
  type="button"
>
  <i class="pi pi-send" aria-hidden="true"></i>
</button>
```

### WCAG Compliance Features
- **Color Contrast**: All status colors meet WCAG AA standards (4.5:1 minimum)
- **Focus Indicators**: Visible focus rings on all interactive elements (2px solid blue)
- **Error Handling**: Clear error messages with screen reader announcements
- **Alternative Text**: Descriptive alt text for all content thumbnails
- **Semantic Markup**: Proper heading hierarchy and landmark roles
- **Live Regions**: Announce real-time updates appropriately

### Responsive Accessibility
- **Touch Targets**: Minimum 44px×44px on mobile devices
- **Zoom Support**: Interface remains usable at 200% zoom
- **Motion Preferences**: Respect prefers-reduced-motion settings
- **High Contrast**: Support for high contrast mode preferences

## 9. Performance Considerations

### Loading Strategy
- **Initial Load**: Skeleton placeholders for all components
- **Pagination**: Load infringements in chunks (10/25/50 per page)
- **Real-time Updates**: WebSocket connection for live data
- **Image Loading**: Lazy loading for thumbnails with fallbacks
- **Chart Rendering**: Asynchronous chart loading with placeholders

### Data Management
- **Caching**: Cache infringement data for 2 minutes
- **Optimistic Updates**: Immediate UI updates for actions
- **Bulk Operations**: Progress tracking with cancelation options
- **Search Optimization**: Debounced search with 300ms delay
- **Filter Persistence**: Remember filter states in session storage

### Component Optimization
```typescript
// Memoized column templates to prevent unnecessary re-renders
const thumbnailTemplate = useMemo(() => 
  (rowData: Infringement) => (
    <ThumbnailComponent data={rowData} />
  ), []
);

// Debounced search handler
const debouncedSearch = useCallback(
  debounce((value: string) => {
    setGlobalFilterValue(value);
    applyFilters({ ...filters, global: { value, matchMode: FilterMatchMode.CONTAINS } });
  }, 300),
  [filters]
);

// Virtual scrolling for large datasets
const virtualizedTable = useMemo(() => 
  infringements.length > 100, 
  [infringements.length]
);
```

### Bundle Size Optimization
- **Tree Shaking**: Import only used PrimeReact components
- **Code Splitting**: Lazy load analytics charts and overlay components
- **Icon Optimization**: Use only required PrimeIcons
- **Chart Libraries**: Conditional loading of Chart.js components

## 10. Error Handling & Edge Cases

### Loading States
```typescript
// Loading skeleton for different components
const renderLoadingSkeleton = () => (
  <div className="grid">
    <div className="col-12">
      <Skeleton height="2rem" className="mb-4" />
      <div className="grid mb-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="col-12 md:col-2">
            <Skeleton height="4rem" />
          </div>
        ))}
      </div>
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="flex align-items-center gap-3 mb-3">
          <Skeleton shape="circle" size="4rem" />
          <div className="flex-1">
            <Skeleton height="1rem" className="mb-2" />
            <Skeleton height="0.8rem" width="60%" />
          </div>
          <Skeleton height="2rem" width="5rem" />
        </div>
      ))}
    </div>
  </div>
);
```

### Empty States
- **No Infringements**: Welcome message with setup instructions
- **Search No Results**: Clear message with filter suggestions
- **Network Errors**: Retry button with offline indicator
- **Permission Errors**: Clear messaging about access requirements

### API Error Handling
```typescript
const handleApiError = (error: any, operation: string) => {
  const errorMessage = error.response?.data?.detail || `Failed to ${operation}`;
  const errorCode = error.response?.status;
  
  toast.current?.show({
    severity: 'error',
    summary: `${operation} Failed`,
    detail: `${errorMessage} ${errorCode ? `(${errorCode})` : ''}`,
    life: 5000
  });
  
  // Log error for debugging
  console.error(`${operation} error:`, error);
  
  // Handle specific error cases
  if (errorCode === 401) {
    // Redirect to login
    window.location.href = '/login';
  } else if (errorCode === 403) {
    // Show permission error
    setPermissionError(true);
  }
};
```

### Real-time Connection Handling
```typescript
// WebSocket connection management
useEffect(() => {
  const connectWebSocket = () => {
    const ws = new WebSocket(process.env.REACT_APP_WS_URL);
    
    ws.onopen = () => {
      setConnectionStatus('connected');
      setRetryAttempts(0);
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleRealtimeUpdate(data);
    };
    
    ws.onclose = () => {
      setConnectionStatus('disconnected');
      // Implement exponential backoff retry
      if (retryAttempts < 5) {
        setTimeout(connectWebSocket, Math.pow(2, retryAttempts) * 1000);
        setRetryAttempts(prev => prev + 1);
      }
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setConnectionStatus('error');
    };
    
    return ws;
  };
  
  const websocket = connectWebSocket();
  return () => websocket?.close();
}, [retryAttempts]);
```

### Edge Cases
- **Large Datasets**: Virtual scrolling for 10,000+ infringements
- **Slow Networks**: Progressive loading with timeout handling
- **Concurrent Operations**: Prevent duplicate bulk actions
- **Browser Compatibility**: Graceful degradation for older browsers
- **Memory Management**: Cleanup intervals for large data sets

## 11. Integration Points

### API Endpoints
```typescript
// Infringement API Service
const infringementApi = {
  // Data retrieval
  getInfringements: (params?: {
    page?: number;
    limit?: number;
    platform?: string;
    status?: string;
    confidence_min?: number;
    date_from?: string;
    date_to?: string;
    include_stats?: boolean;
  }) => GET('/api/infringements', { params }),
  
  // Individual operations
  updateInfringement: (id: string, data: Partial<Infringement>) => 
    PUT(`/api/infringements/${id}`, data),
  
  createTakedownFromInfringement: (id: string) => 
    POST(`/api/infringements/${id}/takedown`),
  
  // Bulk operations
  bulkAction: (params: {
    action: 'send_takedown' | 'mark_false_positive' | 'mark_under_review';
    infringement_ids: string[];
  }) => POST('/api/infringements/bulk', params),
  
  // Analytics
  getAnalytics: (params?: {
    date_from?: string;
    date_to?: string;
    group_by?: 'platform' | 'status' | 'date';
  }) => GET('/api/infringements/analytics', { params }),
  
  // Export
  exportData: (params?: {
    format: 'csv' | 'json';
    infringement_ids?: string[];
    include_metadata?: boolean;
  }) => GET('/api/infringements/export', { params, responseType: 'blob' })
};
```

### WebSocket Integration
```typescript
// Real-time updates subscription
const { profileActivities, notifications } = useProfileRealtime();

// Handle real-time infringement updates
useEffect(() => {
  profileActivities.forEach(activity => {
    switch (activity.type) {
      case 'infringement_detected':
        handleNewInfringement(activity);
        break;
      case 'infringement_updated':
        handleInfringementUpdate(activity);
        break;
      case 'takedown_status_changed':
        handleTakedownStatusUpdate(activity);
        break;
    }
  });
}, [profileActivities]);

// Handle real-time notifications
useEffect(() => {
  notifications.forEach(notification => {
    if (notification.category === 'infringement') {
      showToastNotification(notification);
    }
  });
}, [notifications]);
```

### Context Integration
```typescript
// Authentication and permissions
const { user, hasPermission } = useAuth();
const canSendTakedowns = hasPermission('infringements:takedown');
const canMarkFalsePositive = hasPermission('infringements:update');
const canExportData = hasPermission('infringements:export');

// Layout context for responsive behavior
const { isMobile, sidebarCollapsed } = useLayout();
```

## 12. Technical Implementation Notes

### State Management Architecture
```typescript
// Component state structure
interface InfringementsState {
  // Data states
  infringements: Infringement[];
  stats: InfringementStats;
  loading: boolean;
  
  // UI states  
  selectedInfringements: Infringement[];
  selectedInfringement: Infringement | null;
  globalFilterValue: string;
  dateRange: Date[] | null;
  activeTab: number;
  
  // Filter states
  filters: FilterConfig;
  advancedFiltersVisible: boolean;
  
  // Connection states
  connectionStatus: 'connected' | 'disconnected' | 'error';
  retryAttempts: number;
}
```

### Performance Optimizations
```typescript
// Memoized calculations
const filteredInfringements = useMemo(() => {
  return infringements.filter(infringement => {
    // Apply all active filters
    return applyFilters(infringement, filters);
  });
}, [infringements, filters]);

// Virtualized table for large datasets
const virtualizedProps = useMemo(() => ({
  scrollable: true,
  scrollHeight: "500px",
  virtualScrollerOptions: {
    itemSize: 70,
    showLoader: true,
    loading: loading,
    lazy: true
  }
}), [loading]);

// Debounced search
const debouncedFilter = useCallback(
  debounce((value: string) => {
    setFilters(prev => ({
      ...prev,
      global: { value, matchMode: FilterMatchMode.CONTAINS }
    }));
  }, 300),
  []
);
```

### PrimeReact Configuration
```typescript
// Advanced DataTable configuration
<DataTable
  value={filteredInfringements}
  selection={selectedInfringements}
  onSelectionChange={handleSelectionChange}
  dataKey="id"
  paginator
  rows={25}
  rowsPerPageOptions={[10, 25, 50, 100]}
  paginatorTemplate="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport RowsPerPageDropdown"
  currentPageReportTemplate="Showing {first} to {last} of {totalRecords} infringements"
  globalFilter={globalFilterValue}
  filters={filters}
  onFilter={handleFilterChange}
  filterDisplay="menu"
  globalFilterFields={['title', 'platform', 'profileName', 'description']}
  emptyMessage="No infringements found"
  sortMode="multiple"
  removableSort
  resizableColumns
  columnResizeMode="expand"
  showGridlines
  size="small"
  {...(infringements.length > 100 ? virtualizedProps : {})}
>
```

## 13. Future Enhancements

### Phase 2 Features
- **Advanced AI Analysis**: Content similarity heatmaps and detailed matching reports
- **Automated Takedown Rules**: Smart rules based on confidence thresholds and platform policies
- **Integration Marketplace**: Direct connections to platform APIs for automated takedowns
- **Legal Documentation**: Automatic generation of legal notices and DMCA templates
- **Workflow Automation**: Custom workflows for different infringement types

### Phase 3 Features  
- **Machine Learning Insights**: Predictive analytics for infringement patterns
- **Cross-Platform Correlation**: Link related infringements across multiple platforms
- **Collaborative Review**: Team-based review workflows with approval chains
- **API Access**: Public API for third-party integrations
- **Mobile Application**: Native mobile apps for on-the-go infringement management

### Advanced Analytics
- **Trend Forecasting**: Predict infringement volumes and platform risks
- **ROI Analysis**: Calculate cost-effectiveness of different takedown strategies
- **Platform Intelligence**: Deep insights into platform-specific infringement patterns
- **Content Analysis**: Advanced AI insights into content mutation and variation tracking
- **Performance Benchmarking**: Compare performance against industry standards

This comprehensive specification provides complete guidance for implementing a professional-grade Content Infringements Detection screen with enterprise-level functionality, real-time capabilities, and advanced analytics integration.