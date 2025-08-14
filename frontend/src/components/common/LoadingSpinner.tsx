import React from 'react';
import { ProgressSpinner } from 'primereact/progressspinner';

interface LoadingSpinnerProps {
  message?: string;
  size?: 'small' | 'medium' | 'large';
  fullScreen?: boolean;
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  message = 'Loading...',
  size = 'medium',
  fullScreen = false
}) => {
  const sizeMap = {
    small: '2rem',
    medium: '3rem',
    large: '4rem'
  };

  const spinnerSize = sizeMap[size];

  const spinnerContent = (
    <div className="flex flex-column align-items-center justify-content-center gap-3">
      <ProgressSpinner 
        style={{ width: spinnerSize, height: spinnerSize }} 
        strokeWidth="4"
        animationDuration=".8s"
      />
      {message && (
        <p className="text-600 text-center m-0 font-medium">
          {message}
        </p>
      )}
    </div>
  );

  if (fullScreen) {
    return (
      <div 
        className="fixed top-0 left-0 w-full h-full flex align-items-center justify-content-center bg-white bg-opacity-90 z-5"
        style={{ zIndex: 9999 }}
      >
        {spinnerContent}
      </div>
    );
  }

  return (
    <div className="flex align-items-center justify-content-center p-4">
      {spinnerContent}
    </div>
  );
};

export default LoadingSpinner;