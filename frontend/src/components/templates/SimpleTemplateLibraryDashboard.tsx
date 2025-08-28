import React from 'react';
import { Button } from 'primereact/button';
import { Card } from 'primereact/card';

interface SimpleTemplateLibraryDashboardProps {
  onTemplateEdit?: (template: any) => void;
  onTemplateCreate?: () => void;
  onTemplateView?: (template: any) => void;
}

const SimpleTemplateLibraryDashboard: React.FC<SimpleTemplateLibraryDashboardProps> = ({
  onTemplateCreate,
  onTemplateEdit,
  onTemplateView
}) => {
  return (
    <div className="simple-template-dashboard">
      <div className="flex justify-content-between align-items-center mb-4">
        <h1>DMCA Templates</h1>
        <Button
          label="Create Template"
          icon="pi pi-plus"
          onClick={onTemplateCreate}
        />
      </div>

      <div className="grid">
        <div className="col-12 md:col-6 lg:col-4">
          <Card 
            title="Sample Template 1"
            subTitle="Standard DMCA Notice"
            className="mb-3"
          >
            <p>A basic DMCA takedown notice template for general use.</p>
            <div className="flex gap-2">
              <Button 
                label="View" 
                icon="pi pi-eye" 
                onClick={() => onTemplateView?.({ id: '1', name: 'Sample Template 1' })}
                size="small"
              />
              <Button 
                label="Edit" 
                icon="pi pi-pencil" 
                onClick={() => onTemplateEdit?.({ id: '1', name: 'Sample Template 1' })}
                outlined
                size="small"
              />
            </div>
          </Card>
        </div>

        <div className="col-12 md:col-6 lg:col-4">
          <Card 
            title="Sample Template 2"
            subTitle="Image Copyright"
            className="mb-3"
          >
            <p>Specialized template for image copyright infringement.</p>
            <div className="flex gap-2">
              <Button 
                label="View" 
                icon="pi pi-eye" 
                onClick={() => onTemplateView?.({ id: '2', name: 'Sample Template 2' })}
                size="small"
              />
              <Button 
                label="Edit" 
                icon="pi pi-pencil" 
                onClick={() => onTemplateEdit?.({ id: '2', name: 'Sample Template 2' })}
                outlined
                size="small"
              />
            </div>
          </Card>
        </div>

        <div className="col-12 md:col-6 lg:col-4">
          <Card 
            title="Sample Template 3"
            subTitle="Video Content"
            className="mb-3"
          >
            <p>Template for video content takedown requests.</p>
            <div className="flex gap-2">
              <Button 
                label="View" 
                icon="pi pi-eye" 
                onClick={() => onTemplateView?.({ id: '3', name: 'Sample Template 3' })}
                size="small"
              />
              <Button 
                label="Edit" 
                icon="pi pi-pencil" 
                onClick={() => onTemplateEdit?.({ id: '3', name: 'Sample Template 3' })}
                outlined
                size="small"
              />
            </div>
          </Card>
        </div>
      </div>

      <div className="mt-4 text-center">
        <p className="text-600">
          This is a simplified template library dashboard. The enhanced version with advanced features 
          will be available once all components are properly configured.
        </p>
      </div>
    </div>
  );
};

export default SimpleTemplateLibraryDashboard;