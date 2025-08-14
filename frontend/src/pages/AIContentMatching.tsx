import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Card } from 'primereact/card';
import { TabView, TabPanel } from 'primereact/tabview';
import { FileUpload, FileUploadHandlerEvent } from 'primereact/fileupload';
import { Slider } from 'primereact/slider';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { ProgressBar } from 'primereact/progressbar';
import { Dialog } from 'primereact/dialog';
import { Chart } from 'primereact/chart';
import { Button } from 'primereact/button';
import { InputText } from 'primereact/inputtext';
import { InputTextarea } from 'primereact/inputtextarea';
import { Dropdown } from 'primereact/dropdown';
import { Tag } from 'primereact/tag';
import { Badge } from 'primereact/badge';
import { Toast } from 'primereact/toast';
import { ConfirmDialog, confirmDialog } from 'primereact/confirmdialog';
import { Panel } from 'primereact/panel';
import { Divider } from 'primereact/divider';
import { InputNumber } from 'primereact/inputnumber';
import { SelectButton } from 'primereact/selectbutton';
import { ToggleButton } from 'primereact/togglebutton';
import { Checkbox } from 'primereact/checkbox';
import { Message } from 'primereact/message';
import { Steps } from 'primereact/steps';
import { MenuItem } from 'primereact/menuitem';
import { Skeleton } from 'primereact/skeleton';
import { 
  Chart as ChartJS, 
  CategoryScale, 
  LinearScale, 
  PointElement, 
  LineElement, 
  Title, 
  Tooltip as ChartTooltip, 
  Legend,
  ArcElement,
  BarElement
} from 'chart.js';
import { useAuth } from '../contexts/AuthContext';
import { aiContentMatchingApi } from '../services/api';
import {
  AIModel,
  CreateAIModel,
  AIModelType,
  AIModelStatus,
  TrainingData,
  TrainingDataType,
  TrainingDataStatus,
  ModelTraining,
  TrainingJobStatus,
  DetectionResult,
  DetectionMatchType,
  ContentFingerprint,
  AIGlobalSettings,
  ModelPerformanceMetrics,
  BatchJob,
  RealTimeDetectionStatus,
  ApiResponse,
  PaginatedResponse
} from '../types/api';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  ChartTooltip,
  Legend
);

// Loading states interface
interface LoadingStates {
  models: boolean;
  trainingData: boolean;
  trainingJobs: boolean;
  detectionResults: boolean;
  globalSettings: boolean;
  performanceMetrics: boolean;
  fileUpload: boolean;
  modelCreation: boolean;
  modelUpdate: boolean;
}

// Error states interface
interface ErrorStates {
  models: string | null;
  trainingData: string | null;
  trainingJobs: string | null;
  detectionResults: string | null;
  globalSettings: string | null;
  performanceMetrics: string | null;
}

// File upload progress tracking
interface FileUploadProgress {
  [key: string]: {
    progress: number;
    status: 'uploading' | 'completed' | 'failed';
    error?: string;
  };
}

const AIContentMatching: React.FC = () => {
  const { user } = useAuth();
  const toast = useRef<Toast>(null);
  const [activeIndex, setActiveIndex] = useState(0);
  const refreshIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Loading states
  const [loading, setLoading] = useState<LoadingStates>({
    models: true,
    trainingData: true,
    trainingJobs: true,
    detectionResults: true,
    globalSettings: true,
    performanceMetrics: true,
    fileUpload: false,
    modelCreation: false,
    modelUpdate: false
  });

  // Error states
  const [errors, setErrors] = useState<ErrorStates>({
    models: null,
    trainingData: null,
    trainingJobs: null,
    detectionResults: null,
    globalSettings: null,
    performanceMetrics: null
  });

  // State for AI Models
  const [models, setModels] = useState<AIModel[]>([]);
  const [selectedModel, setSelectedModel] = useState<AIModel | null>(null);
  const [modelDialogVisible, setModelDialogVisible] = useState(false);
  const [trainingData, setTrainingData] = useState<TrainingData[]>([]);
  const [currentTraining, setCurrentTraining] = useState<ModelTraining[]>([]);
  const [detectionResults, setDetectionResults] = useState<DetectionResult[]>([]);
  const [performanceMetrics, setPerformanceMetrics] = useState<ModelPerformanceMetrics[]>([]);
  const [realTimeStatus, setRealTimeStatus] = useState<RealTimeDetectionStatus | null>(null);

  // State for Configuration
  const [globalSettings, setGlobalSettings] = useState<AIGlobalSettings>({
    auto_training: true,
    batch_processing: true,
    real_time_detection: false,
    notification_threshold: 85,
    max_concurrent_trainings: 2,
    data_retention_days: 90,
    processing_settings: {
      max_file_size: 50000000,
      supported_formats: ['jpg', 'jpeg', 'png', 'mp4', 'mov', 'avi'],
      timeout_seconds: 300,
      queue_priority: 'priority'
    },
    performance_settings: {
      gpu_acceleration: true,
      batch_size: 32,
      model_cache_size: 1024,
      parallel_processing: true
    }
  });

  // State for Model Creation
  const [newModelDialogVisible, setNewModelDialogVisible] = useState(false);
  const [newModelStep, setNewModelStep] = useState(0);
  const [newModel, setNewModel] = useState<CreateAIModel>({
    name: '',
    type: AIModelType.FACE_RECOGNITION,
    description: '',
    confidence_threshold: 80
  });

  // File upload progress
  const [fileUploadProgress, setFileUploadProgress] = useState<FileUploadProgress>({});
  const [selectedDataType, setSelectedDataType] = useState<TrainingDataType>(TrainingDataType.REFERENCE);

  // Pagination states
  const [modelsPagination, setModelsPagination] = useState({
    page: 1,
    per_page: 10,
    total: 0,
    pages: 0
  });

  const [detectionPagination, setDetectionPagination] = useState({
    page: 1,
    per_page: 10,
    total: 0,
    pages: 0
  });

  // Fetch functions
  const fetchModels = useCallback(async (page = 1) => {
    try {
      setLoading(prev => ({ ...prev, models: true }));
      setErrors(prev => ({ ...prev, models: null }));

      const response = await aiContentMatchingApi.getModels({
        page,
        per_page: modelsPagination.per_page
      });

      if (response.data.items) {
        // Paginated response
        setModels(response.data.items);
        setModelsPagination({
          page: response.data.page,
          per_page: response.data.per_page,
          total: response.data.total,
          pages: response.data.pages
        });
      } else {
        // Simple array response
        setModels(response.data);
      }
    } catch (error: any) {
      console.error('Failed to fetch AI models:', error);
      setErrors(prev => ({ ...prev, models: error.response?.data?.detail || 'Failed to fetch AI models' }));
      toast.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: 'Failed to fetch AI models',
        life: 5000
      });
    } finally {
      setLoading(prev => ({ ...prev, models: false }));
    }
  }, [modelsPagination.per_page]);

  const fetchTrainingData = useCallback(async () => {
    try {
      setLoading(prev => ({ ...prev, trainingData: true }));
      setErrors(prev => ({ ...prev, trainingData: null }));

      const response = await aiContentMatchingApi.getTrainingData({
        limit: 100
      });

      setTrainingData(response.data.items || response.data);
    } catch (error: any) {
      console.error('Failed to fetch training data:', error);
      setErrors(prev => ({ ...prev, trainingData: error.response?.data?.detail || 'Failed to fetch training data' }));
      toast.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: 'Failed to fetch training data',
        life: 5000
      });
    } finally {
      setLoading(prev => ({ ...prev, trainingData: false }));
    }
  }, []);

  const fetchTrainingJobs = useCallback(async () => {
    try {
      setLoading(prev => ({ ...prev, trainingJobs: true }));
      setErrors(prev => ({ ...prev, trainingJobs: null }));

      const response = await aiContentMatchingApi.getTrainingJobs({
        status: 'running,queued',
        limit: 50
      });

      setCurrentTraining(response.data.items || response.data);
    } catch (error: any) {
      console.error('Failed to fetch training jobs:', error);
      setErrors(prev => ({ ...prev, trainingJobs: error.response?.data?.detail || 'Failed to fetch training jobs' }));
    } finally {
      setLoading(prev => ({ ...prev, trainingJobs: false }));
    }
  }, []);

  const fetchDetectionResults = useCallback(async (page = 1) => {
    try {
      setLoading(prev => ({ ...prev, detectionResults: true }));
      setErrors(prev => ({ ...prev, detectionResults: null }));

      const response = await aiContentMatchingApi.getDetectionResults({
        page,
        per_page: detectionPagination.per_page,
        sort: '-detected_at'
      });

      if (response.data.items) {
        setDetectionResults(response.data.items);
        setDetectionPagination({
          page: response.data.page,
          per_page: response.data.per_page,
          total: response.data.total,
          pages: response.data.pages
        });
      } else {
        setDetectionResults(response.data);
      }
    } catch (error: any) {
      console.error('Failed to fetch detection results:', error);
      setErrors(prev => ({ ...prev, detectionResults: error.response?.data?.detail || 'Failed to fetch detection results' }));
    } finally {
      setLoading(prev => ({ ...prev, detectionResults: false }));
    }
  }, [detectionPagination.per_page]);

  const fetchGlobalSettings = useCallback(async () => {
    try {
      setLoading(prev => ({ ...prev, globalSettings: true }));
      setErrors(prev => ({ ...prev, globalSettings: null }));

      const response = await aiContentMatchingApi.getGlobalSettings();
      setGlobalSettings(response.data);
    } catch (error: any) {
      console.error('Failed to fetch global settings:', error);
      setErrors(prev => ({ ...prev, globalSettings: error.response?.data?.detail || 'Failed to fetch global settings' }));
    } finally {
      setLoading(prev => ({ ...prev, globalSettings: false }));
    }
  }, []);

  const fetchPerformanceMetrics = useCallback(async () => {
    try {
      setLoading(prev => ({ ...prev, performanceMetrics: true }));
      setErrors(prev => ({ ...prev, performanceMetrics: null }));

      const response = await aiContentMatchingApi.getPerformanceMetrics();
      if (Array.isArray(response.data)) {
        setPerformanceMetrics(response.data);
      } else {
        setPerformanceMetrics([response.data]);
      }
    } catch (error: any) {
      console.error('Failed to fetch performance metrics:', error);
      setErrors(prev => ({ ...prev, performanceMetrics: error.response?.data?.detail || 'Failed to fetch performance metrics' }));
    } finally {
      setLoading(prev => ({ ...prev, performanceMetrics: false }));
    }
  }, []);

  const fetchRealTimeStatus = useCallback(async () => {
    try {
      const response = await aiContentMatchingApi.getRealTimeStatus();
      setRealTimeStatus(response.data);
    } catch (error: any) {
      console.error('Failed to fetch real-time status:', error);
    }
  }, []);

  // Initial data load
  useEffect(() => {
    fetchModels();
    fetchTrainingData();
    fetchTrainingJobs();
    fetchDetectionResults();
    fetchGlobalSettings();
    fetchPerformanceMetrics();
    fetchRealTimeStatus();
  }, [fetchModels, fetchTrainingData, fetchTrainingJobs, fetchDetectionResults, fetchGlobalSettings, fetchPerformanceMetrics, fetchRealTimeStatus]);

  // Real-time updates for training progress
  useEffect(() => {
    const interval = setInterval(() => {
      if (currentTraining.some(job => job.status === TrainingJobStatus.RUNNING)) {
        fetchTrainingJobs();
        fetchPerformanceMetrics();
      }
      if (globalSettings.real_time_detection) {
        fetchRealTimeStatus();
      }
    }, 5000);

    refreshIntervalRef.current = interval;
    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }
    };
  }, [currentTraining, globalSettings.real_time_detection, fetchTrainingJobs, fetchPerformanceMetrics, fetchRealTimeStatus]);

  // Event handlers
  const handleFileUpload = async (event: FileUploadHandlerEvent) => {
    if (!selectedModel) {
      toast.current?.show({
        severity: 'warn',
        summary: 'No Model Selected',
        detail: 'Please select a model before uploading training data',
        life: 3000
      });
      return;
    }

    const files = event.files;
    if (files.length === 0) return;

    try {
      setLoading(prev => ({ ...prev, fileUpload: true }));

      // Initialize progress tracking
      const progressTracking: FileUploadProgress = {};
      files.forEach(file => {
        progressTracking[file.name] = {
          progress: 0,
          status: 'uploading'
        };
      });
      setFileUploadProgress(progressTracking);

      // Upload files
      const response = await aiContentMatchingApi.uploadTrainingData(
        selectedModel.id,
        files,
        selectedDataType
      );

      // Update progress to completed
      const completedProgress: FileUploadProgress = {};
      files.forEach(file => {
        completedProgress[file.name] = {
          progress: 100,
          status: 'completed'
        };
      });
      setFileUploadProgress(completedProgress);

      toast.current?.show({
        severity: 'success',
        summary: 'Upload Successful',
        detail: `${files.length} training files uploaded successfully`,
        life: 3000
      });

      // Refresh training data
      fetchTrainingData();
    } catch (error: any) {
      console.error('File upload failed:', error);
      
      // Update progress to failed
      const failedProgress: FileUploadProgress = {};
      files.forEach(file => {
        failedProgress[file.name] = {
          progress: 0,
          status: 'failed',
          error: error.response?.data?.detail || 'Upload failed'
        };
      });
      setFileUploadProgress(failedProgress);

      toast.current?.show({
        severity: 'error',
        summary: 'Upload Failed',
        detail: error.response?.data?.detail || 'Failed to upload training files',
        life: 5000
      });
    } finally {
      setLoading(prev => ({ ...prev, fileUpload: false }));
      
      // Clear progress after 3 seconds
      setTimeout(() => {
        setFileUploadProgress({});
      }, 3000);
    }
  };

  const handleModelTraining = async (modelId: string) => {
    confirmDialog({
      message: 'Are you sure you want to start training this model? This process may take several hours.',
      header: 'Start Model Training',
      icon: 'pi pi-exclamation-triangle',
      acceptClassName: 'p-button-info',
      accept: async () => {
        try {
          await aiContentMatchingApi.trainModel(modelId);
          
          toast.current?.show({
            severity: 'info',
            summary: 'Training Started',
            detail: 'Model training has been queued and will begin shortly',
            life: 3000
          });

          // Refresh training jobs and models
          fetchTrainingJobs();
          fetchModels();
        } catch (error: any) {
          console.error('Failed to start model training:', error);
          toast.current?.show({
            severity: 'error',
            summary: 'Training Failed',
            detail: error.response?.data?.detail || 'Failed to start model training',
            life: 5000
          });
        }
      }
    });
  };

  const handleThresholdChange = async (modelId: string, threshold: number) => {
    try {
      setLoading(prev => ({ ...prev, modelUpdate: true }));

      await aiContentMatchingApi.updateModel(modelId, {
        confidence_threshold: threshold
      });

      // Update local state
      setModels(prev => prev.map(model => 
        model.id === modelId 
          ? { ...model, confidence_threshold: threshold }
          : model
      ));

      toast.current?.show({
        severity: 'success',
        summary: 'Settings Updated',
        detail: 'Confidence threshold updated successfully',
        life: 3000
      });
    } catch (error: any) {
      console.error('Failed to update threshold:', error);
      toast.current?.show({
        severity: 'error',
        summary: 'Update Failed',
        detail: error.response?.data?.detail || 'Failed to update confidence threshold',
        life: 5000
      });
      
      // Revert local state
      fetchModels();
    } finally {
      setLoading(prev => ({ ...prev, modelUpdate: false }));
    }
  };

  const handleModelStatusToggle = async (modelId: string) => {
    const model = models.find(m => m.id === modelId);
    if (!model) return;

    try {
      setLoading(prev => ({ ...prev, modelUpdate: true }));

      if (model.status === AIModelStatus.ACTIVE) {
        await aiContentMatchingApi.deactivateModel(modelId);
      } else {
        await aiContentMatchingApi.activateModel(modelId);
      }

      toast.current?.show({
        severity: 'success',
        summary: 'Status Updated',
        detail: `Model ${model.status === AIModelStatus.ACTIVE ? 'deactivated' : 'activated'} successfully`,
        life: 3000
      });

      // Refresh models
      fetchModels();
    } catch (error: any) {
      console.error('Failed to toggle model status:', error);
      toast.current?.show({
        severity: 'error',
        summary: 'Update Failed',
        detail: error.response?.data?.detail || 'Failed to update model status',
        life: 5000
      });
    } finally {
      setLoading(prev => ({ ...prev, modelUpdate: false }));
    }
  };

  const handleDetectionFeedback = async (resultId: string, feedback: 'correct' | 'incorrect') => {
    try {
      await aiContentMatchingApi.provideFeedback(resultId, feedback);
      
      // Update local state
      setDetectionResults(prev => prev.map(result =>
        result.id === resultId
          ? { ...result, reviewer_feedback: feedback, is_verified: true }
          : result
      ));
      
      toast.current?.show({
        severity: 'success',
        summary: 'Feedback Recorded',
        detail: 'Thank you for helping improve our AI models',
        life: 3000
      });
    } catch (error: any) {
      console.error('Failed to provide feedback:', error);
      toast.current?.show({
        severity: 'error',
        summary: 'Feedback Failed',
        detail: error.response?.data?.detail || 'Failed to record feedback',
        life: 5000
      });
    }
  };

  const handleCreateModel = async () => {
    try {
      setLoading(prev => ({ ...prev, modelCreation: true }));

      const response = await aiContentMatchingApi.createModel(newModel);
      
      toast.current?.show({
        severity: 'success',
        summary: 'Model Created',
        detail: 'New AI model has been created successfully',
        life: 3000
      });

      setNewModelDialogVisible(false);
      setNewModelStep(0);
      setNewModel({
        name: '',
        type: AIModelType.FACE_RECOGNITION,
        description: '',
        confidence_threshold: 80
      });

      // Refresh models
      fetchModels();
    } catch (error: any) {
      console.error('Failed to create model:', error);
      toast.current?.show({
        severity: 'error',
        summary: 'Creation Failed',
        detail: error.response?.data?.detail || 'Failed to create AI model',
        life: 5000
      });
    } finally {
      setLoading(prev => ({ ...prev, modelCreation: false }));
    }
  };

  const handleSaveGlobalSettings = async () => {
    try {
      await aiContentMatchingApi.updateGlobalSettings(globalSettings);
      
      toast.current?.show({
        severity: 'success',
        summary: 'Settings Saved',
        detail: 'Global settings updated successfully',
        life: 3000
      });
    } catch (error: any) {
      console.error('Failed to save settings:', error);
      toast.current?.show({
        severity: 'error',
        summary: 'Save Failed',
        detail: error.response?.data?.detail || 'Failed to save settings',
        life: 5000
      });
      
      // Revert to previous settings
      fetchGlobalSettings();
    }
  };

  // Chart configurations
  const getModelPerformanceData = () => {
    if (models.length === 0) return { labels: [], datasets: [] };

    const labels = models.map(m => m.name);
    return {
      labels,
      datasets: [
        {
          label: 'Accuracy (%)',
          data: models.map(m => m.accuracy),
          backgroundColor: 'rgba(54, 162, 235, 0.6)',
          borderColor: 'rgba(54, 162, 235, 1)',
          borderWidth: 1
        },
        {
          label: 'Processing Speed (img/s)',
          data: models.map(m => m.performance_metrics.processing_speed),
          backgroundColor: 'rgba(75, 192, 192, 0.6)',
          borderColor: 'rgba(75, 192, 192, 1)',
          borderWidth: 1
        }
      ]
    };
  };

  const getConfidenceDistributionData = () => {
    if (detectionResults.length === 0) {
      return {
        labels: ['0-20%', '21-40%', '41-60%', '61-80%', '81-100%'],
        datasets: [{
          data: [0, 0, 0, 0, 0],
          backgroundColor: ['#FF6384', '#FF9F40', '#FFCD56', '#4BC0C0', '#36A2EB'],
          borderWidth: 1
        }]
      };
    }

    const bins = [0, 0, 0, 0, 0];
    detectionResults.forEach(result => {
      const score = result.confidence_score;
      if (score <= 20) bins[0]++;
      else if (score <= 40) bins[1]++;
      else if (score <= 60) bins[2]++;
      else if (score <= 80) bins[3]++;
      else bins[4]++;
    });
    
    return {
      labels: ['0-20%', '21-40%', '41-60%', '61-80%', '81-100%'],
      datasets: [{
        data: bins,
        backgroundColor: ['#FF6384', '#FF9F40', '#FFCD56', '#4BC0C0', '#36A2EB'],
        borderWidth: 1
      }]
    };
  };

  const getTrainingProgressData = () => {
    const training = currentTraining.find(t => t.status === TrainingJobStatus.RUNNING);
    if (!training || !performanceMetrics.length) return null;

    const model = models.find(m => m.id === training.model_id);
    const metrics = performanceMetrics.find(m => m.model_id === training.model_id);
    
    if (!metrics || !metrics.performance_trends.length) return null;

    const labels = metrics.performance_trends.map(trend => new Date(trend.date).toLocaleDateString());
    const accuracyData = metrics.performance_trends.map(trend => trend.accuracy);
    const speedData = metrics.performance_trends.map(trend => trend.processing_speed);

    return {
      labels,
      datasets: [
        {
          label: 'Accuracy',
          data: accuracyData,
          borderColor: '#36A2EB',
          backgroundColor: 'rgba(54, 162, 235, 0.1)',
          yAxisID: 'y',
          tension: 0.4
        },
        {
          label: 'Processing Speed',
          data: speedData,
          borderColor: '#FF6384',
          backgroundColor: 'rgba(255, 99, 132, 0.1)',
          yAxisID: 'y1',
          tension: 0.4
        }
      ]
    };
  };

  // Component templates
  const modelStatusTemplate = (model: AIModel) => {
    const getSeverity = (status: AIModelStatus) => {
      switch (status) {
        case AIModelStatus.ACTIVE: return 'success';
        case AIModelStatus.TRAINING: return 'info';
        case AIModelStatus.ERROR: return 'danger';
        case AIModelStatus.UPDATING: return 'warning';
        default: return 'secondary';
      }
    };
    
    return <Tag value={model.status} severity={getSeverity(model.status)} />;
  };

  const modelTypeTemplate = (model: AIModel) => {
    const typeLabels = {
      [AIModelType.FACE_RECOGNITION]: 'Face Recognition',
      [AIModelType.IMAGE_MATCHING]: 'Image Matching',
      [AIModelType.VIDEO_ANALYSIS]: 'Video Analysis',
      [AIModelType.TEXT_DETECTION]: 'Text Detection',
      [AIModelType.AUDIO_FINGERPRINT]: 'Audio Fingerprint'
    };
    return <Badge value={typeLabels[model.type]} />;
  };

  const accuracyTemplate = (model: AIModel) => (
    <div className="flex align-items-center gap-2">
      <ProgressBar 
        value={model.accuracy} 
        showValue={false} 
        style={{ width: '100px', height: '8px' }}
        color={model.accuracy >= 90 ? '#10B981' : model.accuracy >= 80 ? '#F59E0B' : '#EF4444'}
      />
      <span className="text-sm font-medium">{model.accuracy.toFixed(1)}%</span>
    </div>
  );

  const thresholdTemplate = (model: AIModel) => (
    <div className="flex align-items-center gap-2">
      <Slider
        value={model.confidence_threshold}
        onChange={(e) => handleThresholdChange(model.id, e.value as number)}
        className="w-6rem"
        min={50}
        max={95}
        disabled={loading.modelUpdate}
      />
      <span className="text-sm">{model.confidence_threshold}%</span>
    </div>
  );

  const modelActionsTemplate = (model: AIModel) => (
    <div className="flex gap-1">
      <Button
        icon={model.status === AIModelStatus.ACTIVE ? 'pi pi-pause' : 'pi pi-play'}
        size="small"
        text
        tooltip={model.status === AIModelStatus.ACTIVE ? 'Deactivate' : 'Activate'}
        onClick={() => handleModelStatusToggle(model.id)}
        disabled={loading.modelUpdate || model.status === AIModelStatus.TRAINING}
        loading={loading.modelUpdate}
      />
      <Button
        icon="pi pi-cog"
        size="small"
        text
        tooltip="Configure"
        onClick={() => {
          setSelectedModel(model);
          setModelDialogVisible(true);
        }}
      />
      <Button
        icon="pi pi-refresh"
        size="small"
        text
        tooltip="Retrain"
        onClick={() => handleModelTraining(model.id)}
        disabled={model.status === AIModelStatus.TRAINING}
      />
    </div>
  );

  const detectionConfidenceTemplate = (result: DetectionResult) => (
    <div className="flex align-items-center gap-2">
      <ProgressBar 
        value={result.confidence_score} 
        showValue={false} 
        style={{ width: '80px', height: '6px' }}
        color={result.confidence_score >= 90 ? '#10B981' : 
               result.confidence_score >= 75 ? '#F59E0B' : '#EF4444'}
      />
      <span className="text-sm">{result.confidence_score.toFixed(1)}%</span>
    </div>
  );

  const detectionFeedbackTemplate = (result: DetectionResult) => {
    if (result.is_verified) {
      return (
        <Tag 
          value={result.reviewer_feedback} 
          severity={result.reviewer_feedback === 'correct' ? 'success' : 'danger'}
        />
      );
    }
    
    return (
      <div className="flex gap-1">
        <Button
          icon="pi pi-check"
          size="small"
          severity="success"
          text
          tooltip="Mark as Correct"
          onClick={() => handleDetectionFeedback(result.id, 'correct')}
        />
        <Button
          icon="pi pi-times"
          size="small"
          severity="danger"
          text
          tooltip="Mark as Incorrect"
          onClick={() => handleDetectionFeedback(result.id, 'incorrect')}
        />
      </div>
    );
  };

  const trainingDataStatusTemplate = (data: TrainingData) => {
    const getSeverity = (status: TrainingDataStatus) => {
      switch (status) {
        case TrainingDataStatus.VALIDATED: return 'success';
        case TrainingDataStatus.PROCESSING: return 'info';
        case TrainingDataStatus.REJECTED: return 'danger';
        case TrainingDataStatus.TRAINING: return 'warning';
        default: return 'secondary';
      }
    };
    
    return <Tag value={data.status} severity={getSeverity(data.status)} />;
  };

  const trainingDataTypeTemplate = (data: TrainingData) => {
    const getSeverity = (type: TrainingDataType) => {
      switch (type) {
        case TrainingDataType.REFERENCE: return 'success';
        case TrainingDataType.POSITIVE: return 'info';
        case TrainingDataType.NEGATIVE: return 'warning';
        default: return 'secondary';
      }
    };
    
    return <Tag value={data.type} severity={getSeverity(data.type)} />;
  };

  // New Model Creation Steps
  const modelCreationSteps: MenuItem[] = [
    { label: 'Basic Info' },
    { label: 'Training Data' },
    { label: 'Configuration' },
    { label: 'Review' }
  ];

  // Model type options
  const modelTypeOptions = [
    { label: 'Face Recognition', value: AIModelType.FACE_RECOGNITION },
    { label: 'Image Matching', value: AIModelType.IMAGE_MATCHING },
    { label: 'Video Analysis', value: AIModelType.VIDEO_ANALYSIS },
    { label: 'Text Detection', value: AIModelType.TEXT_DETECTION },
    { label: 'Audio Fingerprint', value: AIModelType.AUDIO_FINGERPRINT }
  ];

  // Data type options
  const dataTypeOptions = [
    { label: 'Reference Images (High Quality)', value: TrainingDataType.REFERENCE },
    { label: 'Positive Training Samples', value: TrainingDataType.POSITIVE },
    { label: 'Negative Training Samples', value: TrainingDataType.NEGATIVE }
  ];

  return (
    <div className="grid">
      <Toast ref={toast} />
      <ConfirmDialog />
      
      {/* Header */}
      <div className="col-12">
        <div className="flex flex-column md:flex-row md:justify-content-between md:align-items-center mb-4 gap-3">
          <div>
            <h2 className="m-0 text-900">AI Content Matching Configuration</h2>
            <p className="text-600 m-0 mt-1">Configure and monitor AI models for automated content detection</p>
            {realTimeStatus && (
              <div className="flex align-items-center gap-2 mt-2">
                <i className={`pi ${realTimeStatus.is_active ? 'pi-circle-fill text-green-500' : 'pi-circle text-gray-400'}`} />
                <span className="text-sm text-600">
                  Real-time detection: {realTimeStatus.is_active ? 'Active' : 'Inactive'}
                  {realTimeStatus.is_active && ` (${realTimeStatus.queue_size} in queue)`}
                </span>
              </div>
            )}
          </div>
          <div className="flex gap-2">
            <Button
              label="Create New Model"
              icon="pi pi-plus"
              onClick={() => setNewModelDialogVisible(true)}
            />
            <Button
              label="Batch Training"
              icon="pi pi-upload"
              outlined
            />
            <Button
              label="Export Settings"
              icon="pi pi-download"
              outlined
            />
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="col-12">
        <TabView activeIndex={activeIndex} onTabChange={(e) => setActiveIndex(e.index)}>
          
          {/* Model Management Tab */}
          <TabPanel header="Model Management" leftIcon="pi pi-cog">
            <div className="grid">
              {/* Model Overview Cards */}
              <div className="col-12 md:col-3">
                <Card className="h-full">
                  <div className="text-center">
                    <div className="bg-blue-100 text-blue-800 border-circle w-3rem h-3rem flex align-items-center justify-content-center mx-auto mb-3">
                      <i className="pi pi-eye text-xl" />
                    </div>
                    <div className="text-900 font-bold text-xl">
                      {loading.models ? <Skeleton width="3rem" height="2rem" /> : models.filter(m => m.status === AIModelStatus.ACTIVE).length}
                    </div>
                    <div className="text-600 text-sm">Active Models</div>
                  </div>
                </Card>
              </div>
              
              <div className="col-12 md:col-3">
                <Card className="h-full">
                  <div className="text-center">
                    <div className="bg-green-100 text-green-800 border-circle w-3rem h-3rem flex align-items-center justify-content-center mx-auto mb-3">
                      <i className="pi pi-chart-line text-xl" />
                    </div>
                    <div className="text-900 font-bold text-xl">
                      {loading.models ? <Skeleton width="4rem" height="2rem" /> : 
                        models.length > 0 ? (models.reduce((sum, m) => sum + m.accuracy, 0) / models.length).toFixed(1) + '%' : '0%'
                      }
                    </div>
                    <div className="text-600 text-sm">Avg Accuracy</div>
                  </div>
                </Card>
              </div>
              
              <div className="col-12 md:col-3">
                <Card className="h-full">
                  <div className="text-center">
                    <div className="bg-purple-100 text-purple-800 border-circle w-3rem h-3rem flex align-items-center justify-content-center mx-auto mb-3">
                      <i className="pi pi-refresh text-xl" />
                    </div>
                    <div className="text-900 font-bold text-xl">
                      {loading.trainingJobs ? <Skeleton width="2rem" height="2rem" /> : currentTraining.filter(t => t.status === TrainingJobStatus.RUNNING).length}
                    </div>
                    <div className="text-600 text-sm">Training</div>
                  </div>
                </Card>
              </div>
              
              <div className="col-12 md:col-3">
                <Card className="h-full">
                  <div className="text-center">
                    <div className="bg-orange-100 text-orange-800 border-circle w-3rem h-3rem flex align-items-center justify-content-center mx-auto mb-3">
                      <i className="pi pi-database text-xl" />
                    </div>
                    <div className="text-900 font-bold text-xl">
                      {loading.models ? <Skeleton width="5rem" height="2rem" /> : 
                        models.reduce((sum, m) => sum + m.training_data_count, 0).toLocaleString()
                      }
                    </div>
                    <div className="text-600 text-sm">Training Samples</div>
                  </div>
                </Card>
              </div>

              {/* Error Messages */}
              {errors.models && (
                <div className="col-12">
                  <Message severity="error" text={errors.models} />
                </div>
              )}

              {/* Models Table */}
              <div className="col-12">
                <Card title="AI Models" className="mt-4">
                  <DataTable 
                    value={models} 
                    paginator 
                    rows={modelsPagination.per_page}
                    totalRecords={modelsPagination.total}
                    lazy
                    first={(modelsPagination.page - 1) * modelsPagination.per_page}
                    onPage={(e) => fetchModels(Math.floor(e.first / e.rows) + 1)}
                    loading={loading.models}
                    showGridlines
                    emptyMessage="No AI models found"
                  >
                    <Column field="name" header="Model Name" sortable />
                    <Column field="type" header="Type" body={modelTypeTemplate} sortable />
                    <Column field="status" header="Status" body={modelStatusTemplate} sortable />
                    <Column field="version" header="Version" />
                    <Column field="accuracy" header="Accuracy" body={accuracyTemplate} sortable />
                    <Column field="confidence_threshold" header="Threshold" body={thresholdTemplate} />
                    <Column 
                      field="last_trained" 
                      header="Last Trained" 
                      body={(model: AIModel) => model.last_trained ? new Date(model.last_trained).toLocaleDateString() : 'Never'} 
                      sortable 
                    />
                    <Column body={modelActionsTemplate} style={{ width: '120px' }} />
                  </DataTable>
                </Card>
              </div>

              {/* Performance Charts */}
              <div className="col-12 lg:col-6">
                <Card title="Model Performance Comparison" className="mt-4">
                  <div style={{ height: '300px' }}>
                    {loading.models ? (
                      <Skeleton width="100%" height="300px" />
                    ) : (
                      <Chart 
                        type="bar" 
                        data={getModelPerformanceData()} 
                        options={{
                          responsive: true,
                          maintainAspectRatio: false,
                          plugins: {
                            legend: { position: 'top' }
                          }
                        }}
                        height="300px"
                      />
                    )}
                  </div>
                </Card>
              </div>

              <div className="col-12 lg:col-6">
                <Card title="Detection Confidence Distribution" className="mt-4">
                  <div style={{ height: '300px' }}>
                    {loading.detectionResults ? (
                      <Skeleton width="100%" height="300px" />
                    ) : (
                      <Chart 
                        type="doughnut" 
                        data={getConfidenceDistributionData()} 
                        options={{
                          responsive: true,
                          maintainAspectRatio: false,
                          plugins: {
                            legend: { position: 'right' }
                          }
                        }}
                        height="300px"
                      />
                    )}
                  </div>
                </Card>
              </div>
            </div>
          </TabPanel>

          {/* Training Data Tab */}
          <TabPanel header="Training Data" leftIcon="pi pi-upload">
            <div className="grid">
              {/* Upload Section */}
              <div className="col-12 lg:col-6">
                <Card title="Upload Training Data" className="h-full">
                  <div className="mb-4">
                    <label className="block text-900 font-medium mb-2">Select Model</label>
                    <Dropdown
                      value={selectedModel}
                      onChange={(e) => setSelectedModel(e.value)}
                      options={models.filter(m => m.status !== AIModelStatus.ERROR)}
                      optionLabel="name"
                      placeholder="Choose a model for training data"
                      className="w-full"
                      disabled={loading.models}
                    />
                  </div>

                  <div className="mb-4">
                    <label className="block text-900 font-medium mb-2">Data Type</label>
                    <Dropdown
                      value={selectedDataType}
                      onChange={(e) => setSelectedDataType(e.value)}
                      options={dataTypeOptions}
                      className="w-full"
                    />
                  </div>
                  
                  <FileUpload
                    name="training_files"
                    multiple
                    accept="image/*,video/*,audio/*"
                    maxFileSize={globalSettings.processing_settings.max_file_size}
                    customUpload
                    uploadHandler={handleFileUpload}
                    disabled={!selectedModel || loading.fileUpload}
                    emptyTemplate={
                      <div className="text-center">
                        <i className="pi pi-cloud-upload text-4xl text-400"></i>
                        <div className="text-600 mt-2">
                          Drag and drop training files here or click to browse
                        </div>
                        <div className="text-500 text-sm mt-1">
                          Supported: {globalSettings.processing_settings.supported_formats.join(', ').toUpperCase()} 
                          (Max {Math.floor(globalSettings.processing_settings.max_file_size / 1024 / 1024)}MB per file)
                        </div>
                      </div>
                    }
                  />

                  {/* File Upload Progress */}
                  {Object.keys(fileUploadProgress).length > 0 && (
                    <div className="mt-4">
                      <h6>Upload Progress</h6>
                      {Object.entries(fileUploadProgress).map(([fileName, progress]) => (
                        <div key={fileName} className="mb-2">
                          <div className="flex justify-content-between mb-1">
                            <span className="text-sm">{fileName}</span>
                            <Tag
                              value={progress.status}
                              severity={
                                progress.status === 'completed' ? 'success' :
                                progress.status === 'failed' ? 'danger' : 'info'
                              }
                            />
                          </div>
                          <ProgressBar
                            value={progress.progress}
                            color={progress.status === 'failed' ? '#ef4444' : undefined}
                          />
                          {progress.error && (
                            <div className="text-red-500 text-xs mt-1">{progress.error}</div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </Card>
              </div>

              {/* Training Status */}
              <div className="col-12 lg:col-6">
                <Card title="Training Status" className="h-full">
                  {loading.trainingJobs ? (
                    <Skeleton width="100%" height="200px" />
                  ) : currentTraining.length > 0 ? (
                    <div>
                      {currentTraining.map(training => (
                        <div key={training.id} className="mb-4 p-3 border-1 border-200 border-round">
                          <div className="flex justify-content-between align-items-center mb-2">
                            <span className="font-medium">
                              {models.find(m => m.id === training.model_id)?.name || 'Unknown Model'}
                            </span>
                            <Tag
                              value={training.status}
                              severity={
                                training.status === TrainingJobStatus.RUNNING ? 'info' :
                                training.status === TrainingJobStatus.COMPLETED ? 'success' :
                                training.status === TrainingJobStatus.FAILED ? 'danger' : 'warning'
                              }
                            />
                          </div>
                          <ProgressBar value={training.progress} showValue />
                          <div className="grid mt-3 text-sm">
                            <div className="col-6">
                              <div className="text-500">
                                Epochs: {training.training_metrics.epochs_completed}/{training.training_metrics.total_epochs}
                              </div>
                            </div>
                            <div className="col-6">
                              <div className="text-500">
                                Current Loss: {training.training_metrics.current_loss.toFixed(4)}
                              </div>
                            </div>
                            <div className="col-6">
                              <div className="text-500">
                                Best Accuracy: {(training.training_metrics.best_accuracy * 100).toFixed(1)}%
                              </div>
                            </div>
                            <div className="col-6">
                              <div className="text-500">
                                ETA: {training.estimated_completion ? new Date(training.estimated_completion).toLocaleTimeString() : 'Unknown'}
                              </div>
                            </div>
                          </div>
                          {training.error_message && (
                            <div className="mt-2 p-2 bg-red-50 border-round">
                              <span className="text-red-600 text-sm">{training.error_message}</span>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <Message severity="info" text="No training processes currently running" />
                  )}

                  {getTrainingProgressData() && (
                    <div className="mt-4">
                      <h5>Training Progress</h5>
                      <div style={{ height: '200px' }}>
                        <Chart 
                          type="line" 
                          data={getTrainingProgressData()!} 
                          options={{
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: {
                              y: {
                                type: 'linear',
                                display: true,
                                position: 'left',
                                min: 0,
                                max: 100
                              },
                              y1: {
                                type: 'linear',
                                display: true,
                                position: 'right',
                                min: 0,
                                grid: { drawOnChartArea: false }
                              }
                            }
                          }}
                          height="200px"
                        />
                      </div>
                    </div>
                  )}
                </Card>
              </div>

              {/* Error Messages */}
              {errors.trainingData && (
                <div className="col-12">
                  <Message severity="error" text={errors.trainingData} />
                </div>
              )}

              {/* Training Data Table */}
              <div className="col-12">
                <Card title="Training Data Management" className="mt-4">
                  <DataTable 
                    value={trainingData} 
                    paginator 
                    rows={10}
                    loading={loading.trainingData}
                    showGridlines
                    emptyMessage="No training data found"
                  >
                    <Column field="name" header="File Name" sortable />
                    <Column field="type" header="Type" body={trainingDataTypeTemplate} />
                    <Column 
                      field="file_size" 
                      header="Size" 
                      body={(data: TrainingData) => `${(data.file_size / 1024 / 1024).toFixed(1)} MB`}
                    />
                    <Column field="status" header="Status" body={trainingDataStatusTemplate} />
                    <Column 
                      field="validation_score" 
                      header="Quality Score" 
                      body={(data: TrainingData) => 
                        data.validation_score ? 
                          <Badge value={(data.validation_score * 100).toFixed(0) + '%'} severity="success" /> : 
                          <span className="text-500">-</span>
                      }
                    />
                    <Column 
                      field="upload_date" 
                      header="Uploaded" 
                      body={(data: TrainingData) => new Date(data.upload_date).toLocaleDateString()}
                      sortable 
                    />
                  </DataTable>
                </Card>
              </div>
            </div>
          </TabPanel>

          {/* Detection Results Tab */}
          <TabPanel header="Detection Results" leftIcon="pi pi-eye">
            <div className="grid">
              {/* Detection Stats */}
              <div className="col-12 md:col-3">
                <Card className="h-full">
                  <div className="text-center">
                    <div className="bg-blue-100 text-blue-800 border-circle w-3rem h-3rem flex align-items-center justify-content-center mx-auto mb-3">
                      <i className="pi pi-search text-xl" />
                    </div>
                    <div className="text-900 font-bold text-xl">
                      {loading.detectionResults ? <Skeleton width="3rem" height="2rem" /> : detectionPagination.total}
                    </div>
                    <div className="text-600 text-sm">Total Detections</div>
                  </div>
                </Card>
              </div>

              <div className="col-12 md:col-3">
                <Card className="h-full">
                  <div className="text-center">
                    <div className="bg-green-100 text-green-800 border-circle w-3rem h-3rem flex align-items-center justify-content-center mx-auto mb-3">
                      <i className="pi pi-check text-xl" />
                    </div>
                    <div className="text-900 font-bold text-xl">
                      {loading.detectionResults ? <Skeleton width="3rem" height="2rem" /> : 
                        detectionResults.filter(r => r.reviewer_feedback === 'correct').length
                      }
                    </div>
                    <div className="text-600 text-sm">True Positives</div>
                  </div>
                </Card>
              </div>

              <div className="col-12 md:col-3">
                <Card className="h-full">
                  <div className="text-center">
                    <div className="bg-red-100 text-red-800 border-circle w-3rem h-3rem flex align-items-center justify-content-center mx-auto mb-3">
                      <i className="pi pi-times text-xl" />
                    </div>
                    <div className="text-900 font-bold text-xl">
                      {loading.detectionResults ? <Skeleton width="3rem" height="2rem" /> : 
                        detectionResults.filter(r => r.reviewer_feedback === 'incorrect').length
                      }
                    </div>
                    <div className="text-600 text-sm">False Positives</div>
                  </div>
                </Card>
              </div>

              <div className="col-12 md:col-3">
                <Card className="h-full">
                  <div className="text-center">
                    <div className="bg-orange-100 text-orange-800 border-circle w-3rem h-3rem flex align-items-center justify-content-center mx-auto mb-3">
                      <i className="pi pi-clock text-xl" />
                    </div>
                    <div className="text-900 font-bold text-xl">
                      {loading.detectionResults ? <Skeleton width="3rem" height="2rem" /> : 
                        detectionResults.filter(r => !r.is_verified).length
                      }
                    </div>
                    <div className="text-600 text-sm">Pending Review</div>
                  </div>
                </Card>
              </div>

              {/* Error Messages */}
              {errors.detectionResults && (
                <div className="col-12">
                  <Message severity="error" text={errors.detectionResults} />
                </div>
              )}

              {/* Detection Results Table */}
              <div className="col-12">
                <Card title="Recent Detections" className="mt-4">
                  <DataTable 
                    value={detectionResults} 
                    paginator 
                    rows={detectionPagination.per_page}
                    totalRecords={detectionPagination.total}
                    lazy
                    first={(detectionPagination.page - 1) * detectionPagination.per_page}
                    onPage={(e) => fetchDetectionResults(Math.floor(e.first / e.rows) + 1)}
                    loading={loading.detectionResults}
                    showGridlines
                    emptyMessage="No detection results found"
                  >
                    <Column 
                      field="content_url" 
                      header="Content" 
                      body={(result: DetectionResult) => (
                        <a 
                          href={result.content_url} 
                          target="_blank" 
                          rel="noopener noreferrer" 
                          className="text-primary no-underline"
                        >
                          {result.content_url.split('/').pop()?.slice(0, 30)}...
                        </a>
                      )}
                    />
                    <Column field="confidence_score" header="Confidence" body={detectionConfidenceTemplate} sortable />
                    <Column 
                      field="match_type" 
                      header="Match Type" 
                      body={(result: DetectionResult) => (
                        <Tag 
                          value={result.match_type} 
                          severity={
                            result.match_type === DetectionMatchType.EXACT ? 'success' :
                            result.match_type === DetectionMatchType.SIMILAR ? 'info' : 'warning'
                          } 
                        />
                      )}
                    />
                    <Column 
                      field="detected_at" 
                      header="Detected" 
                      body={(result: DetectionResult) => new Date(result.detected_at).toLocaleString()}
                      sortable 
                    />
                    <Column field="is_verified" header="Feedback" body={detectionFeedbackTemplate} />
                  </DataTable>
                </Card>
              </div>
            </div>
          </TabPanel>

          {/* Configuration Tab */}
          <TabPanel header="Configuration" leftIcon="pi pi-sliders-h">
            <div className="grid">
              {/* Global Settings */}
              <div className="col-12 lg:col-6">
                <Card title="Global AI Settings" className="h-full">
                  {loading.globalSettings ? (
                    <Skeleton width="100%" height="400px" />
                  ) : (
                    <div className="flex flex-column gap-4">
                      <div className="flex align-items-center justify-content-between">
                        <div>
                          <label className="text-900 font-medium">Auto Training</label>
                          <div className="text-600 text-sm mt-1">Automatically retrain models with new data</div>
                        </div>
                        <ToggleButton
                          checked={globalSettings.auto_training}
                          onChange={(e) => setGlobalSettings(prev => ({ ...prev, auto_training: e.value }))}
                          onIcon="pi pi-check"
                          offIcon="pi pi-times"
                        />
                      </div>
                      
                      <div className="flex align-items-center justify-content-between">
                        <div>
                          <label className="text-900 font-medium">Batch Processing</label>
                          <div className="text-600 text-sm mt-1">Process multiple files simultaneously</div>
                        </div>
                        <ToggleButton
                          checked={globalSettings.batch_processing}
                          onChange={(e) => setGlobalSettings(prev => ({ ...prev, batch_processing: e.value }))}
                          onIcon="pi pi-check"
                          offIcon="pi pi-times"
                        />
                      </div>
                      
                      <div className="flex align-items-center justify-content-between">
                        <div>
                          <label className="text-900 font-medium">Real-time Detection</label>
                          <div className="text-600 text-sm mt-1">Enable real-time content monitoring</div>
                        </div>
                        <ToggleButton
                          checked={globalSettings.real_time_detection}
                          onChange={(e) => setGlobalSettings(prev => ({ ...prev, real_time_detection: e.value }))}
                          onIcon="pi pi-check"
                          offIcon="pi pi-times"
                        />
                      </div>

                      <Divider />

                      <div>
                        <label className="text-900 font-medium block mb-2">Notification Threshold</label>
                        <div className="flex align-items-center gap-3">
                          <Slider
                            value={globalSettings.notification_threshold}
                            onChange={(e) => setGlobalSettings(prev => ({ ...prev, notification_threshold: e.value as number }))}
                            className="w-full"
                            min={50}
                            max={99}
                          />
                          <span className="text-sm font-medium w-3rem">{globalSettings.notification_threshold}%</span>
                        </div>
                        <div className="text-600 text-sm mt-1">Minimum confidence level for notifications</div>
                      </div>

                      <div>
                        <label className="text-900 font-medium block mb-2">Max Concurrent Trainings</label>
                        <InputNumber
                          value={globalSettings.max_concurrent_trainings}
                          onValueChange={(e) => setGlobalSettings(prev => ({ ...prev, max_concurrent_trainings: e.value || 1 }))}
                          min={1}
                          max={5}
                          className="w-full"
                        />
                        <div className="text-600 text-sm mt-1">Maximum number of models training simultaneously</div>
                      </div>

                      <div>
                        <label className="text-900 font-medium block mb-2">Data Retention (Days)</label>
                        <InputNumber
                          value={globalSettings.data_retention_days}
                          onValueChange={(e) => setGlobalSettings(prev => ({ ...prev, data_retention_days: e.value || 30 }))}
                          min={30}
                          max={365}
                          className="w-full"
                        />
                        <div className="text-600 text-sm mt-1">How long to keep detection results and logs</div>
                      </div>

                      <div className="flex justify-content-end">
                        <Button
                          label="Save Settings"
                          icon="pi pi-save"
                          onClick={handleSaveGlobalSettings}
                        />
                      </div>
                    </div>
                  )}
                </Card>
              </div>

              {/* Advanced Configuration */}
              <div className="col-12 lg:col-6">
                <Card title="Advanced Configuration" className="h-full">
                  {loading.globalSettings ? (
                    <Skeleton width="100%" height="400px" />
                  ) : (
                    <div className="flex flex-column gap-4">
                      <Panel header="Performance Settings" toggleable>
                        <div className="flex flex-column gap-3">
                          <div className="flex align-items-center justify-content-between">
                            <div>
                              <label className="text-900 font-medium">GPU Acceleration</label>
                              <div className="text-600 text-sm mt-1">Use GPU for faster processing</div>
                            </div>
                            <ToggleButton
                              checked={globalSettings.performance_settings.gpu_acceleration}
                              onChange={(e) => setGlobalSettings(prev => ({
                                ...prev,
                                performance_settings: {
                                  ...prev.performance_settings,
                                  gpu_acceleration: e.value
                                }
                              }))}
                              onIcon="pi pi-check"
                              offIcon="pi pi-times"
                            />
                          </div>
                          <div>
                            <label className="text-900 font-medium block mb-2">Batch Size</label>
                            <InputNumber
                              value={globalSettings.performance_settings.batch_size}
                              onValueChange={(e) => setGlobalSettings(prev => ({
                                ...prev,
                                performance_settings: {
                                  ...prev.performance_settings,
                                  batch_size: e.value || 1
                                }
                              }))}
                              min={1}
                              max={128}
                              className="w-full"
                            />
                          </div>
                        </div>
                      </Panel>

                      <Panel header="Processing Settings" toggleable>
                        <div className="flex flex-column gap-3">
                          <div>
                            <label className="text-900 font-medium block mb-2">Max File Size (MB)</label>
                            <InputNumber
                              value={Math.floor(globalSettings.processing_settings.max_file_size / 1024 / 1024)}
                              onValueChange={(e) => setGlobalSettings(prev => ({
                                ...prev,
                                processing_settings: {
                                  ...prev.processing_settings,
                                  max_file_size: (e.value || 1) * 1024 * 1024
                                }
                              }))}
                              min={1}
                              max={500}
                              className="w-full"
                            />
                          </div>
                          <div>
                            <label className="text-900 font-medium block mb-2">Timeout (seconds)</label>
                            <InputNumber
                              value={globalSettings.processing_settings.timeout_seconds}
                              onValueChange={(e) => setGlobalSettings(prev => ({
                                ...prev,
                                processing_settings: {
                                  ...prev.processing_settings,
                                  timeout_seconds: e.value || 60
                                }
                              }))}
                              min={30}
                              max={3600}
                              className="w-full"
                            />
                          </div>
                        </div>
                      </Panel>
                    </div>
                  )}
                </Card>
              </div>

              {/* Error Messages */}
              {errors.globalSettings && (
                <div className="col-12">
                  <Message severity="error" text={errors.globalSettings} />
                </div>
              )}
            </div>
          </TabPanel>

          {/* Performance Analytics Tab */}
          <TabPanel header="Analytics" leftIcon="pi pi-chart-bar">
            <div className="grid">
              {/* Performance Metrics */}
              <div className="col-12 md:col-6 lg:col-3">
                <Card className="h-full">
                  <div className="text-center">
                    <div className="bg-blue-100 text-blue-800 border-circle w-3rem h-3rem flex align-items-center justify-content-center mx-auto mb-3">
                      <i className="pi pi-bolt text-xl" />
                    </div>
                    <div className="text-900 font-bold text-xl">
                      {loading.performanceMetrics ? <Skeleton width="4rem" height="2rem" /> : 
                        models.length > 0 ? (models.reduce((sum, m) => sum + m.performance_metrics.processing_speed, 0) / models.length).toFixed(1) : '0'
                      }
                    </div>
                    <div className="text-600 text-sm">Avg Processing Speed (img/s)</div>
                  </div>
                </Card>
              </div>

              <div className="col-12 md:col-6 lg:col-3">
                <Card className="h-full">
                  <div className="text-center">
                    <div className="bg-green-100 text-green-800 border-circle w-3rem h-3rem flex align-items-center justify-content-center mx-auto mb-3">
                      <i className="pi pi-target text-xl" />
                    </div>
                    <div className="text-900 font-bold text-xl">
                      {loading.performanceMetrics ? <Skeleton width="4rem" height="2rem" /> : 
                        models.length > 0 ? (models.reduce((sum, m) => sum + m.performance_metrics.precision, 0) / models.length * 100).toFixed(1) + '%' : '0%'
                      }
                    </div>
                    <div className="text-600 text-sm">Avg Precision</div>
                  </div>
                </Card>
              </div>

              <div className="col-12 md:col-6 lg:col-3">
                <Card className="h-full">
                  <div className="text-center">
                    <div className="bg-purple-100 text-purple-800 border-circle w-3rem h-3rem flex align-items-center justify-content-center mx-auto mb-3">
                      <i className="pi pi-search text-xl" />
                    </div>
                    <div className="text-900 font-bold text-xl">
                      {loading.performanceMetrics ? <Skeleton width="4rem" height="2rem" /> : 
                        models.length > 0 ? (models.reduce((sum, m) => sum + m.performance_metrics.recall, 0) / models.length * 100).toFixed(1) + '%' : '0%'
                      }
                    </div>
                    <div className="text-600 text-sm">Avg Recall</div>
                  </div>
                </Card>
              </div>

              <div className="col-12 md:col-6 lg:col-3">
                <Card className="h-full">
                  <div className="text-center">
                    <div className="bg-red-100 text-red-800 border-circle w-3rem h-3rem flex align-items-center justify-content-center mx-auto mb-3">
                      <i className="pi pi-exclamation-triangle text-xl" />
                    </div>
                    <div className="text-900 font-bold text-xl">
                      {loading.performanceMetrics ? <Skeleton width="4rem" height="2rem" /> : 
                        models.length > 0 ? (models.reduce((sum, m) => sum + m.performance_metrics.false_positive_rate, 0) / models.length * 100).toFixed(1) + '%' : '0%'
                      }
                    </div>
                    <div className="text-600 text-sm">False Positive Rate</div>
                  </div>
                </Card>
              </div>

              {/* Error Messages */}
              {errors.performanceMetrics && (
                <div className="col-12">
                  <Message severity="error" text={errors.performanceMetrics} />
                </div>
              )}

              {/* Detailed Performance Charts */}
              <div className="col-12">
                <Card title="Model Performance Trends" className="mt-4">
                  <div style={{ height: '400px' }}>
                    {loading.performanceMetrics || loading.models ? (
                      <Skeleton width="100%" height="400px" />
                    ) : (
                      <Chart 
                        type="line" 
                        data={{
                          labels: performanceMetrics.length > 0 && performanceMetrics[0].performance_trends.length > 0
                            ? performanceMetrics[0].performance_trends.map(trend => new Date(trend.date).toLocaleDateString())
                            : ['No Data'],
                          datasets: performanceMetrics.map((metric, index) => ({
                            label: metric.model_name,
                            data: metric.performance_trends.map(trend => trend.accuracy),
                            borderColor: [
                              '#3B82F6',
                              '#10B981',
                              '#F59E0B',
                              '#EF4444',
                              '#8B5CF6'
                            ][index % 5],
                            tension: 0.4
                          }))
                        }}
                        options={{
                          responsive: true,
                          maintainAspectRatio: false,
                          plugins: {
                            legend: { position: 'top' }
                          },
                          scales: {
                            y: {
                              beginAtZero: false,
                              min: 70,
                              max: 100
                            }
                          }
                        }}
                        height="400px"
                      />
                    )}
                  </div>
                </Card>
              </div>
            </div>
          </TabPanel>
        </TabView>
      </div>

      {/* New Model Creation Dialog */}
      <Dialog
        header="Create New AI Model"
        visible={newModelDialogVisible}
        onHide={() => setNewModelDialogVisible(false)}
        style={{ width: '80vw', maxWidth: '800px' }}
        modal
        closable
      >
        <div className="mb-4">
          <Steps model={modelCreationSteps} activeIndex={newModelStep} />
        </div>

        {newModelStep === 0 && (
          <div className="grid">
            <div className="col-12">
              <label className="text-900 font-medium block mb-2">Model Name</label>
              <InputText
                value={newModel.name}
                onChange={(e) => setNewModel(prev => ({ ...prev, name: e.target.value }))}
                className="w-full mb-3"
                placeholder="Enter model name"
              />
            </div>
            <div className="col-12">
              <label className="text-900 font-medium block mb-2">Model Type</label>
              <Dropdown
                value={newModel.type}
                onChange={(e) => setNewModel(prev => ({ ...prev, type: e.value }))}
                options={modelTypeOptions}
                className="w-full mb-3"
              />
            </div>
            <div className="col-12">
              <label className="text-900 font-medium block mb-2">Description</label>
              <InputTextarea
                value={newModel.description}
                onChange={(e) => setNewModel(prev => ({ ...prev, description: e.target.value }))}
                className="w-full"
                rows={3}
                placeholder="Describe the purpose and use case for this model"
              />
            </div>
            <div className="col-12">
              <label className="text-900 font-medium block mb-2">Confidence Threshold</label>
              <div className="flex align-items-center gap-3">
                <Slider
                  value={newModel.confidence_threshold}
                  onChange={(e) => setNewModel(prev => ({ ...prev, confidence_threshold: e.value as number }))}
                  className="w-full"
                  min={50}
                  max={95}
                />
                <span className="text-sm font-medium w-3rem">{newModel.confidence_threshold}%</span>
              </div>
            </div>
          </div>
        )}

        <div className="flex justify-content-between mt-4">
          <Button
            label="Previous"
            icon="pi pi-chevron-left"
            outlined
            onClick={() => setNewModelStep(Math.max(0, newModelStep - 1))}
            disabled={newModelStep === 0}
          />
          <div className="flex gap-2">
            <Button
              label="Cancel"
              outlined
              onClick={() => setNewModelDialogVisible(false)}
            />
            {newModelStep < modelCreationSteps.length - 1 ? (
              <Button
                label="Next"
                icon="pi pi-chevron-right"
                iconPos="right"
                onClick={() => setNewModelStep(Math.min(modelCreationSteps.length - 1, newModelStep + 1))}
                disabled={!newModel.name || !newModel.type}
              />
            ) : (
              <Button
                label="Create Model"
                icon="pi pi-check"
                onClick={handleCreateModel}
                loading={loading.modelCreation}
                disabled={!newModel.name || !newModel.type}
              />
            )}
          </div>
        </div>
      </Dialog>

      {/* Model Configuration Dialog */}
      <Dialog
        header={`Configure ${selectedModel?.name}`}
        visible={modelDialogVisible}
        onHide={() => setModelDialogVisible(false)}
        style={{ width: '60vw', maxWidth: '600px' }}
        modal
      >
        {selectedModel && (
          <div className="grid">
            <div className="col-12">
              <h5>Performance Metrics</h5>
              <div className="grid">
                <div className="col-6">
                  <div className="text-500 text-sm">Precision</div>
                  <div className="text-xl font-bold">{(selectedModel.performance_metrics.precision * 100).toFixed(1)}%</div>
                </div>
                <div className="col-6">
                  <div className="text-500 text-sm">Recall</div>
                  <div className="text-xl font-bold">{(selectedModel.performance_metrics.recall * 100).toFixed(1)}%</div>
                </div>
                <div className="col-6">
                  <div className="text-500 text-sm">F1 Score</div>
                  <div className="text-xl font-bold">{(selectedModel.performance_metrics.f1_score * 100).toFixed(1)}%</div>
                </div>
                <div className="col-6">
                  <div className="text-500 text-sm">Processing Speed</div>
                  <div className="text-xl font-bold">{selectedModel.performance_metrics.processing_speed} img/s</div>
                </div>
              </div>
            </div>
            
            <div className="col-12">
              <Divider />
              <h5>Configuration</h5>
              <div className="mb-3">
                <label className="text-900 font-medium block mb-2">Confidence Threshold</label>
                <div className="flex align-items-center gap-3">
                  <Slider
                    value={selectedModel.confidence_threshold}
                    onChange={(e) => {
                      const updatedModel = { ...selectedModel, confidence_threshold: e.value as number };
                      setSelectedModel(updatedModel);
                      handleThresholdChange(selectedModel.id, e.value as number);
                    }}
                    className="w-full"
                    min={50}
                    max={95}
                    disabled={loading.modelUpdate}
                  />
                  <span className="text-sm font-medium w-3rem">{selectedModel.confidence_threshold}%</span>
                </div>
              </div>
            </div>
          </div>
        )}
        
        <div className="flex justify-content-end gap-2 mt-4">
          <Button
            label="Cancel"
            outlined
            onClick={() => setModelDialogVisible(false)}
          />
          <Button
            label="Close"
            onClick={() => setModelDialogVisible(false)}
          />
        </div>
      </Dialog>
    </div>
  );
};

export default AIContentMatching;