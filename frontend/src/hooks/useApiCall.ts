import React, { useState, useCallback, useRef } from 'react';
import { ApiErrorHandler, useApiErrorHandler, withRetry, type ApiError } from '../utils/apiErrorHandler';

interface UseApiCallOptions {
  enableRetry?: boolean;
  maxRetries?: number;
  showComingSoonForNotImplemented?: boolean;
  onError?: (error: ApiError) => void;
  onSuccess?: (data: any) => void;
}

interface UseApiCallResult<T> {
  data: T | null;
  loading: boolean;
  error: ApiError | null;
  execute: (...args: any[]) => Promise<T | null>;
  reset: () => void;
  isFeatureNotAvailable: boolean;
}

export function useApiCall<T = any>(
  apiFunction: (...args: any[]) => Promise<T>,
  options: UseApiCallOptions = {}
): UseApiCallResult<T> {
  const {
    enableRetry = true,
    maxRetries = 3,
    showComingSoonForNotImplemented = true,
    onError,
    onSuccess
  } = options;

  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const cancelRef = useRef<boolean>(false);
  
  const { handleError, isFeatureNotAvailable } = useApiErrorHandler();

  const execute = useCallback(async (...args: any[]): Promise<T | null> => {
    if (loading) return null;

    setLoading(true);
    setError(null);
    cancelRef.current = false;

    try {
      const apiCall = () => apiFunction(...args);
      const result = enableRetry ? await withRetry(apiCall, maxRetries) : await apiCall();
      
      if (!cancelRef.current) {
        setData(result);
        onSuccess?.(result);
      }
      
      return result;
    } catch (err) {
      if (!cancelRef.current) {
        const apiError = handleError(err);
        setError(apiError);
        onError?.(apiError);
      }
      return null;
    } finally {
      if (!cancelRef.current) {
        setLoading(false);
      }
    }
  }, [apiFunction, enableRetry, maxRetries, loading, handleError, onError, onSuccess]);

  const reset = useCallback(() => {
    cancelRef.current = true;
    setData(null);
    setError(null);
    setLoading(false);
    cancelRef.current = false;
  }, []);

  const isFeatureNotAvailable = error ? isFeatureNotAvailable(error) : false;

  return {
    data,
    loading,
    error,
    execute,
    reset,
    isFeatureNotAvailable
  };
}

// Hook specifically for handling API calls that might not be implemented
export function useApiCallWithFallback<T = any>(
  apiFunction: (...args: any[]) => Promise<T>,
  fallbackData?: T,
  options: UseApiCallOptions = {}
) {
  const result = useApiCall(apiFunction, {
    ...options,
    showComingSoonForNotImplemented: true
  });

  // Return fallback data if the feature is not available
  const effectiveData = result.isFeatureNotAvailable && fallbackData !== undefined 
    ? fallbackData 
    : result.data;

  return {
    ...result,
    data: effectiveData
  };
}

// Hook for automatically executing API calls on mount
export function useApiCallOnMount<T = any>(
  apiFunction: () => Promise<T>,
  dependencies: any[] = [],
  options: UseApiCallOptions = {}
) {
  const result = useApiCall(apiFunction, options);

  React.useEffect(() => {
    result.execute();
  }, dependencies);

  return result;
}