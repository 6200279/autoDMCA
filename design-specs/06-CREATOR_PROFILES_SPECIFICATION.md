# Creator Profiles Management Screen - Comprehensive Design Specification

## 1. Screen Overview & Purpose

### Primary Function
Creator Profiles Management screen serves as the central hub for managing content creator profiles within the AutoDMCA system. Users can create, edit, monitor, and manage multiple creator profiles that represent different content creators whose intellectual property needs protection.

### User Goals
- Create and manage multiple creator profiles
- Monitor scanning status and protection statistics
- Configure scanning frequency and priority settings
- Track platform connections and success rates
- Bulk manage profiles efficiently
- View detailed analytics for each profile

### Business Context
This screen is critical for content protection agencies and creators who need to manage multiple profiles, track protection metrics, and maintain organized creator portfolios with different priorities and scanning configurations.

## 2. Layout Architecture

### Primary Layout Structure
```
┌─────────────────────────────────────────────────────┐
│ Header: "Content Creator Profiles"                  │
│ Subtitle: "Manage and monitor your protected..."    │
├─────────────────────────────────────────────────────┤
│ [New Profile] [Delete Selected] | [Search Box] 🔍  │
├─────────────────────────────────────────────────────┤
│ ☑ │ Profile    │ Status │ Platforms │ Stats │ Actions│
│ ☑ │ [Avatar]   │ [Tag]  │ [Chips]   │ Scans │ [Btns] │
│   │ John Doe   │ ACTIVE │ OF IG TW  │ Issues│ ✏️👁️▶️  │
│   │ @johndoe   │        │ +2 more   │       │        │
├─────────────────────────────────────────────────────┤
│ Pagination: "Showing 1-10 of 25 profiles" [<<][>]  │
└─────────────────────────────────────────────────────┘

Modal Dialog (Create/Edit):
┌─────────────────────────────────┐
│ ✕ Create New Profile            │
├─────────────────────────────────┤
│ Profile Name* │ Stage Name*     │
│ [            ]│ [            ] │
│ Description*                    │
│ [                            ] │
│ Status*       │ Scan Frequency* │
│ [Dropdown   ▼]│ [Dropdown    ▼]│
│ Category*     │ Priority*       │
│ [Dropdown   ▼]│ [Dropdown    ▼]│
├─────────────────────────────────┤
│              [Cancel] [Create]  │
└─────────────────────────────────┘
```

### Grid System
- **Desktop**: Full-width data table with responsive columns
- **Tablet**: Collapsible columns with priority display
- **Mobile**: Card-based layout with vertical stacking

### Responsive Breakpoints
- **Large (1200px+)**: Full table with all columns visible
- **Medium (768-1199px)**: Hide less critical columns, maintain table structure
- **Small (576-767px)**: Switch to card layout with essential information
- **Extra Small (<576px)**: Single column cards with action dropdown

## 3. Visual Design System

### Color Palette
```css
/* Status Colors */
--status-active: #10b981 (green-500)
--status-scanning: #3b82f6 (blue-500)
--status-inactive: #f59e0b (amber-500)
--status-paused: #6b7280 (gray-500)
--status-error: #ef4444 (red-500)

/* Background Colors */
--surface-ground: #ffffff
--surface-section: #f8fafc
--surface-card: #ffffff
--surface-overlay: rgba(0,0,0,0.6)

/* Interactive Colors */
--primary-500: #6366f1 (indigo-500)
--primary-600: #4f46e5 (indigo-600)
--success-500: #10b981 (emerald-500)
--danger-500: #ef4444 (red-500)
--info-500: #3b82f6 (blue-500)
--warning-500: #f59e0b (amber-500)

/* Progress Colors */
--success-rate-high: #10b981 (>80%)
--success-rate-medium: #f59e0b (50-80%)
--success-rate-low: #ef4444 (<50%)
```

### Typography
```css
/* Headers */
.page-title: 24px/1.2 'Inter', weight-700, color-gray-900
.page-subtitle: 14px/1.5 'Inter', weight-400, color-gray-600
.table-header: 16px/1.4 'Inter', weight-600, color-gray-900
.column-header: 14px/1.3 'Inter', weight-500, color-gray-700

/* Content */
.profile-name: 14px/1.4 'Inter', weight-600, color-gray-900
.profile-stage: 13px/1.3 'Inter', weight-400, color-gray-600
.stats-label: 12px/1.2 'Inter', weight-400, color-gray-600
.stats-value: 12px/1.2 'Inter', weight-600, color-gray-900

/* Form Elements */
.form-label: 14px/1.3 'Inter', weight-500, color-gray-700
.form-input: 14px/1.4 'Inter', weight-400, color-gray-900
.form-error: 12px/1.2 'Inter', weight-400, color-red-600
.form-help: 12px/1.2 'Inter', weight-400, color-gray-500
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
--form-field-gap: 16px
```

## 4. Interactive Components Breakdown

### Data Table Component
**Purpose**: Display profiles in organized, sortable, filterable table format

**Visual States**:
- **Default**: Clean table with alternating row highlighting
- **Hover**: Subtle row background change (#f8fafc)
- **Selected**: Blue accent (#e0e7ff) with checkbox filled
- **Loading**: Skeleton placeholders in table structure
- **Empty**: Center-aligned message with illustration

**Interactions**:
- **Row Selection**: Checkbox click for single/multiple selection
- **Column Sorting**: Click headers for asc/desc sorting
- **Global Search**: Real-time filtering across all columns
- **Pagination**: Navigate through large datasets
- **Row Actions**: Edit, view, scan controls per row

### Toolbar Component
**Purpose**: Primary actions and search functionality

**Left Section**:
- **New Profile Button**: Primary green button with plus icon
- **Delete Selected Button**: Danger red button, disabled when no selection

**Right Section**:
- **Search Input**: Icon-prefixed input with real-time filtering
- **Advanced Filters**: (Future expansion) dropdown filters

### Profile Avatar Component
**Purpose**: Visual profile identification

**Specifications**:
- **Size**: 40x40px circular avatar
- **Fallback**: Initials with generated background color
- **Border**: 2px white border with subtle shadow
- **Hover**: Scale animation (1.05x) with enhanced shadow

### Status Tag Component
**Purpose**: Visual status communication

**Variants**:
- **Active**: Green background, white text, dot indicator
- **Scanning**: Blue background, white text, spinning indicator
- **Inactive**: Amber background, dark text, pause indicator
- **Paused**: Gray background, dark text, pause indicator
- **Error**: Red background, white text, alert indicator

**Specifications**:
- **Padding**: 4px 8px
- **Border Radius**: 12px (pill shape)
- **Typography**: 12px, weight-500, uppercase
- **Icon**: 12px icon with 4px margin

### Platform Chips Component
**Purpose**: Show connected platforms at a glance

**Design**:
- **Individual Chips**: Platform name in small rounded containers
- **Color Scheme**: Light backgrounds with darker text
- **Overflow Indicator**: "+N more" badge when >3 platforms
- **Hover**: Tooltip showing all platforms

### Progress Bar Component
**Purpose**: Visual representation of success rates

**Specifications**:
- **Dimensions**: 48px width × 8px height
- **Background**: Light gray (#e5e7eb)
- **Fill**: Gradient based on percentage (green high, amber medium, red low)
- **Border Radius**: 4px
- **Animation**: Fill animates on data load

### Modal Dialog Component
**Purpose**: Profile creation and editing

**Structure**:
- **Header**: Title with close button (×)
- **Body**: Form fields in responsive grid
- **Footer**: Action buttons (Cancel/Save)

**Form Layout**:
- **Grid**: 2-column on desktop, single column on mobile
- **Field Types**: Text inputs, dropdowns, textarea
- **Validation**: Real-time with error messages
- **Required Indicators**: Red asterisk (*) on labels

## 5. Interaction Patterns & User Flows

### Create New Profile Flow
1. **Trigger**: User clicks "New Profile" button
2. **Action**: Modal dialog opens with empty form
3. **Form Completion**: User fills required fields with validation
4. **Submission**: Form validates and submits
5. **Success**: Toast notification, modal closes, table refreshes
6. **Error**: Error message displayed, modal remains open

### Edit Existing Profile Flow
1. **Trigger**: User clicks edit icon on profile row
2. **Action**: Modal opens pre-populated with profile data
3. **Modification**: User edits fields with live validation
4. **Submission**: Changes validated and saved
5. **Success**: Profile updated in table, success toast shown
6. **Cancel**: Modal closes, no changes saved

### Bulk Delete Flow
1. **Selection**: User selects multiple profiles via checkboxes
2. **Action**: "Delete Selected" button becomes enabled
3. **Confirmation**: Confirmation dialog appears with count
4. **Execution**: User confirms deletion
5. **Result**: Profiles removed, selection cleared, success toast
6. **Cancel**: Dialog closes, selections maintained

### Search and Filter Flow
1. **Input**: User types in search box
2. **Processing**: Real-time filtering across all columns
3. **Results**: Table updates immediately with matches
4. **Clear**: Search can be cleared to show all profiles
5. **Empty Results**: "No profiles found" message displayed

### Profile Actions Flow
1. **Edit**: Opens edit modal with profile data
2. **View Details**: Navigation to detailed profile view
3. **Start Scan**: Initiates scanning process with status update
4. **Status Updates**: Real-time status changes reflected in table

## 6. Content Strategy & Messaging

### Primary Headings
- **Page Title**: "Content Creator Profiles"
- **Page Subtitle**: "Manage and monitor your protected content profiles"
- **Table Header**: Dynamic count "Showing X to Y of Z profiles"

### Button Labels
- **Primary Actions**: "New Profile", "Delete Selected"
- **Row Actions**: "Edit", "View Details", "Start Scan"
- **Modal Actions**: "Create", "Update", "Cancel"

### Status Messages
- **Loading**: "Loading profiles..."
- **Empty State**: "No profiles found."
- **Search Empty**: "No profiles match your search."
- **Success**: "Profile created successfully", "Profile updated successfully"
- **Error**: "Failed to load profiles", "Failed to save profile"

### Form Labels & Placeholders
```
Profile Name* → "Enter profile name"
Stage Name* → "@username"
Description* → "Describe this profile..."
Status* → "Select status"
Scan Frequency* → "Select frequency"
Category* → "Select category"
Priority* → "Select priority"
```

### Validation Messages
```
Profile Name: "Profile name is required", "Name must be at least 2 characters"
Stage Name: "Stage name is required"
Description: "Description is required", "Description must be less than 500 characters"
Dropdowns: "[Field] is required"
```

## 7. Data Structure & Content Types

### Profile Data Model
```typescript
interface Profile {
  id: string;
  name: string;                    // Display name
  stageName?: string;             // @username or stage name
  description: string;            // Profile description
  image?: string;                 // Avatar URL
  status: 'active' | 'inactive' | 'scanning' | 'error' | 'paused' | 'archived';
  platforms: PlatformAccount[];   // Connected platforms
  totalScans: number;             // Total scan count
  infringementsFound: number;     // Issues discovered
  lastScan: string;               // ISO date string
  createdAt: string;              // ISO date string
  successRate: number;            // Percentage (0-100)
  scanFrequency: 'daily' | 'weekly' | 'monthly';
  tags?: string[];                // Optional tags
  category?: string;              // Profile category
  priority?: string;              // Priority level
}

interface PlatformAccount {
  id: string;
  name: string;                   // Display name
  username: string;               // Platform username
  isConnected: boolean;           // Connection status
  followers?: number;             // Follower count
  platform: string;              // Platform identifier
  lastSync?: string;              // Last synchronization
  scanEnabled?: boolean;          // Scanning enabled flag
}
```

### Form Data Model
```typescript
interface ProfileFormData {
  name: string;
  stageName: string;
  description: string;
  status: string;
  scanFrequency: string;
  category: string;
  priority: string;
}
```

### Configuration Options
```typescript
const statusOptions = [
  { label: 'Active', value: 'active' },
  { label: 'Inactive', value: 'inactive' },
  { label: 'Scanning', value: 'scanning' },
  { label: 'Paused', value: 'paused' },
  { label: 'Error', value: 'error' }
];

const frequencyOptions = [
  { label: 'Daily', value: 'daily' },
  { label: 'Weekly', value: 'weekly' },
  { label: 'Monthly', value: 'monthly' }
];

const categoryOptions = [
  { label: 'Adult Entertainment', value: 'Adult Entertainment' },
  { label: 'Fitness', value: 'Fitness' },
  { label: 'Lifestyle', value: 'Lifestyle' },
  { label: 'Gaming', value: 'Gaming' },
  { label: 'Music', value: 'Music' }
];

const priorityOptions = [
  { label: 'Low', value: 'low' },
  { label: 'Normal', value: 'normal' },
  { label: 'High', value: 'high' }
];
```

## 8. Accessibility Requirements

### Keyboard Navigation
- **Tab Order**: Toolbar → Table → Pagination → Modal (when open)
- **Table Navigation**: Arrow keys for cell navigation, Enter to activate
- **Modal Navigation**: Tab through form fields, Escape to close
- **Search**: Focus indication with visible outline

### Screen Reader Support
```html
<!-- Table Structure -->
<table role="table" aria-label="Content Creator Profiles">
  <thead>
    <tr role="row">
      <th role="columnheader" aria-sort="none">Profile</th>
      <th role="columnheader" aria-sort="ascending">Status</th>
    </tr>
  </thead>
  <tbody>
    <tr role="row" aria-selected="false">
      <td role="gridcell">Profile content</td>
    </tr>
  </tbody>
</table>

<!-- Form Elements -->
<label for="profile-name" class="required">Profile Name</label>
<input 
  id="profile-name" 
  type="text" 
  aria-required="true" 
  aria-describedby="name-error"
  aria-invalid="false"
/>
<div id="name-error" role="alert" aria-live="polite"></div>

<!-- Action Buttons -->
<button 
  aria-label="Edit profile for John Doe"
  title="Edit"
  type="button"
>
  <i class="pi pi-pencil" aria-hidden="true"></i>
</button>
```

### WCAG Compliance Features
- **Color Contrast**: All text meets WCAG AA standards (4.5:1 minimum)
- **Focus Indicators**: Visible focus rings on all interactive elements
- **Error Handling**: Clear error messages with screen reader announcements
- **Alternative Text**: Descriptive labels for all icons and images
- **Semantic Markup**: Proper heading hierarchy and landmark roles

### Responsive Accessibility
- **Touch Targets**: Minimum 44px×44px on mobile devices
- **Zoom Support**: Interface remains usable at 200% zoom
- **Motion Preferences**: Respect prefers-reduced-motion settings

## 9. Performance Considerations

### Loading Strategy
- **Initial Load**: Skeleton placeholders while fetching data
- **Pagination**: Load profiles in chunks (10/25/50 per page)
- **Search**: Debounced search with 300ms delay
- **Images**: Lazy loading for profile avatars with fallbacks

### Data Management
- **Caching**: Cache profile data for 5 minutes
- **Updates**: Optimistic updates for better UX
- **Sorting**: Client-side sorting for loaded data
- **Filtering**: Client-side filtering with server fallback

### Component Optimization
```typescript
// Memoized column templates
const profileBodyTemplate = useMemo(() => (rowData: Profile) => (
  // Template content
), []);

// Debounced search handler
const debouncedSearch = useCallback(
  debounce((value: string) => {
    setGlobalFilterValue(value);
  }, 300),
  []
);
```

### Bundle Size Optimization
- **Tree Shaking**: Import only used PrimeReact components
- **Code Splitting**: Lazy load modal dialog component
- **Icon Optimization**: Use only required PrimeIcons

## 10. Error Handling & Edge Cases

### Loading States
```typescript
// Loading skeleton
if (loading) {
  return (
    <Card>
      <div className="grid">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="col-12 md:col-6 lg:col-4">
            <Skeleton width="100%" height="200px" />
          </div>
        ))}
      </div>
    </Card>
  );
}
```

### Empty States
- **No Profiles**: Illustration with call-to-action button
- **Search No Results**: Clear message with search term
- **Filter No Results**: Option to clear filters

### Error Handling
```typescript
// API Error Handling
const fetchProfiles = async () => {
  try {
    setLoading(true);
    const response = await profileApi.getProfiles();
    setProfiles(response.data?.items || response.data || []);
  } catch (error) {
    toast.current?.show({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to load profiles',
      life: 3000
    });
    console.error('Error fetching profiles:', error);
  } finally {
    setLoading(false);
  }
};
```

### Form Validation
- **Client-side**: Yup schema validation with React Hook Form
- **Real-time**: Field validation on blur/change
- **Server-side**: API error handling with user feedback
- **Network Issues**: Retry mechanisms with user notification

### Edge Cases
- **Large Datasets**: Virtual scrolling for 1000+ profiles
- **Slow Networks**: Progressive loading with timeouts
- **Concurrent Edits**: Conflict resolution with user notification
- **Browser Compatibility**: Graceful degradation for older browsers

## 11. Integration Points

### API Endpoints
```typescript
// Profile API Service
const profileApi = {
  getProfiles: () => GET('/api/profiles'),
  createProfile: (data: ProfileFormData) => POST('/api/profiles', data),
  updateProfile: (id: string, data: Partial<Profile>) => PUT(`/api/profiles/${id}`, data),
  deleteProfile: (id: string) => DELETE(`/api/profiles/${id}`),
  bulkDelete: (ids: string[]) => DELETE('/api/profiles/bulk', { ids }),
  startScan: (id: string) => POST(`/api/profiles/${id}/scan`),
  getProfileStats: (id: string) => GET(`/api/profiles/${id}/stats`)
};
```

### WebSocket Integration
```typescript
// Real-time status updates
useEffect(() => {
  const ws = new WebSocket('ws://localhost:8000/ws');
  
  ws.onmessage = (event) => {
    const { type, profileId, status, data } = JSON.parse(event.data);
    
    if (type === 'profile_status_update') {
      setProfiles(profiles => 
        profiles.map(profile => 
          profile.id === profileId 
            ? { ...profile, status, ...data }
            : profile
        )
      );
    }
  };
  
  return () => ws.close();
}, []);
```

### Context Integration
```typescript
// Authentication Context
const { user, hasPermission } = useAuth();
const canEdit = hasPermission('profiles:edit');
const canDelete = hasPermission('profiles:delete');

// WebSocket Context
const { isConnected, subscribe } = useWebSocket();
useEffect(() => {
  if (isConnected) {
    subscribe('profile-updates', handleProfileUpdate);
  }
}, [isConnected]);
```

## 12. Technical Implementation Notes

### State Management
```typescript
// Component State
const [profiles, setProfiles] = useState<Profile[]>([]);
const [loading, setLoading] = useState(true);
const [globalFilterValue, setGlobalFilterValue] = useState('');
const [selectedProfiles, setSelectedProfiles] = useState<Profile[]>([]);
const [profileDialog, setProfileDialog] = useState(false);
const [editingProfile, setEditingProfile] = useState<Profile | null>(null);

// Table Filters
const [filters, setFilters] = useState({
  global: { value: null, matchMode: FilterMatchMode.CONTAINS }
});
```

### Form Management
```typescript
// React Hook Form with Yup validation
const {
  control,
  handleSubmit,
  reset,
  formState: { errors }
} = useForm<ProfileFormData>({
  resolver: yupResolver(validationSchema),
  defaultValues: {
    name: '',
    stageName: '',
    description: '',
    status: 'active',
    scanFrequency: 'weekly',
    category: 'Lifestyle',
    priority: 'normal'
  }
});
```

### PrimeReact Configuration
```typescript
// DataTable Configuration
<DataTable
  value={profiles}
  selection={selectedProfiles}
  onSelectionChange={(e) => setSelectedProfiles(e.value)}
  dataKey="id"
  paginator
  rows={10}
  rowsPerPageOptions={[5, 10, 25]}
  className="datatable-responsive"
  paginatorTemplate="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport RowsPerPageDropdown"
  currentPageReportTemplate="Showing {first} to {last} of {totalRecords} profiles"
  globalFilter={globalFilterValue}
  filters={filters}
  header={header}
  emptyMessage="No profiles found."
  loading={loading}
>
```

## 13. Future Enhancements

### Phase 2 Features
- **Advanced Filtering**: Multi-column filters with date ranges
- **Bulk Operations**: Bulk edit capabilities beyond delete
- **Export Functionality**: CSV/PDF export of profile data
- **Profile Templates**: Predefined profile configurations
- **Batch Import**: CSV import for multiple profiles

### Phase 3 Features
- **Analytics Dashboard**: Detailed performance metrics per profile
- **Automated Rules**: Smart scanning rules based on profile data
- **Integration Hub**: Third-party platform connections
- **Team Collaboration**: Multi-user profile management
- **Audit Logging**: Complete action history tracking

### Performance Optimizations
- **Virtual Scrolling**: Handle 10,000+ profiles efficiently
- **Intelligent Caching**: Profile-specific cache strategies
- **Background Sync**: Offline-first capabilities
- **Real-time Collaboration**: Multi-user real-time updates

This comprehensive specification provides complete guidance for implementing the Creator Profiles Management screen with professional-grade functionality, accessibility, and user experience standards.