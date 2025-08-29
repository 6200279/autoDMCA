# ShieldMyContent - Dashboard Screen Design Specification

## Table of Contents
- [Overview](#overview)
- [Layout Architecture](#layout-architecture)
- [Visual Design System](#visual-design-system)
- [Components Breakdown](#components-breakdown)
- [Data Visualization](#data-visualization)
- [Widget Specifications](#widget-specifications)
- [Real-time Features](#real-time-features)
- [Interactive Elements](#interactive-elements)
- [States & Loading](#states--loading)
- [Error Handling](#error-handling)
- [Accessibility](#accessibility)
- [Performance Requirements](#performance-requirements)
- [Responsive Design](#responsive-design)
- [Micro-interactions](#micro-interactions)
- [Implementation Notes](#implementation-notes)

---

## Overview

### Purpose
The dashboard serves as the central command center for users to monitor their content protection activities, view key metrics, access quick actions, and get insights into their account performance.

### Business Requirements
- **Primary Goal**: Provide comprehensive overview of protection status
- **Secondary Goals**: Enable quick actions, show value delivered, drive engagement
- **User Types**: Content creators, business users, administrators
- **Key Metrics**: Engagement time >5 minutes, action completion >70%

### Success Metrics
- Daily active users engagement > 80%
- Time spent on dashboard > 5 minutes
- Quick action usage > 60%
- User satisfaction score > 4.5/5

---

## Layout Architecture

### Overall Structure
```
┌─────────────────────────────────────────────────────────────────┐
│                        Header Bar                                │
├─────────────────────────────────────────────────────────────────┤
│          │                                                       │
│          │                Main Dashboard Area                    │
│ Sidebar  │  ┌─────────────┬─────────────┬─────────────────────┐ │
│          │  │   Widget 1  │   Widget 2  │      Widget 3      │ │
│          │  ├─────────────┼─────────────┼─────────────────────┤ │
│          │  │   Widget 4  │   Widget 5  │      Widget 6      │ │
│          │  ├─────────────┼─────────────┼─────────────────────┤ │
│          │  │           Widget 7        │      Widget 8      │ │
│          │  └─────────────┴─────────────┴─────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Grid System
- **Container**: CSS Grid with 12-column layout
- **Widget Sizing**: Flexible 1x1, 1x2, 2x1, 2x2 units
- **Gutters**: 24px between widgets
- **Responsive**: Collapses to single column on mobile
- **Max Width**: 1440px centered

---

## Visual Design System

### Color Palette

#### Dashboard-Specific Colors
- **Success Green**: `#10b981` - Protection active, good metrics
- **Warning Orange**: `#f59e0b` - Attention needed
- **Critical Red**: `#ef4444` - Issues requiring immediate action
- **Info Blue**: `#3b82f6` - General information
- **Neutral Gray**: `#6b7280` - Secondary information

#### Status Indicator Colors
- **Protected**: `#10b981` (Green)
- **Monitoring**: `#3b82f6` (Blue)  
- **At Risk**: `#f59e0b` (Orange)
- **Compromised**: `#ef4444` (Red)
- **Unknown**: `#6b7280` (Gray)

### Typography

#### Dashboard Hierarchy
- **Page Title**: 32px / 40px, Bold (700)
- **Widget Titles**: 20px / 28px, Semi-Bold (600)
- **Metric Values**: 36px / 44px, Bold (700)
- **Metric Labels**: 14px / 20px, Medium (500)
- **Body Text**: 16px / 24px, Regular (400)
- **Small Text**: 14px / 20px, Regular (400)
- **Caption**: 12px / 16px, Regular (400)

### Spacing & Layout
- **Widget Padding**: 24px all sides
- **Section Spacing**: 32px between major sections
- **Element Spacing**: 16px between related elements
- **Metric Spacing**: 8px between value and label

---

## Components Breakdown

### 1. Header Section

#### Welcome Area
```css
Welcome Section {
  padding: 32px 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 12px;
  margin-bottom: 32px;
}

Welcome Title {
  font-size: 28px;
  font-weight: 600;
  margin-bottom: 8px;
}

Welcome Subtitle {
  font-size: 16px;
  opacity: 0.9;
  margin-bottom: 24px;
}
```

**Content Structure:**
- Personalized greeting: "Good morning, [First Name]"
- Status summary: "Your content is actively protected"
- Last activity: "Last scan completed 2 hours ago"

#### Quick Stats Bar
```css
Quick Stats {
  display: flex;
  gap: 32px;
  background: rgba(255, 255, 255, 0.1);
  padding: 20px 24px;
  border-radius: 8px;
  backdrop-filter: blur(10px);
}

Stat Item {
  text-align: center;
  flex: 1;
}

Stat Value {
  font-size: 24px;
  font-weight: 700;
  display: block;
}

Stat Label {
  font-size: 12px;
  opacity: 0.8;
  margin-top: 4px;
}
```

**Quick Stats:**
- Total Protected Content: 1,247 items
- Active Monitoring: 24/7
- Threats Blocked: 23 this week
- Success Rate: 94.2%

### 2. Main Dashboard Widgets

#### Protection Status Widget
```css
Protection Widget {
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  padding: 24px;
  min-height: 200px;
}

Status Indicator {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
}

Status Dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--status-color);
  margin-right: 12px;
  animation: pulse 2s infinite;
}

Status Text {
  font-size: 18px;
  font-weight: 600;
  color: var(--status-color);
}
```

**Status Options:**
- 🟢 **Fully Protected**: All systems active
- 🔵 **Monitoring**: Scans in progress
- 🟡 **Attention Needed**: Some issues detected
- 🔴 **Action Required**: Immediate attention needed

#### Key Metrics Widget
```css
Metrics Grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-top: 20px;
}

Metric Item {
  text-align: center;
  padding: 16px;
  background: #f8fafc;
  border-radius: 8px;
}

Metric Value {
  font-size: 32px;
  font-weight: 700;
  color: #1f2937;
  display: block;
}

Metric Change {
  font-size: 12px;
  font-weight: 500;
  margin-top: 4px;
}

Metric Change.positive {
  color: #10b981;
}

Metric Change.negative {
  color: #ef4444;
}
```

**Key Metrics:**
- Content Items Protected: 1,247
- Active Takedowns: 15
- Success Rate: 94.2%
- Response Time: 6.3 hours avg

#### Recent Activity Feed
```css
Activity Feed {
  max-height: 400px;
  overflow-y: auto;
}

Activity Item {
  padding: 16px 0;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
}

Activity Icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 16px;
  background: var(--activity-bg);
  color: var(--activity-color);
}

Activity Content {
  flex: 1;
}

Activity Title {
  font-size: 14px;
  font-weight: 500;
  color: #1f2937;
  margin-bottom: 4px;
}

Activity Description {
  font-size: 12px;
  color: #6b7280;
}

Activity Time {
  font-size: 12px;
  color: #9ca3af;
  white-space: nowrap;
}
```

**Activity Types:**
- 🛡️ Protection activated for new content
- ⚠️ Potential infringement detected
- ✅ Takedown request successful
- 📧 DMCA notice sent
- 🔍 Scan completed
- 📊 Weekly report generated

#### Analytics Chart Widget
```css
Chart Container {
  position: relative;
  height: 300px;
  margin-top: 20px;
}

Chart Controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

Time Range Selector {
  display: flex;
  gap: 8px;
}

Range Button {
  padding: 6px 12px;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
  background: #ffffff;
  color: #6b7280;
  font-size: 12px;
  cursor: pointer;
}

Range Button.active {
  background: #3b82f6;
  color: #ffffff;
  border-color: #3b82f6;
}
```

**Chart Types:**
- Protection Events Over Time (Line Chart)
- Content Distribution by Platform (Donut Chart)
- Threat Detection Trends (Bar Chart)
- Response Time Analytics (Line Chart)

### 3. Quick Actions Panel

#### Action Buttons Grid
```css
Quick Actions {
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  padding: 24px;
}

Actions Grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-top: 20px;
}

Action Button {
  padding: 20px 16px;
  border-radius: 8px;
  border: 2px solid #e5e7eb;
  background: #ffffff;
  cursor: pointer;
  text-align: center;
  transition: all 0.15s ease;
}

Action Button:hover {
  border-color: #3b82f6;
  background: #f0f9ff;
  transform: translateY(-2px);
}

Action Icon {
  width: 32px;
  height: 32px;
  margin: 0 auto 12px;
  color: #3b82f6;
}

Action Label {
  font-size: 14px;
  font-weight: 500;
  color: #1f2937;
}
```

**Quick Actions:**
- 📁 Upload New Content
- 🔍 Run Manual Scan
- 📧 Send DMCA Notice
- 📊 Generate Report
- ⚙️ Update Settings
- 🎯 Create Profile

### 4. Notifications Widget

#### Notification List
```css
Notifications Panel {
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  padding: 24px;
  max-height: 400px;
}

Notification Item {
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 12px;
  border-left: 4px solid var(--notification-color);
  background: var(--notification-bg);
}

Notification Header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

Notification Title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
}

Notification Time {
  font-size: 12px;
  color: #6b7280;
}

Notification Body {
  font-size: 13px;
  color: #4b5563;
  line-height: 1.4;
}

Notification Actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}
```

**Notification Types:**
- 🔴 **Critical**: Immediate action required
- 🟡 **Warning**: Attention needed
- 🔵 **Info**: General updates
- 🟢 **Success**: Positive outcomes

---

## Data Visualization

### Chart Specifications

#### Protection Events Timeline
```javascript
const timelineChart = {
  type: 'line',
  data: {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
    datasets: [{
      label: 'Content Protected',
      data: [45, 67, 89, 123, 145, 167],
      borderColor: '#10b981',
      backgroundColor: 'rgba(16, 185, 129, 0.1)',
      tension: 0.4
    }, {
      label: 'Threats Blocked',
      data: [12, 19, 25, 31, 28, 35],
      borderColor: '#ef4444',
      backgroundColor: 'rgba(239, 68, 68, 0.1)',
      tension: 0.4
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom'
      }
    },
    scales: {
      y: {
        beginAtZero: true
      }
    }
  }
}
```

#### Platform Distribution Donut Chart
```javascript
const platformChart = {
  type: 'doughnut',
  data: {
    labels: ['OnlyFans', 'Instagram', 'Twitter', 'Reddit', 'Other'],
    datasets: [{
      data: [35, 25, 20, 15, 5],
      backgroundColor: [
        '#3b82f6',
        '#10b981', 
        '#f59e0b',
        '#ef4444',
        '#6b7280'
      ],
      borderWidth: 2,
      borderColor: '#ffffff'
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'right'
      }
    }
  }
}
```

### Progress Indicators

#### Protection Coverage Bar
```css
Coverage Progress {
  width: 100%;
  height: 8px;
  background: #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
  margin: 16px 0;
}

Coverage Fill {
  height: 100%;
  background: linear-gradient(90deg, #10b981 0%, #3b82f6 100%);
  border-radius: 4px;
  transition: width 0.5s ease;
  animation: shimmer 2s infinite;
}

Coverage Label {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #6b7280;
  margin-top: 4px;
}
```

---

## Real-time Features

### WebSocket Integration

#### Real-time Data Updates
- **Stats Refresh**: Every 30 seconds
- **Activity Feed**: Live updates
- **Notifications**: Instant delivery
- **Status Changes**: Immediate updates

#### Connection Handling
```css
Connection Status {
  position: fixed;
  top: 20px;
  right: 20px;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
  z-index: 1000;
}

Status Connected {
  background: #dcfce7;
  color: #166534;
  border: 1px solid #bbf7d0;
}

Status Disconnected {
  background: #fef2f2;
  color: #991b1b;
  border: 1px solid #fecaca;
}

Status Reconnecting {
  background: #fef3c7;
  color: #92400e;
  border: 1px solid #fed7aa;
}
```

### Live Data Indicators

#### Pulsing Status Dots
```css
@keyframes pulse {
  0% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.7;
    transform: scale(1.1);
  }
  100% {
    opacity: 1;
    transform: scale(1);
  }
}

Live Indicator {
  animation: pulse 2s infinite;
}
```

---

## Interactive Elements

### Widget Interactions

#### Hover Effects
```css
Widget:hover {
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
  transition: all 0.15s ease;
}
```

#### Click Actions
- **Widget Expansion**: Full-screen modal view
- **Drill-down**: Navigate to detailed view
- **Quick Actions**: In-place operations
- **Context Menus**: Right-click options

#### Drag & Drop
```css
Widget Dragging {
  opacity: 0.8;
  transform: rotate(3deg);
  z-index: 1000;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
}

Drop Zone {
  border: 2px dashed #3b82f6;
  background: rgba(59, 130, 246, 0.05);
  border-radius: 8px;
}
```

### Filter Controls

#### Date Range Picker
```css
Date Filter {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 8px 12px;
}

Date Input {
  border: none;
  background: transparent;
  font-size: 14px;
  color: #374151;
}

Date Separator {
  color: #9ca3af;
  font-size: 14px;
}
```

---

## States & Loading

### Loading States

#### Widget Loading
```css
Widget Loading {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  background: #f9fafb;
  border-radius: 12px;
}

Loading Spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e5e7eb;
  border-top: 3px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}
```

#### Skeleton Loading
```css
Skeleton Item {
  background: linear-gradient(
    90deg,
    #f0f0f0 25%,
    #e0e0e0 50%,
    #f0f0f0 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 4px;
  height: 20px;
  margin-bottom: 8px;
}

@keyframes shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}
```

### Empty States

#### No Data Available
```css
Empty State {
  text-align: center;
  padding: 48px 24px;
  color: #6b7280;
}

Empty Icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 16px;
  opacity: 0.5;
}

Empty Title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 8px;
}

Empty Description {
  font-size: 14px;
  line-height: 1.5;
  margin-bottom: 24px;
}

Empty Action {
  background: #3b82f6;
  color: #ffffff;
  border: none;
  border-radius: 6px;
  padding: 10px 20px;
  font-size: 14px;
  cursor: pointer;
}
```

---

## Error Handling

### Error States

#### Widget Error Display
```css
Widget Error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 12px;
  padding: 24px;
  text-align: center;
}

Error Icon {
  width: 48px;
  height: 48px;
  color: #ef4444;
  margin: 0 auto 16px;
}

Error Message {
  font-size: 16px;
  font-weight: 500;
  color: #991b1b;
  margin-bottom: 16px;
}

Error Actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}
```

#### Network Error Handling
- **Offline Detection**: Show offline indicator
- **Retry Mechanism**: Automatic retry with backoff
- **Cached Data**: Show last known good data
- **User Feedback**: Clear error messages and actions

---

## Accessibility

### Keyboard Navigation
- **Tab Order**: Logical widget progression
- **Focus Management**: Clear focus indicators
- **Skip Links**: Skip to main content areas
- **Keyboard Shortcuts**: Dashboard-specific shortcuts

### Screen Reader Support
```html
<main role="main" aria-label="Dashboard">
  <section aria-label="Dashboard overview">
    <h1>Dashboard</h1>
    <div role="region" aria-label="Protection status">
      <!-- Status content -->
    </div>
    <div role="region" aria-label="Key metrics">
      <!-- Metrics content -->
    </div>
  </section>
  <!-- Additional sections -->
</main>
```

### ARIA Attributes
- **aria-label**: Descriptive labels for widgets
- **aria-describedby**: Link metrics to descriptions
- **aria-live**: Announce real-time updates
- **role**: Define widget purposes
- **aria-expanded**: Collapsible widgets

---

## Performance Requirements

### Loading Performance
- **Initial Load**: < 3 seconds
- **Widget Refresh**: < 500ms
- **Real-time Updates**: < 100ms latency
- **Chart Rendering**: < 1 second

### Optimization Strategies
1. **Lazy Loading**: Load widgets on demand
2. **Data Caching**: Cache frequently accessed data
3. **Debouncing**: Limit API calls
4. **Virtual Scrolling**: Large data sets
5. **Code Splitting**: Dynamic imports

---

## Responsive Design

### Mobile Layout (320px - 767px)
```css
Mobile Dashboard {
  padding: 16px;
  
  .dashboard-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }
  
  .widget {
    padding: 20px;
    min-height: auto;
  }
  
  .quick-actions {
    grid-template-columns: 1fr;
  }
  
  .metrics-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }
}
```

### Tablet Layout (768px - 1023px)
```css
Tablet Dashboard {
  .dashboard-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 20px;
  }
  
  .full-width-widget {
    grid-column: span 2;
  }
}
```

---

## Micro-interactions

### Widget Animations
```css
@keyframes widgetEntrance {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.widget {
  animation: widgetEntrance 0.3s ease-out;
}
```

### Data Update Animations
```css
@keyframes valueUpdate {
  0% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.1);
    color: #10b981;
  }
  100% {
    transform: scale(1);
  }
}

.metric-value.updated {
  animation: valueUpdate 0.5s ease-out;
}
```

---

## Implementation Notes

### Technical Stack
- **Framework**: React 18+ with TypeScript
- **Charts**: Chart.js with react-chartjs-2
- **Real-time**: WebSocket connection
- **State**: React Query for server state
- **Styling**: Tailwind CSS

### Required APIs
- **GET /dashboard/stats** - Key statistics
- **GET /dashboard/activity** - Recent activity
- **GET /dashboard/analytics** - Chart data
- **GET /dashboard/notifications** - User notifications
- **WebSocket /dashboard** - Real-time updates

### File Structure
```
src/
├── pages/
│   └── Dashboard.tsx
├── components/
│   ├── dashboard/
│   │   ├── ProtectionStatus.tsx
│   │   ├── KeyMetrics.tsx
│   │   ├── ActivityFeed.tsx
│   │   ├── AnalyticsChart.tsx
│   │   └── QuickActions.tsx
│   └── charts/
│       ├── LineChart.tsx
│       ├── DonutChart.tsx
│       └── ProgressBar.tsx
├── hooks/
│   ├── useDashboardData.ts
│   └── useRealtime.ts
└── types/
    └── dashboard.ts
```

This comprehensive specification provides everything needed to design and implement a professional, feature-rich dashboard for ShieldMyContent that serves as an effective command center for users' content protection activities.