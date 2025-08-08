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
import { useAuth } from '../contexts/AuthContext';

// TypeScript interfaces
interface Profile {
  id: string;
  name: string;
  description: string;
  image: string;
  status: 'active' | 'inactive' | 'scanning' | 'error';
  platforms: string[];
  totalScans: number;
  infringementsFound: number;
  lastScan: Date;
  createdAt: Date;
  successRate: number;
  scanFrequency: 'daily' | 'weekly' | 'monthly';
  tags: string[];
}

interface ProfileFormData {
  name: string;
  description: string;
  image?: File;
  platforms: string[];
  scanFrequency: 'daily' | 'weekly' | 'monthly';
  tags: string[];
}

const Profiles: React.FC = () => {
  const { user } = useAuth();
  const toast = useRef<Toast>(null);
  const fileUploadRef = useRef<FileUpload>(null);

  // State management
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [loading, setLoading] = useState(true);
  const [globalFilterValue, setGlobalFilterValue] = useState('');
  const [selectedProfiles, setSelectedProfiles] = useState<Profile[]>([]);
  const [profileDialog, setProfileDialog] = useState(false);
  const [deleteProfilesDialog, setDeleteProfilesDialog] = useState(false);
  const [profileForm, setProfileForm] = useState<ProfileFormData>({
    name: '',
    description: '',
    platforms: [],
    scanFrequency: 'weekly',
    tags: []
  });
  const [editingProfile, setEditingProfile] = useState<Profile | null>(null);
  const [imagePreview, setImagePreview] = useState<string>('');

  // Filter options
  const statusOptions = [
    { label: 'All Statuses', value: null },
    { label: 'Active', value: 'active' },
    { label: 'Inactive', value: 'inactive' },
    { label: 'Scanning', value: 'scanning' },
    { label: 'Error', value: 'error' }
  ];

  const platformOptions = [
    'Instagram', 'TikTok', 'OnlyFans', 'Twitter', 'YouTube', 'Reddit', 'Telegram'
  ];

  const scanFrequencyOptions = [
    { label: 'Daily', value: 'daily' },
    { label: 'Weekly', value: 'weekly' },
    { label: 'Monthly', value: 'monthly' }
  ];

  // DataTable filters
  const [filters, setFilters] = useState({
    global: { value: null, matchMode: FilterMatchMode.CONTAINS },
    name: { value: null, matchMode: FilterMatchMode.STARTS_WITH },
    status: { value: null, matchMode: FilterMatchMode.EQUALS },
    platforms: { value: null, matchMode: FilterMatchMode.CONTAINS }
  });

  // Mock data
  const mockProfiles: Profile[] = [
    {
      id: '1',
      name: 'Sarah Johnson',
      description: 'Professional model and content creator',
      image: '/api/placeholder/150/150',
      status: 'active',
      platforms: ['Instagram', 'TikTok', 'OnlyFans'],
      totalScans: 145,
      infringementsFound: 23,
      lastScan: new Date(Date.now() - 2 * 60 * 60 * 1000),
      createdAt: new Date('2024-01-15'),
      successRate: 89,
      scanFrequency: 'daily',
      tags: ['model', 'verified', 'high-priority']
    },
    {
      id: '2',
      name: 'Emma Davis',
      description: 'Fitness influencer and coach',
      image: '/api/placeholder/150/150',
      status: 'scanning',
      platforms: ['Instagram', 'YouTube', 'TikTok'],
      totalScans: 89,
      infringementsFound: 12,
      lastScan: new Date(Date.now() - 30 * 60 * 1000),
      createdAt: new Date('2024-02-10'),
      successRate: 75,
      scanFrequency: 'weekly',
      tags: ['fitness', 'influencer']
    },
    {
      id: '3',
      name: 'Mia Rodriguez',
      description: 'Artist and digital creator',
      image: '/api/placeholder/150/150',
      status: 'active',
      platforms: ['Instagram', 'Twitter', 'Reddit'],
      totalScans: 67,
      infringementsFound: 18,
      lastScan: new Date(Date.now() - 6 * 60 * 60 * 1000),
      createdAt: new Date('2024-03-05'),
      successRate: 92,
      scanFrequency: 'weekly',
      tags: ['artist', 'verified']
    },
    {
      id: '4',
      name: 'Alex Chen',
      description: 'Gaming streamer and content creator',
      image: '/api/placeholder/150/150',
      status: 'inactive',
      platforms: ['YouTube', 'TikTok', 'Twitter'],
      totalScans: 34,
      infringementsFound: 5,
      lastScan: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
      createdAt: new Date('2024-04-12'),
      successRate: 68,
      scanFrequency: 'monthly',
      tags: ['gaming', 'streamer']
    },
    {
      id: '5',
      name: 'Lisa Thompson',
      description: 'Fashion blogger and photographer',
      image: '/api/placeholder/150/150',
      status: 'error',
      platforms: ['Instagram', 'Pinterest'],
      totalScans: 23,
      infringementsFound: 8,
      lastScan: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000),
      createdAt: new Date('2024-05-20'),
      successRate: 45,
      scanFrequency: 'weekly',
      tags: ['fashion', 'blogger']
    }
  ];

  // Initialize data
  useEffect(() => {
    const timer = setTimeout(() => {
      setProfiles(mockProfiles);
      setLoading(false);
    }, 1000);

    return () => clearTimeout(timer);
  }, []);

  // Helper functions
  const getStatusSeverity = (status: string) => {
    switch (status) {
      case 'active': return 'success';
      case 'scanning': return 'info';
      case 'inactive': return 'warning';
      case 'error': return 'danger';
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

  // Dialog handlers
  const openNew = () => {
    setProfileForm({
      name: '',
      description: '',
      platforms: [],
      scanFrequency: 'weekly',
      tags: []
    });
    setEditingProfile(null);
    setImagePreview('');
    setProfileDialog(true);
  };

  const editProfile = (profile: Profile) => {
    setProfileForm({
      name: profile.name,
      description: profile.description,
      platforms: profile.platforms,
      scanFrequency: profile.scanFrequency,
      tags: profile.tags
    });
    setEditingProfile(profile);
    setImagePreview(profile.image);
    setProfileDialog(true);
  };

  const hideDialog = () => {
    setProfileDialog(false);
    setImagePreview('');
    if (fileUploadRef.current) {
      fileUploadRef.current.clear();
    }
  };

  const saveProfile = () => {
    const newProfile: Profile = {
      id: editingProfile?.id || Date.now().toString(),
      ...profileForm,
      image: imagePreview || '/api/placeholder/150/150',
      status: editingProfile?.status || 'active',
      totalScans: editingProfile?.totalScans || 0,
      infringementsFound: editingProfile?.infringementsFound || 0,
      lastScan: editingProfile?.lastScan || new Date(),
      createdAt: editingProfile?.createdAt || new Date(),
      successRate: editingProfile?.successRate || 0
    };

    if (editingProfile) {
      setProfiles(profiles.map(p => p.id === editingProfile.id ? newProfile : p));
      toast.current?.show({
        severity: 'success',
        summary: 'Success',
        detail: 'Profile updated successfully',
        life: 3000
      });
    } else {
      setProfiles([...profiles, newProfile]);
      toast.current?.show({
        severity: 'success',
        summary: 'Success',
        detail: 'Profile created successfully',
        life: 3000
      });
    }

    hideDialog();
  };

  const confirmDeleteSelected = () => {
    setDeleteProfilesDialog(true);
  };

  const deleteSelectedProfiles = () => {
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

  const onImageUpload = (event: any) => {
    const file = event.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        setImagePreview(e.target?.result as string);
      };
      reader.readAsDataURL(file);
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

  // Column templates
  const profileTemplate = (rowData: Profile) => (
    <div className="flex align-items-center gap-3">
      <Image 
        src={rowData.image} 
        alt={rowData.name}
        width="50"
        height="50"
        className="border-round"
        preview={false}
      />
      <div>
        <div className="font-medium text-900">{rowData.name}</div>
        <div className="text-600 text-sm">{rowData.description}</div>
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
    </div>
  );

  const platformsTemplate = (rowData: Profile) => (
    <div className="flex flex-wrap gap-1">
      {rowData.platforms.slice(0, 2).map((platform, index) => (
        <Badge key={index} value={platform} size="normal" />
      ))}
      {rowData.platforms.length > 2 && (
        <Badge 
          value={`+${rowData.platforms.length - 2}`} 
          severity="secondary" 
          size="normal" 
        />
      )}
    </div>
  );

  const statsTemplate = (rowData: Profile) => (
    <div className="text-center">
      <div className="text-900 font-bold">{rowData.infringementsFound}</div>
      <div className="text-600 text-xs">of {rowData.totalScans} scans</div>
    </div>
  );

  const successRateTemplate = (rowData: Profile) => (
    <div className="flex align-items-center gap-2">
      <ProgressBar 
        value={rowData.successRate} 
        showValue={false}
        style={{ width: '60px', height: '8px' }}
      />
      <span className="text-sm">{rowData.successRate}%</span>
    </div>
  );

  const lastScanTemplate = (rowData: Profile) => (
    <div className="text-center">
      <div className="text-900">{formatTimeSince(rowData.lastScan)}</div>
      <div className="text-600 text-xs">{formatDate(rowData.lastScan)}</div>
    </div>
  );

  const actionsTemplate = (rowData: Profile) => (
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
        icon="pi pi-pencil"
        size="small"
        text
        tooltip="Edit Profile"
        onClick={() => editProfile(rowData)}
      />
      <Button
        icon="pi pi-trash"
        size="small"
        text
        severity="danger"
        tooltip="Delete Profile"
        onClick={() => {
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
        }}
      />
    </div>
  );

  // Toolbar content
  const startContent = (
    <div className="flex align-items-center gap-2">
      <Button 
        label="New Profile" 
        icon="pi pi-plus" 
        onClick={openNew}
      />
      <Button
        label="Delete Selected"
        icon="pi pi-trash"
        severity="danger"
        onClick={confirmDeleteSelected}
        disabled={!selectedProfiles.length}
      />
      <Button
        label="Bulk Scan"
        icon="pi pi-search"
        outlined
        disabled={!selectedProfiles.length}
        onClick={() => {
          selectedProfiles.forEach(profile => {
            if (profile.status !== 'scanning') {
              scanProfile(profile);
            }
          });
          setSelectedProfiles([]);
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
          placeholder="Search profiles..."
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
            setProfiles([...mockProfiles]);
            setLoading(false);
            toast.current?.show({
              severity: 'success',
              summary: 'Success',
              detail: 'Profiles refreshed',
              life: 2000
            });
          }, 500);
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
        <div className="flex flex-column md:flex-row md:justify-content-between md:align-items-center mb-4 gap-3">
          <div>
            <h2 className="m-0 text-900">Profile Management</h2>
            <p className="text-600 m-0 mt-1">Manage and monitor your protected profiles</p>
          </div>
          <div className="flex align-items-center gap-2">
            <Badge value={`${profiles.length} profiles`} size="large" />
            <Badge 
              value={`${profiles.filter(p => p.status === 'active').length} active`} 
              severity="success" 
              size="large" 
            />
          </div>
        </div>

        {/* Statistics Cards */}
        <div className="grid mb-4">
          <div className="col-12 md:col-3">
            <Card className="text-center">
              <div className="text-600 text-sm mb-2">Total Profiles</div>
              <div className="text-900 font-bold text-2xl">{profiles.length}</div>
            </Card>
          </div>
          <div className="col-12 md:col-3">
            <Card className="text-center">
              <div className="text-600 text-sm mb-2">Active Monitoring</div>
              <div className="text-green-600 font-bold text-2xl">
                {profiles.filter(p => p.status === 'active').length}
              </div>
            </Card>
          </div>
          <div className="col-12 md:col-3">
            <Card className="text-center">
              <div className="text-600 text-sm mb-2">Total Scans</div>
              <div className="text-blue-600 font-bold text-2xl">
                {profiles.reduce((sum, p) => sum + p.totalScans, 0)}
              </div>
            </Card>
          </div>
          <div className="col-12 md:col-3">
            <Card className="text-center">
              <div className="text-600 text-sm mb-2">Infringements Found</div>
              <div className="text-orange-600 font-bold text-2xl">
                {profiles.reduce((sum, p) => sum + p.infringementsFound, 0)}
              </div>
            </Card>
          </div>
        </div>

        <Card>
          <Toolbar start={startContent} end={endContent} className="mb-4" />

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
            globalFilterFields={['name', 'description', 'platforms']}
            emptyMessage="No profiles found"
            sortMode="multiple"
            removableSort
          >
            <Column selectionMode="multiple" headerStyle={{ width: '3rem' }} />
            <Column 
              field="name" 
              header="Profile" 
              body={profileTemplate}
              sortable
              style={{ minWidth: '250px' }}
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
              style={{ width: '180px' }}
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
        </Card>

        {/* Profile Dialog */}
        <Dialog
          visible={profileDialog}
          style={{ width: '500px' }}
          header={editingProfile ? 'Edit Profile' : 'New Profile'}
          modal
          className="p-fluid"
          onHide={hideDialog}
        >
          <div className="grid">
            {/* Image Upload */}
            <div className="col-12">
              <label htmlFor="image" className="block text-900 font-medium mb-2">
                Profile Image
              </label>
              <div className="flex align-items-center gap-3">
                {imagePreview && (
                  <Image 
                    src={imagePreview} 
                    alt="Profile preview" 
                    width="80" 
                    height="80" 
                    className="border-round"
                  />
                )}
                <FileUpload
                  ref={fileUploadRef}
                  mode="basic"
                  name="image"
                  accept="image/*"
                  maxFileSize={5000000}
                  onUpload={onImageUpload}
                  chooseLabel="Choose Image"
                  className="flex-1"
                />
              </div>
            </div>

            {/* Name */}
            <div className="col-12">
              <label htmlFor="name" className="block text-900 font-medium mb-2">
                Profile Name *
              </label>
              <InputText
                id="name"
                value={profileForm.name}
                onChange={(e) => setProfileForm({ ...profileForm, name: e.target.value })}
                required
                placeholder="Enter profile name"
              />
            </div>

            {/* Description */}
            <div className="col-12">
              <label htmlFor="description" className="block text-900 font-medium mb-2">
                Description
              </label>
              <InputText
                id="description"
                value={profileForm.description}
                onChange={(e) => setProfileForm({ ...profileForm, description: e.target.value })}
                placeholder="Brief description of the profile"
              />
            </div>

            {/* Platforms */}
            <div className="col-12">
              <label htmlFor="platforms" className="block text-900 font-medium mb-2">
                Monitoring Platforms
              </label>
              <div className="grid">
                {platformOptions.map((platform) => (
                  <div key={platform} className="col-6 md:col-4">
                    <label className="flex align-items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={profileForm.platforms.includes(platform)}
                        onChange={(e) => {
                          const platforms = e.target.checked
                            ? [...profileForm.platforms, platform]
                            : profileForm.platforms.filter(p => p !== platform);
                          setProfileForm({ ...profileForm, platforms });
                        }}
                      />
                      <span>{platform}</span>
                    </label>
                  </div>
                ))}
              </div>
            </div>

            {/* Scan Frequency */}
            <div className="col-12">
              <label htmlFor="frequency" className="block text-900 font-medium mb-2">
                Scan Frequency
              </label>
              <SelectButton
                value={profileForm.scanFrequency}
                onChange={(e) => setProfileForm({ ...profileForm, scanFrequency: e.value })}
                options={scanFrequencyOptions}
                className="w-full"
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
              label={editingProfile ? 'Update' : 'Create'} 
              onClick={saveProfile}
              disabled={!profileForm.name || !profileForm.platforms.length}
            />
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
                Are you sure you want to delete the selected profiles?
              </div>
              <div className="text-600">
                This action cannot be undone and will remove all monitoring data.
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
      </div>
    </div>
  );
};

export default Profiles;