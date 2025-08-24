import { AxiosError } from 'axios';

export interface ApiError {
  message: string;
  status?: number;
  code?: string;
  isNetworkError?: boolean;
  isServerError?: boolean;
  isClientError?: boolean;
  isNotImplemented?: boolean;
}

export class ApiErrorHandler {
  static handle(error: any): ApiError {
    // Handle axios errors
    if (error.response) {
      const status = error.response.status;
      const message = error.response.data?.detail || error.response.data?.message || error.message;
      
      return {
        message: this.getFriendlyMessage(status, message),
        status,
        code: error.response.data?.code,
        isNetworkError: false,
        isServerError: status >= 500,
        isClientError: status >= 400 && status < 500,
        isNotImplemented: status === 501 || status === 404
      };
    }
    
    // Handle network errors
    if (error.request) {
      return {
        message: 'Unable to connect to server. Please check your internet connection.',
        isNetworkError: true,
        isServerError: false,
        isClientError: false,
        isNotImplemented: false
      };
    }
    
    // Handle other errors
    return {
      message: error.message || 'An unexpected error occurred',
      isNetworkError: false,
      isServerError: false,
      isClientError: false,
      isNotImplemented: false
    };
  }

  static getFriendlyMessage(status: number, originalMessage: string): string {
    switch (status) {
      case 400:
        return 'Invalid request. Please check your input and try again.';
      case 401:
        return 'You are not authorized to perform this action. Please log in again.';
      case 403:
        return 'You do not have permission to access this resource.';
      case 404:
        return 'This feature is not yet available. Please check back later.';
      case 500:
        return 'Server error occurred. Our team has been notified.';
      case 501:
        return 'This feature is currently under development.';
      case 502:
      case 503:
      case 504:
        return 'Service temporarily unavailable. Please try again later.';
      default:
        return originalMessage || 'An unexpected error occurred';
    }
  }

  static isFeatureNotAvailable(error: ApiError): boolean {
    return error.isNotImplemented || 
           error.status === 404 || 
           error.status === 501 ||
           (error.message && error.message.toLowerCase().includes('not implemented'));
  }

  static shouldRetry(error: ApiError): boolean {
    return error.isNetworkError || 
           error.status === 502 || 
           error.status === 503 || 
           error.status === 504;
  }

  static getRetryDelay(attemptNumber: number): number {
    // Exponential backoff: 1s, 2s, 4s, 8s, 16s
    return Math.min(1000 * Math.pow(2, attemptNumber - 1), 16000);
  }
}

// Hook for handling API errors in React components
export const useApiErrorHandler = () => {
  const handleError = (error: any): ApiError => {
    const apiError = ApiErrorHandler.handle(error);
    
    // Log error for debugging (only in development)
    if (import.meta.env.DEV) {
      console.error('API Error:', {
        originalError: error,
        processedError: apiError
      });
    }
    
    return apiError;
  };

  const isFeatureNotAvailable = (error: ApiError): boolean => {
    return ApiErrorHandler.isFeatureNotAvailable(error);
  };

  const shouldShowComingSoon = (error: ApiError): boolean => {
    return ApiErrorHandler.isFeatureNotAvailable(error);
  };

  return {
    handleError,
    isFeatureNotAvailable,
    shouldShowComingSoon
  };
};

// Retry wrapper for API calls
export const withRetry = async <T>(
  apiCall: () => Promise<T>,
  maxRetries: number = 3
): Promise<T> => {
  let lastError: any;
  
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await apiCall();
    } catch (error) {
      lastError = error;
      const apiError = ApiErrorHandler.handle(error);
      
      if (!ApiErrorHandler.shouldRetry(apiError) || attempt === maxRetries) {
        throw error;
      }
      
      const delay = ApiErrorHandler.getRetryDelay(attempt);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
  
  throw lastError;
};