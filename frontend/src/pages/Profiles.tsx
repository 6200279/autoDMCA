import React, { useState, useEffect, useRef } from 'react';
import { Card } from 'primereact/card';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Button } from 'primereact/button';
import { Dialog } from 'primereact/dialog';
import { InputText } from 'primereact/inputtext';
import { Tag } from 'primereact/tag';
import { Toolbar } from 'primereact/toolbar';
import { Toast } from 'primereact/toast';
import { ConfirmDialog, confirmDialog } from 'primereact/confirmdialog';
import { Dropdown } from 'primereact/dropdown';
import { Skeleton } from 'primereact/skeleton';
import { Message } from 'primereact/message';
import { Badge } from 'primereact/badge';
import { Avatar } from 'primereact/avatar';
import { Chip } from 'primereact/chip';
import { InputTextarea } from 'primereact/inputtextarea';
import { FilterMatchMode } from 'primereact/api';
import { Controller, useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { profileApi } from '../services/api';

// TypeScript interfaces
interface Profile {
  id: string;
  name: string;
  stageName?: string;
  description: string;
  image?: string;
  status: 'active' | 'inactive' | 'scanning' | 'error' | 'paused' | 'archived';
  platforms: PlatformAccount[];
  totalScans: number;
  infringementsFound: number;
  lastScan: string;
  createdAt: string;
  successRate: number;
  scanFrequency: 'daily' | 'weekly' | 'monthly';
  tags?: string[];
  category?: string;
  priority?: string;
}

interface PlatformAccount {
  id: string;
  name: string;
  username: string;
  isConnected: boolean;
  followers?: number;
  platform: string;
  lastSync?: string;
  scanEnabled?: boolean;
}

interface ProfileFormData {
  name: string;
  stageName: string;
  description: string;
  status: string;
  scanFrequency: string;
  category: string;
  priority: string;
}

const validationSchema = yup.object({
  name: yup.string().required('Profile name is required').min(2, 'Name must be at least 2 characters'),
  stageName: yup.string().required('Stage name is required'),
  description: yup.string().required('Description is required').max(500, 'Description must be less than 500 characters'),
  status: yup.string().required('Status is required'),
  scanFrequency: yup.string().required('Scan frequency is required'),
  category: yup.string().required('Category is required'),
  priority: yup.string().required('Priority is required')
});

const Profiles: React.FC = () => {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [loading, setLoading] = useState(true);
  const [globalFilterValue, setGlobalFilterValue] = useState('');
  const [selectedProfiles, setSelectedProfiles] = useState<Profile[]>([]);
  const [profileDialog, setProfileDialog] = useState(false);
  const [deleteProfilesDialog, setDeleteProfilesDialog] = useState(false);
  const [editingProfile, setEditingProfile] = useState<Profile | null>(null);
  const [filters, setFilters] = useState({
    global: { value: null, matchMode: FilterMatchMode.CONTAINS }
  });

  const toast = useRef<Toast>(null);

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

  useEffect(() => {
    fetchProfiles();
  }, []);

  const fetchProfiles = async () => {
    try {
      setLoading(true);
      const response = await profileApi.getProfiles();
      const profilesData = response.data?.items || response.data || [];
      setProfiles(profilesData);
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

  // Status options
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

  const getStatusSeverity = (status: string) => {
    switch (status) {
      case 'active': return 'success';
      case 'scanning': return 'info';
      case 'inactive': return 'warning';
      case 'paused': return 'secondary';
      case 'error': return 'danger';
      default: return null;
    }
  };

  const onGlobalFilterChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setGlobalFilterValue(value);
    setFilters({
      global: { value, matchMode: FilterMatchMode.CONTAINS }
    });
  };

  const openNew = () => {
    reset();
    setEditingProfile(null);
    setProfileDialog(true);
  };

  const hideDialog = () => {
    setProfileDialog(false);
    setEditingProfile(null);
    reset();
  };

  const editProfile = (profile: Profile) => {
    setEditingProfile(profile);
    reset({
      name: profile.name,
      stageName: profile.stageName || '',
      description: profile.description,
      status: profile.status,
      scanFrequency: profile.scanFrequency,
      category: profile.category || 'Lifestyle',
      priority: profile.priority || 'normal'
    });
    setProfileDialog(true);
  };

  const onSubmit = async (data: ProfileFormData) => {
    try {
      if (editingProfile) {
        // Update existing profile
        const updatedProfile = {
          ...editingProfile,
          ...data
        };
        // Update in local state for demo
        setProfiles(profiles.map(p => p.id === editingProfile.id ? updatedProfile : p));
        toast.current?.show({
          severity: 'success',
          summary: 'Success',
          detail: 'Profile updated successfully'
        });
      } else {
        // Create new profile
        const newProfile: Profile = {
          id: Date.now().toString(),
          ...data,
          platforms: [],
          totalScans: 0,
          infringementsFound: 0,
          lastScan: new Date().toISOString(),
          createdAt: new Date().toISOString(),
          successRate: 0,
          image: `https://picsum.photos/64/64?random=${Date.now()}`
        };
        setProfiles([...profiles, newProfile]);
        toast.current?.show({
          severity: 'success',
          summary: 'Success',
          detail: 'Profile created successfully'
        });
      }
      hideDialog();
    } catch (error) {
      toast.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: 'Failed to save profile'
      });
    }
  };

  const confirmDeleteSelected = () => {
    confirmDialog({
      message: `Are you sure you want to delete ${selectedProfiles.length} selected profiles?`,
      header: 'Confirm',
      icon: 'pi pi-exclamation-triangle',
      accept: deleteSelectedProfiles
    });
  };

  const deleteSelectedProfiles = async () => {
    try {
      const updatedProfiles = profiles.filter(p => !selectedProfiles.find(sp => sp.id === p.id));
      setProfiles(updatedProfiles);
      setSelectedProfiles([]);
      toast.current?.show({
        severity: 'success',
        summary: 'Success',
        detail: 'Profiles deleted successfully'
      });
    } catch (error) {
      toast.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: 'Failed to delete profiles'
      });
    }
  };

  // Column templates
  const profileBodyTemplate = (rowData: Profile) => (
    <div className="flex align-items-center">
      <Avatar 
        image={rowData.image} 
        shape="circle" 
        size="normal"
        className="mr-2"
      />
      <div>
        <div className="font-semibold">{rowData.name}</div>
        <div className="text-sm text-600">{rowData.stageName}</div>
      </div>
    </div>
  );

  const statusBodyTemplate = (rowData: Profile) => (
    <Tag value={rowData.status.toUpperCase()} severity={getStatusSeverity(rowData.status)} />
  );

  const platformsBodyTemplate = (rowData: Profile) => (
    <div className="flex flex-wrap gap-1">
      {rowData.platforms?.slice(0, 3).map((platform, index) => (
        <Chip 
          key={index} 
          label={platform.platform} 
          className="text-xs"
        />
      ))}
      {rowData.platforms?.length > 3 && (
        <Badge value={`+${rowData.platforms.length - 3}`} />
      )}
    </div>
  );

  const statsBodyTemplate = (rowData: Profile) => (
    <div className="text-sm">
      <div>Scans: <span className="font-semibold">{rowData.totalScans}</span></div>
      <div>Issues: <span className="font-semibold text-orange-500">{rowData.infringementsFound}</span></div>
    </div>
  );

  const successRateBodyTemplate = (rowData: Profile) => (
    <div className="flex align-items-center">
      <span className="mr-2">{rowData.successRate}%</span>
      <div className="w-3rem">
        <div 
          className="bg-green-100 border-round-sm h-0-5rem"
          style={{
            background: `linear-gradient(to right, #22c55e ${rowData.successRate}%, #e5e7eb ${rowData.successRate}%)`
          }}
        />
      </div>
    </div>
  );

  const lastScanBodyTemplate = (rowData: Profile) => (
    <span className="text-sm">
      {new Date(rowData.lastScan).toLocaleDateString()}
    </span>
  );

  const actionsBodyTemplate = (rowData: Profile) => (
    <div className="flex gap-1">
      <Button
        icon="pi pi-pencil"
        size="small"
        text
        rounded
        severity="info"
        onClick={() => editProfile(rowData)}
        tooltip="Edit"
      />
      <Button
        icon="pi pi-eye"
        size="small"
        text
        rounded
        severity="help"
        tooltip="View Details"
      />
      <Button
        icon="pi pi-play"
        size="small"
        text
        rounded
        severity="success"
        tooltip="Start Scan"
        disabled={rowData.status === 'scanning'}
      />
    </div>
  );

  // Toolbar
  const leftToolbarTemplate = () => (
    <div className="flex flex-wrap gap-2">
      <Button
        label="New Profile"
        icon="pi pi-plus"
        severity="success"
        onClick={openNew}
      />
      <Button
        label="Delete Selected"
        icon="pi pi-trash"
        severity="danger"
        onClick={confirmDeleteSelected}
        disabled={!selectedProfiles.length}
      />
    </div>
  );

  const rightToolbarTemplate = () => (
    <div className="flex align-items-center gap-2">
      <span className="p-input-icon-left">
        <i className="pi pi-search" />
        <InputText
          value={globalFilterValue}
          onChange={onGlobalFilterChange}
          placeholder="Search profiles..."
        />
      </span>
    </div>
  );

  const header = (
    <div className="table-header">
      <h2 className="text-xl font-bold mb-0">Content Creator Profiles</h2>
      <p className="text-600 mt-1 mb-0">Manage and monitor your protected content profiles</p>
    </div>
  );

  if (loading) {
    return (
      <div className="profiles-page">
        <Card>
          <div className="grid">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="col-12 md:col-6 lg:col-4">
                <Skeleton width="100%" height="200px" />
              </div>
            ))}
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="profiles-page">
      <Toast ref={toast} />
      <ConfirmDialog />

      <Card>
        <Toolbar 
          className="mb-4" 
          left={leftToolbarTemplate} 
          right={rightToolbarTemplate} 
        />

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
          <Column selectionMode="multiple" headerStyle={{ width: '3rem' }} />
          <Column
            field="name"
            header="Profile"
            body={profileBodyTemplate}
            sortable
            style={{ minWidth: '200px' }}
          />
          <Column
            field="status"
            header="Status"
            body={statusBodyTemplate}
            sortable
            style={{ minWidth: '120px' }}
          />
          <Column
            header="Platforms"
            body={platformsBodyTemplate}
            style={{ minWidth: '150px' }}
          />
          <Column
            header="Stats"
            body={statsBodyTemplate}
            style={{ minWidth: '100px' }}
          />
          <Column
            field="successRate"
            header="Success Rate"
            body={successRateBodyTemplate}
            sortable
            style={{ minWidth: '140px' }}
          />
          <Column
            field="lastScan"
            header="Last Scan"
            body={lastScanBodyTemplate}
            sortable
            style={{ minWidth: '120px' }}
          />
          <Column
            header="Actions"
            body={actionsBodyTemplate}
            headerStyle={{ width: '120px' }}
          />
        </DataTable>
      </Card>

      {/* Profile Dialog */}
      <Dialog
        visible={profileDialog}
        header={editingProfile ? 'Edit Profile' : 'Create New Profile'}
        modal
        className="p-fluid"
        style={{ width: '600px' }}
        onHide={hideDialog}
      >
        <form onSubmit={handleSubmit(onSubmit)}>
          <div className="grid">
            <div className="col-12 md:col-6">
              <div className="field">
                <label htmlFor="name" className="font-semibold">Profile Name *</label>
                <Controller
                  name="name"
                  control={control}
                  render={({ field, fieldState }) => (
                    <InputText
                      id={field.name}
                      {...field}
                      className={fieldState.error ? 'p-invalid' : ''}
                      placeholder="Enter profile name"
                    />
                  )}
                />
                {errors.name && <small className="p-error">{errors.name.message}</small>}
              </div>
            </div>

            <div className="col-12 md:col-6">
              <div className="field">
                <label htmlFor="stageName" className="font-semibold">Stage Name *</label>
                <Controller
                  name="stageName"
                  control={control}
                  render={({ field, fieldState }) => (
                    <InputText
                      id={field.name}
                      {...field}
                      className={fieldState.error ? 'p-invalid' : ''}
                      placeholder="@username"
                    />
                  )}
                />
                {errors.stageName && <small className="p-error">{errors.stageName.message}</small>}
              </div>
            </div>

            <div className="col-12">
              <div className="field">
                <label htmlFor="description" className="font-semibold">Description *</label>
                <Controller
                  name="description"
                  control={control}
                  render={({ field, fieldState }) => (
                    <InputTextarea
                      id={field.name}
                      {...field}
                      rows={3}
                      className={fieldState.error ? 'p-invalid' : ''}
                      placeholder="Describe this profile..."
                    />
                  )}
                />
                {errors.description && <small className="p-error">{errors.description.message}</small>}
              </div>
            </div>

            <div className="col-12 md:col-6">
              <div className="field">
                <label htmlFor="status" className="font-semibold">Status *</label>
                <Controller
                  name="status"
                  control={control}
                  render={({ field }) => (
                    <Dropdown
                      id={field.name}
                      value={field.value}
                      onChange={field.onChange}
                      options={statusOptions}
                      optionLabel="label"
                      optionValue="value"
                      placeholder="Select status"
                    />
                  )}
                />
                {errors.status && <small className="p-error">{errors.status.message}</small>}
              </div>
            </div>

            <div className="col-12 md:col-6">
              <div className="field">
                <label htmlFor="scanFrequency" className="font-semibold">Scan Frequency *</label>
                <Controller
                  name="scanFrequency"
                  control={control}
                  render={({ field }) => (
                    <Dropdown
                      id={field.name}
                      value={field.value}
                      onChange={field.onChange}
                      options={frequencyOptions}
                      optionLabel="label"
                      optionValue="value"
                      placeholder="Select frequency"
                    />
                  )}
                />
                {errors.scanFrequency && <small className="p-error">{errors.scanFrequency.message}</small>}
              </div>
            </div>

            <div className="col-12 md:col-6">
              <div className="field">
                <label htmlFor="category" className="font-semibold">Category *</label>
                <Controller
                  name="category"
                  control={control}
                  render={({ field }) => (
                    <Dropdown
                      id={field.name}
                      value={field.value}
                      onChange={field.onChange}
                      options={categoryOptions}
                      optionLabel="label"
                      optionValue="value"
                      placeholder="Select category"
                    />
                  )}
                />
                {errors.category && <small className="p-error">{errors.category.message}</small>}
              </div>
            </div>

            <div className="col-12 md:col-6">
              <div className="field">
                <label htmlFor="priority" className="font-semibold">Priority *</label>
                <Controller
                  name="priority"
                  control={control}
                  render={({ field }) => (
                    <Dropdown
                      id={field.name}
                      value={field.value}
                      onChange={field.onChange}
                      options={priorityOptions}
                      optionLabel="label"
                      optionValue="value"
                      placeholder="Select priority"
                    />
                  )}
                />
                {errors.priority && <small className="p-error">{errors.priority.message}</small>}
              </div>
            </div>
          </div>

          <div className="flex justify-content-end gap-2 mt-3">
            <Button
              type="button"
              label="Cancel"
              icon="pi pi-times"
              outlined
              onClick={hideDialog}
            />
            <Button
              type="submit"
              label={editingProfile ? 'Update' : 'Create'}
              icon="pi pi-check"
            />
          </div>
        </form>
      </Dialog>
    </div>
  );
};

export default Profiles;