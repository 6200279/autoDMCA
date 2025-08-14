import React, { useState, useEffect, useRef } from 'react';
import { Card } from 'primereact/card';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Button } from 'primereact/button';
import { Dialog } from 'primereact/dialog';
import { InputText } from 'primereact/inputtext';
import { FileUpload } from 'primereact/fileupload';
import { Tag } from 'primereact/tag';
import { Image } from 'primereact/image';
import { Toolbar } from 'primereact/toolbar';
import { Toast } from 'primereact/toast';
import { ConfirmDialog, confirmDialog } from 'primereact/confirmdialog';
import { InputSwitch } from 'primereact/inputswitch';
import { Dropdown } from 'primereact/dropdown';
import { Skeleton } from 'primereact/skeleton';
import { Message } from 'primereact/message';
import { Badge } from 'primereact/badge';
import { ProgressBar } from 'primereact/progressbar';
import { Tooltip } from 'primereact/tooltip';
import { SelectButton } from 'primereact/selectbutton';
import { FilterMatchMode } from 'primereact/api';
import { DataView } from 'primereact/dataview';
import { TabView, TabPanel } from 'primereact/tabview';
import { Avatar } from 'primereact/avatar';
import { Chip } from 'primereact/chip';
import { MultiSelect } from 'primereact/multiselect';
import { InputTextarea } from 'primereact/inputtextarea';
import { Calendar } from 'primereact/calendar';
import { Splitter, SplitterPanel } from 'primereact/splitter';
import { Panel } from 'primereact/panel';
import { Steps } from 'primereact/steps';
import { ColorPicker } from 'primereact/colorpicker';
import { Divider } from 'primereact/divider';
import { Menu } from 'primereact/menu';
import { useAuth } from '../contexts/AuthContext';
import { profileApi } from '../services/api';

// TypeScript interfaces
interface Profile {
  id: string;
  name: string;
  stageName?: string;
  description: string;
  image: string;
  status: 'active' | 'inactive' | 'scanning' | 'error' | 'paused' | 'archived';
  platforms: PlatformAccount[];
  totalScans: number;
  infringementsFound: number;
  lastScan: Date;
  createdAt: Date;
  successRate: number;
  scanFrequency: 'daily' | 'weekly' | 'monthly';
  tags: string[];
  category: 'personal' | 'client' | 'test';
  priority: 'low' | 'medium' | 'high' | 'critical';
  contentTypes: string[];
  autoScanEnabled: boolean;
  notificationSettings: NotificationSettings;
  billingInfo?: ProfileBilling;
  teamAccess: string[];
  customColor?: string;
  notes?: string;
  agencyInfo?: AgencyInfo;
  analytics: ProfileAnalytics;
}

interface PlatformAccount {
  platform: string;
  username: string;
  isConnected: boolean;
  lastSync?: Date;
  accountType?: string;
  followersCount?: number;
  isVerified?: boolean;
}

interface NotificationSettings {
  email: boolean;
  sms: boolean;
  inApp: boolean;
  frequency: 'immediate' | 'hourly' | 'daily' | 'weekly';
  infringementAlert: boolean;
  scanComplete: boolean;
  weeklyReport: boolean;
}

interface ProfileBilling {
  monthlyScans: number;
  scanCost: number;
  lastBillingDate: Date;
  nextBillingDate: Date;
}

interface AgencyInfo {
  clientName: string;
  contractStart: Date;
  contractEnd?: Date;
  billingRate: number;
  permissions: string[];
  manager: string;
}

interface ProfileAnalytics {
  totalContentProtected: number;
  averageResponseTime: number;
  topInfringingPlatforms: string[];
  monthlyTrends: { month: string; scans: number; infringements: number }[];
  protectionScore: number;
}

interface ProfileFormData {
  name: string;
  stageName?: string;
  description: string;
  image?: File;
  platforms: PlatformAccount[];
  scanFrequency: 'daily' | 'weekly' | 'monthly';
  tags: string[];
  category: 'personal' | 'client' | 'test';
  priority: 'low' | 'medium' | 'high' | 'critical';
  contentTypes: string[];
  autoScanEnabled: boolean;
  notificationSettings: NotificationSettings;
  customColor?: string;
  notes?: string;
  agencyInfo?: AgencyInfo;
}

interface ViewMode {
  mode: 'table' | 'cards' | 'kanban';
  groupBy?: 'status' | 'category' | 'priority';
  sortBy: string;
  sortOrder: 'asc' | 'desc';
}

const Profiles: React.FC = () => {
  const { user } = useAuth();
  const toast = useRef<Toast>(null);
  const fileUploadRef = useRef<FileUpload>(null);
  const menu = useRef<Menu>(null);

  // State management
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [loading, setLoading] = useState(true);
  const [globalFilterValue, setGlobalFilterValue] = useState('');
  const [selectedProfiles, setSelectedProfiles] = useState<Profile[]>([]);
  const [profileDialog, setProfileDialog] = useState(false);
  const [deleteProfilesDialog, setDeleteProfilesDialog] = useState(false);
  const [profileWizardDialog, setProfileWizardDialog] = useState(false);
  const [bulkOperationsDialog, setBulkOperationsDialog] = useState(false);
  const [profileDetailsDialog, setProfileDetailsDialog] = useState(false);
  const [selectedProfile, setSelectedProfile] = useState<Profile | null>(null);
  const [currentProfileId, setCurrentProfileId] = useState<string | null>(null);
  const [activeWizardStep, setActiveWizardStep] = useState(0);
  
  const [profileForm, setProfileForm] = useState<ProfileFormData>({
    name: '',
    stageName: '',
    description: '',
    platforms: [],
    scanFrequency: 'weekly',
    tags: [],
    category: 'personal',
    priority: 'medium',
    contentTypes: [],
    autoScanEnabled: true,
    notificationSettings: {
      email: true,
      sms: false,
      inApp: true,
      frequency: 'immediate',
      infringementAlert: true,
      scanComplete: true,
      weeklyReport: true
    },
    customColor: '#3B82F6',
    notes: ''
  });
  const [editingProfile, setEditingProfile] = useState<Profile | null>(null);
  const [imagePreview, setImagePreview] = useState<string>('');

  // View management
  const [viewMode, setViewMode] = useState<ViewMode>({
    mode: 'table',
    sortBy: 'name',
    sortOrder: 'asc'
  });
  const [showQuickSwitcher, setShowQuickSwitcher] = useState(false);
  const [showProfileLimitWarning, setShowProfileLimitWarning] = useState(false);

  // Enhanced filter options
  const statusOptions = [
    { label: 'All Statuses', value: null },
    { label: 'Active', value: 'active' },
    { label: 'Inactive', value: 'inactive' },
    { label: 'Scanning', value: 'scanning' },
    { label: 'Paused', value: 'paused' },
    { label: 'Archived', value: 'archived' },
    { label: 'Error', value: 'error' }
  ];

  const categoryOptions = [
    { label: 'All Categories', value: null },
    { label: 'Personal', value: 'personal' },
    { label: 'Client', value: 'client' },
    { label: 'Test', value: 'test' }
  ];

  const priorityOptions = [
    { label: 'All Priorities', value: null },
    { label: 'Critical', value: 'critical' },
    { label: 'High', value: 'high' },
    { label: 'Medium', value: 'medium' },
    { label: 'Low', value: 'low' }
  ];

  const platformOptions = [
    { name: 'Instagram', code: 'instagram' },
    { name: 'TikTok', code: 'tiktok' },
    { name: 'OnlyFans', code: 'onlyfans' },
    { name: 'Twitter', code: 'twitter' },
    { name: 'YouTube', code: 'youtube' },
    { name: 'Reddit', code: 'reddit' },
    { name: 'Telegram', code: 'telegram' },
    { name: 'Snapchat', code: 'snapchat' },
    { name: 'Pinterest', code: 'pinterest' }
  ];

  const contentTypeOptions = [
    { name: 'Photos', code: 'photos' },
    { name: 'Videos', code: 'videos' },
    { name: 'Stories', code: 'stories' },
    { name: 'Live Streams', code: 'live' },
    { name: 'Text Posts', code: 'text' },
    { name: 'Audio', code: 'audio' }
  ];

  const scanFrequencyOptions = [
    { label: 'Daily', value: 'daily' },
    { label: 'Weekly', value: 'weekly' },
    { label: 'Monthly', value: 'monthly' }
  ];

  const viewModeOptions = [
    { label: 'Table', value: 'table', icon: 'pi pi-table' },
    { label: 'Cards', value: 'cards', icon: 'pi pi-th-large' },
    { label: 'Kanban', value: 'kanban', icon: 'pi pi-clone' }
  ];

  const wizardSteps = [
    { label: 'Basic Info' },
    { label: 'Platforms' },
    { label: 'Settings' },
    { label: 'Review' }
  ];

  // Enhanced filters
  const [filters, setFilters] = useState({
    global: { value: null, matchMode: FilterMatchMode.CONTAINS },
    name: { value: null, matchMode: FilterMatchMode.STARTS_WITH },
    status: { value: null, matchMode: FilterMatchMode.EQUALS },
    category: { value: null, matchMode: FilterMatchMode.EQUALS },
    priority: { value: null, matchMode: FilterMatchMode.EQUALS },
    platforms: { value: null, matchMode: FilterMatchMode.CONTAINS }
  });

  // Plan limits (from PRD)
  const planLimits = {
    starter: 1,
    professional: 5,
    enterprise: 25
  };

  const currentPlan = user?.plan || 'starter';
  const maxProfiles = planLimits[currentPlan as keyof typeof planLimits] || 1;

  // Enhanced mock data
  const mockProfiles: Profile[] = [
    {
      id: '1',
      name: 'Sarah Johnson',
      stageName: 'SarahJ_Official',
      description: 'Professional model and content creator',
      image: '/api/placeholder/150/150',
      status: 'active',
      platforms: [
        { platform: 'Instagram', username: '@sarahj_model', isConnected: true, followersCount: 125000, isVerified: true, accountType: 'creator' },
        { platform: 'TikTok', username: '@sarah.creates', isConnected: true, followersCount: 85000, isVerified: false, accountType: 'personal' },
        { platform: 'OnlyFans', username: 'sarahjofficial', isConnected: true, accountType: 'creator' }
      ],
      totalScans: 145,
      infringementsFound: 23,
      lastScan: new Date(Date.now() - 2 * 60 * 60 * 1000),
      createdAt: new Date('2024-01-15'),
      successRate: 89,
      scanFrequency: 'daily',
      tags: ['model', 'verified', 'high-priority'],
      category: 'personal',
      priority: 'high',
      contentTypes: ['photos', 'videos', 'stories'],
      autoScanEnabled: true,
      notificationSettings: {
        email: true,
        sms: true,
        inApp: true,
        frequency: 'immediate',
        infringementAlert: true,
        scanComplete: true,
        weeklyReport: true
      },
      teamAccess: [],
      customColor: '#E11D48',
      notes: 'High-value profile with premium content protection',
      analytics: {
        totalContentProtected: 1250,
        averageResponseTime: 2.3,
        topInfringingPlatforms: ['Reddit', 'Telegram', 'Twitter'],
        monthlyTrends: [
          { month: 'Jan', scans: 45, infringements: 8 },
          { month: 'Feb', scans: 52, infringements: 6 },
          { month: 'Mar', scans: 48, infringements: 9 }
        ],
        protectionScore: 89
      }
    },
    {
      id: '2',
      name: 'Emma Davis',
      stageName: 'FitEmma',
      description: 'Fitness influencer and coach',
      image: '/api/placeholder/150/150',
      status: 'scanning',
      platforms: [
        { platform: 'Instagram', username: '@fit.emma', isConnected: true, followersCount: 67000, isVerified: false, accountType: 'business' },
        { platform: 'YouTube', username: 'FitEmmaWorkouts', isConnected: true, followersCount: 45000, isVerified: true, accountType: 'creator' },
        { platform: 'TikTok', username: '@fitnessemma', isConnected: true, followersCount: 89000, isVerified: false, accountType: 'personal' }
      ],
      totalScans: 89,
      infringementsFound: 12,
      lastScan: new Date(Date.now() - 30 * 60 * 1000),
      createdAt: new Date('2024-02-10'),
      successRate: 75,
      scanFrequency: 'weekly',
      tags: ['fitness', 'influencer', 'coach'],
      category: 'personal',
      priority: 'medium',
      contentTypes: ['videos', 'photos', 'live'],
      autoScanEnabled: true,
      notificationSettings: {
        email: true,
        sms: false,
        inApp: true,
        frequency: 'daily',
        infringementAlert: true,
        scanComplete: true,
        weeklyReport: false
      },
      teamAccess: ['manager@fitagency.com'],
      customColor: '#10B981',
      analytics: {
        totalContentProtected: 890,
        averageResponseTime: 3.1,
        topInfringingPlatforms: ['YouTube', 'TikTok'],
        monthlyTrends: [
          { month: 'Jan', scans: 32, infringements: 4 },
          { month: 'Feb', scans: 29, infringements: 3 },
          { month: 'Mar', scans: 28, infringements: 5 }
        ],
        protectionScore: 75
      }
    },
    {
      id: '3',
      name: 'Mia Rodriguez',
      stageName: 'ArtByMia',
      description: 'Digital artist and NFT creator',
      image: '/api/placeholder/150/150',
      status: 'active',
      platforms: [
        { platform: 'Instagram', username: '@artbymia', isConnected: true, followersCount: 34000, isVerified: false, accountType: 'creator' },
        { platform: 'Twitter', username: '@mia_creates', isConnected: true, followersCount: 23000, isVerified: false, accountType: 'personal' },
        { platform: 'Reddit', username: 'u/ArtByMia', isConnected: true, accountType: 'personal' }
      ],
      totalScans: 67,
      infringementsFound: 18,
      lastScan: new Date(Date.now() - 6 * 60 * 60 * 1000),
      createdAt: new Date('2024-03-05'),
      successRate: 92,
      scanFrequency: 'weekly',
      tags: ['artist', 'verified', 'nft'],
      category: 'personal',
      priority: 'high',
      contentTypes: ['photos', 'text'],
      autoScanEnabled: true,
      notificationSettings: {
        email: true,
        sms: false,
        inApp: true,
        frequency: 'immediate',
        infringementAlert: true,
        scanComplete: false,
        weeklyReport: true
      },
      teamAccess: [],
      customColor: '#8B5CF6',
      notes: 'Digital art protection focus',
      analytics: {
        totalContentProtected: 567,
        averageResponseTime: 1.8,
        topInfringingPlatforms: ['Pinterest', 'DeviantArt', 'Instagram'],
        monthlyTrends: [
          { month: 'Jan', scans: 25, infringements: 7 },
          { month: 'Feb', scans: 22, infringements: 6 },
          { month: 'Mar', scans: 20, infringements: 5 }
        ],
        protectionScore: 92
      }
    },
    {
      id: '4',
      name: 'Alex Chen',
      description: 'Gaming streamer and content creator',
      image: '/api/placeholder/150/150',
      status: 'paused',
      platforms: [
        { platform: 'YouTube', username: 'AlexPlaysGames', isConnected: true, followersCount: 156000, isVerified: true, accountType: 'creator' },
        { platform: 'TikTok', username: '@alexgaming', isConnected: false, followersCount: 78000, accountType: 'personal' },
        { platform: 'Twitter', username: '@alex_streams', isConnected: true, followersCount: 45000, isVerified: false, accountType: 'personal' }
      ],
      totalScans: 34,
      infringementsFound: 5,
      lastScan: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
      createdAt: new Date('2024-04-12'),
      successRate: 68,
      scanFrequency: 'monthly',
      tags: ['gaming', 'streamer', 'youtube'],
      category: 'personal',
      priority: 'low',
      contentTypes: ['videos', 'live', 'audio'],
      autoScanEnabled: false,
      notificationSettings: {
        email: false,
        sms: false,
        inApp: true,
        frequency: 'weekly',
        infringementAlert: false,
        scanComplete: false,
        weeklyReport: false
      },
      teamAccess: [],
      customColor: '#F59E0B',
      notes: 'Currently on break - monitoring paused',
      analytics: {
        totalContentProtected: 234,
        averageResponseTime: 4.2,
        topInfringingPlatforms: ['YouTube', 'Twitch'],
        monthlyTrends: [
          { month: 'Jan', scans: 15, infringements: 2 },
          { month: 'Feb', scans: 12, infringements: 1 },
          { month: 'Mar', scans: 7, infringements: 2 }
        ],
        protectionScore: 68
      }
    },
    {
      id: '5',
      name: 'Jessica Martinez',
      description: 'Agency client - Fashion model',
      image: '/api/placeholder/150/150',
      status: 'active',
      platforms: [
        { platform: 'Instagram', username: '@jess_fashion', isConnected: true, followersCount: 89000, isVerified: true, accountType: 'creator' },
        { platform: 'Pinterest', username: 'JessicaStyle', isConnected: true, followersCount: 23000, accountType: 'business' }
      ],
      totalScans: 78,
      infringementsFound: 15,
      lastScan: new Date(Date.now() - 4 * 60 * 60 * 1000),
      createdAt: new Date('2024-05-20'),
      successRate: 82,
      scanFrequency: 'daily',
      tags: ['fashion', 'model', 'client'],
      category: 'client',
      priority: 'critical',
      contentTypes: ['photos', 'videos', 'stories'],
      autoScanEnabled: true,
      notificationSettings: {
        email: true,
        sms: true,
        inApp: true,
        frequency: 'immediate',
        infringementAlert: true,
        scanComplete: true,
        weeklyReport: true
      },
      teamAccess: ['manager@agency.com', 'support@agency.com'],
      customColor: '#EC4899',
      agencyInfo: {
        clientName: 'Elite Fashion Models',
        contractStart: new Date('2024-05-01'),
        contractEnd: new Date('2024-12-31'),
        billingRate: 150,
        permissions: ['view', 'scan', 'report'],
        manager: 'Sarah Wilson'
      },
      billingInfo: {
        monthlyScans: 30,
        scanCost: 45,
        lastBillingDate: new Date('2024-07-01'),
        nextBillingDate: new Date('2024-08-01')
      },
      analytics: {
        totalContentProtected: 567,
        averageResponseTime: 2.1,
        topInfringingPlatforms: ['Instagram', 'Pinterest', 'Facebook'],
        monthlyTrends: [
          { month: 'Jan', scans: 28, infringements: 5 },
          { month: 'Feb', scans: 25, infringements: 4 },
          { month: 'Mar', scans: 25, infringements: 6 }
        ],
        protectionScore: 82
      }
    }
  ];

  // Initialize data
  useEffect(() => {
    fetchProfiles();
  }, []);

  const fetchProfiles = async () => {
    try {
      setLoading(true);
      const response = await profileApi.getProfiles();
      setProfiles(response.data);
    } catch (error) {
      toast.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: 'Failed to load profiles',
        life: 3000
      });
      console.error('Error fetching profiles:', error);
      // Fallback to mock data if API fails
      setProfiles(mockProfiles);
    } finally {
      setLoading(false);
    }
  };

  // Enhanced helper functions
  const getStatusSeverity = (status: string) => {
    switch (status) {
      case 'active': return 'success';
      case 'scanning': return 'info';
      case 'inactive': return 'warning';
      case 'paused': return 'secondary';
      case 'archived': return null;
      case 'error': return 'danger';
      default: return null;
    }
  };

  const getCategorySeverity = (category: string) => {
    switch (category) {
      case 'personal': return 'success';
      case 'client': return 'info';
      case 'test': return 'warning';
      default: return null;
    }
  };

  const getPrioritySeverity = (priority: string) => {
    switch (priority) {
      case 'critical': return 'danger';
      case 'high': return 'warning';
      case 'medium': return 'info';
      case 'low': return 'secondary';
      default: return null;
    }
  };

  const formatDate = (date: Date) => {
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
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

  const formatNumber = (num: number) => {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
  };

  const getProfileCompletion = (profile: Profile) => {
    let completion = 0;
    const fields = [
      profile.name,
      profile.description,
      profile.image && profile.image !== '/api/placeholder/150/150',
      profile.platforms.length > 0,
      profile.contentTypes.length > 0,
      profile.tags.length > 0
    ];
    
    fields.forEach(field => {
      if (field) completion += 16.67;
    });
    
    return Math.round(completion);
  };

  const canCreateProfile = () => {
    return profiles.length < maxProfiles;
  };

  const switchToProfile = (profileId: string) => {
    setCurrentProfileId(profileId);
    const profile = profiles.find(p => p.id === profileId);
    if (profile) {
      toast.current?.show({
        severity: 'info',
        summary: 'Profile Switched',
        detail: `Switched to ${profile.name}`,
        life: 2000
      });
    }
  };

  // Enhanced dialog handlers
  const openNew = () => {
    if (!canCreateProfile()) {
      setShowProfileLimitWarning(true);
      return;
    }
    
    setProfileForm({
      name: '',
      stageName: '',
      description: '',
      platforms: [],
      scanFrequency: 'weekly',
      tags: [],
      category: 'personal',
      priority: 'medium',
      contentTypes: [],
      autoScanEnabled: true,
      notificationSettings: {
        email: true,
        sms: false,
        inApp: true,
        frequency: 'immediate',
        infringementAlert: true,
        scanComplete: true,
        weeklyReport: true
      },
      customColor: '#3B82F6',
      notes: ''
    });
    setEditingProfile(null);
    setImagePreview('');
    setProfileDialog(true);
  };

  const openWizard = () => {
    if (!canCreateProfile()) {
      setShowProfileLimitWarning(true);
      return;
    }
    
    setProfileForm({
      name: '',
      stageName: '',
      description: '',
      platforms: [],
      scanFrequency: 'weekly',
      tags: [],
      category: 'personal',
      priority: 'medium',
      contentTypes: [],
      autoScanEnabled: true,
      notificationSettings: {
        email: true,
        sms: false,
        inApp: true,
        frequency: 'immediate',
        infringementAlert: true,
        scanComplete: true,
        weeklyReport: true
      },
      customColor: '#3B82F6',
      notes: ''
    });
    setEditingProfile(null);
    setImagePreview('');
    setActiveWizardStep(0);
    setProfileWizardDialog(true);
  };

  const editProfile = (profile: Profile) => {
    setProfileForm({
      name: profile.name,
      stageName: profile.stageName || '',
      description: profile.description,
      platforms: profile.platforms,
      scanFrequency: profile.scanFrequency,
      tags: profile.tags,
      category: profile.category,
      priority: profile.priority,
      contentTypes: profile.contentTypes,
      autoScanEnabled: profile.autoScanEnabled,
      notificationSettings: profile.notificationSettings,
      customColor: profile.customColor || '#3B82F6',
      notes: profile.notes || '',
      agencyInfo: profile.agencyInfo
    });
    setEditingProfile(profile);
    setImagePreview(profile.image);
    setProfileDialog(true);
  };

  const viewProfile = (profile: Profile) => {
    setSelectedProfile(profile);
    setProfileDetailsDialog(true);
  };

  const hideDialog = () => {
    setProfileDialog(false);
    setProfileWizardDialog(false);
    setProfileDetailsDialog(false);
    setImagePreview('');
    setActiveWizardStep(0);
    if (fileUploadRef.current) {
      fileUploadRef.current.clear();
    }
  };

  const nextWizardStep = () => {
    if (activeWizardStep < wizardSteps.length - 1) {
      setActiveWizardStep(activeWizardStep + 1);
    }
  };

  const prevWizardStep = () => {
    if (activeWizardStep > 0) {
      setActiveWizardStep(activeWizardStep - 1);
    }
  };

  const saveProfile = async () => {
    try {
      setLoading(true);
      const profileData = {
        ...profileForm,
        image: imagePreview || '/api/placeholder/150/150',
      };

      let response;
      if (editingProfile) {
        response = await profileApi.updateProfile(parseInt(editingProfile.id), profileData);
        setProfiles(profiles.map(p => p.id === editingProfile.id ? response.data : p));
        toast.current?.show({
          severity: 'success',
          summary: 'Success',
          detail: 'Profile updated successfully',
          life: 3000
        });
      } else {
        response = await profileApi.createProfile(profileData);
        setProfiles([...profiles, response.data]);
        toast.current?.show({
          severity: 'success',
          summary: 'Success', 
          detail: 'Profile created successfully',
          life: 3000
        });
      }

      hideDialog();
    } catch (error) {
      toast.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: editingProfile ? 'Failed to update profile' : 'Failed to create profile',
        life: 3000
      });
      console.error('Error saving profile:', error);
    } finally {
      setLoading(false);
    }
  };

  const bulkUpdateProfiles = (updates: Partial<Profile>) => {
    const updatedProfiles = profiles.map(profile => 
      selectedProfiles.find(sp => sp.id === profile.id) 
        ? { ...profile, ...updates }
        : profile
    );
    
    setProfiles(updatedProfiles);
    setSelectedProfiles([]);
    setBulkOperationsDialog(false);
    
    toast.current?.show({
      severity: 'success',
      summary: 'Bulk Update Complete',
      detail: `Updated ${selectedProfiles.length} profiles`,
      life: 3000
    });
  };

  const archiveProfiles = (profileIds: string[]) => {
    const updatedProfiles = profiles.map(profile =>
      profileIds.includes(profile.id)
        ? { ...profile, status: 'archived' as Profile['status'] }
        : profile
    );
    
    setProfiles(updatedProfiles);
    toast.current?.show({
      severity: 'info',
      summary: 'Profiles Archived',
      detail: `Archived ${profileIds.length} profiles`,
      life: 3000
    });
  };

  const confirmDeleteSelected = () => {
    setDeleteProfilesDialog(true);
  };

  const deleteSelectedProfiles = async () => {
    try {
      setLoading(true);
      // Delete profiles one by one from backend
      for (const profile of selectedProfiles) {
        await profileApi.deleteProfile(parseInt(profile.id));
      }
      
      const remainingProfiles = profiles.filter(p => !selectedProfiles.includes(p));
      setProfiles(remainingProfiles);
      setSelectedProfiles([]);
      setDeleteProfilesDialog(false);
      
      toast.current?.show({
        severity: 'success',
        summary: 'Success',
        detail: 'Profiles deleted successfully',
        life: 3000
      });
    } catch (error) {
      toast.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: 'Failed to delete profiles',
        life: 3000
      });
      console.error('Error deleting profiles:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleProfileStatus = (profile: Profile) => {
    const newStatus = profile.status === 'active' ? 'inactive' : 'active';
    const updatedProfile = { ...profile, status: newStatus as Profile['status'] };
    setProfiles(profiles.map(p => p.id === profile.id ? updatedProfile : p));
    
    toast.current?.show({
      severity: 'info',
      summary: 'Status Updated',
      detail: `Profile ${newStatus === 'active' ? 'activated' : 'deactivated'}`,
      life: 3000
    });
  };

  const scanProfile = (profile: Profile) => {
    const updatedProfile = { ...profile, status: 'scanning' as Profile['status'] };
    setProfiles(profiles.map(p => p.id === profile.id ? updatedProfile : p));
    
    toast.current?.show({
      severity: 'info',
      summary: 'Scan Started',
      detail: `Started scanning ${profile.name}`,
      life: 3000
    });

    // Simulate scan completion after 5 seconds
    setTimeout(() => {
      const completedProfile = { 
        ...updatedProfile, 
        status: 'active' as Profile['status'],
        lastScan: new Date(),
        totalScans: updatedProfile.totalScans + 1
      };
      setProfiles(prev => prev.map(p => p.id === profile.id ? completedProfile : p));
      
      toast.current?.show({
        severity: 'success',
        summary: 'Scan Complete',
        detail: `Scan completed for ${profile.name}`,
        life: 3000
      });
    }, 5000);
  };

  const onImageUpload = async (event: any) => {
    const file = event.files[0];
    if (file) {
      // Show preview immediately
      const reader = new FileReader();
      reader.onload = (e) => {
        setImagePreview(e.target?.result as string);
      };
      reader.readAsDataURL(file);
      
      // If editing existing profile, upload immediately
      if (editingProfile) {
        try {
          const response = await profileApi.uploadProfileImage(parseInt(editingProfile.id), file);
          toast.current?.show({
            severity: 'success',
            summary: 'Success',
            detail: 'Profile image updated successfully',
            life: 3000
          });
        } catch (error) {
          toast.current?.show({
            severity: 'error',
            summary: 'Error',
            detail: 'Failed to upload image',
            life: 3000
          });
          console.error('Error uploading image:', error);
        }
      }
      
      setProfileForm({ ...profileForm, image: file });
    }
  };

  const onGlobalFilterChange = (e: any) => {
    const value = e.target.value;
    let _filters = { ...filters };
    _filters['global'].value = value;
    setFilters(_filters);
    setGlobalFilterValue(value);
  };

  // Enhanced column templates
  const profileTemplate = (rowData: Profile) => (
    <div className="flex align-items-center gap-3">
      <div className="relative">
        <Avatar 
          image={rowData.image} 
          size="large"
          shape="circle"
          className="border-2"
          style={{ borderColor: rowData.customColor || '#3B82F6' }}
        />
        {currentProfileId === rowData.id && (
          <div className="absolute -top-1 -right-1">
            <Badge value="CURRENT" severity="success" size="small" />
          </div>
        )}
      </div>
      <div className="flex-1">
        <div className="flex align-items-center gap-2 mb-1">
          <span className="font-medium text-900">{rowData.name}</span>
          {rowData.stageName && (
            <Chip label={rowData.stageName} className="text-xs" />
          )}
        </div>
        <div className="text-600 text-sm mb-1">{rowData.description}</div>
        <div className="flex align-items-center gap-2">
          <Tag value={rowData.category} severity={getCategorySeverity(rowData.category)} />
          <Tag value={rowData.priority} severity={getPrioritySeverity(rowData.priority)} />
          <div className="text-xs text-500">
            {getProfileCompletion(rowData)}% complete
          </div>
        </div>
      </div>
    </div>
  );

  const statusTemplate = (rowData: Profile) => (
    <div className="flex align-items-center gap-2">
      <Tag 
        value={rowData.status} 
        severity={getStatusSeverity(rowData.status)}
        icon={rowData.status === 'scanning' ? 'pi pi-spin pi-spinner' : undefined}
      />
      {rowData.status === 'scanning' && (
        <ProgressBar 
          mode="indeterminate" 
          style={{ height: '4px', width: '60px' }}
        />
      )}
      {rowData.autoScanEnabled && (
        <i className="pi pi-sync text-green-500" title="Auto-scan enabled" />
      )}
    </div>
  );

  const platformsTemplate = (rowData: Profile) => (
    <div className="flex flex-wrap gap-1">
      {rowData.platforms.slice(0, 2).map((platform, index) => (
        <div key={index} className="flex align-items-center gap-1">
          <Chip 
            label={platform.platform}
            className={`text-xs ${platform.isConnected ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}
          />
          {platform.isVerified && (
            <i className="pi pi-verified text-blue-500 text-xs" title="Verified account" />
          )}
        </div>
      ))}
      {rowData.platforms.length > 2 && (
        <Badge 
          value={`+${rowData.platforms.length - 2}`} 
          severity="secondary" 
          size="small" 
        />
      )}
    </div>
  );

  const statsTemplate = (rowData: Profile) => (
    <div className="text-center">
      <div className="text-900 font-bold">{rowData.infringementsFound}</div>
      <div className="text-600 text-xs">of {rowData.totalScans} scans</div>
      <div className="text-xs mt-1">
        <span className="text-blue-600">Score: {rowData.analytics.protectionScore}</span>
      </div>
    </div>
  );

  const successRateTemplate = (rowData: Profile) => (
    <div className="flex align-items-center gap-2">
      <ProgressBar 
        value={rowData.successRate} 
        showValue={false}
        style={{ width: '60px', height: '8px' }}
        color={rowData.successRate >= 80 ? '#10B981' : rowData.successRate >= 60 ? '#F59E0B' : '#EF4444'}
      />
      <span className="text-sm">{rowData.successRate}%</span>
    </div>
  );

  const lastScanTemplate = (rowData: Profile) => (
    <div className="text-center">
      <div className="text-900">{formatTimeSince(rowData.lastScan)}</div>
      <div className="text-600 text-xs">{formatDate(rowData.lastScan)}</div>
      <div className="text-xs text-500 mt-1">
        Next: {rowData.scanFrequency}
      </div>
    </div>
  );

  const analyticsTemplate = (rowData: Profile) => (
    <div className="text-center">
      <div className="text-900 font-medium">{formatNumber(rowData.analytics.totalContentProtected)}</div>
      <div className="text-600 text-xs">content items</div>
      <div className="text-xs text-500 mt-1">
        {rowData.analytics.averageResponseTime}h avg response
      </div>
    </div>
  );

  const actionsTemplate = (rowData: Profile) => {
    const items = [
      {
        label: 'View Details',
        icon: 'pi pi-eye',
        command: () => viewProfile(rowData)
      },
      {
        label: currentProfileId === rowData.id ? 'Current Profile' : 'Switch To',
        icon: 'pi pi-user',
        command: () => switchToProfile(rowData.id),
        disabled: currentProfileId === rowData.id
      },
      {
        label: rowData.status === 'active' ? 'Pause' : 'Resume',
        icon: rowData.status === 'active' ? 'pi pi-pause' : 'pi pi-play',
        command: () => toggleProfileStatus(rowData)
      },
      {
        label: 'Start Scan',
        icon: 'pi pi-search',
        command: () => scanProfile(rowData),
        disabled: rowData.status === 'scanning'
      },
      {
        separator: true
      },
      {
        label: 'Edit Profile',
        icon: 'pi pi-pencil',
        command: () => editProfile(rowData)
      },
      {
        label: 'Archive',
        icon: 'pi pi-archive',
        command: () => archiveProfiles([rowData.id])
      },
      {
        label: 'Delete',
        icon: 'pi pi-trash',
        className: 'text-red-500',
        command: () => {
          confirmDialog({
            message: `Are you sure you want to delete ${rowData.name}?`,
            header: 'Delete Confirmation',
            icon: 'pi pi-exclamation-triangle',
            accept: () => {
              setProfiles(profiles.filter(p => p.id !== rowData.id));
              toast.current?.show({
                severity: 'success',
                summary: 'Success',
                detail: 'Profile deleted successfully',
                life: 3000
              });
            }
          });
        }
      }
    ];

    return (
      <div className="flex gap-1">
        <Button
          icon={rowData.status === 'active' ? 'pi pi-pause' : 'pi pi-play'}
          size="small"
          text
          tooltip={rowData.status === 'active' ? 'Pause Monitoring' : 'Resume Monitoring'}
          onClick={() => toggleProfileStatus(rowData)}
          severity={rowData.status === 'active' ? 'warning' : 'success'}
        />
        <Button
          icon="pi pi-search"
          size="small"
          text
          tooltip="Start Scan"
          onClick={() => scanProfile(rowData)}
          disabled={rowData.status === 'scanning'}
        />
        <Button
          icon="pi pi-eye"
          size="small"
          text
          tooltip="View Details"
          onClick={() => viewProfile(rowData)}
        />
        <Button
          icon="pi pi-ellipsis-v"
          size="small"
          text
          tooltip="More Actions"
          onClick={(event) => {
            menu.current?.toggle(event);
            // Set items for this specific profile
            (menu.current as any)?.setItems(items);
          }}
        />
      </div>
    );
  };

  // Enhanced toolbar content
  const startContent = (
    <div className="flex align-items-center gap-2 flex-wrap">
      <Button 
        label="New Profile" 
        icon="pi pi-plus" 
        onClick={openNew}
        disabled={!canCreateProfile()}
      />
      <Button 
        label="Setup Wizard" 
        icon="pi pi-cog" 
        outlined
        onClick={openWizard}
        disabled={!canCreateProfile()}
      />
      <Divider layout="vertical" className="mx-2" />
      <Button
        label="Bulk Operations"
        icon="pi pi-cog"
        severity="secondary"
        onClick={() => setBulkOperationsDialog(true)}
        disabled={!selectedProfiles.length}
      />
      <Button
        label="Delete Selected"
        icon="pi pi-trash"
        severity="danger"
        onClick={confirmDeleteSelected}
        disabled={!selectedProfiles.length}
      />
      <Button
        label="Archive Selected"
        icon="pi pi-archive"
        outlined
        onClick={() => archiveProfiles(selectedProfiles.map(p => p.id))}
        disabled={!selectedProfiles.length}
      />
    </div>
  );

  const endContent = (
    <div className="flex align-items-center gap-2 flex-wrap">
      <Dropdown
        value={filters.category.value}
        options={categoryOptions}
        onChange={(e) => {
          const _filters = { ...filters };
          _filters.category.value = e.value;
          setFilters(_filters);
        }}
        placeholder="Filter by category"
        showClear
        className="w-10rem"
        size="small"
      />
      <Dropdown
        value={filters.status.value}
        options={statusOptions}
        onChange={(e) => {
          const _filters = { ...filters };
          _filters.status.value = e.value;
          setFilters(_filters);
        }}
        placeholder="Filter by status"
        showClear
        className="w-10rem"
        size="small"
      />
      <Divider layout="vertical" className="mx-2" />
      <SelectButton
        value={viewMode.mode}
        options={viewModeOptions}
        onChange={(e) => setViewMode({ ...viewMode, mode: e.value })}
        size="small"
      />
      <Divider layout="vertical" className="mx-2" />
      <span className="p-input-icon-left">
        <i className="pi pi-search" />
        <InputText
          value={globalFilterValue}
          onChange={onGlobalFilterChange}
          placeholder="Search profiles..."
          size="small"
          className="w-12rem"
        />
      </span>
      <Button
        icon="pi pi-refresh"
        text
        tooltip="Refresh"
        onClick={() => {
          fetchProfiles();
          toast.current?.show({
            severity: 'success',
            summary: 'Success',
            detail: 'Profiles refreshed',
            life: 2000
          });
        }}
      />
    </div>
  );

  if (loading) {
    return (
      <div className="grid">
        <div className="col-12">
          <Card>
            <Skeleton height="2rem" className="mb-4" />
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex align-items-center gap-3 mb-3">
                <Skeleton shape="circle" size="3rem" />
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
        {/* Enhanced Header with Quick Profile Switcher */}
        <div className="flex flex-column lg:flex-row lg:justify-content-between lg:align-items-center mb-4 gap-3">
          <div className="flex align-items-center gap-3">
            <div>
              <h2 className="m-0 text-900">Multi-Profile Management</h2>
              <p className="text-600 m-0 mt-1">Manage and monitor your protected profiles across multiple platforms</p>
            </div>
            {currentProfileId && (
              <div className="flex align-items-center gap-2 p-2 border-round bg-blue-50">
                <i className="pi pi-user text-blue-600" />
                <span className="text-blue-900 font-medium">
                  Current: {profiles.find(p => p.id === currentProfileId)?.name}
                </span>
              </div>
            )}
          </div>
          <div className="flex align-items-center gap-2 flex-wrap">
            <Button
              label="Quick Switch"
              icon="pi pi-users"
              outlined
              onClick={() => setShowQuickSwitcher(true)}
              className="mr-2"
            />
            <Badge value={`${profiles.length}/${maxProfiles} profiles`} size="large" />
            <Badge 
              value={`${profiles.filter(p => p.status === 'active').length} active`} 
              severity="success" 
              size="large" 
            />
            <Badge 
              value={`${profiles.filter(p => p.category === 'client').length} clients`} 
              severity="info" 
              size="large" 
            />
          </div>
        </div>

        {/* Plan Limit Warning */}
        {profiles.length >= maxProfiles * 0.8 && (
          <Message 
            severity="warn" 
            text={`You're using ${profiles.length} of ${maxProfiles} available profiles. Upgrade to add more profiles.`}
            className="mb-4"
          />
        )}

        {/* Enhanced Statistics Dashboard */}
        <div className="grid mb-4">
          <div className="col-12 lg:col-3">
            <Card className="text-center h-full">
              <div className="text-600 text-sm mb-2">Total Profiles</div>
              <div className="text-900 font-bold text-2xl mb-2">{profiles.length}</div>
              <ProgressBar 
                value={(profiles.length / maxProfiles) * 100} 
                showValue={false} 
                style={{ height: '6px' }}
                className="mb-2"
              />
              <div className="text-xs text-500">of {maxProfiles} allowed</div>
            </Card>
          </div>
          <div className="col-12 lg:col-3">
            <Card className="text-center h-full">
              <div className="text-600 text-sm mb-2">Active Monitoring</div>
              <div className="text-green-600 font-bold text-2xl mb-2">
                {profiles.filter(p => p.status === 'active').length}
              </div>
              <div className="flex justify-content-center gap-1">
                <Chip label={`${profiles.filter(p => p.autoScanEnabled).length} auto-scan`} className="text-xs" />
              </div>
            </Card>
          </div>
          <div className="col-12 lg:col-3">
            <Card className="text-center h-full">
              <div className="text-600 text-sm mb-2">Total Content Protected</div>
              <div className="text-blue-600 font-bold text-2xl mb-2">
                {formatNumber(profiles.reduce((sum, p) => sum + p.analytics.totalContentProtected, 0))}
              </div>
              <div className="text-xs text-500">
                {profiles.reduce((sum, p) => sum + p.totalScans, 0)} scans performed
              </div>
            </Card>
          </div>
          <div className="col-12 lg:col-3">
            <Card className="text-center h-full">
              <div className="text-600 text-sm mb-2">Infringements Found</div>
              <div className="text-orange-600 font-bold text-2xl mb-2">
                {profiles.reduce((sum, p) => sum + p.infringementsFound, 0)}
              </div>
              <div className="text-xs text-500">
                Avg response: {(profiles.reduce((sum, p) => sum + p.analytics.averageResponseTime, 0) / profiles.length || 0).toFixed(1)}h
              </div>
            </Card>
          </div>
        </div>

        {/* Category Overview */}
        <div className="grid mb-4">
          {['personal', 'client', 'test'].map(category => {
            const categoryProfiles = profiles.filter(p => p.category === category);
            return (
              <div key={category} className="col-12 md:col-4">
                <Card>
                  <div className="flex justify-content-between align-items-center mb-3">
                    <div>
                      <h6 className="m-0 text-900 capitalize">{category} Profiles</h6>
                      <div className="text-600 text-sm mt-1">{categoryProfiles.length} profiles</div>
                    </div>
                    <Tag value={category} severity={getCategorySeverity(category)} />
                  </div>
                  <div className="grid">
                    <div className="col-6 text-center">
                      <div className="text-900 font-bold">{categoryProfiles.filter(p => p.status === 'active').length}</div>
                      <div className="text-600 text-xs">Active</div>
                    </div>
                    <div className="col-6 text-center">
                      <div className="text-900 font-bold">
                        {categoryProfiles.reduce((sum, p) => sum + p.infringementsFound, 0)}
                      </div>
                      <div className="text-600 text-xs">Infringements</div>
                    </div>
                  </div>
                </Card>
              </div>
            );
          })}
        </div>

        <Card>
          <Toolbar start={startContent} end={endContent} className="mb-4" />

          {/* Dynamic View Modes */}
          {viewMode.mode === 'table' && (
            <DataTable
              value={profiles}
              selection={selectedProfiles}
              onSelectionChange={(e) => setSelectedProfiles(e.value)}
              paginator
              rows={10}
              rowsPerPageOptions={[5, 10, 25, 50]}
              size="small"
              showGridlines
              filters={filters}
              globalFilterFields={['name', 'description', 'platforms', 'category', 'priority']}
              emptyMessage="No profiles found"
              sortMode="multiple"
              removableSort
              responsiveLayout="stack"
              breakpoint="768px"
            >
              <Column selectionMode="multiple" headerStyle={{ width: '3rem' }} />
              <Column 
                field="name" 
                header="Profile" 
                body={profileTemplate}
                sortable
                style={{ minWidth: '300px' }}
              />
              <Column 
                field="status" 
                header="Status" 
                body={statusTemplate}
                sortable
                style={{ width: '150px' }}
              />
              <Column 
                field="platforms" 
                header="Platforms" 
                body={platformsTemplate}
                style={{ width: '200px' }}
              />
              <Column 
                header="Analytics" 
                body={analyticsTemplate}
                style={{ width: '140px' }}
              />
              <Column 
                header="Infringements" 
                body={statsTemplate}
                sortable
                sortField="infringementsFound"
                style={{ width: '120px' }}
              />
              <Column 
                field="successRate" 
                header="Success Rate" 
                body={successRateTemplate}
                sortable
                style={{ width: '140px' }}
              />
              <Column 
                field="lastScan" 
                header="Last Scan" 
                body={lastScanTemplate}
                sortable
                style={{ width: '120px' }}
              />
              <Column 
                body={actionsTemplate} 
                header="Actions"
                style={{ width: '180px' }}
              />
            </DataTable>
          )}

          {/* Card View Mode */}
          {viewMode.mode === 'cards' && (
            <DataView
              value={profiles}
              layout="grid"
              paginator
              rows={12}
              sortField={viewMode.sortBy}
              sortOrder={viewMode.sortOrder === 'asc' ? 1 : -1}
              itemTemplate={(profile: Profile, index: number) => (
                <div className="col-12 md:col-6 lg:col-4 xl:col-3 p-2" key={profile.id}>
                  <Card 
                    className={`h-full cursor-pointer hover:shadow-3 transition-all transition-duration-200 ${
                      selectedProfiles.includes(profile) ? 'border-primary' : ''
                    }`}
                    onClick={() => {
                      const isSelected = selectedProfiles.includes(profile);
                      if (isSelected) {
                        setSelectedProfiles(selectedProfiles.filter(p => p.id !== profile.id));
                      } else {
                        setSelectedProfiles([...selectedProfiles, profile]);
                      }
                    }}
                    style={{ borderLeft: `4px solid ${profile.customColor || '#3B82F6'}` }}
                  >
                    <div className="text-center mb-3">
                      <div className="relative inline-block">
                        <Avatar 
                          image={profile.image} 
                          size="large" 
                          shape="circle"
                          className="mb-2"
                        />
                        <Tag 
                          value={profile.status}
                          severity={getStatusSeverity(profile.status)}
                          className="absolute -top-1 -right-1"
                          style={{ fontSize: '0.7rem' }}
                        />
                      </div>
                      <div className="font-bold text-900 mb-1">{profile.name}</div>
                      {profile.stageName && (
                        <div className="text-600 text-sm mb-2">@{profile.stageName}</div>
                      )}
                      <div className="text-600 text-sm line-height-3 mb-3" style={{ minHeight: '3rem' }}>
                        {profile.description}
                      </div>
                    </div>

                    <div className="flex justify-content-between align-items-center mb-3">
                      <Tag value={profile.category} severity={getCategorySeverity(profile.category)} />
                      <Tag value={profile.priority} severity={getPrioritySeverity(profile.priority)} />
                    </div>

                    <div className="grid mb-3 text-center">
                      <div className="col-4">
                        <div className="text-900 font-bold">{profile.platforms.length}</div>
                        <div className="text-600 text-xs">Platforms</div>
                      </div>
                      <div className="col-4">
                        <div className="text-900 font-bold">{profile.infringementsFound}</div>
                        <div className="text-600 text-xs">Found</div>
                      </div>
                      <div className="col-4">
                        <div className="text-900 font-bold">{profile.analytics.protectionScore}</div>
                        <div className="text-600 text-xs">Score</div>
                      </div>
                    </div>

                    <div className="flex align-items-center justify-content-between mb-3">
                      <div className="text-600 text-sm">
                        Last scan: {formatTimeSince(profile.lastScan)}
                      </div>
                      {profile.autoScanEnabled && (
                        <i className="pi pi-sync text-green-500" title="Auto-scan enabled" />
                      )}
                    </div>

                    <ProgressBar 
                      value={getProfileCompletion(profile)} 
                      showValue={false} 
                      style={{ height: '4px' }}
                      className="mb-3"
                    />

                    <div className="flex justify-content-between gap-1">
                      <Button
                        icon="pi pi-eye"
                        size="small"
                        text
                        tooltip="View Details"
                        onClick={(e) => {
                          e.stopPropagation();
                          viewProfile(profile);
                        }}
                      />
                      <Button
                        icon={profile.status === 'active' ? 'pi pi-pause' : 'pi pi-play'}
                        size="small"
                        text
                        tooltip={profile.status === 'active' ? 'Pause' : 'Resume'}
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleProfileStatus(profile);
                        }}
                      />
                      <Button
                        icon="pi pi-search"
                        size="small"
                        text
                        tooltip="Start Scan"
                        onClick={(e) => {
                          e.stopPropagation();
                          scanProfile(profile);
                        }}
                        disabled={profile.status === 'scanning'}
                      />
                      <Button
                        icon="pi pi-pencil"
                        size="small"
                        text
                        tooltip="Edit"
                        onClick={(e) => {
                          e.stopPropagation();
                          editProfile(profile);
                        }}
                      />
                    </div>
                  </Card>
                </div>
              )}
              emptyMessage="No profiles found"
            />
          )}

          {/* Kanban View Mode */}
          {viewMode.mode === 'kanban' && (
            <div className="grid">
              {['active', 'inactive', 'scanning', 'paused', 'error'].map(status => {
                const statusProfiles = profiles.filter(p => p.status === status);
                return (
                  <div key={status} className="col-12 lg:col-2-4 xl:col">
                    <Panel header={
                      <div className="flex align-items-center gap-2">
                        <Tag value={status} severity={getStatusSeverity(status)} />
                        <Badge value={statusProfiles.length} severity="secondary" />
                      </div>
                    }>
                      <div className="flex flex-column gap-2">
                        {statusProfiles.map(profile => (
                          <Card key={profile.id} className="cursor-pointer hover:shadow-2">
                            <div className="flex align-items-center gap-2 mb-2">
                              <Avatar image={profile.image} size="normal" />
                              <div className="flex-1">
                                <div className="font-medium text-900">{profile.name}</div>
                                <div className="text-600 text-sm">{profile.category}</div>
                              </div>
                            </div>
                            <div className="text-600 text-sm mb-2" style={{ height: '2rem', overflow: 'hidden' }}>
                              {profile.description}
                            </div>
                            <div className="flex justify-content-between text-xs">
                              <span>{profile.platforms.length} platforms</span>
                              <span>{formatTimeSince(profile.lastScan)}</span>
                            </div>
                          </Card>
                        ))}
                        {statusProfiles.length === 0 && (
                          <div className="text-center text-500 py-4">
                            No {status} profiles
                          </div>
                        )}
                      </div>
                    </Panel>
                  </div>
                );
              })}
            </div>
          )}
        </Card>

        {/* Enhanced Profile Creation/Edit Dialog */}
        <Dialog
          visible={profileDialog}
          style={{ width: '800px', maxWidth: '95vw' }}
          header={editingProfile ? 'Edit Profile' : 'Create New Profile'}
          modal
          className="p-fluid"
          onHide={hideDialog}
          maximizable
        >
          <TabView>
            <TabPanel header="Basic Information">
              <div className="grid">
                <div className="col-12 md:col-4 text-center">
                  <label className="block text-900 font-medium mb-2">Profile Image</label>
                  <div className="mb-3">
                    {imagePreview ? (
                      <Avatar image={imagePreview} size="xlarge" shape="circle" className="mb-2" />
                    ) : (
                      <Avatar label={profileForm.name?.charAt(0)?.toUpperCase() || '?'} size="xlarge" shape="circle" className="mb-2" />
                    )}
                  </div>
                  <FileUpload
                    ref={fileUploadRef}
                    mode="basic"
                    name="image"
                    accept="image/*"
                    maxFileSize={5000000}
                    onUpload={onImageUpload}
                    chooseLabel="Upload Image"
                    className="w-full"
                  />
                </div>
                <div className="col-12 md:col-8">
                  <div className="grid">
                    <div className="col-12">
                      <label htmlFor="name" className="block text-900 font-medium mb-2">Profile Name *</label>
                      <InputText
                        id="name"
                        value={profileForm.name}
                        onChange={(e) => setProfileForm({ ...profileForm, name: e.target.value })}
                        placeholder="Enter full name or brand name"
                      />
                    </div>
                    <div className="col-12">
                      <label htmlFor="stageName" className="block text-900 font-medium mb-2">Stage Name / Username</label>
                      <InputText
                        id="stageName"
                        value={profileForm.stageName}
                        onChange={(e) => setProfileForm({ ...profileForm, stageName: e.target.value })}
                        placeholder="@username or stage name"
                      />
                    </div>
                    <div className="col-12">
                      <label htmlFor="description" className="block text-900 font-medium mb-2">Description</label>
                      <InputTextarea
                        id="description"
                        value={profileForm.description}
                        onChange={(e) => setProfileForm({ ...profileForm, description: e.target.value })}
                        placeholder="Brief description of the profile and content type"
                        rows={3}
                      />
                    </div>
                    <div className="col-6">
                      <label htmlFor="category" className="block text-900 font-medium mb-2">Category</label>
                      <Dropdown
                        value={profileForm.category}
                        options={categoryOptions.filter(opt => opt.value)}
                        onChange={(e) => setProfileForm({ ...profileForm, category: e.value })}
                        optionLabel="label"
                        optionValue="value"
                        placeholder="Select category"
                      />
                    </div>
                    <div className="col-6">
                      <label htmlFor="priority" className="block text-900 font-medium mb-2">Priority</label>
                      <Dropdown
                        value={profileForm.priority}
                        options={priorityOptions.filter(opt => opt.value)}
                        onChange={(e) => setProfileForm({ ...profileForm, priority: e.value })}
                        optionLabel="label"
                        optionValue="value"
                        placeholder="Select priority"
                      />
                    </div>
                    <div className="col-6">
                      <label htmlFor="customColor" className="block text-900 font-medium mb-2">Theme Color</label>
                      <ColorPicker
                        value={profileForm.customColor}
                        onChange={(e) => setProfileForm({ ...profileForm, customColor: e.value as string })}
                        format="hex"
                      />
                    </div>
                    <div className="col-6">
                      <label htmlFor="autoScan" className="block text-900 font-medium mb-2">Auto Scan</label>
                      <InputSwitch
                        checked={profileForm.autoScanEnabled}
                        onChange={(e) => setProfileForm({ ...profileForm, autoScanEnabled: e.value })}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </TabPanel>

            <TabPanel header="Platforms & Content">
              <div className="grid">
                <div className="col-12">
                  <label className="block text-900 font-medium mb-2">Social Media Platforms *</label>
                  <div className="grid">
                    {platformOptions.map((platform) => {
                      const existingPlatform = profileForm.platforms.find(p => p.platform === platform.name);
                      return (
                        <div key={platform.code} className="col-12 md:col-6 lg:col-4">
                          <Card className="h-full">
                            <div className="flex align-items-center justify-content-between mb-2">
                              <div className="flex align-items-center gap-2">
                                <input
                                  type="checkbox"
                                  checked={!!existingPlatform}
                                  onChange={(e) => {
                                    let updatedPlatforms = [...profileForm.platforms];
                                    if (e.target.checked) {
                                      updatedPlatforms.push({
                                        platform: platform.name,
                                        username: '',
                                        isConnected: false
                                      });
                                    } else {
                                      updatedPlatforms = updatedPlatforms.filter(p => p.platform !== platform.name);
                                    }
                                    setProfileForm({ ...profileForm, platforms: updatedPlatforms });
                                  }}
                                />
                                <strong>{platform.name}</strong>
                              </div>
                            </div>
                            {existingPlatform && (
                              <div>
                                <InputText
                                  placeholder="Username"
                                  value={existingPlatform.username}
                                  onChange={(e) => {
                                    const updatedPlatforms = profileForm.platforms.map(p => 
                                      p.platform === platform.name 
                                        ? { ...p, username: e.target.value }
                                        : p
                                    );
                                    setProfileForm({ ...profileForm, platforms: updatedPlatforms });
                                  }}
                                  className="w-full text-sm"
                                />
                              </div>
                            )}
                          </Card>
                        </div>
                      );
                    })}
                  </div>
                </div>
                <div className="col-12">
                  <label className="block text-900 font-medium mb-2">Content Types</label>
                  <MultiSelect
                    value={profileForm.contentTypes}
                    options={contentTypeOptions}
                    onChange={(e) => setProfileForm({ ...profileForm, contentTypes: e.value })}
                    optionLabel="name"
                    optionValue="code"
                    placeholder="Select content types to monitor"
                    className="w-full"
                  />
                </div>
              </div>
            </TabPanel>

            <TabPanel header="Monitoring Settings">
              <div className="grid">
                <div className="col-12 md:col-6">
                  <label className="block text-900 font-medium mb-2">Scan Frequency</label>
                  <SelectButton
                    value={profileForm.scanFrequency}
                    onChange={(e) => setProfileForm({ ...profileForm, scanFrequency: e.value })}
                    options={scanFrequencyOptions}
                    className="w-full"
                  />
                </div>
                <div className="col-12 md:col-6">
                  <label className="block text-900 font-medium mb-2">Notification Frequency</label>
                  <Dropdown
                    value={profileForm.notificationSettings.frequency}
                    options={[
                      { label: 'Immediate', value: 'immediate' },
                      { label: 'Hourly', value: 'hourly' },
                      { label: 'Daily', value: 'daily' },
                      { label: 'Weekly', value: 'weekly' }
                    ]}
                    onChange={(e) => setProfileForm({ 
                      ...profileForm, 
                      notificationSettings: { ...profileForm.notificationSettings, frequency: e.value }
                    })}
                    optionLabel="label"
                    optionValue="value"
                  />
                </div>
                <div className="col-12">
                  <h6 className="text-900 mb-3">Notification Preferences</h6>
                  <div className="grid">
                    <div className="col-12 md:col-4">
                      <div className="flex align-items-center gap-2">
                        <InputSwitch
                          checked={profileForm.notificationSettings.email}
                          onChange={(e) => setProfileForm({
                            ...profileForm,
                            notificationSettings: { ...profileForm.notificationSettings, email: e.value }
                          })}
                        />
                        <label>Email Notifications</label>
                      </div>
                    </div>
                    <div className="col-12 md:col-4">
                      <div className="flex align-items-center gap-2">
                        <InputSwitch
                          checked={profileForm.notificationSettings.sms}
                          onChange={(e) => setProfileForm({
                            ...profileForm,
                            notificationSettings: { ...profileForm.notificationSettings, sms: e.value }
                          })}
                        />
                        <label>SMS Notifications</label>
                      </div>
                    </div>
                    <div className="col-12 md:col-4">
                      <div className="flex align-items-center gap-2">
                        <InputSwitch
                          checked={profileForm.notificationSettings.inApp}
                          onChange={(e) => setProfileForm({
                            ...profileForm,
                            notificationSettings: { ...profileForm.notificationSettings, inApp: e.value }
                          })}
                        />
                        <label>In-App Notifications</label>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="col-12">
                  <label htmlFor="notes" className="block text-900 font-medium mb-2">Notes</label>
                  <InputTextarea
                    id="notes"
                    value={profileForm.notes}
                    onChange={(e) => setProfileForm({ ...profileForm, notes: e.target.value })}
                    placeholder="Internal notes about this profile"
                    rows={3}
                  />
                </div>
              </div>
            </TabPanel>

            {profileForm.category === 'client' && (
              <TabPanel header="Agency Settings">
                <div className="grid">
                  <div className="col-12 md:col-6">
                    <label className="block text-900 font-medium mb-2">Client Name</label>
                    <InputText
                      value={profileForm.agencyInfo?.clientName || ''}
                      onChange={(e) => setProfileForm({
                        ...profileForm,
                        agencyInfo: { ...profileForm.agencyInfo, clientName: e.target.value } as AgencyInfo
                      })}
                      placeholder="Client or agency name"
                    />
                  </div>
                  <div className="col-12 md:col-6">
                    <label className="block text-900 font-medium mb-2">Account Manager</label>
                    <InputText
                      value={profileForm.agencyInfo?.manager || ''}
                      onChange={(e) => setProfileForm({
                        ...profileForm,
                        agencyInfo: { ...profileForm.agencyInfo, manager: e.target.value } as AgencyInfo
                      })}
                      placeholder="Account manager name"
                    />
                  </div>
                  <div className="col-12 md:col-6">
                    <label className="block text-900 font-medium mb-2">Contract Start</label>
                    <Calendar
                      value={profileForm.agencyInfo?.contractStart}
                      onChange={(e) => setProfileForm({
                        ...profileForm,
                        agencyInfo: { ...profileForm.agencyInfo, contractStart: e.value as Date } as AgencyInfo
                      })}
                      dateFormat="mm/dd/yy"
                    />
                  </div>
                  <div className="col-12 md:col-6">
                    <label className="block text-900 font-medium mb-2">Hourly Rate ($)</label>
                    <InputText
                      type="number"
                      value={profileForm.agencyInfo?.billingRate?.toString() || ''}
                      onChange={(e) => setProfileForm({
                        ...profileForm,
                        agencyInfo: { ...profileForm.agencyInfo, billingRate: parseFloat(e.target.value) } as AgencyInfo
                      })}
                      placeholder="150"
                    />
                  </div>
                </div>
              </TabPanel>
            )}
          </TabView>

          <div className="flex justify-content-end gap-2 mt-4">
            <Button label="Cancel" outlined onClick={hideDialog} />
            <Button 
              label={editingProfile ? 'Update Profile' : 'Create Profile'} 
              onClick={saveProfile}
              disabled={!profileForm.name || !profileForm.platforms.length}
            />
          </div>
        </Dialog>

        {/* Profile Creation Wizard */}
        <Dialog
          visible={profileWizardDialog}
          style={{ width: '900px', maxWidth: '95vw' }}
          header="Profile Setup Wizard"
          modal
          onHide={hideDialog}
          closable={false}
        >
          <Steps model={wizardSteps} activeIndex={activeWizardStep} />
          <div className="mt-4">
            {activeWizardStep === 0 && (
              <div className="grid">
                <div className="col-12 text-center mb-4">
                  <h5>Let's start with basic information</h5>
                  <p className="text-600">We'll help you set up your profile step by step</p>
                </div>
                <div className="col-12 md:col-6 md:col-offset-3">
                  <div className="field">
                    <label htmlFor="wizardName">Profile Name *</label>
                    <InputText
                      id="wizardName"
                      value={profileForm.name}
                      onChange={(e) => setProfileForm({ ...profileForm, name: e.target.value })}
                      placeholder="Enter your name or brand name"
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="wizardStageName">Stage Name / Username</label>
                    <InputText
                      id="wizardStageName"
                      value={profileForm.stageName}
                      onChange={(e) => setProfileForm({ ...profileForm, stageName: e.target.value })}
                      placeholder="@username or public name"
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="wizardDescription">Description</label>
                    <InputTextarea
                      id="wizardDescription"
                      value={profileForm.description}
                      onChange={(e) => setProfileForm({ ...profileForm, description: e.target.value })}
                      placeholder="Describe your content and audience"
                      rows={3}
                    />
                  </div>
                </div>
              </div>
            )}

            {activeWizardStep === 1 && (
              <div className="grid">
                <div className="col-12 text-center mb-4">
                  <h5>Connect Your Platforms</h5>
                  <p className="text-600">Select the platforms where you publish content</p>
                </div>
                <div className="col-12">
                  <div className="grid">
                    {platformOptions.map((platform) => {
                      const isSelected = profileForm.platforms.some(p => p.platform === platform.name);
                      return (
                        <div key={platform.code} className="col-12 md:col-6 lg:col-4 mb-3">
                          <Card 
                            className={`cursor-pointer text-center transition-all transition-duration-200 ${
                              isSelected ? 'border-primary shadow-2' : 'hover:shadow-1'
                            }`}
                            onClick={() => {
                              let updatedPlatforms = [...profileForm.platforms];
                              if (isSelected) {
                                updatedPlatforms = updatedPlatforms.filter(p => p.platform !== platform.name);
                              } else {
                                updatedPlatforms.push({
                                  platform: platform.name,
                                  username: '',
                                  isConnected: false
                                });
                              }
                              setProfileForm({ ...profileForm, platforms: updatedPlatforms });
                            }}
                          >
                            <div className="py-3">
                              <i className={`pi pi-${isSelected ? 'check-circle' : 'circle'} text-2xl mb-2 ${isSelected ? 'text-primary' : 'text-400'}`} />
                              <div className="font-medium">{platform.name}</div>
                            </div>
                          </Card>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}

            {activeWizardStep === 2 && (
              <div className="grid">
                <div className="col-12 text-center mb-4">
                  <h5>Configure Protection Settings</h5>
                  <p className="text-600">Set up how often we should scan for infringements</p>
                </div>
                <div className="col-12 md:col-8 md:col-offset-2">
                  <div className="field">
                    <label>Scan Frequency</label>
                    <SelectButton
                      value={profileForm.scanFrequency}
                      onChange={(e) => setProfileForm({ ...profileForm, scanFrequency: e.value })}
                      options={scanFrequencyOptions}
                      className="w-full"
                    />
                  </div>
                  <div className="field">
                    <label>Content Types to Monitor</label>
                    <MultiSelect
                      value={profileForm.contentTypes}
                      options={contentTypeOptions}
                      onChange={(e) => setProfileForm({ ...profileForm, contentTypes: e.value })}
                      optionLabel="name"
                      optionValue="code"
                      placeholder="Select content types"
                      className="w-full"
                    />
                  </div>
                  <div className="field">
                    <div className="flex align-items-center gap-2">
                      <InputSwitch
                        checked={profileForm.autoScanEnabled}
                        onChange={(e) => setProfileForm({ ...profileForm, autoScanEnabled: e.value })}
                      />
                      <label>Enable automatic scanning</label>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeWizardStep === 3 && (
              <div className="grid">
                <div className="col-12 text-center mb-4">
                  <h5>Review Your Profile</h5>
                  <p className="text-600">Everything looks good? Let's create your profile!</p>
                </div>
                <div className="col-12 md:col-8 md:col-offset-2">
                  <Card>
                    <div className="text-center mb-3">
                      <Avatar 
                        label={profileForm.name.charAt(0).toUpperCase()} 
                        size="large" 
                        shape="circle" 
                        className="mb-2"
                        style={{ backgroundColor: profileForm.customColor }}
                      />
                      <h6 className="m-0">{profileForm.name}</h6>
                      {profileForm.stageName && <p className="text-600 m-0">@{profileForm.stageName}</p>}
                    </div>
                    <Divider />
                    <div className="grid">
                      <div className="col-6">
                        <strong>Platforms:</strong> {profileForm.platforms.length}
                      </div>
                      <div className="col-6">
                        <strong>Scan Frequency:</strong> {profileForm.scanFrequency}
                      </div>
                      <div className="col-6">
                        <strong>Content Types:</strong> {profileForm.contentTypes.length}
                      </div>
                      <div className="col-6">
                        <strong>Auto-scan:</strong> {profileForm.autoScanEnabled ? 'Yes' : 'No'}
                      </div>
                    </div>
                  </Card>
                </div>
              </div>
            )}
          </div>

          <div className="flex justify-content-between mt-4">
            <Button 
              label="Previous" 
              outlined 
              onClick={prevWizardStep}
              disabled={activeWizardStep === 0}
            />
            <div className="flex gap-2">
              <Button label="Cancel" outlined onClick={hideDialog} />
              {activeWizardStep < wizardSteps.length - 1 ? (
                <Button 
                  label="Next" 
                  onClick={nextWizardStep}
                  disabled={
                    (activeWizardStep === 0 && !profileForm.name) ||
                    (activeWizardStep === 1 && profileForm.platforms.length === 0)
                  }
                />
              ) : (
                <Button 
                  label="Create Profile" 
                  onClick={saveProfile}
                />
              )}
            </div>
          </div>
        </Dialog>

        {/* Quick Profile Switcher */}
        <Dialog
          visible={showQuickSwitcher}
          style={{ width: '400px' }}
          header="Switch Profile"
          modal
          onHide={() => setShowQuickSwitcher(false)}
        >
          <div className="flex flex-column gap-2">
            {profiles.map(profile => (
              <div 
                key={profile.id}
                className={`flex align-items-center gap-3 p-3 border-round cursor-pointer hover:surface-100 ${
                  currentProfileId === profile.id ? 'bg-primary-50 border-primary' : ''
                }`}
                onClick={() => {
                  switchToProfile(profile.id);
                  setShowQuickSwitcher(false);
                }}
              >
                <Avatar 
                  image={profile.image} 
                  size="normal"
                  style={{ borderColor: profile.customColor, borderWidth: '2px' }}
                />
                <div className="flex-1">
                  <div className="font-medium">{profile.name}</div>
                  <div className="text-600 text-sm">{profile.platforms.length} platforms</div>
                </div>
                <Tag value={profile.status} severity={getStatusSeverity(profile.status)} />
                {currentProfileId === profile.id && (
                  <i className="pi pi-check text-primary" />
                )}
              </div>
            ))}
          </div>
        </Dialog>

        {/* Profile Details Dialog */}
        <Dialog
          visible={profileDetailsDialog}
          style={{ width: '1000px', maxWidth: '95vw' }}
          header={selectedProfile ? `${selectedProfile.name} - Profile Details` : 'Profile Details'}
          modal
          onHide={() => setProfileDetailsDialog(false)}
          maximizable
        >
          {selectedProfile && (
            <TabView>
              <TabPanel header="Overview">
                <div className="grid">
                  <div className="col-12 md:col-4 text-center">
                    <Avatar 
                      image={selectedProfile.image} 
                      size="xlarge" 
                      shape="circle"
                      className="mb-3"
                      style={{ borderColor: selectedProfile.customColor, borderWidth: '3px' }}
                    />
                    <h5 className="m-0 mb-1">{selectedProfile.name}</h5>
                    {selectedProfile.stageName && (
                      <p className="text-600 m-0 mb-2">@{selectedProfile.stageName}</p>
                    )}
                    <div className="flex justify-content-center gap-2 mb-3">
                      <Tag value={selectedProfile.category} severity={getCategorySeverity(selectedProfile.category)} />
                      <Tag value={selectedProfile.priority} severity={getPrioritySeverity(selectedProfile.priority)} />
                    </div>
                    <Button 
                      label="Switch to this Profile"
                      onClick={() => switchToProfile(selectedProfile.id)}
                      disabled={currentProfileId === selectedProfile.id}
                      className="w-full"
                    />
                  </div>
                  <div className="col-12 md:col-8">
                    <div className="grid">
                      <div className="col-12 md:col-6">
                        <Card className="text-center h-full">
                          <h6 className="text-600 m-0 mb-2">Protection Score</h6>
                          <div className="text-3xl font-bold text-primary mb-2">{selectedProfile.analytics.protectionScore}</div>
                          <ProgressBar value={selectedProfile.analytics.protectionScore} showValue={false} style={{ height: '6px' }} />
                        </Card>
                      </div>
                      <div className="col-12 md:col-6">
                        <Card className="text-center h-full">
                          <h6 className="text-600 m-0 mb-2">Content Protected</h6>
                          <div className="text-3xl font-bold text-green-600 mb-2">
                            {formatNumber(selectedProfile.analytics.totalContentProtected)}
                          </div>
                          <div className="text-sm text-500">items monitored</div>
                        </Card>
                      </div>
                      <div className="col-12 md:col-6">
                        <Card className="text-center h-full">
                          <h6 className="text-600 m-0 mb-2">Infringements Found</h6>
                          <div className="text-3xl font-bold text-orange-600 mb-2">{selectedProfile.infringementsFound}</div>
                          <div className="text-sm text-500">of {selectedProfile.totalScans} scans</div>
                        </Card>
                      </div>
                      <div className="col-12 md:col-6">
                        <Card className="text-center h-full">
                          <h6 className="text-600 m-0 mb-2">Response Time</h6>
                          <div className="text-3xl font-bold text-blue-600 mb-2">{selectedProfile.analytics.averageResponseTime}h</div>
                          <div className="text-sm text-500">average</div>
                        </Card>
                      </div>
                    </div>
                  </div>
                </div>
              </TabPanel>

              <TabPanel header="Platforms">
                <div className="grid">
                  {selectedProfile.platforms.map((platform, index) => (
                    <div key={index} className="col-12 md:col-6 lg:col-4 mb-3">
                      <Card>
                        <div className="flex justify-content-between align-items-center mb-2">
                          <h6 className="m-0">{platform.platform}</h6>
                          <div className="flex gap-1">
                            {platform.isVerified && <i className="pi pi-verified text-blue-500" />}
                            <Tag 
                              value={platform.isConnected ? 'Connected' : 'Disconnected'}
                              severity={platform.isConnected ? 'success' : 'danger'}
                            />
                          </div>
                        </div>
                        <div className="text-600 mb-2">@{platform.username}</div>
                        {platform.followersCount && (
                          <div className="text-sm text-500">
                            {formatNumber(platform.followersCount)} followers
                          </div>
                        )}
                        {platform.lastSync && (
                          <div className="text-xs text-400 mt-2">
                            Last sync: {formatTimeSince(platform.lastSync)}
                          </div>
                        )}
                      </Card>
                    </div>
                  ))}
                </div>
              </TabPanel>

              <TabPanel header="Analytics">
                <div className="grid">
                  <div className="col-12">
                    <Card>
                      <h6>Monthly Trends</h6>
                      <div className="grid">
                        {selectedProfile.analytics.monthlyTrends.map((trend, index) => (
                          <div key={index} className="col-4 md:col-2 text-center">
                            <div className="text-600 text-sm">{trend.month}</div>
                            <div className="font-bold text-lg">{trend.scans}</div>
                            <div className="text-xs text-orange-600">{trend.infringements} found</div>
                          </div>
                        ))}
                      </div>
                    </Card>
                  </div>
                  <div className="col-12">
                    <Card>
                      <h6>Top Infringing Platforms</h6>
                      <div className="flex flex-wrap gap-2">
                        {selectedProfile.analytics.topInfringingPlatforms.map((platform, index) => (
                          <Chip key={index} label={platform} className="text-sm" />
                        ))}
                      </div>
                    </Card>
                  </div>
                </div>
              </TabPanel>

              {selectedProfile.agencyInfo && (
                <TabPanel header="Agency Info">
                  <div className="grid">
                    <div className="col-12 md:col-6">
                      <Card>
                        <h6>Client Information</h6>
                        <div className="field">
                          <label>Client Name:</label>
                          <div className="font-medium">{selectedProfile.agencyInfo.clientName}</div>
                        </div>
                        <div className="field">
                          <label>Account Manager:</label>
                          <div className="font-medium">{selectedProfile.agencyInfo.manager}</div>
                        </div>
                        <div className="field">
                          <label>Billing Rate:</label>
                          <div className="font-medium">${selectedProfile.agencyInfo.billingRate}/hour</div>
                        </div>
                      </Card>
                    </div>
                    <div className="col-12 md:col-6">
                      <Card>
                        <h6>Contract Details</h6>
                        <div className="field">
                          <label>Start Date:</label>
                          <div className="font-medium">{formatDate(selectedProfile.agencyInfo.contractStart)}</div>
                        </div>
                        {selectedProfile.agencyInfo.contractEnd && (
                          <div className="field">
                            <label>End Date:</label>
                            <div className="font-medium">{formatDate(selectedProfile.agencyInfo.contractEnd)}</div>
                          </div>
                        )}
                        <div className="field">
                          <label>Permissions:</label>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {selectedProfile.agencyInfo.permissions.map((permission, index) => (
                              <Chip key={index} label={permission} size="small" />
                            ))}
                          </div>
                        </div>
                      </Card>
                    </div>
                  </div>
                </TabPanel>
              )}
            </TabView>
          )}
        </Dialog>

        {/* Bulk Operations Dialog */}
        <Dialog
          visible={bulkOperationsDialog}
          style={{ width: '600px' }}
          header={`Bulk Operations (${selectedProfiles.length} profiles)`}
          modal
          onHide={() => setBulkOperationsDialog(false)}
        >
          <div className="grid">
            <div className="col-12 mb-3">
              <h6>Selected Profiles:</h6>
              <div className="flex flex-wrap gap-2">
                {selectedProfiles.map(profile => (
                  <Chip key={profile.id} label={profile.name} />
                ))}
              </div>
            </div>
            <div className="col-12 md:col-6">
              <Button
                label="Activate All"
                icon="pi pi-play"
                className="w-full mb-2"
                onClick={() => bulkUpdateProfiles({ status: 'active' })}
              />
            </div>
            <div className="col-12 md:col-6">
              <Button
                label="Pause All"
                icon="pi pi-pause"
                severity="warning"
                className="w-full mb-2"
                onClick={() => bulkUpdateProfiles({ status: 'paused' })}
              />
            </div>
            <div className="col-12 md:col-6">
              <Button
                label="Enable Auto-Scan"
                icon="pi pi-sync"
                className="w-full mb-2"
                onClick={() => bulkUpdateProfiles({ autoScanEnabled: true })}
              />
            </div>
            <div className="col-12 md:col-6">
              <Button
                label="Disable Auto-Scan"
                icon="pi pi-ban"
                outlined
                className="w-full mb-2"
                onClick={() => bulkUpdateProfiles({ autoScanEnabled: false })}
              />
            </div>
            <div className="col-12">
              <Button
                label="Archive All"
                icon="pi pi-archive"
                severity="secondary"
                className="w-full mb-2"
                onClick={() => bulkUpdateProfiles({ status: 'archived' })}
              />
            </div>
          </div>
        </Dialog>

        {/* Profile Limit Warning Dialog */}
        <Dialog
          visible={showProfileLimitWarning}
          style={{ width: '450px' }}
          header="Profile Limit Reached"
          modal
          onHide={() => setShowProfileLimitWarning(false)}
        >
          <div className="flex align-items-center gap-3">
            <i className="pi pi-exclamation-triangle text-orange-500" style={{ fontSize: '2rem' }} />
            <div>
              <div className="text-900 font-medium mb-2">
                You've reached your profile limit
              </div>
              <div className="text-600 mb-3">
                Your {currentPlan} plan allows up to {maxProfiles} profiles. Upgrade to add more profiles.
              </div>
              <div className="flex gap-2">
                <Button label="Upgrade Plan" size="small" />
                <Button label="Manage Profiles" outlined size="small" onClick={() => setShowProfileLimitWarning(false)} />
              </div>
            </div>
          </div>
        </Dialog>

        {/* Delete Dialog */}
        <Dialog
          visible={deleteProfilesDialog}
          style={{ width: '450px' }}
          header="Confirm Delete"
          modal
          onHide={() => setDeleteProfilesDialog(false)}
        >
          <div className="flex align-items-center gap-3">
            <i className="pi pi-exclamation-triangle text-orange-500" style={{ fontSize: '2rem' }} />
            <div>
              <div className="text-900 font-medium mb-2">
                Are you sure you want to delete {selectedProfiles.length} profile(s)?
              </div>
              <div className="text-600 mb-2">
                This action cannot be undone and will remove all monitoring data.
              </div>
              <div className="text-sm text-500">
                Profiles: {selectedProfiles.map(p => p.name).join(', ')}
              </div>
            </div>
          </div>
          <div className="flex justify-content-end gap-2 mt-4">
            <Button 
              label="Cancel" 
              outlined 
              onClick={() => setDeleteProfilesDialog(false)} 
            />
            <Button 
              label="Delete" 
              severity="danger" 
              onClick={deleteSelectedProfiles}
            />
          </div>
        </Dialog>

        <Toast ref={toast} />
        <ConfirmDialog />
        <Menu ref={menu} model={[]} popup />
      </div>
    </div>
  );
};

export default Profiles;