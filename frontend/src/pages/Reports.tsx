import React from 'react';
import ComingSoon from '../components/common/ComingSoon';

const Reports: React.FC = () => {
  return (
    <ComingSoon 
      featureName="Advanced Reports & Analytics"
      description="Comprehensive reporting dashboard with detailed analytics, ROI analysis, and customizable report generation."
      icon="pi-chart-bar"
      expectedDate="Q3 2024"
    />
  );
};

export default Reports;