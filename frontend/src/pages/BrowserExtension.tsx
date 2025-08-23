import React from 'react';
import ComingSoon from '../components/common/ComingSoon';

const BrowserExtension: React.FC = () => {
  return (
    <ComingSoon 
      featureName="Browser Extension"
      description="Chrome and Firefox browser extensions for automated content monitoring and one-click reporting of copyright infringements."
      icon="pi-globe"
      expectedDate="Q4 2024"
    />
  );
};

export default BrowserExtension;