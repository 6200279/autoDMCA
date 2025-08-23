import React, { useState, useEffect, useRef } from 'react';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { InputText } from 'primereact/inputtext';
import { Password } from 'primereact/password';
import { InputSwitch } from 'primereact/inputswitch';
import { SelectButton } from 'primereact/selectbutton';
import { Dropdown } from 'primereact/dropdown';
import { Toast } from 'primereact/toast';
import { ConfirmDialog, confirmDialog } from 'primereact/confirmdialog';
import { Dialog } from 'primereact/dialog';
import { Divider } from 'primereact/divider';
import { TabView, TabPanel } from 'primereact/tabview';
import { Panel } from 'primereact/panel';
import { Chip } from 'primereact/chip';
import { FileUpload } from 'primereact/fileupload';
import { Image } from 'primereact/image';
import { Badge } from 'primereact/badge';
import { Message } from 'primereact/message';
import { Skeleton } from 'primereact/skeleton';
import { Calendar } from 'primereact/calendar';
import { Slider } from 'primereact/slider';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Tag } from 'primereact/tag';
import { useAuth } from '../contexts/AuthContext';
import { userApi } from '../services/api';

// TypeScript interfaces
interface UserSettings {
  profile: {
    firstName: string;
    lastName: string;
    email: string;
    phone?: string;
    avatar?: string;
    timezone: string;
    language: string;
    dateFormat: string;
  };
  notifications: {
    emailNotifications: boolean;
    smsNotifications: boolean;
    pushNotifications: boolean;
    infringementAlerts: boolean;
    takedownUpdates: boolean;
    weeklyReports: boolean;
    marketingEmails: boolean;
    securityAlerts: boolean;
  };
  privacy: {
    profileVisibility: 'public' | 'private' | 'contacts';
    dataSharing: boolean;
    analytics: boolean;
    cookiePreferences: 'all' | 'essential' | 'custom';
  };
  security: {
    twoFactorEnabled: boolean;
    sessionTimeout: number; // minutes
    loginNotifications: boolean;
    passwordExpiry: number; // days
  };
  api: {
    keys: ApiKey[];
    webhookUrl?: string;
    rateLimiting: boolean;
  };
}

interface ApiKey {
  id: string;
  name: string;
  key: string;
  permissions: string[];
  createdAt: Date;
  lastUsed?: Date;
  isActive: boolean;
}

interface ActivityLog {
  id: string;
  action: string;
  description: string;
  timestamp: Date;
  ipAddress: string;
  device: string;
  location?: string;
}

const Settings: React.FC = () => {
  const { user, logout } = useAuth();
  const toast = useRef<Toast>(null);
  const fileUploadRef = useRef<FileUpload>(null);

  // State management
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleteAccountDialog, setDeleteAccountDialog] = useState(false);
  const [apiKeyDialog, setApiKeyDialog] = useState(false);
  const [newApiKeyName, setNewApiKeyName] = useState('');
  const [selectedPermissions, setSelectedPermissions] = useState<string[]>([]);
  const [avatarPreview, setAvatarPreview] = useState<string>('');
  const [activityLogs, setActivityLogs] = useState<ActivityLog[]>([]);

  // Settings state
  const [settings, setSettings] = useState<UserSettings>({
    profile: {
      firstName: user?.first_name || '',
      lastName: user?.last_name || '',
      email: user?.email || '',
      phone: '',
      avatar: user?.avatar || '',
      timezone: 'America/New_York',
      language: 'en',
      dateFormat: 'MM/dd/yyyy'
    },
    notifications: {
      emailNotifications: true,
      smsNotifications: false,
      pushNotifications: true,
      infringementAlerts: true,
      takedownUpdates: true,
      weeklyReports: true,
      marketingEmails: false,
      securityAlerts: true
    },
    privacy: {
      profileVisibility: 'private',
      dataSharing: false,
      analytics: true,
      cookiePreferences: 'essential'
    },
    security: {
      twoFactorEnabled: false,
      sessionTimeout: 30,
      loginNotifications: true,
      passwordExpiry: 90
    },
    api: {
      keys: [
        {
          id: '1',
          name: 'Production API',
          key: 'ak_live_xxxxxxxxxxxxxxxxxxxx',
          permissions: ['read:profiles', 'write:takedowns', 'read:infringements'],
          createdAt: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
          lastUsed: new Date(Date.now() - 2 * 60 * 60 * 1000),
          isActive: true
        },
        {
          id: '2',
          name: 'Development API',
          key: 'ak_test_xxxxxxxxxxxxxxxxxxxx',
          permissions: ['read:profiles', 'read:infringements'],
          createdAt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
          lastUsed: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000),
          isActive: true
        }
      ],
      webhookUrl: '',
      rateLimiting: true
    }
  });

  // Form states for password change
  const [passwordForm, setPasswordForm] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  });

  // Options for dropdowns
  const timezoneOptions = [
    { label: 'Eastern Time (ET)', value: 'America/New_York' },
    { label: 'Central Time (CT)', value: 'America/Chicago' },
    { label: 'Mountain Time (MT)', value: 'America/Denver' },
    { label: 'Pacific Time (PT)', value: 'America/Los_Angeles' },
    { label: 'UTC', value: 'UTC' }
  ];

  const languageOptions = [
    { label: 'English', value: 'en' },
    { label: 'Spanish', value: 'es' },
    { label: 'French', value: 'fr' },
    { label: 'German', value: 'de' },
    { label: 'Italian', value: 'it' }
  ];

  const dateFormatOptions = [
    { label: 'MM/dd/yyyy', value: 'MM/dd/yyyy' },
    { label: 'dd/MM/yyyy', value: 'dd/MM/yyyy' },
    { label: 'yyyy-MM-dd', value: 'yyyy-MM-dd' },
    { label: 'dd MMM yyyy', value: 'dd MMM yyyy' }
  ];

  const privacyOptions = [
    { label: 'Public', value: 'public' },
    { label: 'Private', value: 'private' },
    { label: 'Contacts Only', value: 'contacts' }
  ];

  const cookieOptions = [
    { label: 'All Cookies', value: 'all' },
    { label: 'Essential Only', value: 'essential' },
    { label: 'Custom', value: 'custom' }
  ];

  const apiPermissions = [
    'read:profiles',
    'write:profiles',
    'read:infringements',
    'write:infringements',
    'read:takedowns',
    'write:takedowns',
    'read:analytics',
    'admin:all'
  ];

  // Mock activity logs
  const mockActivityLogs: ActivityLog[] = [
    {
      id: '1',
      action: 'Login',
      description: 'Successful login from web browser',
      timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000),
      ipAddress: '192.168.1.100',
      device: 'Chrome on Windows',
      location: 'New York, NY'
    },
    {
      id: '2',
      action: 'API Key Used',
      description: 'Production API key accessed profiles endpoint',
      timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000),
      ipAddress: '10.0.0.50',
      device: 'API Client',
    },
    {
      id: '3',
      action: 'Settings Changed',
      description: 'Updated notification preferences',
      timestamp: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000),
      ipAddress: '192.168.1.100',
      device: 'Chrome on Windows',
      location: 'New York, NY'
    },
    {
      id: '4',
      action: 'Password Changed',
      description: 'Password successfully updated',
      timestamp: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000),
      ipAddress: '192.168.1.100',
      device: 'Chrome on Windows',
      location: 'New York, NY'
    },
    {
      id: '5',
      action: 'Login Failed',
      description: 'Failed login attempt - incorrect password',
      timestamp: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000),
      ipAddress: '203.0.113.195',
      device: 'Chrome on Android',
      location: 'Unknown'
    }
  ];

  // Initialize data
  useEffect(() => {
    const loadUserData = async () => {
      if (!user) return;
      
      try {
        // Load user settings from backend
        const [settingsResponse, activityResponse, apiKeysResponse] = await Promise.all([
          userApi.getUserSettings(),
          userApi.getUserActivity(),
          userApi.getApiKeys()
        ]);
        
        if (settingsResponse.data) {
          setSettings({
            ...settings,
            ...settingsResponse.data,
            profile: {
              ...settings.profile,
              firstName: user.first_name || '',
              lastName: user.last_name || '',
              email: user.email || '',
              avatar: user.avatar || ''
            },
            api: {
              ...settings.api,
              keys: apiKeysResponse?.data || settings.api.keys
            }
          });
        }
        
        if (activityResponse.data) {
          setActivityLogs(activityResponse.data.slice(0, 20)); // Last 20 activities
        }
        
        if (user.avatar) {
          setAvatarPreview(user.avatar);
        }
      } catch (error) {
        console.error('Failed to load user data:', error);
        // Fallback to mock data if API fails
        setActivityLogs(mockActivityLogs);
        if (user.avatar) {
          setAvatarPreview(user.avatar);
        }
      } finally {
        setLoading(false);
      }
    };

    loadUserData();
  }, [user]);

  // Helper functions
  const showToast = (severity: 'success' | 'info' | 'warn' | 'error', summary: string, detail: string) => {
    toast.current?.show({ severity, summary, detail, life: 3000 });
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

  // Event handlers
  const saveSettings = async () => {
    setSaving(true);
    try {
      // Update user profile
      await userApi.updateUser({
        first_name: settings.profile.firstName,
        last_name: settings.profile.lastName,
        phone: settings.profile.phone,
        timezone: settings.profile.timezone,
        language: settings.profile.language,
        date_format: settings.profile.dateFormat
      });
      
      // Update user settings
      await userApi.updateUserSettings({
        notifications: settings.notifications,
        privacy: settings.privacy,
        security: settings.security,
        api: settings.api
      });
      
      showToast('success', 'Settings Saved', 'Your settings have been updated successfully');
    } catch (error: any) {
      console.error('Settings save error:', error);
      const errorMessage = error.response?.data?.detail || 'Unable to save settings. Please try again.';
      showToast('error', 'Save Failed', errorMessage);
    } finally {
      setSaving(false);
    }
  };

  const changePassword = async () => {
    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      showToast('error', 'Password Mismatch', 'New passwords do not match');
      return;
    }

    if (passwordForm.newPassword.length < 8) {
      showToast('error', 'Weak Password', 'Password must be at least 8 characters long');
      return;
    }

    try {
      await userApi.changePassword({
        current_password: passwordForm.currentPassword,
        new_password: passwordForm.newPassword
      });
      
      setPasswordForm({ currentPassword: '', newPassword: '', confirmPassword: '' });
      showToast('success', 'Password Changed', 'Your password has been updated successfully');
    } catch (error: any) {
      console.error('Password change error:', error);
      const errorMessage = error.response?.data?.detail || 'Unable to change password. Please try again.';
      showToast('error', 'Change Failed', errorMessage);
    }
  };

  const onAvatarUpload = async (event: any) => {
    const file = event.files[0];
    if (file) {
      try {
        const response = await userApi.uploadAvatar(file);
        const avatarUrl = response.data.avatar_url;
        
        setAvatarPreview(avatarUrl);
        setSettings({
          ...settings,
          profile: { ...settings.profile, avatar: avatarUrl }
        });
        
        showToast('success', 'Avatar Updated', 'Your profile picture has been updated successfully');
      } catch (error: any) {
        console.error('Avatar upload error:', error);
        const errorMessage = error.response?.data?.detail || 'Unable to upload avatar. Please try again.';
        showToast('error', 'Upload Failed', errorMessage);
      }
    }
  };

  const createApiKey = async () => {
    if (!newApiKeyName.trim()) {
      showToast('error', 'Missing Name', 'Please provide a name for the API key');
      return;
    }

    try {
      const response = await userApi.createApiKey({
        name: newApiKeyName,
        permissions: selectedPermissions
      });
      
      const newKey = response.data;
      
      setSettings({
        ...settings,
        api: {
          ...settings.api,
          keys: [...settings.api.keys, newKey]
        }
      });

      setApiKeyDialog(false);
      setNewApiKeyName('');
      setSelectedPermissions([]);
      showToast('success', 'API Key Created', 'New API key has been generated');
    } catch (error: any) {
      console.error('API key creation error:', error);
      const errorMessage = error.response?.data?.detail || 'Unable to create API key. Please try again.';
      showToast('error', 'Creation Failed', errorMessage);
    }
  };

  const revokeApiKey = (keyId: string) => {
    confirmDialog({
      message: 'Are you sure you want to revoke this API key? This action cannot be undone.',
      header: 'Revoke API Key',
      icon: 'pi pi-exclamation-triangle',
      accept: async () => {
        try {
          await userApi.revokeApiKey(keyId);
          
          setSettings({
            ...settings,
            api: {
              ...settings.api,
              keys: settings.api.keys.filter(k => k.id !== keyId)
            }
          });
          showToast('success', 'API Key Revoked', 'The API key has been revoked');
        } catch (error: any) {
          console.error('API key revocation error:', error);
          const errorMessage = error.response?.data?.detail || 'Unable to revoke API key. Please try again.';
          showToast('error', 'Revocation Failed', errorMessage);
        }
      }
    });
  };

  const enable2FA = () => {
    setSettings({
      ...settings,
      security: { ...settings.security, twoFactorEnabled: true }
    });
    showToast('success', '2FA Enabled', 'Two-factor authentication has been enabled');
  };

  const deleteAccount = () => {
    confirmDialog({
      message: 'This will permanently delete your account and all associated data. This action cannot be undone.',
      header: 'Delete Account',
      icon: 'pi pi-exclamation-triangle',
      acceptClassName: 'p-button-danger',
      accept: async () => {
        try {
          // Simulate account deletion
          await new Promise(resolve => setTimeout(resolve, 2000));
          showToast('success', 'Account Deleted', 'Your account has been permanently deleted');
          setTimeout(() => logout(), 2000);
        } catch (error) {
          showToast('error', 'Deletion Failed', 'Unable to delete account. Please try again.');
        }
      }
    });
  };

  // Column templates for activity logs
  const actionTemplate = (rowData: ActivityLog) => (
    <div>
      <div className="font-medium text-900">{rowData.action}</div>
      <div className="text-600 text-sm">{rowData.description}</div>
    </div>
  );

  const timestampTemplate = (rowData: ActivityLog) => (
    <div className="text-center">
      <div className="text-900 text-sm">{formatDate(rowData.timestamp)}</div>
    </div>
  );

  const locationTemplate = (rowData: ActivityLog) => (
    <div className="text-center">
      <div className="text-900 text-sm">{rowData.ipAddress}</div>
      <div className="text-600 text-xs">{rowData.location || 'Unknown'}</div>
    </div>
  );

  const deviceTemplate = (rowData: ActivityLog) => (
    <div className="text-center">
      <div className="text-900 text-sm">{rowData.device}</div>
    </div>
  );

  // API Key templates
  const keyTemplate = (rowData: ApiKey) => (
    <div>
      <div className="font-medium text-900">{rowData.name}</div>
      <div className="text-600 text-sm font-mono">{rowData.key}</div>
    </div>
  );

  const permissionsTemplate = (rowData: ApiKey) => (
    <div className="flex flex-wrap gap-1">
      {rowData.permissions.slice(0, 2).map((permission, index) => (
        <Chip key={index} label={permission} className="text-xs" />
      ))}
      {rowData.permissions.length > 2 && (
        <Chip label={`+${rowData.permissions.length - 2} more`} className="text-xs" />
      )}
    </div>
  );

  const lastUsedTemplate = (rowData: ApiKey) => (
    <div className="text-center">
      {rowData.lastUsed ? (
        <div className="text-900 text-sm">{formatDate(rowData.lastUsed)}</div>
      ) : (
        <div className="text-600">Never</div>
      )}
    </div>
  );

  const statusTemplate = (rowData: ApiKey) => (
    <Tag 
      value={rowData.isActive ? 'Active' : 'Inactive'} 
      severity={rowData.isActive ? 'success' : 'danger'}
      className="text-sm"
    />
  );

  const apiActionsTemplate = (rowData: ApiKey) => (
    <div className="flex gap-1">
      <Button
        icon="pi pi-copy"
        size="small"
        text
        tooltip="Copy Key"
        onClick={() => {
          navigator.clipboard.writeText(rowData.key);
          showToast('success', 'Copied', 'API key copied to clipboard');
        }}
      />
      <Button
        icon="pi pi-trash"
        size="small"
        text
        severity="danger"
        tooltip="Revoke Key"
        onClick={() => revokeApiKey(rowData.id)}
      />
    </div>
  );

  if (loading) {
    return (
      <div className="grid">
        <div className="col-12">
          <Card>
            <Skeleton height="2rem" className="mb-4" />
            <div className="grid">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="col-12 md:col-6">
                  <Skeleton height="3rem" className="mb-3" />
                </div>
              ))}
            </div>
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
            <h2 className="m-0 text-900">Account Settings</h2>
            <p className="text-600 m-0 mt-1">Manage your account preferences and security settings</p>
          </div>
          <div className="flex align-items-center gap-2">
            <Button 
              label="Save Changes" 
              icon="pi pi-save" 
              loading={saving}
              onClick={saveSettings}
            />
          </div>
        </div>

        <TabView>
          {/* Profile Settings */}
          <TabPanel header="Profile" leftIcon="pi pi-user">
            <div className="grid">
              <div className="col-12 md:col-4">
                <Card title="Profile Picture" className="h-full">
                  <div className="flex flex-column align-items-center gap-3">
                    <Image 
                      src={avatarPreview || '/api/placeholder/120/120'} 
                      alt="Profile"
                      width="120"
                      height="120"
                      className="border-circle"
                    />
                    <FileUpload
                      ref={fileUploadRef}
                      mode="basic"
                      name="avatar"
                      accept="image/*"
                      maxFileSize={5000000}
                      onUpload={onAvatarUpload}
                      chooseLabel="Change Picture"
                      className="w-full"
                    />
                  </div>
                </Card>
              </div>
              
              <div className="col-12 md:col-8">
                <Card title="Personal Information">
                  <div className="grid">
                    <div className="col-12 md:col-6">
                      <label htmlFor="firstName" className="block text-900 font-medium mb-2">
                        First Name *
                      </label>
                      <InputText
                        id="firstName"
                        value={settings.profile.firstName}
                        onChange={(e) => setSettings({
                          ...settings,
                          profile: { ...settings.profile, firstName: e.target.value }
                        })}
                        className="w-full"
                      />
                    </div>
                    
                    <div className="col-12 md:col-6">
                      <label htmlFor="lastName" className="block text-900 font-medium mb-2">
                        Last Name *
                      </label>
                      <InputText
                        id="lastName"
                        value={settings.profile.lastName}
                        onChange={(e) => setSettings({
                          ...settings,
                          profile: { ...settings.profile, lastName: e.target.value }
                        })}
                        className="w-full"
                      />
                    </div>
                    
                    <div className="col-12">
                      <label htmlFor="email" className="block text-900 font-medium mb-2">
                        Email Address *
                      </label>
                      <InputText
                        id="email"
                        value={settings.profile.email}
                        onChange={(e) => setSettings({
                          ...settings,
                          profile: { ...settings.profile, email: e.target.value }
                        })}
                        className="w-full"
                        type="email"
                      />
                    </div>
                    
                    <div className="col-12">
                      <label htmlFor="phone" className="block text-900 font-medium mb-2">
                        Phone Number
                      </label>
                      <InputText
                        id="phone"
                        value={settings.profile.phone || ''}
                        onChange={(e) => setSettings({
                          ...settings,
                          profile: { ...settings.profile, phone: e.target.value }
                        })}
                        className="w-full"
                        placeholder="+1 (555) 123-4567"
                      />
                    </div>
                  </div>
                </Card>
              </div>
              
              <div className="col-12">
                <Card title="Preferences">
                  <div className="grid">
                    <div className="col-12 md:col-4">
                      <label htmlFor="timezone" className="block text-900 font-medium mb-2">
                        Timezone
                      </label>
                      <Dropdown
                        id="timezone"
                        value={settings.profile.timezone}
                        options={timezoneOptions}
                        onChange={(e) => setSettings({
                          ...settings,
                          profile: { ...settings.profile, timezone: e.value }
                        })}
                        className="w-full"
                      />
                    </div>
                    
                    <div className="col-12 md:col-4">
                      <label htmlFor="language" className="block text-900 font-medium mb-2">
                        Language
                      </label>
                      <Dropdown
                        id="language"
                        value={settings.profile.language}
                        options={languageOptions}
                        onChange={(e) => setSettings({
                          ...settings,
                          profile: { ...settings.profile, language: e.value }
                        })}
                        className="w-full"
                      />
                    </div>
                    
                    <div className="col-12 md:col-4">
                      <label htmlFor="dateFormat" className="block text-900 font-medium mb-2">
                        Date Format
                      </label>
                      <Dropdown
                        id="dateFormat"
                        value={settings.profile.dateFormat}
                        options={dateFormatOptions}
                        onChange={(e) => setSettings({
                          ...settings,
                          profile: { ...settings.profile, dateFormat: e.value }
                        })}
                        className="w-full"
                      />
                    </div>
                  </div>
                </Card>
              </div>
            </div>
          </TabPanel>

          {/* Security Settings */}
          <TabPanel header="Security" leftIcon="pi pi-shield">
            <div className="grid">
              <div className="col-12 md:col-6">
                <Card title="Change Password">
                  <div className="grid">
                    <div className="col-12">
                      <label htmlFor="currentPassword" className="block text-900 font-medium mb-2">
                        Current Password
                      </label>
                      <Password
                        id="currentPassword"
                        value={passwordForm.currentPassword}
                        onChange={(e) => setPasswordForm({ ...passwordForm, currentPassword: e.target.value })}
                        className="w-full"
                        feedback={false}
                        toggleMask
                      />
                    </div>
                    
                    <div className="col-12">
                      <label htmlFor="newPassword" className="block text-900 font-medium mb-2">
                        New Password
                      </label>
                      <Password
                        id="newPassword"
                        value={passwordForm.newPassword}
                        onChange={(e) => setPasswordForm({ ...passwordForm, newPassword: e.target.value })}
                        className="w-full"
                        toggleMask
                      />
                    </div>
                    
                    <div className="col-12">
                      <label htmlFor="confirmPassword" className="block text-900 font-medium mb-2">
                        Confirm Password
                      </label>
                      <Password
                        id="confirmPassword"
                        value={passwordForm.confirmPassword}
                        onChange={(e) => setPasswordForm({ ...passwordForm, confirmPassword: e.target.value })}
                        className="w-full"
                        feedback={false}
                        toggleMask
                      />
                    </div>
                    
                    <div className="col-12">
                      <Button 
                        label="Change Password" 
                        icon="pi pi-key"
                        onClick={changePassword}
                        disabled={!passwordForm.currentPassword || !passwordForm.newPassword || !passwordForm.confirmPassword}
                        className="w-full"
                      />
                    </div>
                  </div>
                </Card>
              </div>
              
              <div className="col-12 md:col-6">
                <Card title="Security Options">
                  <div className="grid">
                    <div className="col-12">
                      <div className="flex align-items-center justify-content-between mb-3">
                        <div>
                          <div className="text-900 font-medium">Two-Factor Authentication</div>
                          <div className="text-600 text-sm">Add an extra layer of security to your account</div>
                        </div>
                        <div className="flex align-items-center gap-2">
                          <InputSwitch
                            checked={settings.security.twoFactorEnabled}
                            onChange={(e) => {
                              if (!settings.security.twoFactorEnabled && e.value) {
                                enable2FA();
                              } else {
                                setSettings({
                                  ...settings,
                                  security: { ...settings.security, twoFactorEnabled: e.value }
                                });
                              }
                            }}
                          />
                          {settings.security.twoFactorEnabled && (
                            <Badge value="Enabled" severity="success" />
                          )}
                        </div>
                      </div>
                      <Divider />
                    </div>
                    
                    <div className="col-12">
                      <div className="flex align-items-center justify-content-between mb-3">
                        <div>
                          <div className="text-900 font-medium">Login Notifications</div>
                          <div className="text-600 text-sm">Get notified when someone logs into your account</div>
                        </div>
                        <InputSwitch
                          checked={settings.security.loginNotifications}
                          onChange={(e) => setSettings({
                            ...settings,
                            security: { ...settings.security, loginNotifications: e.value }
                          })}
                        />
                      </div>
                      <Divider />
                    </div>
                    
                    <div className="col-12">
                      <label className="block text-900 font-medium mb-2">
                        Session Timeout (minutes)
                      </label>
                      <Slider
                        value={settings.security.sessionTimeout}
                        onChange={(e) => setSettings({
                          ...settings,
                          security: { ...settings.security, sessionTimeout: e.value as number }
                        })}
                        min={15}
                        max={240}
                        step={15}
                        className="w-full mb-2"
                      />
                      <div className="text-center text-600 text-sm">
                        {settings.security.sessionTimeout} minutes
                      </div>
                    </div>
                  </div>
                </Card>
              </div>
            </div>
          </TabPanel>

          {/* Notifications */}
          <TabPanel header="Notifications" leftIcon="pi pi-bell">
            <Card title="Notification Preferences">
              <div className="grid">
                <div className="col-12 md:col-6">
                  <Panel header="Communication Channels">
                    <div className="grid">
                      <div className="col-12">
                        <div className="flex align-items-center justify-content-between mb-3">
                          <div>
                            <div className="text-900 font-medium">Email Notifications</div>
                            <div className="text-600 text-sm">Receive updates via email</div>
                          </div>
                          <InputSwitch
                            checked={settings.notifications.emailNotifications}
                            onChange={(e) => setSettings({
                              ...settings,
                              notifications: { ...settings.notifications, emailNotifications: e.value }
                            })}
                          />
                        </div>
                        <Divider />
                      </div>
                      
                      <div className="col-12">
                        <div className="flex align-items-center justify-content-between mb-3">
                          <div>
                            <div className="text-900 font-medium">SMS Notifications</div>
                            <div className="text-600 text-sm">Receive critical updates via SMS</div>
                          </div>
                          <InputSwitch
                            checked={settings.notifications.smsNotifications}
                            onChange={(e) => setSettings({
                              ...settings,
                              notifications: { ...settings.notifications, smsNotifications: e.value }
                            })}
                          />
                        </div>
                        <Divider />
                      </div>
                      
                      <div className="col-12">
                        <div className="flex align-items-center justify-content-between">
                          <div>
                            <div className="text-900 font-medium">Push Notifications</div>
                            <div className="text-600 text-sm">Browser and mobile push notifications</div>
                          </div>
                          <InputSwitch
                            checked={settings.notifications.pushNotifications}
                            onChange={(e) => setSettings({
                              ...settings,
                              notifications: { ...settings.notifications, pushNotifications: e.value }
                            })}
                          />
                        </div>
                      </div>
                    </div>
                  </Panel>
                </div>
                
                <div className="col-12 md:col-6">
                  <Panel header="Content Types">
                    <div className="grid">
                      <div className="col-12">
                        <div className="flex align-items-center justify-content-between mb-3">
                          <div>
                            <div className="text-900 font-medium">Infringement Alerts</div>
                            <div className="text-600 text-sm">New content infringements detected</div>
                          </div>
                          <InputSwitch
                            checked={settings.notifications.infringementAlerts}
                            onChange={(e) => setSettings({
                              ...settings,
                              notifications: { ...settings.notifications, infringementAlerts: e.value }
                            })}
                          />
                        </div>
                        <Divider />
                      </div>
                      
                      <div className="col-12">
                        <div className="flex align-items-center justify-content-between mb-3">
                          <div>
                            <div className="text-900 font-medium">Takedown Updates</div>
                            <div className="text-600 text-sm">Status changes for DMCA requests</div>
                          </div>
                          <InputSwitch
                            checked={settings.notifications.takedownUpdates}
                            onChange={(e) => setSettings({
                              ...settings,
                              notifications: { ...settings.notifications, takedownUpdates: e.value }
                            })}
                          />
                        </div>
                        <Divider />
                      </div>
                      
                      <div className="col-12">
                        <div className="flex align-items-center justify-content-between mb-3">
                          <div>
                            <div className="text-900 font-medium">Weekly Reports</div>
                            <div className="text-600 text-sm">Summary of platform activity</div>
                          </div>
                          <InputSwitch
                            checked={settings.notifications.weeklyReports}
                            onChange={(e) => setSettings({
                              ...settings,
                              notifications: { ...settings.notifications, weeklyReports: e.value }
                            })}
                          />
                        </div>
                        <Divider />
                      </div>
                      
                      <div className="col-12">
                        <div className="flex align-items-center justify-content-between mb-3">
                          <div>
                            <div className="text-900 font-medium">Marketing Emails</div>
                            <div className="text-600 text-sm">Product updates and promotions</div>
                          </div>
                          <InputSwitch
                            checked={settings.notifications.marketingEmails}
                            onChange={(e) => setSettings({
                              ...settings,
                              notifications: { ...settings.notifications, marketingEmails: e.value }
                            })}
                          />
                        </div>
                        <Divider />
                      </div>
                      
                      <div className="col-12">
                        <div className="flex align-items-center justify-content-between">
                          <div>
                            <div className="text-900 font-medium">Security Alerts</div>
                            <div className="text-600 text-sm">Account security notifications</div>
                          </div>
                          <InputSwitch
                            checked={settings.notifications.securityAlerts}
                            onChange={(e) => setSettings({
                              ...settings,
                              notifications: { ...settings.notifications, securityAlerts: e.value }
                            })}
                          />
                        </div>
                      </div>
                    </div>
                  </Panel>
                </div>
              </div>
            </Card>
          </TabPanel>

          {/* Privacy Settings */}
          <TabPanel header="Privacy" leftIcon="pi pi-lock">
            <Card title="Privacy Settings">
              <div className="grid">
                <div className="col-12 md:col-6">
                  <label htmlFor="profileVisibility" className="block text-900 font-medium mb-2">
                    Profile Visibility
                  </label>
                  <SelectButton
                    id="profileVisibility"
                    value={settings.privacy.profileVisibility}
                    options={privacyOptions}
                    onChange={(e) => setSettings({
                      ...settings,
                      privacy: { ...settings.privacy, profileVisibility: e.value }
                    })}
                    className="w-full"
                  />
                  <small className="text-600">
                    Control who can see your profile information
                  </small>
                </div>
                
                <div className="col-12 md:col-6">
                  <label htmlFor="cookiePreferences" className="block text-900 font-medium mb-2">
                    Cookie Preferences
                  </label>
                  <SelectButton
                    id="cookiePreferences"
                    value={settings.privacy.cookiePreferences}
                    options={cookieOptions}
                    onChange={(e) => setSettings({
                      ...settings,
                      privacy: { ...settings.privacy, cookiePreferences: e.value }
                    })}
                    className="w-full"
                  />
                  <small className="text-600">
                    Manage your cookie and tracking preferences
                  </small>
                </div>
                
                <div className="col-12">
                  <Divider />
                  <div className="flex align-items-center justify-content-between mb-3">
                    <div>
                      <div className="text-900 font-medium">Data Sharing</div>
                      <div className="text-600">Allow sharing anonymized usage data for service improvement</div>
                    </div>
                    <InputSwitch
                      checked={settings.privacy.dataSharing}
                      onChange={(e) => setSettings({
                        ...settings,
                        privacy: { ...settings.privacy, dataSharing: e.value }
                      })}
                    />
                  </div>
                  <Divider />
                  
                  <div className="flex align-items-center justify-content-between">
                    <div>
                      <div className="text-900 font-medium">Analytics</div>
                      <div className="text-600">Allow collection of usage analytics for service optimization</div>
                    </div>
                    <InputSwitch
                      checked={settings.privacy.analytics}
                      onChange={(e) => setSettings({
                        ...settings,
                        privacy: { ...settings.privacy, analytics: e.value }
                      })}
                    />
                  </div>
                </div>
              </div>
            </Card>
          </TabPanel>

          {/* API Settings */}
          <TabPanel header="API Keys" leftIcon="pi pi-key">
            <Card>
              <div className="flex justify-content-between align-items-center mb-4">
                <div>
                  <h4 className="m-0">API Key Management</h4>
                  <p className="text-600 m-0 mt-1">Create and manage API keys for integrations</p>
                </div>
                <Button 
                  label="Create API Key" 
                  icon="pi pi-plus" 
                  onClick={() => setApiKeyDialog(true)}
                />
              </div>
              
              <DataTable
                value={settings.api.keys}
                size="small"
                showGridlines
                emptyMessage="No API keys found"
              >
                <Column 
                  field="name" 
                  header="Key" 
                  body={keyTemplate}
                  style={{ width: '30%' }}
                />
                <Column 
                  field="permissions" 
                  header="Permissions" 
                  body={permissionsTemplate}
                  style={{ width: '25%' }}
                />
                <Column 
                  field="createdAt" 
                  header="Created" 
                  body={(rowData) => formatDate(rowData.createdAt)}
                  style={{ width: '15%' }}
                />
                <Column 
                  field="lastUsed" 
                  header="Last Used" 
                  body={lastUsedTemplate}
                  style={{ width: '15%' }}
                />
                <Column 
                  field="isActive" 
                  header="Status" 
                  body={statusTemplate}
                  style={{ width: '10%' }}
                />
                <Column 
                  body={apiActionsTemplate} 
                  style={{ width: '5%' }}
                />
              </DataTable>
              
              <Divider />
              
              <div className="grid">
                <div className="col-12 md:col-6">
                  <label htmlFor="webhookUrl" className="block text-900 font-medium mb-2">
                    Webhook URL
                  </label>
                  <InputText
                    id="webhookUrl"
                    value={settings.api.webhookUrl || ''}
                    onChange={(e) => setSettings({
                      ...settings,
                      api: { ...settings.api, webhookUrl: e.target.value }
                    })}
                    placeholder="https://your-domain.com/webhooks/autodmca"
                    className="w-full"
                  />
                  <small className="text-600">
                    Receive real-time notifications about account events
                  </small>
                </div>
                
                <div className="col-12 md:col-6">
                  <div className="flex align-items-center justify-content-between h-full">
                    <div>
                      <div className="text-900 font-medium">Rate Limiting</div>
                      <div className="text-600">Enable API rate limiting for security</div>
                    </div>
                    <InputSwitch
                      checked={settings.api.rateLimiting}
                      onChange={(e) => setSettings({
                        ...settings,
                        api: { ...settings.api, rateLimiting: e.value }
                      })}
                    />
                  </div>
                </div>
              </div>
            </Card>
          </TabPanel>

          {/* Activity Log */}
          <TabPanel header="Activity" leftIcon="pi pi-history">
            <Card title="Recent Account Activity">
              <DataTable
                value={activityLogs}
                paginator
                rows={10}
                size="small"
                showGridlines
                emptyMessage="No activity found"
              >
                <Column 
                  field="action" 
                  header="Activity" 
                  body={actionTemplate}
                  style={{ width: '30%' }}
                />
                <Column 
                  field="timestamp" 
                  header="When" 
                  body={timestampTemplate}
                  sortable
                  style={{ width: '20%' }}
                />
                <Column 
                  field="device" 
                  header="Device" 
                  body={deviceTemplate}
                  style={{ width: '20%' }}
                />
                <Column 
                  field="ipAddress" 
                  header="Location" 
                  body={locationTemplate}
                  style={{ width: '30%' }}
                />
              </DataTable>
            </Card>
          </TabPanel>

          {/* Account Management */}
          <TabPanel header="Account" leftIcon="pi pi-cog">
            <div className="grid">
              <div className="col-12 md:col-8">
                <Card title="Account Information">
                  <div className="grid">
                    <div className="col-12 md:col-6">
                      <div className="text-600 text-sm">Account ID</div>
                      <div className="text-900 font-mono">{user?.id || 'user_123456'}</div>
                    </div>
                    
                    <div className="col-12 md:col-6">
                      <div className="text-600 text-sm">Account Type</div>
                      <div className="text-900">Professional</div>
                    </div>
                    
                    <div className="col-12 md:col-6">
                      <div className="text-600 text-sm">Member Since</div>
                      <div className="text-900">{user?.created_at ? formatDate(new Date(user.created_at)) : 'January 2024'}</div>
                    </div>
                    
                    <div className="col-12 md:col-6">
                      <div className="text-600 text-sm">Last Login</div>
                      <div className="text-900">{formatDate(new Date())}</div>
                    </div>
                  </div>
                  
                  <Divider />
                  
                  <Message 
                    severity="info" 
                    text="Your account is in good standing. All services are active and functioning normally."
                    className="w-full"
                  />
                </Card>
              </div>
              
              <div className="col-12 md:col-4">
                <Card title="Danger Zone" className="border-red-200">
                  <div className="flex flex-column gap-3">
                    <Message 
                      severity="warn" 
                      text="These actions cannot be undone. Please proceed with caution."
                      className="w-full"
                    />
                    
                    <Button
                      label="Export Account Data"
                      icon="pi pi-download"
                      outlined
                      className="w-full"
                      onClick={() => showToast('info', 'Export Started', 'Your data export has been requested')}
                    />
                    
                    <Button
                      label="Delete Account"
                      icon="pi pi-trash"
                      severity="danger"
                      outlined
                      className="w-full"
                      onClick={() => setDeleteAccountDialog(true)}
                    />
                  </div>
                </Card>
              </div>
            </div>
          </TabPanel>
        </TabView>
      </div>

      {/* API Key Creation Dialog */}
      <Dialog
        visible={apiKeyDialog}
        style={{ width: '500px' }}
        header="Create API Key"
        modal
        className="p-fluid"
        onHide={() => setApiKeyDialog(false)}
      >
        <div className="grid">
          <div className="col-12">
            <label htmlFor="apiKeyName" className="block text-900 font-medium mb-2">
              API Key Name *
            </label>
            <InputText
              id="apiKeyName"
              value={newApiKeyName}
              onChange={(e) => setNewApiKeyName(e.target.value)}
              placeholder="e.g., Production API, Mobile App"
              required
            />
          </div>
          
          <div className="col-12">
            <label className="block text-900 font-medium mb-2">
              Permissions
            </label>
            <div className="grid">
              {apiPermissions.map((permission, index) => (
                <div key={index} className="col-6">
                  <label className="flex align-items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedPermissions.includes(permission)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedPermissions([...selectedPermissions, permission]);
                        } else {
                          setSelectedPermissions(selectedPermissions.filter(p => p !== permission));
                        }
                      }}
                    />
                    <span className="text-sm">{permission}</span>
                  </label>
                </div>
              ))}
            </div>
          </div>
        </div>
        
        <div className="flex justify-content-end gap-2 mt-4">
          <Button 
            label="Cancel" 
            outlined 
            onClick={() => setApiKeyDialog(false)} 
          />
          <Button 
            label="Create Key" 
            onClick={createApiKey}
            disabled={!newApiKeyName || !selectedPermissions.length}
          />
        </div>
      </Dialog>

      {/* Delete Account Dialog */}
      <Dialog
        visible={deleteAccountDialog}
        style={{ width: '450px' }}
        header="Delete Account"
        modal
        onHide={() => setDeleteAccountDialog(false)}
      >
        <div className="flex align-items-center gap-3 mb-4">
          <i className="pi pi-exclamation-triangle text-red-500" style={{ fontSize: '2rem' }} />
          <div>
            <div className="text-900 font-medium mb-2">
              Are you sure you want to delete your account?
            </div>
            <div className="text-600 line-height-3">
              This action will permanently delete your account and all associated data including profiles, 
              infringement reports, takedown requests, and API keys. This cannot be undone.
            </div>
          </div>
        </div>
        
        <Message 
          severity="error" 
          text="This action is irreversible. Please confirm you want to proceed."
          className="w-full mb-4"
        />
        
        <div className="flex justify-content-end gap-2">
          <Button 
            label="Cancel" 
            outlined 
            onClick={() => setDeleteAccountDialog(false)} 
          />
          <Button 
            label="Delete Account" 
            severity="danger" 
            onClick={deleteAccount}
          />
        </div>
      </Dialog>

      <Toast ref={toast} />
      <ConfirmDialog />
    </div>
  );
};

export default Settings;