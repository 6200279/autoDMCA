import React, { useState, useEffect, useRef } from 'react';
import { Card } from 'primereact/card';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Button } from 'primereact/button';
import { Dialog } from 'primereact/dialog';
import { InputText } from 'primereact/inputtext';
import { InputTextarea } from 'primereact/inputtextarea';
import { Tag } from 'primereact/tag';
import { Timeline } from 'primereact/timeline';
import { Toolbar } from 'primereact/toolbar';
import { Toast } from 'primereact/toast';
import { Skeleton } from 'primereact/skeleton';
import { Badge } from 'primereact/badge';
// import { Chip } from 'primereact/chip';
// import { Panel } from 'primereact/panel';
import { TabView, TabPanel } from 'primereact/tabview';
import { ProgressBar } from 'primereact/progressbar';
import { Calendar } from 'primereact/calendar';
import { Dropdown } from 'primereact/dropdown';
import { Chart } from 'primereact/chart';
import { Divider } from 'primereact/divider';
// import { Image } from 'primereact/image';
import { OverlayPanel } from 'primereact/overlaypanel';
import { Steps } from 'primereact/steps';
import { FilterMatchMode } from 'primereact/api';
import { useAuth } from '../contexts/AuthContext';
import { takedownApi } from '../services/api';
import { useNotificationsRealtime } from '../contexts/WebSocketContext';

// TypeScript interfaces
interface TakedownRequest {
  id: string;
  requestId: string;
  title: string;
  platform: string;
  targetUrl: string;
  status: 'draft' | 'submitted' | 'under_review' | 'accepted' | 'rejected' | 'completed' | 'counter_noticed' | 'escalated';
  priority: 'low' | 'medium' | 'high' | 'urgent';
  infringementId: string;
  profileId: string;
  profileName: string;
  submittedAt: Date;
  lastUpdated: Date;
  responseTime?: number; // hours
  platformResponse?: string;
  counterNoticeReceived?: boolean;
  escalationLevel?: number;
  documents: Document[];
  communications: Communication[];
  legalBasis: string;
  copyrightOwner: string;
  contactEmail: string;
  swornStatement: boolean;
}

interface Document {
  id: string;
  name: string;
  type: 'dmca_notice' | 'copyright_proof' | 'identity_verification' | 'counter_notice' | 'court_order';
  url: string;
  uploadedAt: Date;
}

interface Communication {
  id: string;
  type: 'submission' | 'platform_response' | 'counter_notice' | 'escalation' | 'resolution';
  message: string;
  sender: string;
  timestamp: Date;
  attachments?: string[];
}

interface TakedownStats {
  total: number;
  submitted: number;
  underReview: number;
  accepted: number;
  rejected: number;
  completed: number;
  counterNoticed: number;
  successRate: number;
  avgResponseTime: number;
}

const TakedownRequests: React.FC = () => {
  const { user } = useAuth();
  const toast = useRef<Toast>(null);
  const timelineOverlay = useRef<OverlayPanel>(null);
  
  // WebSocket real-time updates
  const { notifications } = useNotificationsRealtime();

  // State management
  const [takedownRequests, setTakedownRequests] = useState<TakedownRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedRequests, setSelectedRequests] = useState<TakedownRequest[]>([]);
  const [requestDialog, setRequestDialog] = useState(false);
  const [selectedRequest, setSelectedRequest] = useState<TakedownRequest | null>(null);
  const [globalFilterValue, setGlobalFilterValue] = useState('');
  const [dateRange, setDateRange] = useState<Date[] | null>(null);
  const [stats, setStats] = useState<TakedownStats>({
    total: 0,
    submitted: 0,
    underReview: 0,
    accepted: 0,
    rejected: 0,
    completed: 0,
    counterNoticed: 0,
    successRate: 0,
    avgResponseTime: 0
  });

  // Form state for new takedown request
  const [newRequest, setNewRequest] = useState({
    title: '',
    platform: '',
    targetUrl: '',
    priority: 'medium' as TakedownRequest['priority'],
    legalBasis: '',
    copyrightOwner: '',
    contactEmail: user?.email || '',
    description: ''
  });

  // Filter options
  const platformOptions = [
    'Instagram', 'TikTok', 'OnlyFans', 'Twitter', 'YouTube', 'Reddit', 'Telegram', 'Facebook'
  ];

  // const statusOptions = [
  //   { label: 'Draft', value: 'draft' },
  //   { label: 'Submitted', value: 'submitted' },
  //   { label: 'Under Review', value: 'under_review' },
  //   { label: 'Accepted', value: 'accepted' },
  //   { label: 'Rejected', value: 'rejected' },
  //   { label: 'Completed', value: 'completed' },
  //   { label: 'Counter Notice', value: 'counter_noticed' },
  //   { label: 'Escalated', value: 'escalated' }
  // ];

  const priorityOptions = [
    { label: 'Low', value: 'low' },
    { label: 'Medium', value: 'medium' },
    { label: 'High', value: 'high' },
    { label: 'Urgent', value: 'urgent' }
  ];

  // DataTable filters
  const [filters, setFilters] = useState({
    global: { value: null, matchMode: FilterMatchMode.CONTAINS },
    requestId: { value: null, matchMode: FilterMatchMode.CONTAINS },
    platform: { value: null, matchMode: FilterMatchMode.EQUALS },
    status: { value: null, matchMode: FilterMatchMode.EQUALS },
    priority: { value: null, matchMode: FilterMatchMode.EQUALS }
  });

  // Mock data
  const mockTakedownRequests: TakedownRequest[] = [
    {
      id: '1',
      requestId: 'DMCA-2024-001',
      title: 'Unauthorized Instagram Content',
      platform: 'Instagram',
      targetUrl: 'https://instagram.com/p/example1',
      status: 'accepted',
      priority: 'high',
      infringementId: '1',
      profileId: '1',
      profileName: 'Sarah Johnson',
      submittedAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000),
      lastUpdated: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000),
      responseTime: 48,
      platformResponse: 'Content has been removed as requested.',
      legalBasis: 'Copyright infringement under DMCA',
      copyrightOwner: 'Sarah Johnson',
      contactEmail: 'sarah@example.com',
      swornStatement: true,
      documents: [
        {
          id: '1',
          name: 'DMCA_Notice_001.pdf',
          type: 'dmca_notice',
          url: '/documents/dmca-001.pdf',
          uploadedAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000)
        }
      ],
      communications: [
        {
          id: '1',
          type: 'submission',
          message: 'DMCA takedown request submitted for copyright infringement.',
          sender: 'AutoDMCA System',
          timestamp: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000)
        },
        {
          id: '2',
          type: 'platform_response',
          message: 'Request received and is under review. Expected response within 48 hours.',
          sender: 'Instagram Legal Team',
          timestamp: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000)
        },
        {
          id: '3',
          type: 'resolution',
          message: 'Content has been removed successfully.',
          sender: 'Instagram Legal Team',
          timestamp: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000)
        }
      ]
    },
    {
      id: '2',
      requestId: 'DMCA-2024-002',
      title: 'TikTok Video Theft',
      platform: 'TikTok',
      targetUrl: 'https://tiktok.com/@user/video/example2',
      status: 'under_review',
      priority: 'medium',
      infringementId: '2',
      profileId: '2',
      profileName: 'Emma Davis',
      submittedAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000),
      lastUpdated: new Date(Date.now() - 12 * 60 * 60 * 1000),
      legalBasis: 'Copyright infringement under DMCA',
      copyrightOwner: 'Emma Davis',
      contactEmail: 'emma@example.com',
      swornStatement: true,
      documents: [
        {
          id: '2',
          name: 'DMCA_Notice_002.pdf',
          type: 'dmca_notice',
          url: '/documents/dmca-002.pdf',
          uploadedAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000)
        }
      ],
      communications: [
        {
          id: '1',
          type: 'submission',
          message: 'DMCA takedown request submitted for video content theft.',
          sender: 'AutoDMCA System',
          timestamp: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000)
        },
        {
          id: '2',
          type: 'platform_response',
          message: 'Request is currently under review by our content team.',
          sender: 'TikTok Legal',
          timestamp: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000)
        }
      ]
    },
    {
      id: '3',
      requestId: 'DMCA-2024-003',
      title: 'OnlyFans Profile Impersonation',
      platform: 'OnlyFans',
      targetUrl: 'https://onlyfans.com/fake_profile',
      status: 'counter_noticed',
      priority: 'urgent',
      infringementId: '3',
      profileId: '3',
      profileName: 'Mia Rodriguez',
      submittedAt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
      lastUpdated: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000),
      responseTime: 72,
      counterNoticeReceived: true,
      legalBasis: 'Identity theft and copyright infringement',
      copyrightOwner: 'Mia Rodriguez',
      contactEmail: 'mia@example.com',
      swornStatement: true,
      documents: [
        {
          id: '3',
          name: 'DMCA_Notice_003.pdf',
          type: 'dmca_notice',
          url: '/documents/dmca-003.pdf',
          uploadedAt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
        },
        {
          id: '4',
          name: 'Counter_Notice_003.pdf',
          type: 'counter_notice',
          url: '/documents/counter-003.pdf',
          uploadedAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000)
        }
      ],
      communications: [
        {
          id: '1',
          type: 'submission',
          message: 'DMCA takedown request submitted for profile impersonation.',
          sender: 'AutoDMCA System',
          timestamp: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
        },
        {
          id: '2',
          type: 'platform_response',
          message: 'Content has been temporarily disabled pending review.',
          sender: 'OnlyFans Support',
          timestamp: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000)
        },
        {
          id: '3',
          type: 'counter_notice',
          message: 'Counter-notice received from the uploader claiming fair use.',
          sender: 'OnlyFans Legal',
          timestamp: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000)
        }
      ]
    },
    {
      id: '4',
      requestId: 'DMCA-2024-004',
      title: 'YouTube Content Theft',
      platform: 'YouTube',
      targetUrl: 'https://youtube.com/watch?v=example4',
      status: 'completed',
      priority: 'medium',
      infringementId: '4',
      profileId: '1',
      profileName: 'Sarah Johnson',
      submittedAt: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000),
      lastUpdated: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000),
      responseTime: 120,
      platformResponse: 'Video has been removed and account strike issued.',
      legalBasis: 'Copyright infringement under DMCA',
      copyrightOwner: 'Sarah Johnson',
      contactEmail: 'sarah@example.com',
      swornStatement: true,
      documents: [
        {
          id: '5',
          name: 'DMCA_Notice_004.pdf',
          type: 'dmca_notice',
          url: '/documents/dmca-004.pdf',
          uploadedAt: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000)
        }
      ],
      communications: [
        {
          id: '1',
          type: 'submission',
          message: 'DMCA takedown request submitted for video content.',
          sender: 'AutoDMCA System',
          timestamp: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000)
        },
        {
          id: '2',
          type: 'platform_response',
          message: 'We have received your copyright takedown request.',
          sender: 'YouTube Copyright Team',
          timestamp: new Date(Date.now() - 8 * 24 * 60 * 60 * 1000)
        },
        {
          id: '3',
          type: 'resolution',
          message: 'Video has been removed and uploader received a copyright strike.',
          sender: 'YouTube Copyright Team',
          timestamp: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000)
        }
      ]
    },
    {
      id: '5',
      requestId: 'DMCA-2024-005',
      title: 'Twitter Image Theft',
      platform: 'Twitter',
      targetUrl: 'https://twitter.com/user/status/example5',
      status: 'rejected',
      priority: 'low',
      infringementId: '5',
      profileId: '4',
      profileName: 'Alex Chen',
      submittedAt: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000),
      lastUpdated: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
      responseTime: 168,
      platformResponse: 'After review, we determined this does not constitute copyright infringement.',
      legalBasis: 'Copyright infringement under DMCA',
      copyrightOwner: 'Alex Chen',
      contactEmail: 'alex@example.com',
      swornStatement: true,
      documents: [
        {
          id: '6',
          name: 'DMCA_Notice_005.pdf',
          type: 'dmca_notice',
          url: '/documents/dmca-005.pdf',
          uploadedAt: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000)
        }
      ],
      communications: [
        {
          id: '1',
          type: 'submission',
          message: 'DMCA takedown request submitted for image theft.',
          sender: 'AutoDMCA System',
          timestamp: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000)
        },
        {
          id: '2',
          type: 'platform_response',
          message: 'Your report has been reviewed by our team.',
          sender: 'Twitter Legal',
          timestamp: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
        }
      ]
    }
  ];

  // Initialize data
  useEffect(() => {
    const loadTakedownRequests = async () => {
      try {
        setLoading(true);
        
        // Load takedown requests from backend
        const response = await takedownApi.getTakedowns({
          page: 1,
          limit: 100,
          include_stats: true
        });
        
        if (response.data) {
          const requestsData = response.data.items || response.data;
          const statsData = response.data.stats;
          
          // Map backend data to frontend format
          const mappedRequests = requestsData.map((item: any) => ({
            requestId: item.id,
            title: item.title,
            platform: item.platform,
            targetUrl: item.target_url,
            status: item.status,
            priority: item.priority || 'medium',
            infringementId: item.infringement_id,
            profileId: item.profile_id,
            profileName: item.profile_name || 'Unknown Profile',
            submittedAt: new Date(item.submitted_at || item.created_at),
            lastUpdated: new Date(item.updated_at),
            responseTime: item.response_time_hours,
            legalBasis: item.legal_basis,
            copyrightOwner: item.copyright_owner,
            contactEmail: item.contact_email,
            swornStatement: item.sworn_statement,
            documents: item.documents || [],
            communications: item.communications || [],
            notes: item.notes
          }));
          
          setTakedownRequests(mappedRequests);
          
          // Use backend stats if available, otherwise calculate from data
          if (statsData) {
            setStats({
              total: statsData.total || mappedRequests.length,
              submitted: statsData.submitted || 0,
              underReview: statsData.under_review || 0,
              accepted: statsData.accepted || 0,
              rejected: statsData.rejected || 0,
              completed: statsData.completed || 0,
              counterNoticed: statsData.counter_noticed || 0,
              successRate: statsData.success_rate || 0,
              avgResponseTime: statsData.avg_response_time || 0
            });
          } else {
            // Calculate stats from data
            const total = mappedRequests.length;
            const submitted = mappedRequests.filter((r: any) => r.status === 'submitted').length;
            const underReview = mappedRequests.filter((r: any) => r.status === 'under_review').length;
            const accepted = mappedRequests.filter((r: any) => r.status === 'accepted').length;
            const rejected = mappedRequests.filter((r: any) => r.status === 'rejected').length;
            const completed = mappedRequests.filter((r: any) => r.status === 'completed').length;
            const counterNoticed = mappedRequests.filter((r: any) => r.status === 'counter_noticed').length;
            
            const successful = accepted + completed;
            const resolved = successful + rejected;
            const successRate = resolved > 0 ? Math.round((successful / resolved) * 100) : 0;
            
            const avgResponseTime = mappedRequests
              .filter((r: any) => r.responseTime)
              .reduce((sum: number, r: any) => sum + (r.responseTime || 0), 0) / 
              mappedRequests.filter((r: any) => r.responseTime).length;
            
            setStats({
              total,
              submitted,
              underReview,
              accepted,
              rejected,
              completed,
              counterNoticed,
              successRate,
              avgResponseTime: Math.round(avgResponseTime)
            });
          }
        }
      } catch (error) {
        console.error('Failed to load takedown requests:', error);
        // Fallback to mock data if API fails
        setTakedownRequests(mockTakedownRequests);
        
        const total = mockTakedownRequests.length;
        const submitted = mockTakedownRequests.filter(r => r.status === 'submitted').length;
        const underReview = mockTakedownRequests.filter(r => r.status === 'under_review').length;
        const accepted = mockTakedownRequests.filter(r => r.status === 'accepted').length;
        const rejected = mockTakedownRequests.filter(r => r.status === 'rejected').length;
        const completed = mockTakedownRequests.filter(r => r.status === 'completed').length;
        const counterNoticed = mockTakedownRequests.filter(r => r.status === 'counter_noticed').length;
        
        const successful = accepted + completed;
        const resolved = successful + rejected;
        const successRate = resolved > 0 ? Math.round((successful / resolved) * 100) : 0;
        
        const avgResponseTime = mockTakedownRequests
          .filter(r => r.responseTime)
          .reduce((sum, r) => sum + (r.responseTime || 0), 0) / 
          mockTakedownRequests.filter(r => r.responseTime).length;
        
        setStats({
          total,
          submitted,
          underReview,
          accepted,
          rejected,
          completed,
          counterNoticed,
          successRate,
          avgResponseTime: Math.round(avgResponseTime)
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

    loadTakedownRequests();
  }, []);
  
  // Handle real-time notifications for takedown updates
  useEffect(() => {
    notifications.forEach(notification => {
      if (notification.category === 'takedown') {
        // Update takedown request status if notification contains update
        if (notification.data?.requestId && notification.data?.status) {
          setTakedownRequests(prev => prev.map(request => 
            request.requestId === notification.data.requestId
              ? { 
                  ...request, 
                  status: notification.data.status,
                  lastUpdated: new Date(notification.timestamp),
                  communications: [
                    ...request.communications,
                    {
                      id: Date.now().toString(),
                      type: 'update' as Communication['type'],
                      message: notification.message,
                      sender: 'Platform Response',
                      timestamp: new Date(notification.timestamp)
                    }
                  ]
                }
              : request
          ));
        }
        
        // Show toast notification
        toast.current?.show({
          severity: notification.type === 'success' ? 'success' : 
                   notification.type === 'error' ? 'error' : 'info',
          summary: notification.title,
          detail: notification.message,
          life: 5000
        });
      }
    });
  }, [notifications]);

  // Helper functions
  const getStatusSeverity = (status: string) => {
    switch (status) {
      case 'draft': return 'secondary';
      case 'submitted': return 'info';
      case 'under_review': return 'warning';
      case 'accepted': return 'success';
      case 'rejected': return 'danger';
      case 'completed': return 'success';
      case 'counter_noticed': return 'warning';
      case 'escalated': return 'danger';
      default: return null;
    }
  };

  const getPrioritySeverity = (priority: string) => {
    switch (priority) {
      case 'low': return 'secondary';
      case 'medium': return 'info';
      case 'high': return 'warning';
      case 'urgent': return 'danger';
      default: return null;
    }
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
    const diffInDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
    
    if (diffInDays === 0) {
      const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));
      return `${diffInHours}h ago`;
    } else {
      return `${diffInDays}d ago`;
    }
  };

  // Dialog handlers
  const openNew = () => {
    setNewRequest({
      title: '',
      platform: '',
      targetUrl: '',
      priority: 'medium',
      legalBasis: 'Copyright infringement under DMCA',
      copyrightOwner: '',
      contactEmail: user?.email || '',
      description: ''
    });
    setRequestDialog(true);
  };

  const hideDialog = () => {
    setRequestDialog(false);
  };

  const saveRequest = () => {
    const request: TakedownRequest = {
      id: Date.now().toString(),
      requestId: `DMCA-${new Date().getFullYear()}-${String(takedownRequests.length + 1).padStart(3, '0')}`,
      title: newRequest.title,
      platform: newRequest.platform,
      targetUrl: newRequest.targetUrl,
      status: 'draft',
      priority: newRequest.priority,
      infringementId: '',
      profileId: '1',
      profileName: 'Current User',
      submittedAt: new Date(),
      lastUpdated: new Date(),
      legalBasis: newRequest.legalBasis,
      copyrightOwner: newRequest.copyrightOwner,
      contactEmail: newRequest.contactEmail,
      swornStatement: false,
      documents: [],
      communications: [
        {
          id: '1',
          type: 'submission',
          message: `Manual DMCA request created: ${newRequest.description}`,
          sender: 'User',
          timestamp: new Date()
        }
      ]
    };

    setTakedownRequests([...takedownRequests, request]);
    hideDialog();
    
    toast.current?.show({
      severity: 'success',
      summary: 'Success',
      detail: 'Takedown request created successfully',
      life: 3000
    });
  };

  const submitRequest = async (request: TakedownRequest) => {
    try {
      // Submit takedown request via API
      const response = await takedownApi.sendTakedown(request.requestId);
      
      const updatedRequest = {
        ...request,
        status: 'submitted' as TakedownRequest['status'],
        lastUpdated: new Date(),
        communications: [
          ...request.communications,
          {
            id: Date.now().toString(),
            type: 'submission' as Communication['type'],
            message: 'Request has been submitted to the platform.',
            sender: 'AutoDMCA System',
            timestamp: new Date()
          }
        ]
      };

      setTakedownRequests(takedownRequests.map(r => 
        r.requestId === request.requestId ? updatedRequest : r
      ));

      toast.current?.show({
        severity: 'success',
        summary: 'Request Submitted',
        detail: `${request.requestId} has been submitted`,
        life: 3000
      });
    } catch (error: any) {
      console.error('Submit request error:', error);
      const errorMessage = error.response?.data?.detail || 'Failed to submit takedown request';
      toast.current?.show({
        severity: 'error',
        summary: 'Submission Failed',
        detail: errorMessage,
        life: 5000
      });
    }
  };

  const showTimeline = (request: TakedownRequest, event: any) => {
    setSelectedRequest(request);
    timelineOverlay.current?.toggle(event);
  };

  const onGlobalFilterChange = (e: any) => {
    const value = e.target.value;
    let _filters = { ...filters };
    _filters['global'].value = value;
    setFilters(_filters);
    setGlobalFilterValue(value);
  };

  // Column templates
  const requestTemplate = (rowData: TakedownRequest) => (
    <div>
      <div className="font-medium text-900">{rowData.requestId}</div>
      <div className="text-600 text-sm">{rowData.title}</div>
    </div>
  );

  const statusTemplate = (rowData: TakedownRequest) => (
    <Tag 
      value={rowData.status.replace('_', ' ')} 
      severity={getStatusSeverity(rowData.status)}
      className="text-sm"
    />
  );

  const priorityTemplate = (rowData: TakedownRequest) => (
    <Tag 
      value={rowData.priority.toUpperCase()} 
      severity={getPrioritySeverity(rowData.priority)}
      className="text-xs"
    />
  );

  const platformTemplate = (rowData: TakedownRequest) => (
    <Badge value={rowData.platform} />
  );

  const responseTimeTemplate = (rowData: TakedownRequest) => (
    <div className="text-center">
      {rowData.responseTime ? (
        <>
          <div className="text-900">{rowData.responseTime}h</div>
          <div className="text-600 text-xs">response time</div>
        </>
      ) : (
        <div className="text-600">-</div>
      )}
    </div>
  );

  const dateTemplate = (rowData: TakedownRequest) => (
    <div className="text-center">
      <div className="text-900 text-sm">{formatTimeSince(rowData.submittedAt)}</div>
      <div className="text-600 text-xs">{formatDate(rowData.submittedAt)}</div>
    </div>
  );

  const actionsTemplate = (rowData: TakedownRequest) => (
    <div className="flex gap-1">
      <Button
        icon="pi pi-clock"
        size="small"
        text
        tooltip="View Timeline"
        onClick={(e) => showTimeline(rowData, e)}
      />
      <Button
        icon="pi pi-external-link"
        size="small"
        text
        tooltip="Open URL"
        onClick={() => window.open(rowData.targetUrl, '_blank')}
      />
      {rowData.status === 'draft' && (
        <Button
          icon="pi pi-send"
          size="small"
          text
          severity="success"
          tooltip="Submit Request"
          onClick={() => submitRequest(rowData)}
        />
      )}
      <Button
        icon="pi pi-download"
        size="small"
        text
        tooltip="Download Documents"
        onClick={() => {
          toast.current?.show({
            severity: 'info',
            summary: 'Download',
            detail: 'Documents download started',
            life: 2000
          });
        }}
      />
    </div>
  );

  // Steps for the timeline
  const getTimelineSteps = (request: TakedownRequest) => {
    const steps = [
      { label: 'Created', icon: 'pi pi-plus' },
      { label: 'Submitted', icon: 'pi pi-send' },
      { label: 'Under Review', icon: 'pi pi-clock' },
      { label: 'Resolved', icon: 'pi pi-check' }
    ];

    const currentStepIndex = 
      request.status === 'draft' ? 0 :
      request.status === 'submitted' ? 1 :
      ['under_review', 'counter_noticed'].includes(request.status) ? 2 : 3;

    return { steps, currentStepIndex };
  };

  // Toolbar content
  const startContent = (
    <div className="flex align-items-center gap-2">
      <Button 
        label="New Request" 
        icon="pi pi-plus" 
        onClick={openNew}
      />
      <Button
        label="Bulk Submit"
        icon="pi pi-send"
        severity="success"
        outlined
        disabled={!selectedRequests.length || selectedRequests.every(r => r.status !== 'draft')}
        onClick={() => {
          const draftRequests = selectedRequests.filter(r => r.status === 'draft');
          draftRequests.forEach(request => submitRequest(request));
          setSelectedRequests([]);
        }}
      />
      <Button
        label="Export"
        icon="pi pi-download"
        outlined
        onClick={() => {
          const csvContent = [
            ['Request ID', 'Title', 'Platform', 'Status', 'Priority', 'Submitted At', 'Response Time'],
            ...takedownRequests.map(r => [
              r.requestId,
              r.title,
              r.platform,
              r.status,
              r.priority,
              r.submittedAt.toISOString(),
              r.responseTime ? `${r.responseTime}h` : 'N/A'
            ])
          ].map(row => row.join(',')).join('\n');
          
          const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
          const link = document.createElement('a');
          const url = URL.createObjectURL(blob);
          link.setAttribute('href', url);
          link.setAttribute('download', `takedown_requests_${Date.now()}.csv`);
          link.style.visibility = 'hidden';
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
        }}
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
          placeholder="Search requests..."
          aria-label="Search takedown requests"
          size="small"
        />
      </span>
      <Button
        icon="pi pi-refresh"
        text
        tooltip="Refresh"
        onClick={() => {
          setLoading(true);
          setTimeout(() => {
            setTakedownRequests([...mockTakedownRequests]);
            setLoading(false);
          }, 500);
        }}
      />
    </div>
  );

  // Chart data
  const statusChartData = {
    labels: ['Submitted', 'Under Review', 'Accepted', 'Completed', 'Rejected', 'Counter Noticed'],
    datasets: [
      {
        data: [stats.submitted, stats.underReview, stats.accepted, stats.completed, stats.rejected, stats.counterNoticed],
        backgroundColor: ['#2196F3', '#FF9800', '#4CAF50', '#00E676', '#F44336', '#FF5722']
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
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="col-12 md:col-2">
                  <Skeleton height="4rem" />
                </div>
              ))}
            </div>
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="grid mb-3">
                <div className="col-3"><Skeleton height="1rem" /></div>
                <div className="col-2"><Skeleton height="1rem" /></div>
                <div className="col-2"><Skeleton height="1rem" /></div>
                <div className="col-2"><Skeleton height="1rem" /></div>
                <div className="col-2"><Skeleton height="1rem" /></div>
                <div className="col-1"><Skeleton height="1rem" /></div>
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
            <h2 className="m-0 text-900">Takedown Requests</h2>
            <p className="text-600 m-0 mt-1">Manage and track DMCA takedown requests</p>
          </div>
          <div className="flex align-items-center gap-2">
            <Calendar 
              value={dateRange} 
              onChange={(e) => setDateRange(e.value as Date[])} 
              selectionMode="range" 
              readOnlyInput 
              showIcon
              placeholder="Filter by date range"
              aria-label="Filter takedown requests by date range"
            />
          </div>
        </div>

        {/* Statistics Cards */}
        <div className="grid mb-4">
          <div className="col-12 md:col-2">
            <Card className="text-center h-full">
              <div className="text-600 text-sm mb-2">Total Requests</div>
              <div className="text-900 font-bold text-2xl">{stats.total}</div>
            </Card>
          </div>
          <div className="col-12 md:col-2">
            <Card className="text-center h-full">
              <div className="text-600 text-sm mb-2">Under Review</div>
              <div className="text-orange-600 font-bold text-2xl">{stats.underReview}</div>
            </Card>
          </div>
          <div className="col-12 md:col-2">
            <Card className="text-center h-full">
              <div className="text-600 text-sm mb-2">Accepted</div>
              <div className="text-green-600 font-bold text-2xl">{stats.accepted}</div>
            </Card>
          </div>
          <div className="col-12 md:col-2">
            <Card className="text-center h-full">
              <div className="text-600 text-sm mb-2">Completed</div>
              <div className="text-green-600 font-bold text-2xl">{stats.completed}</div>
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
          <TabPanel header="Requests List" leftIcon="pi pi-list">
            <Card>
              <Toolbar start={startContent} end={endContent} className="mb-4" />

              <DataTable
                value={takedownRequests}
                selection={selectedRequests}
                onSelectionChange={(e) => setSelectedRequests(e.value as TakedownRequest[])}
                selectionMode="multiple"
                paginator
                rows={10}
                rowsPerPageOptions={[5, 10, 25, 50]}
                size="small"
                showGridlines
                filters={filters}
                globalFilterFields={['requestId', 'title', 'platform']}
                emptyMessage="No takedown requests found"
                sortMode="multiple"
                removableSort
              >
                <Column selectionMode="multiple" headerStyle={{ width: '3rem' }} />
                <Column 
                  field="requestId" 
                  header="Request" 
                  body={requestTemplate}
                  sortable
                  style={{ minWidth: '200px' }}
                />
                <Column 
                  field="status" 
                  header="Status" 
                  body={statusTemplate}
                  sortable
                  style={{ width: '140px' }}
                />
                <Column 
                  field="priority" 
                  header="Priority" 
                  body={priorityTemplate}
                  sortable
                  style={{ width: '100px' }}
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
                  sortable
                  style={{ width: '150px' }}
                />
                <Column 
                  field="responseTime" 
                  header="Response Time" 
                  body={responseTimeTemplate}
                  sortable
                  style={{ width: '120px' }}
                />
                <Column 
                  field="submittedAt" 
                  header="Submitted" 
                  body={dateTemplate}
                  sortable
                  style={{ width: '140px' }}
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
                <Card title="Request Trends">
                  <div style={{ height: '300px' }}>
                    <div className="flex align-items-center justify-content-center h-full text-600">
                      Request trends chart would be displayed here
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
                      const platformRequests = takedownRequests.filter(r => r.platform === platform);
                      const successful = platformRequests.filter(r => ['accepted', 'completed'].includes(r.status)).length;
                      const total = platformRequests.length;
                      const avgResponseTime = platformRequests
                        .filter(r => r.responseTime)
                        .reduce((sum, r) => sum + (r.responseTime || 0), 0) / 
                        platformRequests.filter(r => r.responseTime).length || 0;
                      
                      return {
                        platform,
                        total,
                        successful,
                        successRate: total > 0 ? Math.round((successful / total) * 100) : 0,
                        avgResponseTime: Math.round(avgResponseTime)
                      };
                    })}
                    size="small"
                    showGridlines
                  >
                    <Column field="platform" header="Platform" />
                    <Column 
                      field="total" 
                      header="Total Requests"
                      body={(rowData) => <Badge value={rowData.total} />}
                    />
                    <Column 
                      field="successful" 
                      header="Successful"
                      body={(rowData) => <Badge value={rowData.successful} severity="success" />}
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
                      field="avgResponseTime" 
                      header="Avg Response Time"
                      body={(rowData) => (
                        <span className="text-sm">
                          {rowData.avgResponseTime > 0 ? `${rowData.avgResponseTime}h` : 'N/A'}
                        </span>
                      )}
                    />
                  </DataTable>
                </Card>
              </div>
            </div>
          </TabPanel>
        </TabView>

        {/* Request Dialog */}
        <Dialog
          visible={requestDialog}
          style={{ width: '600px' }}
          header="Create New Takedown Request"
          modal
          className="p-fluid"
          onHide={hideDialog}
        >
          <div className="grid">
            <div className="col-12">
              <label htmlFor="title" className="block text-900 font-medium mb-2">
                Request Title *
              </label>
              <InputText
                id="title"
                value={newRequest.title}
                onChange={(e) => setNewRequest({ ...newRequest, title: e.target.value })}
                placeholder="Brief description of the infringement"
                required
              />
            </div>

            <div className="col-12 md:col-6">
              <label htmlFor="platform" className="block text-900 font-medium mb-2">
                Platform *
              </label>
              <Dropdown
                id="platform"
                value={newRequest.platform}
                options={platformOptions.map(p => ({ label: p, value: p }))}
                onChange={(e) => setNewRequest({ ...newRequest, platform: e.value })}
                placeholder="Select platform"
                required
              />
            </div>

            <div className="col-12 md:col-6">
              <label htmlFor="priority" className="block text-900 font-medium mb-2">
                Priority
              </label>
              <Dropdown
                id="priority"
                value={newRequest.priority}
                options={priorityOptions}
                onChange={(e) => setNewRequest({ ...newRequest, priority: e.value })}
              />
            </div>

            <div className="col-12">
              <label htmlFor="targetUrl" className="block text-900 font-medium mb-2">
                Infringing URL *
              </label>
              <InputText
                id="targetUrl"
                value={newRequest.targetUrl}
                onChange={(e) => setNewRequest({ ...newRequest, targetUrl: e.target.value })}
                placeholder="https://..."
                required
              />
            </div>

            <div className="col-12">
              <label htmlFor="copyrightOwner" className="block text-900 font-medium mb-2">
                Copyright Owner *
              </label>
              <InputText
                id="copyrightOwner"
                value={newRequest.copyrightOwner}
                onChange={(e) => setNewRequest({ ...newRequest, copyrightOwner: e.target.value })}
                placeholder="Name of the copyright owner"
                required
              />
            </div>

            <div className="col-12">
              <label htmlFor="contactEmail" className="block text-900 font-medium mb-2">
                Contact Email *
              </label>
              <InputText
                id="contactEmail"
                value={newRequest.contactEmail}
                onChange={(e) => setNewRequest({ ...newRequest, contactEmail: e.target.value })}
                type="email"
                required
              />
            </div>

            <div className="col-12">
              <label htmlFor="legalBasis" className="block text-900 font-medium mb-2">
                Legal Basis
              </label>
              <InputTextarea
                id="legalBasis"
                value={newRequest.legalBasis}
                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setNewRequest({ ...newRequest, legalBasis: e.target.value })}
                rows={3}
                placeholder="Legal basis for the takedown request"
              />
            </div>

            <div className="col-12">
              <label htmlFor="description" className="block text-900 font-medium mb-2">
                Description
              </label>
              <InputTextarea
                id="description"
                value={newRequest.description}
                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setNewRequest({ ...newRequest, description: e.target.value })}
                rows={4}
                placeholder="Detailed description of the infringement"
              />
            </div>
          </div>

          <div className="flex justify-content-end gap-2 mt-4">
            <Button 
              label="Cancel" 
              outlined 
              onClick={hideDialog} 
            />
            <Button 
              label="Create Request" 
              onClick={saveRequest}
              disabled={!newRequest.title || !newRequest.platform || !newRequest.targetUrl || !newRequest.copyrightOwner}
            />
          </div>
        </Dialog>

        {/* Timeline Overlay Panel */}
        <OverlayPanel ref={timelineOverlay} showCloseIcon style={{ width: '500px' }}>
          {selectedRequest && (
            <div>
              <h4 className="mt-0 mb-3">{selectedRequest.requestId} Timeline</h4>
              
              <div className="mb-4">
                <Steps 
                  model={getTimelineSteps(selectedRequest).steps}
                  activeIndex={getTimelineSteps(selectedRequest).currentStepIndex}
                  readOnly
                />
              </div>
              
              <Divider />
              
              <div className="mb-3">
                <label className="block text-600 text-sm mb-1">Communications</label>
                <Timeline 
                  value={selectedRequest.communications} 
                  align="left"
                  className="customized-timeline"
                  marker={(item) => (
                    <span className="flex w-2rem h-2rem align-items-center justify-content-center text-white border-circle z-1 shadow-1"
                          style={{ backgroundColor: 
                            item.type === 'submission' ? '#2196F3' :
                            item.type === 'platform_response' ? '#FF9800' :
                            item.type === 'counter_notice' ? '#F44336' :
                            item.type === 'resolution' ? '#4CAF50' : '#9E9E9E'
                          }}>
                      <i className={
                        item.type === 'submission' ? 'pi pi-send' :
                        item.type === 'platform_response' ? 'pi pi-reply' :
                        item.type === 'counter_notice' ? 'pi pi-exclamation-triangle' :
                        item.type === 'resolution' ? 'pi pi-check' : 'pi pi-info'
                      }></i>
                    </span>
                  )}
                  content={(item) => (
                    <Card className="mt-3">
                      <div className="flex justify-content-between align-items-start mb-2">
                        <div className="font-medium text-900">{item.sender}</div>
                        <div className="text-600 text-sm">{formatDate(item.timestamp)}</div>
                      </div>
                      <p className="text-700 line-height-3 m-0">{item.message}</p>
                    </Card>
                  )}
                />
              </div>
              
              {selectedRequest.documents.length > 0 && (
                <>
                  <Divider />
                  <div>
                    <label className="block text-600 text-sm mb-2">Documents</label>
                    {selectedRequest.documents.map((doc, index) => (
                      <div key={index} className="flex align-items-center gap-2 mb-2">
                        <i className="pi pi-file-pdf text-red-500" />
                        <span className="text-900">{doc.name}</span>
                        <Button 
                          icon="pi pi-download" 
                          size="small" 
                          text 
                          onClick={() => {
                            toast.current?.show({
                              severity: 'info',
                              summary: 'Download Started',
                              detail: `Downloading ${doc.name}`,
                              life: 2000
                            });
                          }}
                        />
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}
        </OverlayPanel>

        <Toast ref={toast} />
      </div>
    </div>
  );
};

export default TakedownRequests;