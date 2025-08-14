// AI Content Matching API endpoints for DMCA system
// This follows the same patterns as existing APIs in services/api.ts

// ===== AI CONTENT MATCHING API TYPES =====

export enum ContentFingerprintType {
  PERCEPTUAL_HASH = 'perceptual_hash',
  FEATURE_VECTOR = 'feature_vector',
  AUDIO_FINGERPRINT = 'audio_fingerprint',
  VIDEO_SIGNATURE = 'video_signature',
  TEXT_EMBEDDING = 'text_embedding',
  COMBINED_MULTIMODAL = 'combined_multimodal'
}

export enum ModelType {
  IMAGE_SIMILARITY = 'image_similarity',
  VIDEO_MATCHING = 'video_matching',
  AUDIO_DETECTION = 'audio_detection',
  TEXT_CLASSIFICATION = 'text_classification',
  MULTIMODAL_FUSION = 'multimodal_fusion',
  DEEPFAKE_DETECTION = 'deepfake_detection'
}

export enum ModelStatus {
  TRAINING = 'training',
  VALIDATING = 'validating',
  DEPLOYED = 'deployed',
  DEPRECATED = 'deprecated',
  FAILED = 'failed'
}

export enum ScanStatus {
  QUEUED = 'queued',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled'
}

export enum TrainingDataLabel {
  POSITIVE = 'positive',
  NEGATIVE = 'negative',
  NEUTRAL = 'neutral',
  SYNTHETIC = 'synthetic'
}

export interface ContentFingerprint {
  id: string;
  content_id: string;
  fingerprint_type: ContentFingerprintType;
  fingerprint_data: string; // Base64 encoded fingerprint
  hash_algorithm: string;
  extraction_method: string;
  confidence_score: number;
  metadata: {
    image_resolution?: string;
    video_duration?: number;
    audio_sample_rate?: number;
    file_size: number;
    mime_type: string;
    extraction_time_ms: number;
  };
  created_at: string;
  expires_at?: string;
}

export interface AIModel {
  id: string;
  name: string;
  description: string;
  type: ModelType;
  version: string;
  status: ModelStatus;
  accuracy: number;
  precision: number;
  recall: number;
  f1_score: number;
  deployment_config: {
    gpu_required: boolean;
    memory_mb: number;
    cpu_cores: number;
    inference_time_ms: number;
    batch_size: number;
  };
  training_data_size: number;
  last_training: string;
  deployment_date?: string;
  is_default: boolean;
  supported_formats: string[];
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface ContentMatch {
  id: string;
  query_content_id: string;
  matched_content_id: string;
  similarity_score: number;
  confidence_level: number;
  match_type: 'exact' | 'near_duplicate' | 'similar' | 'variant';
  model_id: string;
  detection_method: string;
  match_regions?: Array<{
    x: number;
    y: number;
    width: number;
    height: number;
    confidence: number;
  }>;
  metadata: {
    processing_time_ms: number;
    feature_distance: number;
    hash_distance?: number;
    visual_similarity?: number;
  };
  is_verified: boolean;
  verified_by?: number;
  verified_at?: string;
  notes?: string;
  created_at: string;
}

export interface ContentScan {
  id: string;
  user_id: number;
  profile_id?: number;
  scan_type: 'single' | 'batch' | 'continuous';
  status: ScanStatus;
  content_urls: string[];
  model_ids: string[];
  similarity_threshold: number;
  confidence_threshold: number;
  scan_parameters: {
    include_variants: boolean;
    check_transformations: boolean;
    deep_scan_enabled: boolean;
    max_results: number;
    region_detection: boolean;
  };
  progress: {
    total_items: number;
    processed_items: number;
    matches_found: number;
    errors: number;
    estimated_completion?: string;
  };
  results_summary: {
    total_matches: number;
    high_confidence_matches: number;
    exact_matches: number;
    similar_matches: number;
    false_positives_filtered: number;
  };
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
}

export interface TrainingDataset {
  id: string;
  name: string;
  description: string;
  model_type: ModelType;
  total_samples: number;
  positive_samples: number;
  negative_samples: number;
  neutral_samples: number;
  synthetic_samples: number;
  validation_split: number;
  test_split: number;
  data_quality_score: number;
  is_balanced: boolean;
  augmentation_applied: boolean;
  tags: string[];
  created_at: string;
  updated_at: string;
  last_validation: string;
}

export interface TrainingSample {
  id: string;
  dataset_id: string;
  content_url: string;
  content_type: string;
  label: TrainingDataLabel;
  annotation_data?: {
    bounding_boxes?: Array<{
      x: number;
      y: number;
      width: number;
      height: number;
      label: string;
      confidence: number;
    }>;
    keypoints?: Array<{
      x: number;
      y: number;
      visibility: number;
      label: string;
    }>;
    text_annotations?: string[];
    metadata?: Record<string, any>;
  };
  quality_score: number;
  is_validated: boolean;
  validated_by?: number;
  validated_at?: string;
  created_at: string;
}

export interface ModelPerformanceMetrics {
  model_id: string;
  evaluation_date: string;
  test_dataset_id: string;
  metrics: {
    accuracy: number;
    precision: number;
    recall: number;
    f1_score: number;
    auc_roc: number;
    confusion_matrix: number[][];
    false_positive_rate: number;
    false_negative_rate: number;
  };
  performance_by_class?: Record<string, {
    precision: number;
    recall: number;
    f1_score: number;
    support: number;
  }>;
  latency_metrics: {
    avg_inference_time_ms: number;
    p95_inference_time_ms: number;
    p99_inference_time_ms: number;
    throughput_per_second: number;
  };
  resource_usage: {
    gpu_utilization: number;
    memory_usage_mb: number;
    cpu_utilization: number;
  };
  created_at: string;
}

export interface SystemHealthMetrics {
  timestamp: string;
  overall_status: 'healthy' | 'degraded' | 'critical';
  services: {
    fingerprinting_service: 'online' | 'offline' | 'degraded';
    matching_service: 'online' | 'offline' | 'degraded';
    model_inference: 'online' | 'offline' | 'degraded';
    training_pipeline: 'online' | 'offline' | 'degraded';
    data_pipeline: 'online' | 'offline' | 'degraded';
  };
  performance_metrics: {
    avg_scan_time_ms: number;
    queue_depth: number;
    active_scans: number;
    daily_processed_items: number;
    error_rate: number;
    success_rate: number;
  };
  resource_metrics: {
    cpu_usage: number;
    memory_usage: number;
    gpu_usage: number;
    storage_usage: number;
    network_throughput: number;
  };
  model_metrics: {
    active_models: number;
    total_inferences_today: number;
    avg_model_accuracy: number;
    model_load_balancing: Record<string, number>;
  };
}

// ===== AI CONTENT MATCHING API ENDPOINTS =====

export const aiContentMatchingApi = {
  // ==== Content Fingerprinting & Analysis ====
  
  // Upload and fingerprint content
  uploadContentForFingerprinting: (files: File[], options?: {
    fingerprint_types?: ContentFingerprintType[];
    extract_metadata?: boolean;
    priority?: 'low' | 'normal' | 'high';
  }) => {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    if (options) {
      formData.append('options', JSON.stringify(options));
    }
    return api.post('/ai/content/fingerprint/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },

  // Generate fingerprints for URLs
  generateFingerprints: (data: {
    urls: string[];
    fingerprint_types: ContentFingerprintType[];
    extract_metadata?: boolean;
    batch_size?: number;
  }) => api.post('/ai/content/fingerprint/generate', data),

  // Get fingerprint by ID
  getFingerprint: (fingerprintId: string) => 
    api.get(`/ai/content/fingerprint/${fingerprintId}`),

  // Get fingerprints for content
  getContentFingerprints: (contentId: string, params?: {
    fingerprint_type?: ContentFingerprintType;
    include_expired?: boolean;
  }) => api.get(`/ai/content/${contentId}/fingerprints`, { params }),

  // Batch fingerprint processing
  batchFingerprintProcessing: (data: {
    content_batch: Array<{
      id: string;
      url: string;
      type: string;
    }>;
    fingerprint_types: ContentFingerprintType[];
    processing_options: {
      parallel_jobs: number;
      timeout_seconds: number;
      retry_failed: boolean;
    };
  }) => api.post('/ai/content/fingerprint/batch', data),

  // Get batch processing status
  getBatchProcessingStatus: (batchId: string) => 
    api.get(`/ai/content/fingerprint/batch/${batchId}/status`),

  // Content similarity analysis
  analyzeContentSimilarity: (data: {
    source_content_id: string;
    target_content_ids: string[];
    similarity_algorithms?: string[];
    include_regions?: boolean;
    threshold?: number;
  }) => api.post('/ai/content/similarity/analyze', data),

  // Compare two pieces of content directly
  compareContent: (data: {
    source_url: string;
    target_url: string;
    comparison_type: 'visual' | 'audio' | 'text' | 'multimodal';
    detailed_analysis?: boolean;
  }) => api.post('/ai/content/compare', data),

  // ==== ML Model Management ====
  
  // Get available AI models
  getAvailableModels: (params?: {
    model_type?: ModelType;
    status?: ModelStatus;
    include_performance?: boolean;
    tags?: string[];
  }) => api.get('/ai/models', { params }),

  // Get specific model details
  getModel: (modelId: string, params?: {
    include_performance?: boolean;
    include_deployment_info?: boolean;
  }) => api.get(`/ai/models/${modelId}`, { params }),

  // Create/register new model
  createModel: (data: {
    name: string;
    description: string;
    type: ModelType;
    version: string;
    model_file_url?: string;
    deployment_config: any;
    supported_formats: string[];
    tags?: string[];
  }) => api.post('/ai/models', data),

  // Update model configuration
  updateModel: (modelId: string, data: any) => 
    api.put(`/ai/models/${modelId}`, data),

  // Deploy model to production
  deployModel: (modelId: string, data?: {
    deployment_config?: any;
    auto_scale?: boolean;
    max_instances?: number;
  }) => api.post(`/ai/models/${modelId}/deploy`, data),

  // Start model training
  startModelTraining: (data: {
    model_type: ModelType;
    dataset_id: string;
    training_config: {
      epochs: number;
      batch_size: number;
      learning_rate: number;
      validation_split: number;
      early_stopping: boolean;
      augmentation: boolean;
    };
    name: string;
    description?: string;
  }) => api.post('/ai/models/train', data),

  // Get training status
  getTrainingStatus: (trainingJobId: string) => 
    api.get(`/ai/models/training/${trainingJobId}/status`),

  // Cancel model training
  cancelTraining: (trainingJobId: string) => 
    api.post(`/ai/models/training/${trainingJobId}/cancel`),

  // Get model performance metrics
  getModelPerformance: (modelId: string, params?: {
    date_range?: { start: string; end: string };
    include_confusion_matrix?: boolean;
    include_latency?: boolean;
  }) => api.get(`/ai/models/${modelId}/performance`, { params }),

  // Fine-tune existing model
  finetuneModel: (modelId: string, data: {
    dataset_id: string;
    training_config: any;
    name: string;
    description?: string;
  }) => api.post(`/ai/models/${modelId}/finetune`, data),

  // Model versioning
  createModelVersion: (modelId: string, data: {
    version: string;
    changes: string;
    model_file_url: string;
    performance_improvements?: string;
  }) => api.post(`/ai/models/${modelId}/versions`, data),

  // Get model versions
  getModelVersions: (modelId: string) => 
    api.get(`/ai/models/${modelId}/versions`),

  // Set default model
  setDefaultModel: (modelId: string, modelType: ModelType) => 
    api.post(`/ai/models/${modelId}/set-default`, { model_type: modelType }),

  // ==== Content Matching & Detection ====
  
  // Submit content for matching
  submitContentMatching: (data: {
    content_urls: string[];
    model_ids?: string[];
    similarity_threshold?: number;
    confidence_threshold?: number;
    scan_parameters?: {
      include_variants: boolean;
      check_transformations: boolean;
      deep_scan_enabled: boolean;
      max_results: number;
    };
    priority?: 'low' | 'normal' | 'high';
    callback_url?: string;
  }) => api.post('/ai/matching/submit', data),

  // Get matching results
  getMatchingResults: (scanId: string, params?: {
    min_confidence?: number;
    match_type?: string;
    include_metadata?: boolean;
    page?: number;
    per_page?: number;
  }) => api.get(`/ai/matching/${scanId}/results`, { params }),

  // Real-time content scanning
  startRealtimeScanning: (data: {
    profile_id: number;
    monitoring_urls: string[];
    scan_interval_minutes: number;
    model_ids: string[];
    alert_thresholds: {
      high_confidence: number;
      exact_match: number;
      similar_match: number;
    };
    notification_settings: {
      email: boolean;
      webhook: boolean;
      dashboard: boolean;
    };
  }) => api.post('/ai/matching/realtime/start', data),

  // Stop real-time scanning
  stopRealtimeScanning: (scanId: string) => 
    api.post(`/ai/matching/realtime/${scanId}/stop`),

  // Get real-time scan status
  getRealtimeScanStatus: (scanId: string) => 
    api.get(`/ai/matching/realtime/${scanId}/status`),

  // Bulk content matching
  bulkContentMatching: (data: {
    content_batches: Array<{
      batch_id: string;
      urls: string[];
      profile_id?: number;
    }>;
    global_settings: {
      model_ids: string[];
      similarity_threshold: number;
      confidence_threshold: number;
      max_concurrent_jobs: number;
    };
    priority: 'low' | 'normal' | 'high';
  }) => api.post('/ai/matching/bulk', data),

  // Get bulk matching status
  getBulkMatchingStatus: (bulkJobId: string) => 
    api.get(`/ai/matching/bulk/${bulkJobId}/status`),

  // Configure similarity thresholds
  updateSimilarityThresholds: (data: {
    profile_id?: number;
    global_defaults?: boolean;
    thresholds: {
      exact_match: number;
      high_similarity: number;
      medium_similarity: number;
      low_similarity: number;
    };
    model_specific_thresholds?: Record<string, {
      similarity_threshold: number;
      confidence_threshold: number;
    }>;
  }) => api.put('/ai/matching/thresholds', data),

  // Get current threshold configuration
  getSimilarityThresholds: (params?: {
    profile_id?: number;
    model_id?: string;
  }) => api.get('/ai/matching/thresholds', { params }),

  // Verify/validate matches
  verifyMatch: (matchId: string, data: {
    is_valid: boolean;
    confidence_adjustment?: number;
    notes?: string;
    match_regions?: any[];
  }) => api.post(`/ai/matching/matches/${matchId}/verify`, data),

  // Report false positive
  reportFalsePositive: (matchId: string, data: {
    reason: string;
    feedback_data?: any;
    improve_model?: boolean;
  }) => api.post(`/ai/matching/matches/${matchId}/false-positive`, data),

  // ==== Training Data Management ====
  
  // Create training dataset
  createTrainingDataset: (data: {
    name: string;
    description: string;
    model_type: ModelType;
    validation_split?: number;
    test_split?: number;
    tags?: string[];
  }) => api.post('/ai/training/datasets', data),

  // Get training datasets
  getTrainingDatasets: (params?: {
    model_type?: ModelType;
    include_stats?: boolean;
    tags?: string[];
  }) => api.get('/ai/training/datasets', { params }),

  // Get specific dataset
  getTrainingDataset: (datasetId: string, params?: {
    include_samples?: boolean;
    sample_limit?: number;
  }) => api.get(`/ai/training/datasets/${datasetId}`, { params }),

  // Update dataset
  updateTrainingDataset: (datasetId: string, data: any) => 
    api.put(`/ai/training/datasets/${datasetId}`, data),

  // Upload training samples
  uploadTrainingSamples: (datasetId: string, files: File[], metadata: {
    labels: TrainingDataLabel[];
    annotations?: any[];
    batch_name?: string;
  }) => {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    formData.append('metadata', JSON.stringify(metadata));
    return api.post(`/ai/training/datasets/${datasetId}/samples/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },

  // Add training samples from URLs
  addTrainingSamplesFromUrls: (datasetId: string, data: {
    samples: Array<{
      url: string;
      label: TrainingDataLabel;
      annotation_data?: any;
    }>;
    batch_name?: string;
    validate_urls?: boolean;
  }) => api.post(`/ai/training/datasets/${datasetId}/samples/from-urls`, data),

  // Get training samples
  getTrainingSamples: (datasetId: string, params?: {
    label?: TrainingDataLabel;
    validated_only?: boolean;
    page?: number;
    per_page?: number;
  }) => api.get(`/ai/training/datasets/${datasetId}/samples`, { params }),

  // Update training sample
  updateTrainingSample: (sampleId: string, data: {
    label?: TrainingDataLabel;
    annotation_data?: any;
    quality_score?: number;
  }) => api.put(`/ai/training/samples/${sampleId}`, data),

  // Delete training sample
  deleteTrainingSample: (sampleId: string) => 
    api.delete(`/ai/training/samples/${sampleId}`),

  // Bulk label samples
  bulkLabelSamples: (data: {
    sample_ids: string[];
    label: TrainingDataLabel;
    annotation_data?: any;
  }) => api.post('/ai/training/samples/bulk-label', data),

  // Data labeling interface
  getLabeingQueue: (params?: {
    dataset_id?: string;
    unlabeled_only?: boolean;
    priority?: 'high' | 'medium' | 'low';
    limit?: number;
  }) => api.get('/ai/training/labeling/queue', { params }),

  // Submit annotation
  submitAnnotation: (sampleId: string, data: {
    label: TrainingDataLabel;
    annotation_data: any;
    confidence: number;
    time_spent_seconds?: number;
  }) => api.post(`/ai/training/samples/${sampleId}/annotate`, data),

  // Validate training data
  validateTrainingData: (datasetId: string, params?: {
    check_duplicates?: boolean;
    check_quality?: boolean;
    check_balance?: boolean;
  }) => api.post(`/ai/training/datasets/${datasetId}/validate`, {}, { params }),

  // Get data quality report
  getDataQualityReport: (datasetId: string) => 
    api.get(`/ai/training/datasets/${datasetId}/quality-report`),

  // Generate synthetic data
  generateSyntheticData: (datasetId: string, data: {
    generation_method: 'augmentation' | 'gan' | 'diffusion';
    target_samples: number;
    quality_threshold: number;
    preserve_balance?: boolean;
  }) => api.post(`/ai/training/datasets/${datasetId}/generate-synthetic`, data),

  // Export dataset
  exportDataset: (datasetId: string, params: {
    format: 'coco' | 'yolo' | 'pascal_voc' | 'csv' | 'json';
    include_annotations?: boolean;
    split?: 'train' | 'val' | 'test' | 'all';
  }) => api.get(`/ai/training/datasets/${datasetId}/export`, { params }),

  // Import dataset
  importDataset: (file: File, metadata: {
    name: string;
    description: string;
    format: 'coco' | 'yolo' | 'pascal_voc' | 'csv' | 'json';
    model_type: ModelType;
  }) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('metadata', JSON.stringify(metadata));
    return api.post('/ai/training/datasets/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },

  // ==== Analytics & Monitoring ====
  
  // Get matching accuracy metrics
  getMatchingAccuracyMetrics: (params?: {
    date_range?: { start: string; end: string };
    model_id?: string;
    profile_id?: number;
    content_type?: string;
  }) => api.get('/ai/analytics/accuracy', { params }),

  // Get model performance analytics
  getModelPerformanceAnalytics: (params?: {
    date_range?: { start: string; end: string };
    model_ids?: string[];
    include_comparison?: boolean;
  }) => api.get('/ai/analytics/model-performance', { params }),

  // Get content detection statistics
  getContentDetectionStats: (params?: {
    date_range?: { start: string; end: string };
    group_by?: 'day' | 'week' | 'month';
    platform?: string;
    content_type?: string;
  }) => api.get('/ai/analytics/detection-stats', { params }),

  // Get system health monitoring
  getSystemHealthMetrics: () => 
    api.get('/ai/monitoring/system-health'),

  // Get processing queue status
  getProcessingQueueStatus: () => 
    api.get('/ai/monitoring/queue-status'),

  // Get resource utilization
  getResourceUtilization: (params?: {
    time_range?: 'hour' | 'day' | 'week';
    resource_type?: 'cpu' | 'gpu' | 'memory' | 'storage';
  }) => api.get('/ai/monitoring/resources', { params }),

  // Get model inference statistics
  getModelInferenceStats: (params?: {
    date_range?: { start: string; end: string };
    model_id?: string;
    include_latency?: boolean;
  }) => api.get('/ai/analytics/inference-stats', { params }),

  // Get false positive/negative analysis
  getFalsePositiveAnalysis: (params?: {
    date_range?: { start: string; end: string };
    model_id?: string;
    confidence_range?: { min: number; max: number };
  }) => api.get('/ai/analytics/false-positive-analysis', { params }),

  // Get content distribution analytics
  getContentDistributionAnalytics: (params?: {
    date_range?: { start: string; end: string };
    group_by?: 'content_type' | 'platform' | 'region';
  }) => api.get('/ai/analytics/content-distribution', { params }),

  // Get model drift analysis
  getModelDriftAnalysis: (modelId: string, params?: {
    time_window?: 'week' | 'month' | 'quarter';
    include_recommendations?: boolean;
  }) => api.get(`/ai/analytics/models/${modelId}/drift-analysis`, { params }),

  // Set up monitoring alerts
  createMonitoringAlert: (data: {
    name: string;
    type: 'accuracy_drop' | 'high_latency' | 'queue_backup' | 'resource_usage';
    threshold: number;
    model_id?: string;
    notification_channels: ('email' | 'webhook' | 'dashboard')[];
    recipients: string[];
    is_active: boolean;
  }) => api.post('/ai/monitoring/alerts', data),

  // Get monitoring alerts
  getMonitoringAlerts: (params?: {
    type?: string;
    is_active?: boolean;
    model_id?: string;
  }) => api.get('/ai/monitoring/alerts', { params }),

  // Update monitoring alert
  updateMonitoringAlert: (alertId: string, data: any) => 
    api.put(`/ai/monitoring/alerts/${alertId}`, data),

  // Delete monitoring alert
  deleteMonitoringAlert: (alertId: string) => 
    api.delete(`/ai/monitoring/alerts/${alertId}`),

  // Get alert history
  getAlertHistory: (params?: {
    date_range?: { start: string; end: string };
    alert_id?: string;
    status?: 'triggered' | 'resolved';
  }) => api.get('/ai/monitoring/alert-history', { params }),

  // Generate comprehensive AI analytics report
  generateAIAnalyticsReport: (data: {
    date_range: { start: string; end: string };
    include_sections: ('performance' | 'accuracy' | 'resource_usage' | 'model_comparison' | 'trends')[];
    model_ids?: string[];
    format: 'pdf' | 'csv' | 'json';
    recipients?: string[];
  }) => api.post('/ai/analytics/reports/generate', data),

  // Get generated report status
  getReportStatus: (reportId: string) => 
    api.get(`/ai/analytics/reports/${reportId}/status`),

  // Download generated report
  downloadReport: (reportId: string) => 
    api.get(`/ai/analytics/reports/${reportId}/download`, {
      responseType: 'blob'
    }),
};