import React from 'react';
import ComingSoon from '../components/common/ComingSoon';

const Submissions: React.FC = () => {
  return (
    <ComingSoon 
      featureName="Content Submissions"
      description="Bulk content upload and submission system for protecting large volumes of creative works and intellectual property."
      icon="pi-upload"
      expectedDate="Q2 2024"
    />
  );
};

export default Submissions;