import React, { useState, useEffect, useRef } from 'react';
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
import { Tooltip } from 'primereact/tooltip';
import { Message } from 'primereact/message';
import { Steps } from 'primereact/steps';
import { MenuItem } from 'primereact/menuitem';
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

// Types for AI Content Matching
interface AIModel {
  id: string;
  name: string;
  type: 'face_recognition' | 'image_matching' | 'video_analysis' | 'text_detection' | 'audio_fingerprint';
  version: string;
  status: 'training' | 'active' | 'inactive' | 'error' | 'updating';
  accuracy: number;
  confidence_threshold: number;
  training_data_count: number;
  last_trained: Date;
  created_at: Date;
  performance_metrics: {
    precision: number;
    recall: number;
    f1_score: number;
    false_positive_rate: number;
    processing_speed: number; // images per second
  };
}

interface TrainingData {
  id: string;
  model_id: string;
  name: string;
  type: 'reference' | 'positive' | 'negative';
  file_path: string;
  file_size: number;
  upload_date: Date;
  status: 'processing' | 'validated' | 'rejected' | 'training';
  validation_score?: number;
  metadata: {
    width?: number;
    height?: number;
    duration?: number; // for videos
    faces_detected?: number;
    quality_score?: number;
  };
}

interface ModelTraining {
  id: string;
  model_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  started_at: Date;
  estimated_completion?: Date;
  completed_at?: Date;
  training_metrics: {
    epochs_completed: number;
    total_epochs: number;
    current_loss: number;
    best_accuracy: number;
    learning_rate: number;
  };
  error_message?: string;
}

interface DetectionResult {
  id: string;
  model_id: string;
  content_url: string;
  confidence_score: number;
  match_type: 'exact' | 'similar' | 'partial';
  detected_at: Date;
  is_verified: boolean;
  reviewer_feedback?: 'correct' | 'incorrect';
  bounding_boxes?: Array<{
    x: number;
    y: number;
    width: number;
    height: number;
    confidence: number;
  }>;
}

interface ContentFingerprint {
  id: string;
  content_hash: string;
  perceptual_hash: string;
  content_type: 'image' | 'video' | 'audio';
  source_url: string;
  created_at: Date;
  model_version: string;
  metadata: {
    file_size: number;
    dimensions?: string;
    duration?: number;
    bitrate?: number;
  };
}

const AIContentMatching: React.FC = () => {
  const { user } = useAuth();
  const toast = useRef<Toast>(null);
  const [activeIndex, setActiveIndex] = useState(0);
  const [loading, setLoading] = useState(false);

  // State for AI Models
  const [models, setModels] = useState<AIModel[]>([]);
  const [selectedModel, setSelectedModel] = useState<AIModel | null>(null);
  const [modelDialogVisible, setModelDialogVisible] = useState(false);
  const [trainingData, setTrainingData] = useState<TrainingData[]>([]);
  const [currentTraining, setCurrentTraining] = useState<ModelTraining[]>([]);

  // State for Configuration
  const [globalSettings, setGlobalSettings] = useState({
    auto_training: true,
    batch_processing: true,
    real_time_detection: false,
    notification_threshold: 85,
    max_concurrent_trainings: 2,
    data_retention_days: 90
  });

  // State for Detection Results
  const [detectionResults, setDetectionResults] = useState<DetectionResult[]>([]);
  const [fingerprints, setFingerprints] = useState<ContentFingerprint[]>([]);

  // State for Model Creation
  const [newModelDialogVisible, setNewModelDialogVisible] = useState(false);
  const [newModelStep, setNewModelStep] = useState(0);
  const [newModel, setNewModel] = useState({
    name: '',
    type: 'face_recognition',
    description: '',
    confidence_threshold: 80
  });

  // Mock data initialization
  useEffect(() => {
    initializeMockData();
  }, []);

  const initializeMockData = () => {
    const mockModels: AIModel[] = [
      {
        id: '1',
        name: 'Primary Face Recognition',
        type: 'face_recognition',
        version: '2.1.0',
        status: 'active',
        accuracy: 94.2,
        confidence_threshold: 85,
        training_data_count: 1250,
        last_trained: new Date('2024-01-15'),
        created_at: new Date('2023-12-01'),
        performance_metrics: {
          precision: 0.942,
          recall: 0.887,
          f1_score: 0.914,
          false_positive_rate: 0.058,
          processing_speed: 12.5
        }
      },
      {
        id: '2',
        name: 'Advanced Image Matching',
        type: 'image_matching',
        version: '1.3.2',
        status: 'training',
        accuracy: 89.7,
        confidence_threshold: 75,
        training_data_count: 2800,
        last_trained: new Date('2024-01-10'),
        created_at: new Date('2023-11-15'),
        performance_metrics: {
          precision: 0.897,
          recall: 0.923,
          f1_score: 0.910,
          false_positive_rate: 0.103,
          processing_speed: 8.2
        }
      },
      {
        id: '3',
        name: 'Video Content Analyzer',
        type: 'video_analysis',
        version: '1.0.5',
        status: 'inactive',
        accuracy: 82.1,
        confidence_threshold: 70,
        training_data_count: 450,
        last_trained: new Date('2023-12-20'),
        created_at: new Date('2023-10-01'),
        performance_metrics: {
          precision: 0.821,
          recall: 0.834,
          f1_score: 0.827,
          false_positive_rate: 0.179,
          processing_speed: 2.1
        }
      }
    ];

    const mockTrainingData: TrainingData[] = [
      {
        id: '1',
        model_id: '1',
        name: 'Reference_Portrait_001.jpg',
        type: 'reference',
        file_path: '/uploads/training/face_001.jpg',
        file_size: 2048576,
        upload_date: new Date('2024-01-12'),
        status: 'validated',
        validation_score: 0.95,
        metadata: {
          width: 1920,
          height: 1080,
          faces_detected: 1,
          quality_score: 0.92
        }
      },
      {
        id: '2',
        model_id: '1',
        name: 'Training_Set_Batch_15.zip',
        type: 'positive',
        file_path: '/uploads/training/batch_15.zip',
        file_size: 15728640,
        upload_date: new Date('2024-01-14'),
        status: 'training',
        validation_score: 0.88,
        metadata: {
          faces_detected: 45,
          quality_score: 0.87
        }
      }
    ];

    const mockTraining: ModelTraining[] = [
      {
        id: '1',
        model_id: '2',
        status: 'running',
        progress: 67,
        started_at: new Date('2024-01-16T10:30:00'),
        estimated_completion: new Date('2024-01-16T14:15:00'),
        training_metrics: {
          epochs_completed: 67,
          total_epochs: 100,
          current_loss: 0.0234,
          best_accuracy: 0.897,
          learning_rate: 0.001
        }
      }
    ];

    const mockDetectionResults: DetectionResult[] = [
      {
        id: '1',
        model_id: '1',
        content_url: 'https://example.com/image1.jpg',
        confidence_score: 92.5,
        match_type: 'exact',
        detected_at: new Date('2024-01-15T15:30:00'),
        is_verified: true,
        reviewer_feedback: 'correct',
        bounding_boxes: [
          { x: 150, y: 200, width: 300, height: 400, confidence: 0.925 }
        ]
      },
      {
        id: '2',
        model_id: '1',
        content_url: 'https://example.com/image2.jpg',
        confidence_score: 78.3,
        match_type: 'similar',
        detected_at: new Date('2024-01-15T16:45:00'),
        is_verified: false
      }
    ];

    setModels(mockModels);
    setTrainingData(mockTrainingData);
    setCurrentTraining(mockTraining);
    setDetectionResults(mockDetectionResults);
  };

  // Chart configurations
  const getModelPerformanceData = () => {
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
    const bins = ['0-20%', '21-40%', '41-60%', '61-80%', '81-100%'];
    const data = [5, 12, 28, 45, 67]; // Mock distribution
    
    return {
      labels: bins,
      datasets: [
        {
          data,
          backgroundColor: [
            '#FF6384',
            '#FF9F40',
            '#FFCD56',
            '#4BC0C0',
            '#36A2EB'
          ],
          borderWidth: 1
        }
      ]
    };
  };

  const getTrainingProgressData = () => {
    const training = currentTraining.find(t => t.status === 'running');
    if (!training) return null;

    const epochs = Array.from({ length: training.training_metrics.epochs_completed }, (_, i) => i + 1);
    const accuracyData = epochs.map(epoch => 
      Math.min(0.95, 0.3 + (epoch / training.training_metrics.total_epochs) * 0.65 + Math.random() * 0.05)
    );
    const lossData = epochs.map(epoch => 
      Math.max(0.01, 0.5 - (epoch / training.training_metrics.total_epochs) * 0.45 + Math.random() * 0.02)
    );

    return {
      labels: epochs,
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
          label: 'Loss',
          data: lossData,
          borderColor: '#FF6384',
          backgroundColor: 'rgba(255, 99, 132, 0.1)',
          yAxisID: 'y1',
          tension: 0.4
        }
      ]
    };
  };

  // Event handlers
  const handleFileUpload = (event: FileUploadHandlerEvent) => {
    const files = event.files;
    if (files.length > 0) {
      // Mock file processing
      toast.current?.show({
        severity: 'success',
        summary: 'Upload Successful',
        detail: `${files.length} training files uploaded successfully`,
        life: 3000
      });
    }
  };

  const handleModelTraining = (modelId: string) => {
    confirmDialog({
      message: 'Are you sure you want to start training this model? This process may take several hours.',
      header: 'Start Model Training',
      icon: 'pi pi-exclamation-triangle',
      accept: () => {
        toast.current?.show({
          severity: 'info',
          summary: 'Training Started',
          detail: 'Model training has been queued and will begin shortly',
          life: 3000
        });
      }
    });
  };

  const handleThresholdChange = (modelId: string, threshold: number) => {
    setModels(prev => prev.map(model => 
      model.id === modelId 
        ? { ...model, confidence_threshold: threshold }
        : model
    ));
  };

  const handleModelStatusToggle = (modelId: string) => {
    setModels(prev => prev.map(model => 
      model.id === modelId 
        ? { 
            ...model, 
            status: model.status === 'active' ? 'inactive' : 'active' 
          }
        : model
    ));
  };

  const handleDetectionFeedback = (resultId: string, feedback: 'correct' | 'incorrect') => {
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
  };

  // Component templates
  const modelStatusTemplate = (model: AIModel) => {
    const severity = model.status === 'active' ? 'success' : 
                    model.status === 'training' ? 'info' :
                    model.status === 'error' ? 'danger' : 'warning';
    return <Tag value={model.status} severity={severity} />;
  };

  const modelTypeTemplate = (model: AIModel) => {
    const typeLabels = {
      face_recognition: 'Face Recognition',
      image_matching: 'Image Matching',
      video_analysis: 'Video Analysis',
      text_detection: 'Text Detection',
      audio_fingerprint: 'Audio Fingerprint'
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
      />
      <span className="text-sm">{model.confidence_threshold}%</span>
    </div>
  );

  const modelActionsTemplate = (model: AIModel) => (
    <div className="flex gap-1">
      <Button
        icon={model.status === 'active' ? 'pi pi-pause' : 'pi pi-play'}
        size="small"
        text
        tooltip={model.status === 'active' ? 'Deactivate' : 'Activate'}
        onClick={() => handleModelStatusToggle(model.id)}
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
        disabled={model.status === 'training'}
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

  // New Model Creation Steps
  const modelCreationSteps: MenuItem[] = [
    { label: 'Basic Info' },
    { label: 'Training Data' },
    { label: 'Configuration' },
    { label: 'Review' }
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
                    <div className="text-900 font-bold text-xl">{models.filter(m => m.status === 'active').length}</div>
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
                      {(models.reduce((sum, m) => sum + m.accuracy, 0) / models.length).toFixed(1)}%
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
                    <div className="text-900 font-bold text-xl">{models.filter(m => m.status === 'training').length}</div>
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
                      {models.reduce((sum, m) => sum + m.training_data_count, 0).toLocaleString()}
                    </div>
                    <div className="text-600 text-sm">Training Samples</div>
                  </div>
                </Card>
              </div>

              {/* Models Table */}
              <div className="col-12">
                <Card title="AI Models" className="mt-4">
                  <DataTable 
                    value={models} 
                    paginator 
                    rows={10}
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
                      body={(model: AIModel) => model.last_trained.toLocaleDateString()} 
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
                  </div>
                </Card>
              </div>

              <div className="col-12 lg:col-6">
                <Card title="Detection Confidence Distribution" className="mt-4">
                  <div style={{ height: '300px' }}>
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
                      options={models}
                      optionLabel="name"
                      placeholder="Choose a model for training data"
                      className="w-full"
                    />
                  </div>
                  
                  <FileUpload
                    name="training_files"
                    url="/api/upload/training-data"
                    multiple
                    accept="image/*,video/*"
                    maxFileSize={50000000}
                    onUpload={handleFileUpload}
                    emptyTemplate={
                      <div className="text-center">
                        <i className="pi pi-cloud-upload text-4xl text-400"></i>
                        <div className="text-600 mt-2">
                          Drag and drop training files here or click to browse
                        </div>
                        <div className="text-500 text-sm mt-1">
                          Supported: JPG, PNG, MP4, MOV (Max 50MB per file)
                        </div>
                      </div>
                    }
                  />
                  
                  <div className="mt-4">
                    <h5>Data Type Selection</h5>
                    <div className="flex flex-column gap-2">
                      <div className="flex align-items-center">
                        <Checkbox inputId="reference" />
                        <label htmlFor="reference" className="ml-2">Reference Images (High Quality)</label>
                      </div>
                      <div className="flex align-items-center">
                        <Checkbox inputId="positive" />
                        <label htmlFor="positive" className="ml-2">Positive Training Samples</label>
                      </div>
                      <div className="flex align-items-center">
                        <Checkbox inputId="negative" />
                        <label htmlFor="negative" className="ml-2">Negative Training Samples</label>
                      </div>
                    </div>
                  </div>
                </Card>
              </div>

              {/* Training Status */}
              <div className="col-12 lg:col-6">
                <Card title="Training Status" className="h-full">
                  {currentTraining.length > 0 ? (
                    <div>
                      {currentTraining.map(training => (
                        <div key={training.id} className="mb-4 p-3 border-1 border-200 border-round">
                          <div className="flex justify-content-between align-items-center mb-2">
                            <span className="font-medium">Model Training in Progress</span>
                            <Tag value={training.status} severity="info" />
                          </div>
                          <ProgressBar value={training.progress} showValue />
                          <div className="grid mt-3 text-sm">
                            <div className="col-6">
                              <div className="text-500">Epochs: {training.training_metrics.epochs_completed}/{training.training_metrics.total_epochs}</div>
                            </div>
                            <div className="col-6">
                              <div className="text-500">Current Loss: {training.training_metrics.current_loss.toFixed(4)}</div>
                            </div>
                            <div className="col-6">
                              <div className="text-500">Best Accuracy: {(training.training_metrics.best_accuracy * 100).toFixed(1)}%</div>
                            </div>
                            <div className="col-6">
                              <div className="text-500">ETA: {training.estimated_completion?.toLocaleTimeString()}</div>
                            </div>
                          </div>
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
                                max: 1
                              },
                              y1: {
                                type: 'linear',
                                display: true,
                                position: 'right',
                                min: 0,
                                max: 0.5,
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

              {/* Training Data Table */}
              <div className="col-12">
                <Card title="Training Data Management" className="mt-4">
                  <DataTable 
                    value={trainingData} 
                    paginator 
                    rows={10}
                    showGridlines
                    emptyMessage="No training data found"
                  >
                    <Column field="name" header="File Name" sortable />
                    <Column 
                      field="type" 
                      header="Type" 
                      body={(data: TrainingData) => 
                        <Tag value={data.type} severity={
                          data.type === 'reference' ? 'success' :
                          data.type === 'positive' ? 'info' : 'warning'
                        } />
                      } 
                    />
                    <Column 
                      field="file_size" 
                      header="Size" 
                      body={(data: TrainingData) => `${(data.file_size / 1024 / 1024).toFixed(1)} MB`}
                    />
                    <Column 
                      field="status" 
                      header="Status" 
                      body={(data: TrainingData) => 
                        <Tag value={data.status} severity={
                          data.status === 'validated' ? 'success' :
                          data.status === 'processing' ? 'info' : 
                          data.status === 'rejected' ? 'danger' : 'warning'
                        } />
                      }
                    />
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
                      body={(data: TrainingData) => data.upload_date.toLocaleDateString()}
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
                    <div className="text-900 font-bold text-xl">{detectionResults.length}</div>
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
                      {detectionResults.filter(r => r.reviewer_feedback === 'correct').length}
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
                      {detectionResults.filter(r => r.reviewer_feedback === 'incorrect').length}
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
                      {detectionResults.filter(r => !r.is_verified).length}
                    </div>
                    <div className="text-600 text-sm">Pending Review</div>
                  </div>
                </Card>
              </div>

              {/* Detection Results Table */}
              <div className="col-12">
                <Card title="Recent Detections" className="mt-4">
                  <DataTable 
                    value={detectionResults} 
                    paginator 
                    rows={10}
                    showGridlines
                    emptyMessage="No detection results found"
                  >
                    <Column 
                      field="content_url" 
                      header="Content" 
                      body={(result: DetectionResult) => (
                        <a href={result.content_url} target="_blank" rel="noopener noreferrer" className="text-primary">
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
                            result.match_type === 'exact' ? 'success' :
                            result.match_type === 'similar' ? 'info' : 'warning'
                          } 
                        />
                      )}
                    />
                    <Column 
                      field="detected_at" 
                      header="Detected" 
                      body={(result: DetectionResult) => result.detected_at.toLocaleString()}
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
                  </div>
                </Card>
              </div>

              {/* Advanced Configuration */}
              <div className="col-12 lg:col-6">
                <Card title="Advanced Configuration" className="h-full">
                  <div className="flex flex-column gap-4">
                    <Panel header="Face Recognition Settings" toggleable>
                      <div className="flex flex-column gap-3">
                        <div>
                          <label className="text-900 font-medium block mb-2">Face Detection Sensitivity</label>
                          <SelectButton
                            value="medium"
                            options={[
                              { label: 'Low', value: 'low' },
                              { label: 'Medium', value: 'medium' },
                              { label: 'High', value: 'high' }
                            ]}
                            onChange={(e) => console.log(e.value)}
                          />
                        </div>
                        <div>
                          <label className="text-900 font-medium block mb-2">Multiple Face Support</label>
                          <ToggleButton
                            checked={true}
                            onIcon="pi pi-check"
                            offIcon="pi pi-times"
                          />
                        </div>
                      </div>
                    </Panel>

                    <Panel header="Image Matching Settings" toggleable>
                      <div className="flex flex-column gap-3">
                        <div>
                          <label className="text-900 font-medium block mb-2">Crop Tolerance</label>
                          <Slider value={25} className="w-full" />
                          <div className="text-600 text-sm mt-1">Allow matching of cropped images</div>
                        </div>
                        <div>
                          <label className="text-900 font-medium block mb-2">Color Variance</label>
                          <Slider value={15} className="w-full" />
                          <div className="text-600 text-sm mt-1">Tolerance for color adjustments</div>
                        </div>
                      </div>
                    </Panel>

                    <Panel header="Video Analysis Settings" toggleable>
                      <div className="flex flex-column gap-3">
                        <div>
                          <label className="text-900 font-medium block mb-2">Frame Sampling Rate</label>
                          <Dropdown
                            value="1fps"
                            options={[
                              { label: '0.5 FPS', value: '0.5fps' },
                              { label: '1 FPS', value: '1fps' },
                              { label: '2 FPS', value: '2fps' },
                              { label: '5 FPS', value: '5fps' }
                            ]}
                            className="w-full"
                          />
                        </div>
                        <div>
                          <label className="text-900 font-medium block mb-2">Temporal Consistency</label>
                          <ToggleButton
                            checked={true}
                            onIcon="pi pi-check"
                            offIcon="pi pi-times"
                          />
                          <div className="text-600 text-sm mt-1">Require detection in multiple frames</div>
                        </div>
                      </div>
                    </Panel>
                  </div>
                </Card>
              </div>
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
                      {(models.reduce((sum, m) => sum + m.performance_metrics.processing_speed, 0) / models.length).toFixed(1)}
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
                      {(models.reduce((sum, m) => sum + m.performance_metrics.precision, 0) / models.length * 100).toFixed(1)}%
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
                      {(models.reduce((sum, m) => sum + m.performance_metrics.recall, 0) / models.length * 100).toFixed(1)}%
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
                      {(models.reduce((sum, m) => sum + m.performance_metrics.false_positive_rate, 0) / models.length * 100).toFixed(1)}%
                    </div>
                    <div className="text-600 text-sm">False Positive Rate</div>
                  </div>
                </Card>
              </div>

              {/* Detailed Performance Charts */}
              <div className="col-12">
                <Card title="Model Performance Trends" className="mt-4">
                  <div style={{ height: '400px' }}>
                    <Chart 
                      type="line" 
                      data={{
                        labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                        datasets: models.map((model, index) => ({
                          label: model.name,
                          data: [
                            model.accuracy - 5 + Math.random() * 3,
                            model.accuracy - 2 + Math.random() * 2,
                            model.accuracy + Math.random() * 2,
                            model.accuracy
                          ],
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
                options={[
                  { label: 'Face Recognition', value: 'face_recognition' },
                  { label: 'Image Matching', value: 'image_matching' },
                  { label: 'Video Analysis', value: 'video_analysis' },
                  { label: 'Text Detection', value: 'text_detection' }
                ]}
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
              />
            ) : (
              <Button
                label="Create Model"
                icon="pi pi-check"
                onClick={() => {
                  toast.current?.show({
                    severity: 'success',
                    summary: 'Model Created',
                    detail: 'New AI model has been created successfully',
                    life: 3000
                  });
                  setNewModelDialogVisible(false);
                  setNewModelStep(0);
                }}
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
                    onChange={(e) => handleThresholdChange(selectedModel.id, e.value as number)}
                    className="w-full"
                    min={50}
                    max={95}
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
            label="Save Changes"
            onClick={() => {
              toast.current?.show({
                severity: 'success',
                summary: 'Settings Saved',
                detail: 'Model configuration updated successfully',
                life: 3000
              });
              setModelDialogVisible(false);
            }}
          />
        </div>
      </Dialog>
    </div>
  );
};

export default AIContentMatching;