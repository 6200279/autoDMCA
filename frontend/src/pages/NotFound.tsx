import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from 'primereact/button';
import { Card } from 'primereact/card';

const NotFound: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex align-items-center justify-content-center bg-gray-50">
      <Card className="w-full max-w-md">
        <div className="text-center">
          <div className="text-6xl font-bold text-primary mb-3">404</div>
          <h2 className="text-2xl text-900 mb-3">Page Not Found</h2>
          <p className="text-600 mb-4 line-height-3">
            The page you are looking for might have been removed, renamed, or is temporarily unavailable.
          </p>
          <div className="flex flex-column sm:flex-row gap-2">
            <Button 
              label="Go to Dashboard" 
              icon="pi pi-home" 
              onClick={() => navigate('/dashboard')}
              className="flex-1"
            />
            <Button 
              label="Go Back" 
              icon="pi pi-arrow-left" 
              outlined
              onClick={() => navigate(-1)}
              className="flex-1"
            />
          </div>
        </div>
      </Card>
    </div>
  );
};

export default NotFound;