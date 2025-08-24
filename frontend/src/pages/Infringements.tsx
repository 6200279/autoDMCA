import React, { useState, useEffect, useRef } from 'react';
import { Card } from 'primereact/card';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Button } from 'primereact/button';
import { Tag } from 'primereact/tag';
import { Image } from 'primereact/image';
import { Toolbar } from 'primereact/toolbar';
import { Toast } from 'primereact/toast';
import { OverlayPanel } from 'primereact/overlaypanel';
import { Timeline } from 'primereact/timeline';
import { InputText } from 'primereact/inputtext';
import { Calendar } from 'primereact/calendar';
import { Dropdown } from 'primereact/dropdown';
import { MultiSelect } from 'primereact/multiselect';
import { Skeleton } from 'primereact/skeleton';
import { Badge } from 'primereact/badge';
import { Chip } from 'primereact/chip';
import { Panel } from 'primereact/panel';
import { TabView, TabPanel } from 'primereact/tabview';
import { Chart } from 'primereact/chart';
import { ProgressBar } from 'primereact/progressbar';
import { ConfirmDialog, confirmDialog } from 'primereact/confirmdialog';
import { FilterMatchMode, FilterOperator } from 'primereact/api';
import { useAuth } from '../contexts/AuthContext';
import { infringementApi } from '../services/api';
import { useProfileRealtime, useNotificationsRealtime } from '../contexts/WebSocketContext';

// TypeScript interfaces
interface Infringement {
  id: string;
  title: string;
  description: string;
  url: string;
  platform: string;
  status: 'pending' | 'under_review' | 'takedown_sent' | 'removed' | 'rejected' | 'false_positive';
  confidence: number;
  similarity: number;
  profileId: string;
  profileName: string;
  thumbnail: string;
  originalContent: string;
  detectedAt: Date;
  lastUpdated: Date;
  takedownRequestId?: string;
  reportedBy: 'system' | 'user';
  tags: string[];
  metadata: {
    uploader?: string;
    viewCount?: number;
    likeCount?: number;
    commentCount?: number;
    duration?: number;
    contentType: 'image' | 'video' | 'text' | 'audio';
  };
}

interface InfringementStats {
  total: number;
  pending: number;
  underReview: number;
  takedownSent: number;
  removed: number;
  rejected: number;
  falsePositive: number;
  avgResponseTime: number;
  successRate: number;
}

const Infringements: React.FC = () => {
  const { user } = useAuth();
  const toast = useRef<Toast>(null);
  const detailsOverlay = useRef<OverlayPanel>(null);
  
  // WebSocket real-time updates
  const { profileActivities } = useProfileRealtime();
  const { notifications } = useNotificationsRealtime();

  // State management
  const [infringements, setInfringements] = useState<Infringement[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedInfringements, setSelectedInfringements] = useState<Infringement[]>([]);
  const [globalFilterValue, setGlobalFilterValue] = useState('');
  const [selectedInfringement, setSelectedInfringement] = useState<Infringement | null>(null);
  const [dateRange, setDateRange] = useState<Date[] | null>(null);
  const [stats, setStats] = useState<InfringementStats>({
    total: 0,
    pending: 0,
    underReview: 0,
    takedownSent: 0,
    removed: 0,
    rejected: 0,
    falsePositive: 0,
    avgResponseTime: 0,
    successRate: 0
  });

  // Filter options
  const platformOptions = [
    'Instagram', 'TikTok', 'OnlyFans', 'Twitter', 'YouTube', 'Reddit', 'Telegram'
  ];

  const statusOptions = [
    { label: 'Pending', value: 'pending' },
    { label: 'Under Review', value: 'under_review' },
    { label: 'Takedown Sent', value: 'takedown_sent' },
    { label: 'Removed', value: 'removed' },
    { label: 'Rejected', value: 'rejected' },
    { label: 'False Positive', value: 'false_positive' }
  ];

  const confidenceOptions = [
    { label: 'High (90%+)', value: 'high' },
    { label: 'Medium (70-89%)', value: 'medium' },
    { label: 'Low (<70%)', value: 'low' }
  ];

  // DataTable filters
  const [filters, setFilters] = useState({
    global: { value: null, matchMode: FilterMatchMode.CONTAINS },
    title: { value: null, matchMode: FilterMatchMode.CONTAINS },
    platform: { value: null, matchMode: FilterMatchMode.IN },
    status: { value: null, matchMode: FilterMatchMode.IN },
    confidence: { value: null, matchMode: FilterMatchMode.GREATER_THAN_OR_EQUAL_TO },
    detectedAt: { operator: FilterOperator.AND, constraints: [{ value: null, matchMode: FilterMatchMode.DATE_IS }] },
    profileName: { value: null, matchMode: FilterMatchMode.CONTAINS }
  });

  // Mock data
  const mockInfringements: Infringement[] = [
    {
      id: '1',
      title: 'Unauthorized Content Distribution',
      description: 'Original content reposted without permission on Instagram',
      url: 'https://instagram.com/p/example1',
      platform: 'Instagram',
      status: 'pending',
      confidence: 95,
      similarity: 98,
      profileId: '1',
      profileName: 'Sarah Johnson',
      thumbnail: '/api/placeholder/200/200',
      originalContent: '/api/placeholder/400/400',
      detectedAt: new Date(Date.now() - 2 * 60 * 60 * 1000),
      lastUpdated: new Date(Date.now() - 1 * 60 * 60 * 1000),
      reportedBy: 'system',
      tags: ['exact-match', 'high-confidence'],
      metadata: {
        uploader: '@unauthorized_account',
        viewCount: 15420,
        likeCount: 342,
        commentCount: 28,
        contentType: 'image'
      }
    },
    {
      id: '2',
      title: 'Video Content Theft',
      description: 'TikTok video uploaded without authorization',
      url: 'https://tiktok.com/@user/video/example2',
      platform: 'TikTok',
      status: 'takedown_sent',
      confidence: 88,
      similarity: 92,
      profileId: '2',
      profileName: 'Emma Davis',
      thumbnail: '/api/placeholder/200/200',
      originalContent: '/api/placeholder/400/300',
      detectedAt: new Date(Date.now() - 8 * 60 * 60 * 1000),
      lastUpdated: new Date(Date.now() - 2 * 60 * 60 * 1000),
      takedownRequestId: 'TKD-001',
      reportedBy: 'system',
      tags: ['video-match', 'medium-confidence'],
      metadata: {
        uploader: '@content_thief',
        viewCount: 8750,
        likeCount: 189,
        commentCount: 15,
        duration: 30,
        contentType: 'video'
      }
    },
    {
      id: '3',
      title: 'Profile Image Misuse',
      description: 'Profile photo used without permission on OnlyFans',
      url: 'https://onlyfans.com/fake_profile',
      platform: 'OnlyFans',
      status: 'under_review',
      confidence: 92,
      similarity: 95,
      profileId: '3',
      profileName: 'Mia Rodriguez',
      thumbnail: '/api/placeholder/200/200',
      originalContent: '/api/placeholder/400/400',
      detectedAt: new Date(Date.now() - 12 * 60 * 60 * 1000),
      lastUpdated: new Date(Date.now() - 4 * 60 * 60 * 1000),
      reportedBy: 'user',
      tags: ['profile-theft', 'identity-fraud'],
      metadata: {
        uploader: 'fake_profile_user',
        contentType: 'image'
      }
    },
    {
      id: '4',
      title: 'Content Remix/Edit',
      description: 'Modified version of original content on YouTube',
      url: 'https://youtube.com/watch?v=example4',
      platform: 'YouTube',
      status: 'removed',
      confidence: 75,
      similarity: 85,
      profileId: '1',
      profileName: 'Sarah Johnson',
      thumbnail: '/api/placeholder/200/200',
      originalContent: '/api/placeholder/400/300',
      detectedAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000),
      lastUpdated: new Date(Date.now() - 6 * 60 * 60 * 1000),
      takedownRequestId: 'YT-002',
      reportedBy: 'system',
      tags: ['modified-content', 'successful-removal'],
      metadata: {
        uploader: 'ContentRemixer',
        viewCount: 2340,
        likeCount: 45,
        commentCount: 8,
        duration: 120,
        contentType: 'video'
      }
    },
    {
      id: '5',
      title: 'False Positive - Similar Content',
      description: 'Content flagged but determined to be original',
      url: 'https://twitter.com/user/status/example5',
      platform: 'Twitter',
      status: 'false_positive',
      confidence: 68,
      similarity: 72,
      profileId: '4',
      profileName: 'Alex Chen',
      thumbnail: '/api/placeholder/200/200',
      originalContent: '/api/placeholder/400/400',
      detectedAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000),
      lastUpdated: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000),
      reportedBy: 'system',
      tags: ['false-positive', 'manual-review'],
      metadata: {
        uploader: '@legitimate_creator',
        likeCount: 23,
        commentCount: 5,
        contentType: 'image'
      }
    },
    {
      id: '6',
      title: 'Repost with Credit',
      description: 'Content reposted but may fall under fair use',
      url: 'https://reddit.com/r/example/post6',
      platform: 'Reddit',
      status: 'rejected',
      confidence: 85,
      similarity: 89,
      profileId: '5',
      profileName: 'Lisa Thompson',
      thumbnail: '/api/placeholder/200/200',
      originalContent: '/api/placeholder/400/400',
      detectedAt: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000),
      lastUpdated: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000),
      takedownRequestId: 'RDT-003',
      reportedBy: 'system',
      tags: ['credited-repost', 'fair-use-claim'],
      metadata: {
        uploader: 'u/fashion_fan',
        likeCount: 156,
        commentCount: 34,
        contentType: 'image'
      }
    }
  ];

  // Initialize data
  useEffect(() => {
    const loadInfringements = async () => {
      try {
        setLoading(true);
        
        // Load infringements from backend
        const response = await infringementApi.getInfringements({
          page: 1,
          limit: 100,
          include_stats: true
        });
        
        if (response.data) {
          const infringementsData = response.data.items || response.data;
          const statsData = response.data.stats;
          
          // Map backend data to frontend format
          const mappedInfringements = infringementsData.map((item: any) => ({
            ...item,
            detectedAt: new Date(item.detected_at || item.created_at),
            lastUpdated: new Date(item.updated_at),
            profileId: item.profile_id,
            profileName: item.profile_name || 'Unknown Profile',
            originalContent: item.original_content_url || item.original_url,
            reportedBy: item.reported_by || 'system',
            tags: item.tags || [],
            metadata: {
              contentType: item.content_type || 'image',
              uploader: item.uploader,
              viewCount: item.view_count,
              likeCount: item.like_count,
              commentCount: item.comment_count,
              duration: item.duration
            }
          }));
          
          setInfringements(mappedInfringements);
          
          // Use backend stats if available, otherwise calculate from data
          if (statsData) {
            setStats({
              total: statsData.total || mappedInfringements.length,
              pending: statsData.pending || 0,
              underReview: statsData.under_review || 0,
              takedownSent: statsData.takedown_sent || 0,
              removed: statsData.removed || 0,
              rejected: statsData.rejected || 0,
              falsePositive: statsData.false_positive || 0,
              avgResponseTime: statsData.avg_response_time || 24,
              successRate: statsData.success_rate || 0
            });
          } else {
            // Calculate stats from data
            const total = mappedInfringements.length;
            const pending = mappedInfringements.filter((i: any) => i.status === 'pending').length;
            const underReview = mappedInfringements.filter((i: any) => i.status === 'under_review').length;
            const takedownSent = mappedInfringements.filter((i: any) => i.status === 'takedown_sent').length;
            const removed = mappedInfringements.filter((i: any) => i.status === 'removed').length;
            const rejected = mappedInfringements.filter((i: any) => i.status === 'rejected').length;
            const falsePositive = mappedInfringements.filter((i: any) => i.status === 'false_positive').length;
            
            setStats({
              total,
              pending,
              underReview,
              takedownSent,
              removed,
              rejected,
              falsePositive,
              avgResponseTime: 24,
              successRate: Math.round((removed / (removed + rejected + falsePositive)) * 100) || 0
            });
          }
        }
      } catch (error) {
        console.error('Failed to load infringements:', error);
        // Fallback to mock data if API fails
        setInfringements(mockInfringements);
        
        const total = mockInfringements.length;
        const pending = mockInfringements.filter(i => i.status === 'pending').length;
        const underReview = mockInfringements.filter(i => i.status === 'under_review').length;
        const takedownSent = mockInfringements.filter(i => i.status === 'takedown_sent').length;
        const removed = mockInfringements.filter(i => i.status === 'removed').length;
        const rejected = mockInfringements.filter(i => i.status === 'rejected').length;
        const falsePositive = mockInfringements.filter(i => i.status === 'false_positive').length;
        
        setStats({
          total,
          pending,
          underReview,
          takedownSent,
          removed,
          rejected,
          falsePositive,
          avgResponseTime: 24,
          successRate: Math.round((removed / (removed + rejected + falsePositive)) * 100) || 0
        });
        
        toast.current?.show({
          severity: 'warn',
          summary: 'API Error',
          detail: 'Failed to load live data, showing sample data instead',
          life: 5000
        });
      } finally {
        setLoading(false);
      }
    };

    loadInfringements();
  }, []);
  
  // Handle real-time profile activities
  useEffect(() => {
    profileActivities.forEach(activity => {
      if (activity.type === 'infringement_detected') {
        // Add new infringement to the list
        const newInfringement: Infringement = {
          id: activity.infringement_id,
          title: activity.title,
          description: activity.description,
          url: activity.url,
          platform: activity.platform,
          status: activity.status || 'pending',
          confidence: activity.confidence || 0,
          similarity: activity.similarity || 0,
          profileId: activity.profile_id,
          profileName: activity.profile_name || 'Unknown Profile',
          thumbnail: activity.thumbnail || '',
          originalContent: activity.original_content || '',
          detectedAt: new Date(activity.timestamp),
          lastUpdated: new Date(activity.timestamp),
          reportedBy: 'system',
          tags: activity.tags || [],
          metadata: {
            contentType: activity.content_type || 'image',
            uploader: activity.uploader,
            viewCount: activity.view_count,
            likeCount: activity.like_count,
            commentCount: activity.comment_count,
            duration: activity.duration
          }
        };
        
        setInfringements(prev => {
          // Check if infringement already exists
          if (prev.find(inf => inf.id === newInfringement.id)) {
            return prev;
          }
          return [newInfringement, ...prev];
        });
        
        // Update stats
        setStats(prev => ({
          ...prev,
          total: prev.total + 1,
          pending: prev.pending + 1
        }));
        
        // Show notification
        toast.current?.show({
          severity: 'info',
          summary: 'New Infringement Detected',
          detail: `Found new infringement: ${activity.title}`,
          life: 5000
        });
      } else if (activity.type === 'infringement_updated') {
        // Update existing infringement
        setInfringements(prev => prev.map(inf => 
          inf.id === activity.infringement_id 
            ? { ...inf, status: activity.status, lastUpdated: new Date(activity.timestamp) }
            : inf
        ));
      }
    });
  }, [profileActivities]);
  
  // Handle real-time notifications
  useEffect(() => {
    notifications.forEach(notification => {
      if (notification.category === 'infringement') {
        toast.current?.show({
          severity: notification.type === 'success' ? 'success' : 
                   notification.type === 'error' ? 'error' : 'info',
          summary: notification.title,
          detail: notification.message,
          life: 4000
        });
      }
    });
  }, [notifications]);

  // Helper functions
  const getStatusSeverity = (status: string) => {
    switch (status) {
      case 'pending': return 'warning';
      case 'under_review': return 'info';
      case 'takedown_sent': return 'info';
      case 'removed': return 'success';
      case 'rejected': return 'danger';
      case 'false_positive': return 'secondary';
      default: return null;
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 90) return 'text-green-600';
    if (confidence >= 70) return 'text-orange-600';
    return 'text-red-600';
  };

  const formatDate = (date: Date) => {
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatTimeSince = (date: Date) => {
    const now = new Date();
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));
    
    if (diffInHours < 1) {
      const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));
      return `${diffInMinutes}m ago`;
    } else if (diffInHours < 24) {
      return `${diffInHours}h ago`;
    } else {
      const diffInDays = Math.floor(diffInHours / 24);
      return `${diffInDays}d ago`;
    }
  };

  // Action handlers
  const sendTakedown = async (infringement: Infringement) => {
    try {
      // Create takedown request via API
      const response = await infringementApi.createTakedownFromInfringement(infringement.id);
      
      const updatedInfringement = { 
        ...infringement, 
        status: 'takedown_sent' as Infringement['status'],
        takedownRequestId: response.data.id,
        lastUpdated: new Date()
      };
      
      setInfringements(infringements.map(i => 
        i.id === infringement.id ? updatedInfringement : i
      ));
      
      toast.current?.show({
        severity: 'success',
        summary: 'Takedown Sent',
        detail: `Takedown request sent for ${infringement.title}`,
        life: 3000
      });
    } catch (error: any) {
      console.error('Takedown send error:', error);
      const errorMessage = error.response?.data?.detail || 'Failed to send takedown request';
      toast.current?.show({
        severity: 'error',
        summary: 'Takedown Failed',
        detail: errorMessage,
        life: 5000
      });
    }
  };

  const markAsFalsePositive = async (infringement: Infringement) => {
    try {
      // Update infringement status via API
      await infringementApi.updateInfringement(infringement.id, {
        status: 'false_positive'
      });
      
      const updatedInfringement = { 
        ...infringement, 
        status: 'false_positive' as Infringement['status'],
        lastUpdated: new Date()
      };
      
      setInfringements(infringements.map(i => 
        i.id === infringement.id ? updatedInfringement : i
      ));
      
      toast.current?.show({
        severity: 'info',
        summary: 'Marked as False Positive',
        detail: 'Infringement marked as false positive',
        life: 3000
      });
    } catch (error: any) {
      console.error('False positive marking error:', error);
      const errorMessage = error.response?.data?.detail || 'Failed to mark as false positive';
      toast.current?.show({
        severity: 'error',
        summary: 'Update Failed',
        detail: errorMessage,
        life: 5000
      });
    }
  };

  const bulkSendTakedowns = async () => {
    const eligibleInfringements = selectedInfringements.filter(
      i => ['pending', 'under_review'].includes(i.status)
    );
    
    if (eligibleInfringements.length === 0) {
      toast.current?.show({
        severity: 'warn',
        summary: 'No Eligible Infringements',
        detail: 'Selected infringements are not eligible for takedown',
        life: 3000
      });
      return;
    }
    
    try {
      // Use bulk action API
      const response = await infringementApi.bulkAction({
        action: 'send_takedown',
        infringement_ids: eligibleInfringements.map(i => i.id)
      });
      
      // Update local state for successful takedowns
      const successfulIds = response.data.successful || eligibleInfringements.map(i => i.id);
      setInfringements(infringements.map(i => 
        successfulIds.includes(i.id) 
          ? { ...i, status: 'takedown_sent' as Infringement['status'], lastUpdated: new Date() }
          : i
      ));
      
      setSelectedInfringements([]);
      
      toast.current?.show({
        severity: 'success',
        summary: 'Bulk Takedowns Sent',
        detail: `${successfulIds.length} takedown requests sent successfully`,
        life: 3000
      });
    } catch (error: any) {
      console.error('Bulk takedown error:', error);
      const errorMessage = error.response?.data?.detail || 'Failed to send bulk takedowns';
      toast.current?.show({
        severity: 'error',
        summary: 'Bulk Operation Failed',
        detail: errorMessage,
        life: 5000
      });
    }
  };

  const showDetails = (infringement: Infringement, event: any) => {
    setSelectedInfringement(infringement);
    detailsOverlay.current?.toggle(event);
  };

  const exportData = () => {
    const csvContent = [
      ['ID', 'Title', 'Platform', 'Status', 'Confidence', 'Detected At', 'Profile'],
      ...infringements.map(i => [
        i.id,
        i.title,
        i.platform,
        i.status,
        `${i.confidence}%`,
        i.detectedAt.toISOString(),
        i.profileName
      ])
    ].map(row => row.join(',')).join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `infringements_${Date.now()}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    toast.current?.show({
      severity: 'success',
      summary: 'Export Complete',
      detail: 'Infringement data exported to CSV',
      life: 3000
    });
  };

  const onGlobalFilterChange = (e: any) => {
    const value = e.target.value;
    let _filters = { ...filters };
    _filters['global'].value = value;
    setFilters(_filters);
    setGlobalFilterValue(value);
  };

  // Column templates
  const thumbnailTemplate = (rowData: Infringement) => (
    <div className="flex align-items-center gap-2">
      <Image 
        src={rowData.thumbnail} 
        alt="Thumbnail"
        width="60"
        height="60"
        className="border-round"
        preview
      />
      <div>
        <div className="font-medium text-900 text-sm line-height-3">{rowData.title}</div>
        <div className="text-600 text-xs">{rowData.platform}</div>
      </div>
    </div>
  );

  const statusTemplate = (rowData: Infringement) => (
    <Tag 
      value={rowData.status.replace('_', ' ')} 
      severity={getStatusSeverity(rowData.status)}
      className="text-sm"
    />
  );

  const confidenceTemplate = (rowData: Infringement) => (
    <div className="text-center">
      <div className={`font-bold ${getConfidenceColor(rowData.confidence)}`}>
        {rowData.confidence}%
      </div>
      <div className="text-600 text-xs">
        {rowData.similarity}% similar
      </div>
    </div>
  );

  const platformTemplate = (rowData: Infringement) => (
    <Badge value={rowData.platform} />
  );

  const profileTemplate = (rowData: Infringement) => (
    <div className="text-center">
      <div className="font-medium text-900 text-sm">{rowData.profileName}</div>
      <div className="text-600 text-xs">Profile ID: {rowData.profileId}</div>
    </div>
  );

  const dateTemplate = (rowData: Infringement) => (
    <div className="text-center">
      <div className="text-900 text-sm">{formatTimeSince(rowData.detectedAt)}</div>
      <div className="text-600 text-xs">{formatDate(rowData.detectedAt)}</div>
    </div>
  );

  const actionsTemplate = (rowData: Infringement) => (
    <div className="flex gap-1">
      <Button
        icon="pi pi-eye"
        size="small"
        text
        tooltip="View Details"
        onClick={(e) => showDetails(rowData, e)}
      />
      <Button
        icon="pi pi-external-link"
        size="small"
        text
        tooltip="Open URL"
        onClick={() => window.open(rowData.url, '_blank')}
      />
      {['pending', 'under_review'].includes(rowData.status) && (
        <Button
          icon="pi pi-send"
          size="small"
          text
          severity="success"
          tooltip="Send Takedown"
          onClick={() => sendTakedown(rowData)}
        />
      )}
      {['pending', 'under_review'].includes(rowData.status) && (
        <Button
          icon="pi pi-times"
          size="small"
          text
          severity="danger"
          tooltip="Mark as False Positive"
          onClick={() => markAsFalsePositive(rowData)}
        />
      )}
    </div>
  );

  // Toolbar content
  const startContent = (
    <div className="flex align-items-center gap-2">
      <Button
        label="Bulk Takedown"
        icon="pi pi-send"
        severity="success"
        disabled={!selectedInfringements.length}
        onClick={bulkSendTakedowns}
      />
      <Button
        label="Mark False Positives"
        icon="pi pi-times"
        severity="danger"
        outlined
        disabled={!selectedInfringements.length}
        onClick={() => {
          selectedInfringements.forEach(infringement => markAsFalsePositive(infringement));
          setSelectedInfringements([]);
        }}
      />
      <Button
        label="Export"
        icon="pi pi-download"
        outlined
        onClick={exportData}
      />
    </div>
  );

  const endContent = (
    <div className="flex align-items-center gap-2">
      <span className="p-input-icon-left">
        <i className="pi pi-search" />
        <InputText
          value={globalFilterValue}
          onChange={onGlobalFilterChange}
          placeholder="Search infringements..."
          aria-label="Search infringements"
          size="small"
        />
      </span>
      <Button
        icon="pi pi-filter"
        text
        tooltip="Advanced Filters"
        onClick={() => {
          // Toggle advanced filters panel
        }}
      />
      <Button
        icon="pi pi-refresh"
        text
        tooltip="Refresh"
        onClick={() => {
          setLoading(true);
          setTimeout(() => {
            setInfringements([...mockInfringements]);
            setLoading(false);
          }, 500);
        }}
      />
    </div>
  );

  // Chart data for statistics
  const statusChartData = {
    labels: ['Pending', 'Under Review', 'Takedown Sent', 'Removed', 'Rejected', 'False Positive'],
    datasets: [
      {
        data: [stats.pending, stats.underReview, stats.takedownSent, stats.removed, stats.rejected, stats.falsePositive],
        backgroundColor: [
          '#FF9800',
          '#2196F3', 
          '#00BCD4',
          '#4CAF50',
          '#F44336',
          '#9E9E9E'
        ]
      }
    ]
  };

  if (loading) {
    return (
      <div className="grid">
        <div className="col-12">
          <Card>
            <Skeleton height="2rem" className="mb-4" />
            <div className="grid mb-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="col-12 md:col-3">
                  <Skeleton height="4rem" />
                </div>
              ))}
            </div>
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="flex align-items-center gap-3 mb-3">
                <Skeleton shape="circle" size="4rem" />
                <div className="flex-1">
                  <Skeleton height="1rem" className="mb-2" />
                  <Skeleton height="0.8rem" width="60%" />
                </div>
                <Skeleton height="2rem" width="5rem" />
              </div>
            ))}
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="grid">
      <div className="col-12">
        <div className="flex flex-column md:flex-row md:justify-content-between md:align-items-center mb-4 gap-3">
          <div>
            <h2 className="m-0 text-900">Infringement Detection</h2>
            <p className="text-600 m-0 mt-1">Monitor and manage detected content infringements</p>
          </div>
          <div className="flex align-items-center gap-2">
            <Calendar 
              value={dateRange} 
              onChange={(e) => setDateRange(e.value as Date[])} 
              selectionMode="range" 
              readOnlyInput 
              showIcon
              placeholder="Filter by date range"
              size="small"
            />
          </div>
        </div>

        {/* Statistics Cards */}
        <div className="grid mb-4">
          <div className="col-12 md:col-2">
            <Card className="text-center h-full">
              <div className="text-600 text-sm mb-2">Total Detections</div>
              <div className="text-900 font-bold text-2xl">{stats.total}</div>
            </Card>
          </div>
          <div className="col-12 md:col-2">
            <Card className="text-center h-full">
              <div className="text-600 text-sm mb-2">Pending Action</div>
              <div className="text-orange-600 font-bold text-2xl">{stats.pending}</div>
            </Card>
          </div>
          <div className="col-12 md:col-2">
            <Card className="text-center h-full">
              <div className="text-600 text-sm mb-2">Under Review</div>
              <div className="text-blue-600 font-bold text-2xl">{stats.underReview}</div>
            </Card>
          </div>
          <div className="col-12 md:col-2">
            <Card className="text-center h-full">
              <div className="text-600 text-sm mb-2">Successfully Removed</div>
              <div className="text-green-600 font-bold text-2xl">{stats.removed}</div>
            </Card>
          </div>
          <div className="col-12 md:col-2">
            <Card className="text-center h-full">
              <div className="text-600 text-sm mb-2">Success Rate</div>
              <div className="text-green-600 font-bold text-2xl">{stats.successRate}%</div>
            </Card>
          </div>
          <div className="col-12 md:col-2">
            <Card className="text-center h-full">
              <div className="text-600 text-sm mb-2">Avg Response</div>
              <div className="text-blue-600 font-bold text-2xl">{stats.avgResponseTime}h</div>
            </Card>
          </div>
        </div>

        <TabView>
          <TabPanel header="Infringements List" leftIcon="pi pi-list">
            <Card>
              <Toolbar start={startContent} end={endContent} className="mb-4" />

              <DataTable
                value={infringements}
                selection={selectedInfringements}
                onSelectionChange={(e) => setSelectedInfringements(e.value)}
                paginator
                rows={10}
                rowsPerPageOptions={[5, 10, 25, 50]}
                size="small"
                showGridlines
                filters={filters}
                globalFilterFields={['title', 'platform', 'profileName']}
                emptyMessage="No infringements found"
                sortMode="multiple"
                removableSort
                scrollable
                scrollHeight="500px"
              >
                <Column selectionMode="multiple" headerStyle={{ width: '3rem' }} />
                <Column 
                  header="Content" 
                  body={thumbnailTemplate}
                  style={{ minWidth: '280px' }}
                />
                <Column 
                  field="status" 
                  header="Status" 
                  body={statusTemplate}
                  sortable
                  style={{ width: '140px' }}
                />
                <Column 
                  field="confidence" 
                  header="Confidence" 
                  body={confidenceTemplate}
                  sortable
                  style={{ width: '120px' }}
                />
                <Column 
                  field="platform" 
                  header="Platform" 
                  body={platformTemplate}
                  sortable
                  style={{ width: '120px' }}
                />
                <Column 
                  field="profileName" 
                  header="Profile" 
                  body={profileTemplate}
                  sortable
                  style={{ width: '150px' }}
                />
                <Column 
                  field="detectedAt" 
                  header="Detected" 
                  body={dateTemplate}
                  sortable
                  style={{ width: '150px' }}
                />
                <Column 
                  body={actionsTemplate} 
                  header="Actions"
                  style={{ width: '180px' }}
                />
              </DataTable>
            </Card>
          </TabPanel>

          <TabPanel header="Analytics" leftIcon="pi pi-chart-bar">
            <div className="grid">
              <div className="col-12 md:col-8">
                <Card title="Detection Trends">
                  <div style={{ height: '300px' }}>
                    {/* Chart would go here */}
                    <div className="flex align-items-center justify-content-center h-full text-600">
                      Detection trends chart would be displayed here
                    </div>
                  </div>
                </Card>
              </div>
              <div className="col-12 md:col-4">
                <Card title="Status Distribution">
                  <div style={{ height: '300px' }}>
                    <Chart 
                      type="doughnut" 
                      data={statusChartData} 
                      options={{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                          legend: {
                            position: 'bottom'
                          }
                        }
                      }}
                    />
                  </div>
                </Card>
              </div>
              
              <div className="col-12">
                <Card title="Platform Performance">
                  <DataTable 
                    value={platformOptions.map(platform => {
                      const platformInfringements = infringements.filter(i => i.platform === platform);
                      const removed = platformInfringements.filter(i => i.status === 'removed').length;
                      const total = platformInfringements.length;
                      return {
                        platform,
                        total,
                        removed,
                        successRate: total > 0 ? Math.round((removed / total) * 100) : 0,
                        avgConfidence: total > 0 ? Math.round(
                          platformInfringements.reduce((sum, i) => sum + i.confidence, 0) / total
                        ) : 0
                      };
                    })}
                    size="small"
                    showGridlines
                  >
                    <Column field="platform" header="Platform" />
                    <Column 
                      field="total" 
                      header="Total Detections"
                      body={(rowData) => <Badge value={rowData.total} />}
                    />
                    <Column 
                      field="removed" 
                      header="Successfully Removed"
                      body={(rowData) => <Badge value={rowData.removed} severity="success" />}
                    />
                    <Column 
                      field="successRate" 
                      header="Success Rate"
                      body={(rowData) => (
                        <div className="flex align-items-center gap-2">
                          <ProgressBar 
                            value={rowData.successRate} 
                            showValue={false} 
                            style={{ width: '60px', height: '6px' }}
                          />
                          <span className="text-sm">{rowData.successRate}%</span>
                        </div>
                      )}
                    />
                    <Column 
                      field="avgConfidence" 
                      header="Avg Confidence"
                      body={(rowData) => (
                        <span className={getConfidenceColor(rowData.avgConfidence)}>
                          {rowData.avgConfidence}%
                        </span>
                      )}
                    />
                  </DataTable>
                </Card>
              </div>
            </div>
          </TabPanel>
        </TabView>

        {/* Details Overlay Panel */}
        <OverlayPanel ref={detailsOverlay} showCloseIcon style={{ width: '600px' }}>
          {selectedInfringement && (
            <div className="grid">
              <div className="col-12">
                <h4 className="mt-0 mb-3">{selectedInfringement.title}</h4>
              </div>
              
              <div className="col-12 md:col-6">
                <Image 
                  src={selectedInfringement.thumbnail} 
                  alt="Infringement content"
                  width="100%"
                  preview
                />
              </div>
              
              <div className="col-12 md:col-6">
                <div className="grid">
                  <div className="col-12">
                    <label className="block text-600 text-sm mb-1">Status</label>
                    <Tag 
                      value={selectedInfringement.status.replace('_', ' ')} 
                      severity={getStatusSeverity(selectedInfringement.status)}
                    />
                  </div>
                  
                  <div className="col-6">
                    <label className="block text-600 text-sm mb-1">Confidence</label>
                    <div className={`font-bold ${getConfidenceColor(selectedInfringement.confidence)}`}>
                      {selectedInfringement.confidence}%
                    </div>
                  </div>
                  
                  <div className="col-6">
                    <label className="block text-600 text-sm mb-1">Similarity</label>
                    <div className="text-900 font-bold">
                      {selectedInfringement.similarity}%
                    </div>
                  </div>
                  
                  <div className="col-12">
                    <label className="block text-600 text-sm mb-1">Platform</label>
                    <Badge value={selectedInfringement.platform} />
                  </div>
                  
                  <div className="col-12">
                    <label className="block text-600 text-sm mb-1">Detected</label>
                    <div className="text-900">{formatDate(selectedInfringement.detectedAt)}</div>
                  </div>
                  
                  <div className="col-12">
                    <label className="block text-600 text-sm mb-1">Profile</label>
                    <div className="text-900">{selectedInfringement.profileName}</div>
                  </div>
                </div>
              </div>
              
              <div className="col-12">
                <label className="block text-600 text-sm mb-1">Description</label>
                <p className="text-900 line-height-3">{selectedInfringement.description}</p>
              </div>
              
              <div className="col-12">
                <label className="block text-600 text-sm mb-1">Metadata</label>
                <div className="flex flex-wrap gap-2">
                  {selectedInfringement.metadata.uploader && (
                    <Chip label={`Uploader: ${selectedInfringement.metadata.uploader}`} />
                  )}
                  {selectedInfringement.metadata.viewCount && (
                    <Chip label={`Views: ${selectedInfringement.metadata.viewCount.toLocaleString()}`} />
                  )}
                  {selectedInfringement.metadata.likeCount && (
                    <Chip label={`Likes: ${selectedInfringement.metadata.likeCount}`} />
                  )}
                  <Chip label={`Type: ${selectedInfringement.metadata.contentType}`} />
                </div>
              </div>
              
              <div className="col-12">
                <label className="block text-600 text-sm mb-1">Tags</label>
                <div className="flex flex-wrap gap-1">
                  {selectedInfringement.tags.map((tag, index) => (
                    <Chip key={index} label={tag} className="text-xs" />
                  ))}
                </div>
              </div>
              
              <div className="col-12 mt-3">
                <div className="flex gap-2">
                  <Button 
                    label="Open URL" 
                    icon="pi pi-external-link" 
                    size="small"
                    outlined
                    onClick={() => window.open(selectedInfringement.url, '_blank')}
                  />
                  {['pending', 'under_review'].includes(selectedInfringement.status) && (
                    <Button 
                      label="Send Takedown" 
                      icon="pi pi-send" 
                      size="small"
                      severity="success"
                      onClick={() => {
                        sendTakedown(selectedInfringement);
                        detailsOverlay.current?.hide();
                      }}
                    />
                  )}
                </div>
              </div>
            </div>
          )}
        </OverlayPanel>

        <Toast ref={toast} />
        <ConfirmDialog />
      </div>
    </div>
  );
};

export default Infringements;