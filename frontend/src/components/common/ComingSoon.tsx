import React from 'react';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { Message } from 'primereact/message';
import { Divider } from 'primereact/divider';

interface ComingSoonProps {
  featureName: string;
  description?: string;
  icon?: string;
  expectedDate?: string;
  contactSupport?: boolean;
}

const ComingSoon: React.FC<ComingSoonProps> = ({ 
  featureName, 
  description, 
  icon = 'pi-wrench',
  expectedDate,
  contactSupport = true
}) => {
  return (
    <div className="flex justify-content-center align-items-center min-h-screen">
      <Card className="w-full max-w-600px">
        <div className="text-center">
          <i className={`pi ${icon} text-6xl text-blue-500 mb-3`}></i>
          <h1 className="text-3xl font-bold mb-3">{featureName}</h1>
          <h2 className="text-xl text-600 mb-4">Coming Soon!</h2>
          
          {description && (
            <p className="text-700 mb-4 line-height-3">
              {description}
            </p>
          )}
          
          <Message 
            severity="info" 
            text="This feature is currently under development and will be available in a future update."
            className="mb-4"
          />
          
          {expectedDate && (
            <div className="mb-4">
              <strong>Expected Release:</strong> {expectedDate}
            </div>
          )}
          
          <Divider />
          
          <div className="flex flex-column gap-3 align-items-center">
            <Button 
              label="Back to Dashboard" 
              icon="pi pi-home"
              onClick={() => window.location.href = '/dashboard'}
              className="p-button-primary"
            />
            
            {contactSupport && (
              <Button 
                label="Contact Support" 
                icon="pi pi-envelope"
                onClick={() => window.open('mailto:support@automdca.com', '_blank')}
                className="p-button-outlined"
                size="small"
              />
            )}
          </div>
        </div>
      </Card>
    </div>
  );
};

export default ComingSoon;