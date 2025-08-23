import React from 'react';
import ComingSoon from '../components/common/ComingSoon';

const AdminPanel: React.FC = () => {
  return (
    <ComingSoon 
      featureName="Admin Panel"
      description="Comprehensive administrative interface for managing users, system settings, and platform configuration."
      icon="pi-cog"
      expectedDate="Q2 2024"
    />
  );
};

export default AdminPanel;