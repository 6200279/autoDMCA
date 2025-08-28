import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { Badge } from 'primereact/badge';
import { Tag } from 'primereact/tag';
import { Toast } from 'primereact/toast';
import { ConfirmDialog } from 'primereact/confirmdialog';
import { Toolbar } from 'primereact/toolbar';
import { SelectButton } from 'primereact/selectbutton';
import { InputText } from 'primereact/inputtext';
import { Dropdown } from 'primereact/dropdown';
import { ProgressBar } from 'primereact/progressbar';
import { Checkbox } from 'primereact/checkbox';
import { Avatar } from 'primereact/avatar';
import { Panel } from 'primereact/panel';
import { Skeleton } from 'primereact/skeleton';
import { Message } from 'primereact/message';
import { Chip } from 'primereact/chip';
import { Timeline } from 'primereact/timeline';
import { Divider } from 'primereact/divider';
import { ToggleButton } from 'primereact/togglebutton';
import { Accordion, AccordionTab } from 'primereact/accordion';
import { useDashboardRealtime } from '../../contexts/WebSocketContext';
import { infringementApi, profileApi } from '../../services/api';
import { automationService, SmartGrouping, ActionRequired } from '../../services/automationService';
import './ContentProtectionWorkbench.enhanced.css';

// Types for the unified workbench
export interface WorkbenchTask {
  id: string;
  type: 'new_detection' | 'in_progress' | 'awaiting_response' | 'completed';
  priority: 'critical' | 'high' | 'medium' | 'low';
  confidence: number; // 0-100
  title: string;
  description: string;
  profileName: string;
  profileImage?: string;
  platform: string;
  platformIcon: string;
  originalContentUrl?: string;
  infringingUrl: string;
  thumbnail?: string;
  detectedAt: Date;
  lastUpdated: Date;
  suggestedAction: 'auto_approve' | 'manual_review' | 'auto_reject' | 'batch_process';
  aiReasoning?: string;
  estimatedImpact: 'high' | 'medium' | 'low';
  tags: string[];
  metadata: {
    similarity?: number;
    contentType: 'image' | 'video' | 'audio' | 'text';
    engagement?: {
      views?: number;
      likes?: number;
      shares?: number;
    };
  };
  takedownRequest?: {
    id: string;
    status: 'draft' | 'sent' | 'acknowledged' | 'resolved' | 'rejected';
    sentAt?: Date;
    expectedResponseDate?: Date;
  };
}

interface WorkbenchLane {
  id: string;
  title: string;
  subtitle: string;
  icon: string;
  color: string;
  tasks: WorkbenchTask[];
  showBatchActions: boolean;
}

interface WorkbenchFilters {
  priority: string[];
  platform: string[];
  confidence: [number, number];
  profile: string[];
  timeRange: string;
}

const ContentProtectionWorkbench: React.FC = () => {
  const [tasks, setTasks] = useState<WorkbenchTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTasks, setSelectedTasks] = useState<string[]>([]);
  const [filters, setFilters] = useState<WorkbenchFilters>({
    priority: [],
    platform: [],
    confidence: [0, 100],
    profile: [],
    timeRange: 'today'
  });
  const [searchTerm, setSearchTerm] = useState('');
  const [activeView, setActiveView] = useState('kanban');
  const [smartGroupings, setSmartGroupings] = useState<SmartGrouping[]>([]);
  const [actionRequiredItems, setActionRequiredItems] = useState<ActionRequired[]>([]);
  const [hideActionNotRequired, setHideActionNotRequired] = useState(false);
  const [userExperienceLevel, setUserExperienceLevel] = useState<'basic' | 'intermediate' | 'advanced'>('intermediate');
  const [autoMoveAnimations, setAutoMoveAnimations] = useState<{ [taskId: string]: { fromLane: string; toLane: string } }>({});
  const [dailyDigest, setDailyDigest] = useState<string>('');
  const [showSmartGrouping, setShowSmartGrouping] = useState(true);
  const toast = useRef<Toast>(null);
  
  // Real-time updates
  const { dashboardStats } = useDashboardRealtime();

  // View options
  const viewOptions = [
    { label: 'Workflow Lanes', value: 'kanban', icon: 'pi pi-th' },
    { label: 'Priority List', value: 'list', icon: 'pi pi-list' },
    { label: 'Quick Actions', value: 'quick', icon: 'pi pi-bolt' }
  ];

  // Calculate AI priority score
  const calculatePriorityScore = (task: WorkbenchTask): number => {
    let score = 0;
    
    // Confidence weight (higher confidence = higher priority)
    score += task.confidence * 0.3;
    
    // Priority weight
    const priorityWeights = { critical: 40, high: 30, medium: 20, low: 10 };
    score += priorityWeights[task.priority];
    
    // Impact weight
    const impactWeights = { high: 20, medium: 15, low: 10 };
    score += impactWeights[task.estimatedImpact];
    
    // Recency weight (newer = higher priority)
    const hoursSinceDetection = (new Date().getTime() - task.detectedAt.getTime()) / (1000 * 60 * 60);
    score += Math.max(0, 10 - hoursSinceDetection * 0.1);
    
    // Engagement impact (higher engagement = higher priority)
    if (task.metadata.engagement?.views) {
      score += Math.min(10, task.metadata.engagement.views / 1000);
    }
    
    return score;
  };

  // AI-powered task prioritization with action-required filtering
  const prioritizedTasks = useMemo(() => {
    return tasks
      .filter(task => {
        // Apply filters
        if (searchTerm && !task.title.toLowerCase().includes(searchTerm.toLowerCase())) return false;
        if (filters.priority.length > 0 && !filters.priority.includes(task.priority)) return false;
        if (filters.platform.length > 0 && !filters.platform.includes(task.platform)) return false;
        if (task.confidence < filters.confidence[0] || task.confidence > filters.confidence[1]) return false;
        
        // Action required filter
        if (hideActionNotRequired) {
          const requiresAction = (
            task.type === 'new_detection' || 
            task.priority === 'critical' || 
            task.suggestedAction === 'manual_review' ||
            (task.takedownRequest?.expectedResponseDate && 
             new Date(task.takedownRequest.expectedResponseDate).getTime() - Date.now() < 24 * 60 * 60 * 1000)
          );
          if (!requiresAction) return false;
        }
        
        return true;
      })
      .sort((a, b) => {
        // AI prioritization algorithm with auto-move animation priority
        const aHasAnimation = autoMoveAnimations[a.id];
        const bHasAnimation = autoMoveAnimations[b.id];
        
        // Prioritize animated tasks
        if (aHasAnimation && !bHasAnimation) return -1;
        if (!aHasAnimation && bHasAnimation) return 1;
        
        const aPriorityScore = calculatePriorityScore(a);
        const bPriorityScore = calculatePriorityScore(b);
        return bPriorityScore - aPriorityScore;
      });
  }, [tasks, searchTerm, filters, hideActionNotRequired, autoMoveAnimations]);

  // Enhanced Task Card Component with Auto-Move Animation
  const EnhancedTaskCard: React.FC<{
    task: WorkbenchTask;
    selected: boolean;
    onAction: (taskId: string, action: string) => void;
    onSelect: (taskId: string, selected: boolean) => void;
  }> = ({ task, selected, onAction, onSelect }) => {
    const getConfidenceBadgeClass = (confidence: number) => {
      if (confidence >= 80) return 'confidence-badge high';
      if (confidence >= 60) return 'confidence-badge medium';
      return 'confidence-badge low';
    };

    const formatTimeAgo = (date: Date) => {
      const hours = Math.floor((new Date().getTime() - date.getTime()) / (1000 * 60 * 60));
      if (hours < 1) return 'Just now';
      if (hours === 1) return '1 hour ago';
      if (hours < 24) return `${hours} hours ago`;
      return `${Math.floor(hours / 24)} days ago`;
    };

    const isAutoMoving = autoMoveAnimations[task.id];
    
    return (
      <div 
        className={`task-card ${selected ? 'selected' : ''} ${isAutoMoving ? 'auto-moving' : ''}`}
        role="listitem"
        tabIndex={0}
        onClick={() => onSelect(task.id, !selected)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onSelect(task.id, !selected);
          }
        }}
        style={isAutoMoving ? {
          animation: 'task-auto-move 2s ease-in-out',
          border: '2px solid var(--color-info-500)',
          boxShadow: '0 0 20px rgba(14, 165, 233, 0.3)'
        } : {}}
      >
        <div className={`task-priority-indicator ${task.priority}`} aria-hidden="true" />
        
        {/* Auto-move notification */}
        {isAutoMoving && (
          <div className="auto-move-notification">
            <div className="flex align-items-center gap-2 p-2 bg-blue-50 border-round mb-2">
              <i className="pi pi-arrow-right text-blue-600" />
              <span className="text-xs text-blue-700">
                AI moved from {isAutoMoving.fromLane.replace('_', ' ')} to {isAutoMoving.toLane.replace('_', ' ')}
              </span>
            </div>
          </div>
        )}
        
        <div className="task-header">
          <Checkbox
            checked={selected}
            onChange={(e) => {
              e.stopPropagation();
              onSelect(task.id, e.checked || false);
            }}
            className="task-checkbox"
            aria-label={`Select task: ${task.title}`}
          />
          <div className="task-info">
            <h4 className="task-title">{task.title}</h4>
            <p className="task-description">{task.description}</p>
          </div>
        </div>

        <div className="task-metadata">
          <div className="platform-badge">
            <i className={task.platformIcon} aria-hidden="true" />
            <span>{task.platform}</span>
          </div>
          <div className={getConfidenceBadgeClass(task.confidence)}>
            {task.confidence}%
          </div>
          <span className="text-caption">{formatTimeAgo(task.detectedAt)}</span>
        </div>

        {task.aiReasoning && (
          <div className="ai-reasoning">
            <div className="ai-reasoning-header">
              <i className="pi pi-brain" style={{ color: 'var(--color-info-600)' }} aria-hidden="true" />
              <span className="text-caption">AI Analysis</span>
            </div>
            <p className="ai-reasoning-text">{task.aiReasoning}</p>
          </div>
        )}

        <div className="task-actions" onClick={(e) => e.stopPropagation()}>
          {task.suggestedAction === 'auto_approve' && (
            <button
              className="task-action-btn primary"
              onClick={() => onAction(task.id, 'approve')}
              title="Approve takedown"
              aria-label="Approve takedown"
            >
              <i className="pi pi-check" aria-hidden="true" />
            </button>
          )}
          <button
            className="task-action-btn"
            onClick={() => onAction(task.id, 'review')}
            title="Review details"
            aria-label="Review task details"
          >
            <i className="pi pi-eye" aria-hidden="true" />
          </button>
          <button
            className="task-action-btn destructive"
            onClick={() => onAction(task.id, 'reject')}
            title="Reject as false positive"
            aria-label="Reject as false positive"
          >
            <i className="pi pi-times" aria-hidden="true" />
          </button>
        </div>
      </div>
    );
  };

  // Organize tasks into workflow lanes
  const workflowLanes: WorkbenchLane[] = useMemo(() => {
    const groupedTasks = prioritizedTasks.reduce((acc, task) => {
      acc[task.type] = acc[task.type] || [];
      acc[task.type].push(task);
      return acc;
    }, {} as Record<string, WorkbenchTask[]>);

    return [
      {
        id: 'new_detection',
        title: 'New Detections',
        subtitle: 'Require Review',
        icon: 'pi pi-exclamation-triangle',
        color: 'orange',
        tasks: groupedTasks.new_detection || [],
        showBatchActions: true
      },
      {
        id: 'in_progress',
        title: 'In Progress',
        subtitle: 'Takedowns Processing',
        icon: 'pi pi-clock',
        color: 'blue',
        tasks: groupedTasks.in_progress || [],
        showBatchActions: false
      },
      {
        id: 'awaiting_response',
        title: 'Awaiting Response',
        subtitle: 'Platform Review',
        icon: 'pi pi-hourglass',
        color: 'purple',
        tasks: groupedTasks.awaiting_response || [],
        showBatchActions: false
      },
      {
        id: 'completed',
        title: 'Completed',
        subtitle: 'Resolved Cases',
        icon: 'pi pi-check-circle',
        color: 'green',
        tasks: groupedTasks.completed || [],
        showBatchActions: false
      }
    ];
  }, [prioritizedTasks]);

  // Load initial data and initialize automation
  useEffect(() => {
    loadWorkbenchData();
    automationService.loadConfig();
    
    // Set user experience level from localStorage
    const savedExperience = localStorage.getItem('userExperienceLevel');
    if (savedExperience) {
      setUserExperienceLevel(savedExperience as any);
    }
  }, []);

  // Auto-move tasks and update groupings
  useEffect(() => {
    if (tasks.length > 0) {
      const autoMovedTasks = automationService.autoMoveTasks(tasks);
      const groupings = automationService.findSmartGroupings(autoMovedTasks);
      const actionItems = automationService.getActionRequiredItems(autoMovedTasks);
      const digest = automationService.getDailyDigest(autoMovedTasks);
      
      // Track auto-moves for animations
      const movements: typeof autoMoveAnimations = {};
      autoMovedTasks.forEach((task, index) => {
        if (task.type !== tasks[index]?.type) {
          movements[task.id] = {
            fromLane: tasks[index]?.type || 'new_detection',
            toLane: task.type
          };
        }
      });
      
      setTasks(autoMovedTasks);
      setSmartGroupings(groupings);
      setActionRequiredItems(actionItems);
      setDailyDigest(digest);
      setAutoMoveAnimations(movements);
      
      // Clear animations after delay
      if (Object.keys(movements).length > 0) {
        setTimeout(() => setAutoMoveAnimations({}), 3000);
      }
    }
  }, [tasks.length]); // Only when tasks change count, not on every update

  const loadWorkbenchData = async () => {
    try {
      setLoading(true);
      
      // In a real implementation, this would be a unified API call
      // For now, we'll combine data from existing endpoints
      const [infringementsResponse] = await Promise.all([
        infringementApi.getInfringements({ page: 1, limit: 100, include_stats: true })
      ]);

      // Transform infringement data into workbench tasks
      const transformedTasks: WorkbenchTask[] = infringementsResponse.data.items?.map((infringement: any) => ({
        id: infringement.id,
        type: determineTaskType(infringement.status),
        priority: determinePriority(infringement),
        confidence: infringement.confidence || Math.round(infringement.similarity || 75),
        title: infringement.description || `${infringement.platform} Content Match`,
        description: `Potential infringement detected on ${infringement.platform}`,
        profileName: infringement.profile_name || 'Unknown Profile',
        platform: infringement.platform,
        platformIcon: getPlatformIcon(infringement.platform),
        infringingUrl: infringement.url,
        originalContentUrl: infringement.original_url,
        detectedAt: new Date(infringement.detected_at),
        lastUpdated: new Date(infringement.detected_at),
        suggestedAction: determineSuggestedAction(infringement),
        aiReasoning: generateAIReasoning(infringement),
        estimatedImpact: determineImpact(infringement),
        tags: infringement.tags || [],
        metadata: {
          similarity: infringement.similarity,
          contentType: infringement.description?.toLowerCase().includes('video') ? 'video' : 'image',
          engagement: {
            views: Math.floor(Math.random() * 10000),
            likes: Math.floor(Math.random() * 500),
            shares: Math.floor(Math.random() * 100)
          }
        },
        takedownRequest: infringement.takedown_sent ? {
          id: `TD-${infringement.id}`,
          status: infringement.response_received ? 'resolved' : 'sent',
          sentAt: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000)
        } : undefined
      })) || [];

      setTasks(transformedTasks);
    } catch (error) {
      console.error('Failed to load workbench data:', error);
      toast.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: 'Failed to load workbench data',
        life: 5000
      });
    } finally {
      setLoading(false);
    }
  };

  // Helper functions
  const determineTaskType = (status: string): WorkbenchTask['type'] => {
    switch (status) {
      case 'detected': return 'new_detection';
      case 'submitted': return 'in_progress';
      case 'pending': return 'awaiting_response';
      case 'resolved': return 'completed';
      default: return 'new_detection';
    }
  };

  const determinePriority = (infringement: any): WorkbenchTask['priority'] => {
    const confidence = infringement.confidence || infringement.similarity || 0;
    const severity = infringement.severity || 'medium';
    
    if (confidence > 90 && severity === 'high') return 'critical';
    if (confidence > 80 || severity === 'high') return 'high';
    if (confidence > 60 || severity === 'medium') return 'medium';
    return 'low';
  };

  const determineSuggestedAction = (infringement: any): WorkbenchTask['suggestedAction'] => {
    const confidence = infringement.confidence || infringement.similarity || 0;
    
    if (confidence > 95) return 'auto_approve';
    if (confidence < 60) return 'auto_reject';
    if (confidence > 80) return 'batch_process';
    return 'manual_review';
  };

  const generateAIReasoning = (infringement: any): string => {
    const confidence = infringement.confidence || infringement.similarity || 0;
    const platform = infringement.platform;
    
    if (confidence > 95) {
      return `High confidence match (${confidence}%) with identical content structure. Recommended for immediate takedown.`;
    }
    if (confidence > 80) {
      return `Strong similarity (${confidence}%) detected. Content appears to be unauthorized use. Consider batch processing with similar cases.`;
    }
    if (confidence < 60) {
      return `Low confidence match (${confidence}%). May be coincidental similarity or fair use. Manual review recommended.`;
    }
    return `Medium confidence match (${confidence}%) on ${platform}. Manual review suggested to confirm infringement.`;
  };

  const determineImpact = (infringement: any): WorkbenchTask['estimatedImpact'] => {
    const platform = infringement.platform?.toLowerCase();
    const confidence = infringement.confidence || infringement.similarity || 0;
    
    // High-impact platforms
    if (['youtube', 'instagram', 'tiktok'].includes(platform) && confidence > 80) return 'high';
    if (['facebook', 'twitter'].includes(platform) && confidence > 70) return 'medium';
    return 'low';
  };

  const getPlatformIcon = (platform: string): string => {
    const icons: Record<string, string> = {
      'instagram': 'pi pi-instagram',
      'youtube': 'pi pi-youtube',
      'tiktok': 'pi pi-video',
      'twitter': 'pi pi-twitter',
      'facebook': 'pi pi-facebook',
      'reddit': 'pi pi-reddit'
    };
    return icons[platform.toLowerCase()] || 'pi pi-globe';
  };

  // Select all high-confidence tasks
  const handleSelectHighConfidence = useCallback(() => {
    const highConfidenceTasks = tasks.filter(task => task.confidence > 90).map(task => task.id);
    setSelectedTasks(highConfidenceTasks);
    
    toast.current?.show({
      severity: 'info',
      summary: 'High Confidence Selected',
      detail: `${highConfidenceTasks.length} tasks with >90% confidence selected`,
      life: 3000
    });
  }, [tasks]);

  // Handle smart grouping selection
  const handleSelectSmartGroup = useCallback((grouping: SmartGrouping) => {
    setSelectedTasks(grouping.taskIds);
    
    toast.current?.show({
      severity: 'info',
      summary: 'Smart Group Selected',
      detail: grouping.reason,
      life: 3000
    });
  }, []);

  // Progressive disclosure controls
  const getVisibleFeatures = useCallback(() => {
    switch (userExperienceLevel) {
      case 'basic':
        return {
          showAdvancedFilters: false,
          showBatchActions: true,
          showSmartGrouping: true,
          showAutomationSettings: false,
          maxGroupingSuggestions: 2
        };
      case 'intermediate':
        return {
          showAdvancedFilters: true,
          showBatchActions: true,
          showSmartGrouping: true,
          showAutomationSettings: false,
          maxGroupingSuggestions: 3
        };
      case 'advanced':
        return {
          showAdvancedFilters: true,
          showBatchActions: true,
          showSmartGrouping: true,
          showAutomationSettings: true,
          maxGroupingSuggestions: 5
        };
    }
  }, [userExperienceLevel]);

  // Action handlers
  const handleTaskAction = async (taskId: string, action: string) => {
    try {
      const task = tasks.find(t => t.id === taskId);
      if (task) {
        // Learn from user action
        automationService.learnFromAction(task, action);
      }

      // Implementation for task actions
      toast.current?.show({
        severity: 'success',
        summary: 'Action Complete',
        detail: `Task ${action} successfully`,
        life: 3000
      });
      
      // Reload data
      await loadWorkbenchData();
    } catch (error) {
      toast.current?.show({
        severity: 'error',
        summary: 'Error',
        detail: `Failed to ${action} task`,
        life: 5000
      });
    }
  };

  const handleBatchAction = async (taskIds: string[], action: string) => {
    try {
      const selectedTasksData = tasks.filter(task => taskIds.includes(task.id));
      let successMessage = '';
      let detailMessage = '';

      switch (action) {
        case 'approve':
          // Auto-approve high confidence tasks
          await Promise.all(taskIds.map(id => 
            infringementApi.updateInfringement(id, { status: 'approved' })
          ));
          successMessage = 'Batch Approval Complete';
          detailMessage = `${taskIds.length} tasks approved and queued for takedown requests`;
          break;

        case 'reject':
          // Mark as false positives
          await Promise.all(taskIds.map(id => 
            infringementApi.updateInfringement(id, { status: 'false_positive' })
          ));
          successMessage = 'Batch Rejection Complete';
          detailMessage = `${taskIds.length} tasks marked as false positives`;
          break;

        case 'takedown':
          // Generate bulk takedown requests
          const takedownData = selectedTasksData.map(task => ({
            infringement_id: task.id,
            platform: task.platform,
            infringing_url: task.infringingUrl,
            original_url: task.originalContentUrl,
            confidence: task.confidence,
            priority: task.priority
          }));
          
          // In real implementation, this would call a bulk takedown API
          await Promise.all(takedownData.map(data => 
            // Simulate takedown request creation
            new Promise(resolve => setTimeout(resolve, 100))
          ));
          
          successMessage = 'Bulk Takedown Requests Sent';
          detailMessage = `${taskIds.length} takedown requests generated and sent to platforms`;
          break;

        case 'similar_batch':
          // Group similar tasks for batch processing
          const similarTasks = findSimilarTasks(selectedTasksData[0]);
          const similarIds = similarTasks.map(t => t.id);
          setSelectedTasks(similarIds);
          
          successMessage = 'Similar Tasks Selected';
          detailMessage = `${similarIds.length} similar tasks selected for batch processing`;
          return; // Don't clear selection or reload data

        default:
          throw new Error(`Unknown batch action: ${action}`);
      }
      
      toast.current?.show({
        severity: 'success',
        summary: successMessage,
        detail: detailMessage,
        life: 4000
      });
      
      setSelectedTasks([]);
      await loadWorkbenchData();
    } catch (error) {
      toast.current?.show({
        severity: 'error',
        summary: 'Batch Action Failed',
        detail: `Failed to ${action} selected tasks. Please try again.`,
        life: 5000
      });
    }
  };

  // Smart batch processing: find similar tasks
  const findSimilarTasks = (referenceTask: WorkbenchTask): WorkbenchTask[] => {
    return tasks.filter(task => {
      if (task.id === referenceTask.id) return false;
      
      // Same platform and similar confidence
      const samePlatform = task.platform === referenceTask.platform;
      const similarConfidence = Math.abs(task.confidence - referenceTask.confidence) < 10;
      const samePriority = task.priority === referenceTask.priority;
      const sameProfile = task.profileName === referenceTask.profileName;
      
      // Score similarity (0-100)
      let similarityScore = 0;
      if (samePlatform) similarityScore += 30;
      if (similarConfidence) similarityScore += 25;
      if (samePriority) similarityScore += 20;
      if (sameProfile) similarityScore += 25;
      
      return similarityScore >= 50; // 50% similarity threshold
    });
  };

  // Smart batch suggestions
  const getBatchSuggestions = (): { action: string; taskIds: string[]; reason: string; confidence: number }[] => {
    const suggestions = [];
    
    // High confidence auto-approve suggestion
    const highConfidenceTasks = tasks.filter(t => 
      t.confidence > 90 && 
      t.type === 'new_detection' && 
      t.suggestedAction === 'auto_approve'
    );
    
    if (highConfidenceTasks.length >= 3) {
      suggestions.push({
        action: 'approve',
        taskIds: highConfidenceTasks.map(t => t.id),
        reason: `${highConfidenceTasks.length} high-confidence matches (>90%) ready for automatic approval`,
        confidence: 95
      });
    }

    // Same platform batch suggestion
    const platformGroups = tasks.reduce((acc, task) => {
      if (task.type === 'new_detection' && task.confidence > 80) {
        acc[task.platform] = acc[task.platform] || [];
        acc[task.platform].push(task);
      }
      return acc;
    }, {} as Record<string, WorkbenchTask[]>);

    Object.entries(platformGroups).forEach(([platform, platformTasks]) => {
      if (platformTasks.length >= 5) {
        suggestions.push({
          action: 'takedown',
          taskIds: platformTasks.map(t => t.id),
          reason: `${platformTasks.length} similar infringements on ${platform} ready for bulk takedown`,
          confidence: 85
        });
      }
    });

    // Low confidence false positive suggestion
    const lowConfidenceTasks = tasks.filter(t => 
      t.confidence < 65 && 
      t.type === 'new_detection'
    );
    
    if (lowConfidenceTasks.length >= 3) {
      suggestions.push({
        action: 'reject',
        taskIds: lowConfidenceTasks.map(t => t.id),
        reason: `${lowConfidenceTasks.length} low-confidence matches (<65%) likely false positives`,
        confidence: 75
      });
    }

    return suggestions.sort((a, b) => b.confidence - a.confidence);
  };

  if (loading) {
    return (
      <div className="workbench-container">
        <div className="workbench-header">
          <Skeleton width="300px" height="2rem" className="mb-2" />
          <Skeleton width="500px" height="1rem" />
        </div>
        <div className="workbench-filters mb-4">
          <div className="grid">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="col-12 md:col-3">
                <Skeleton height="3rem" />
              </div>
            ))}
          </div>
        </div>
        <div className="workbench-lanes">
          <div className="grid">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="col-12 lg:col-3">
                <Skeleton height="400px" />
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="workbench-container">
      <Toast ref={toast} />
      <ConfirmDialog />
      
      {/* Header Section with Daily Digest */}
      <div className="workbench-header">
        <div className="flex align-items-start justify-content-between">
          <div>
            <h1 className="workbench-title">Content Protection Workbench</h1>
            <p className="workbench-subtitle">
              AI-powered unified workflow for efficient content protection management
            </p>
          </div>
          <div className="experience-level-selector">
            <Dropdown
              value={userExperienceLevel}
              options={[
                { label: 'Basic', value: 'basic', icon: 'pi pi-user' },
                { label: 'Intermediate', value: 'intermediate', icon: 'pi pi-cog' },
                { label: 'Advanced', value: 'advanced', icon: 'pi pi-wrench' }
              ]}
              onChange={(e) => {
                setUserExperienceLevel(e.value);
                localStorage.setItem('userExperienceLevel', e.value);
              }}
              itemTemplate={(option) => (
                <div className="flex align-items-center gap-2">
                  <i className={option.icon} />
                  <span>{option.label}</span>
                </div>
              )}
              placeholder="Experience Level"
            />
          </div>
        </div>
        
        {/* Daily Digest */}
        {dailyDigest && (
          <div className="daily-digest mt-4">
            <Card className="border-left-3 border-primary-500">
              <div className="flex align-items-start gap-3">
                <i className="pi pi-calendar-plus text-primary-600 text-xl mt-1" />
                <div>
                  <h4 className="m-0 mb-2 text-primary-700">Today's Summary</h4>
                  <div className="white-space-pre-line text-600" style={{ fontSize: '0.9rem' }}>
                    {dailyDigest}
                  </div>
                </div>
              </div>
            </Card>
          </div>
        )}
      </div>

      {/* Enhanced Smart Grouping Panel */}
      {showSmartGrouping && smartGroupings.length > 0 && getVisibleFeatures().showSmartGrouping && (
        <div className="smart-grouping-panel mb-4">
          <Accordion activeIndex={0}>
            <AccordionTab 
              header={
                <div className="flex align-items-center gap-2">
                  <i className="pi pi-brain text-primary-500" />
                  <span className="font-semibold">AI Smart Grouping Suggestions</span>
                  <Badge value={smartGroupings.length} />
                </div>
              }
            >
              <div className="grid">
                {smartGroupings.slice(0, getVisibleFeatures().maxGroupingSuggestions).map((grouping, index) => (
                  <div key={grouping.id} className="col-12 md:col-6 xl:col-4">
                    <Card 
                      className={`smart-grouping-card h-full cursor-pointer transition-all duration-200 ${
                        selectedTasks.some(id => grouping.taskIds.includes(id)) ? 'border-primary-500 bg-primary-50' : 'border-200 hover:border-primary-300'
                      }`}
                      onClick={() => handleSelectSmartGroup(grouping)}
                    >
                      <div className="flex align-items-start gap-3">
                        <div className="flex-shrink-0">
                          <div className="w-3rem h-3rem bg-primary-100 border-round flex align-items-center justify-content-center">
                            <i className={`pi pi-${grouping.suggestedAction === 'batch_takedown' ? 'send' : 'sitemap'} text-primary-600 text-lg`} />
                          </div>
                        </div>
                        <div className="flex-1">
                          <div className="flex align-items-center gap-2 mb-2">
                            <Tag 
                              value={`${grouping.confidence}% confidence`} 
                              severity="success"
                              icon="pi pi-chart-line"
                            />
                            <Badge value={`${grouping.taskIds.length} tasks`} severity="info" />
                          </div>
                          <div className="text-sm line-height-3 mb-3 text-700">
                            {grouping.reason}
                          </div>
                          
                          {/* Common attributes */}
                          <div className="flex flex-wrap gap-1 mb-3">
                            {grouping.commonAttributes.platform && (
                              <Chip label={grouping.commonAttributes.platform} className="p-chip-sm" />
                            )}
                            {grouping.commonAttributes.profile && (
                              <Chip label={grouping.commonAttributes.profile} className="p-chip-sm" />
                            )}
                            {grouping.commonAttributes.contentType && (
                              <Chip label={grouping.commonAttributes.contentType} className="p-chip-sm" />
                            )}
                          </div>
                          
                          <div className="flex gap-2">
                            <Button
                              label="Select Group"
                              icon="pi pi-check"
                              size="small"
                              className="flex-1"
                              severity="info"
                              outlined
                              onClick={(e) => {
                                e.stopPropagation();
                                handleSelectSmartGroup(grouping);
                              }}
                            />
                            <Button
                              label="Process"
                              icon="pi pi-cog"
                              size="small"
                              severity="success"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleBatchAction(grouping.taskIds, grouping.suggestedAction);
                              }}
                            />
                          </div>
                        </div>
                      </div>
                    </Card>
                  </div>
                ))}
              </div>
              
              {smartGroupings.length > getVisibleFeatures().maxGroupingSuggestions && (
                <div className="text-center mt-3">
                  <Button
                    label={`Show ${smartGroupings.length - getVisibleFeatures().maxGroupingSuggestions} More Suggestions`}
                    icon="pi pi-angle-down"
                    link
                    onClick={() => setShowSmartGrouping(false)}
                  />
                </div>
              )}
            </AccordionTab>
          </Accordion>
        </div>
      )}

      {/* Enhanced Workbench Controls */}
      <div className="workbench-controls mb-4">
        <div className="workbench-toolbar">
          <div className="toolbar-row">
            <div className="search-container">
              <InputText 
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search tasks, platforms, or profiles..."
                className="search-input"
                aria-label="Search tasks"
              />
              <i className="pi pi-search search-icon" aria-hidden="true" />
            </div>
            
            <div className="view-toggle" role="tablist" aria-label="View options">
              {viewOptions.map((option) => (
                <button
                  key={option.value}
                  className={`view-option ${activeView === option.value ? 'active' : ''}`}
                  onClick={() => setActiveView(option.value)}
                  role="tab"
                  aria-selected={activeView === option.value}
                  aria-label={option.label}
                >
                  <i className={option.icon} aria-hidden="true" />
                  <span>{option.label}</span>
                </button>
              ))}
            </div>
          </div>
          
          {/* Automation Controls Row */}
          <div className="toolbar-row">
            <div className="automation-controls flex align-items-center gap-4 flex-wrap">
              {/* Quick Action Buttons */}
              <div className="quick-actions-group">
                <Button
                  label="Select All High-Confidence"
                  icon="pi pi-star"
                  size="small"
                  severity="success"
                  outlined
                  onClick={handleSelectHighConfidence}
                  disabled={tasks.filter(t => t.confidence > 90).length === 0}
                />
                
                {selectedTasks.length > 0 && (
                  <Button
                    label={`Process ${selectedTasks.length} Selected`}
                    icon="pi pi-cog"
                    size="small"
                    severity="info"
                    className="ml-2"
                    onClick={() => {
                      // Determine best action for selected tasks
                      const selectedTasksData = tasks.filter(t => selectedTasks.includes(t.id));
                      const highConfidence = selectedTasksData.filter(t => t.confidence > 90);
                      const action = highConfidence.length > selectedTasksData.length / 2 ? 'approve' : 'review';
                      handleBatchAction(selectedTasks, action);
                    }}
                  />
                )}
              </div>
              
              {/* Action Required Filter */}
              <div className="filter-controls">
                <ToggleButton
                  checked={hideActionNotRequired}
                  onChange={(e) => setHideActionNotRequired(e.value)}
                  onLabel="Show Action Required Only"
                  offLabel="Show All Tasks"
                  onIcon="pi pi-filter"
                  offIcon="pi pi-list"
                  className="p-button-sm"
                />
              </div>
              
              {/* Progressive Disclosure Toggle */}
              {getVisibleFeatures().showAutomationSettings && (
                <div className="automation-settings">
                  <Button
                    icon="pi pi-cog"
                    label="Automation Settings"
                    size="small"
                    text
                    onClick={() => {
                      // Open automation settings modal (would implement separately)
                      toast.current?.show({
                        severity: 'info',
                        summary: 'Automation Settings',
                        detail: 'Advanced automation settings coming soon',
                        life: 3000
                      });
                    }}
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* AI Insights Panel */}
      <div className="ai-insights">
        <div className="ai-insights-header">
          <h3 className="ai-insights-title">AI Insights</h3>
          <span className="ai-badge">AI</span>
        </div>
        <div className="insights-grid">
          <div className="insight-metric">
            <div className="metric-value">{prioritizedTasks.length}</div>
            <div className="metric-label">Active Tasks</div>
            <div className="metric-change positive">+12% vs yesterday</div>
          </div>
          <div className="insight-metric">
            <div className="metric-value">
              {Math.round(prioritizedTasks.reduce((sum, task) => sum + task.confidence, 0) / (prioritizedTasks.length || 1))}%
            </div>
            <div className="metric-label">Avg Confidence</div>
            <div className="metric-change positive">+5% improvement</div>
          </div>
          <div className="insight-metric">
            <div className="metric-value">
              {prioritizedTasks.filter(t => t.suggestedAction === 'auto_approve').length}
            </div>
            <div className="metric-label">Auto-Approve Ready</div>
            <div className="metric-change positive">Ready for action</div>
          </div>
          <div className="insight-metric">
            <div className="metric-value">
              {workflowLanes.find(l => l.id === 'new_detection')?.tasks.length || 0}
            </div>
            <div className="metric-label">Pending Review</div>
            <div className="metric-change negative">-3 vs yesterday</div>
          </div>
        </div>
      </div>

      {/* Floating Bulk Actions Bar */}
      {selectedTasks.length > 0 && (
        <div className="bulk-actions">
          <div className="bulk-count">
            {selectedTasks.length} task{selectedTasks.length > 1 ? 's' : ''} selected
          </div>
          <div className="bulk-actions-buttons">
            <button 
              className="bulk-action-btn"
              onClick={() => handleBatchAction(selectedTasks, 'similar_batch')}
              title="Find similar tasks for batch processing"
            >
              <i className="pi pi-sitemap" />
              Find Similar
            </button>
            <button 
              className="bulk-action-btn primary"
              onClick={() => handleBatchAction(selectedTasks, 'approve')}
            >
              <i className="pi pi-check" />
              Approve Selected
            </button>
            <button 
              className="bulk-action-btn"
              onClick={() => handleBatchAction(selectedTasks, 'reject')}
            >
              <i className="pi pi-times" />
              Reject Selected
            </button>
            <button 
              className="bulk-action-btn"
              onClick={() => handleBatchAction(selectedTasks, 'takedown')}
            >
              <i className="pi pi-file" />
              Bulk Takedown
            </button>
            <button 
              className="bulk-action-btn"
              onClick={() => setSelectedTasks([])}
              title="Clear selection"
            >
              <i className="pi pi-times" />
            </button>
          </div>
        </div>
      )}

      {/* Workflow Lanes */}
      {activeView === 'kanban' && (
        <div className="kanban-container" role="main" aria-label="Content protection workflow">
          {workflowLanes.map((lane) => (
            <div key={lane.id} className="kanban-lane" role="region" aria-labelledby={`lane-title-${lane.id}`}>
              <div className="lane-header">
                <div className="lane-title-group">
                  <i className={`lane-icon ${lane.color} ${lane.icon}`} aria-hidden="true" />
                  <div>
                    <h3 id={`lane-title-${lane.id}`} className="lane-title">{lane.title}</h3>
                    <p className="lane-subtitle">{lane.subtitle}</p>
                  </div>
                </div>
                <div className="lane-count" aria-label={`${lane.tasks.length} tasks`}>
                  {lane.tasks.length}
                </div>
              </div>
              <div className="lane-tasks" role="list">
                {lane.tasks.length === 0 ? (
                  <div className="empty-state">
                    <i className="empty-state-icon pi pi-inbox" aria-hidden="true" />
                    <h4 className="empty-state-title">No tasks in this lane</h4>
                    <p className="empty-state-description">Tasks will appear here as they progress through the workflow</p>
                  </div>
                ) : (
                  lane.tasks.map((task) => (
                    <EnhancedTaskCard
                      key={task.id}
                      task={task}
                      selected={selectedTasks.includes(task.id)}
                      onAction={handleTaskAction}
                      onSelect={(taskId, selected) => {
                        setSelectedTasks(prev => 
                          selected 
                            ? [...prev, taskId]
                            : prev.filter(id => id !== taskId)
                        );
                      }}
                    />
                  ))
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Priority List View */}
      {activeView === 'list' && (
        <PriorityListView
          tasks={prioritizedTasks}
          onTaskAction={handleTaskAction}
          onTaskSelect={(taskId, selected) => {
            setSelectedTasks(prev => 
              selected 
                ? [...prev, taskId]
                : prev.filter(id => id !== taskId)
            );
          }}
          selectedTasks={selectedTasks}
        />
      )}

      {/* Quick Actions View */}
      {activeView === 'quick' && (
        <QuickActionsView
          tasks={prioritizedTasks.filter(t => t.suggestedAction === 'auto_approve' || t.suggestedAction === 'batch_process')}
          onBatchAction={handleBatchAction}
          onTaskAction={handleTaskAction}
        />
      )}
    </div>
  );
};

// Enhanced WorkflowLane with guided workflow features
const WorkflowLane: React.FC<{
  lane: WorkbenchLane;
  onTaskAction: (taskId: string, action: string) => void;
  onTaskSelect: (taskId: string, selected: boolean) => void;
  selectedTasks: string[];
}> = ({ lane, onTaskAction, onTaskSelect, selectedTasks }) => {
  const [showGuidance, setShowGuidance] = useState(true);

  // Get lane-specific guidance and suggestions
  const getLaneGuidance = (laneId: string) => {
    const guidanceMap: Record<string, { 
      title: string; 
      description: string; 
      quickActions: { label: string; action: string; icon: string; severity?: string }[];
      tips: string[];
    }> = {
      new_detection: {
        title: "Review & Process New Detections",
        description: "Evaluate AI-detected potential infringements and decide on appropriate actions.",
        quickActions: [
          { label: "Auto-approve High Confidence (>90%)", action: "auto_approve_high", icon: "pi pi-check", severity: "success" },
          { label: "Reject Low Confidence (<60%)", action: "auto_reject_low", icon: "pi pi-times", severity: "secondary" },
          { label: "Batch Similar Tasks", action: "batch_similar", icon: "pi pi-sitemap" }
        ],
        tips: [
          "Focus on high-confidence matches first",
          "Use batch processing for similar platforms",
          "Check content previews before approving"
        ]
      },
      in_progress: {
        title: "Monitor Active Takedowns",
        description: "Track the progress of submitted takedown requests and follow up when needed.",
        quickActions: [
          { label: "Check All Statuses", action: "check_statuses", icon: "pi pi-refresh" },
          { label: "Send Follow-ups", action: "send_followups", icon: "pi pi-send", severity: "warning" },
          { label: "Escalate Overdue", action: "escalate_overdue", icon: "pi pi-exclamation-triangle", severity: "danger" }
        ],
        tips: [
          "Follow up on requests older than 7 days",
          "Most platforms respond within 2-5 business days",
          "Document all communications"
        ]
      },
      awaiting_response: {
        title: "Platform Review Pending",
        description: "Takedown requests submitted and awaiting platform review and action.",
        quickActions: [
          { label: "Send Reminders", action: "send_reminders", icon: "pi pi-bell", severity: "info" },
          { label: "Escalate to Legal", action: "escalate_legal", icon: "pi pi-briefcase", severity: "warning" },
          { label: "Update Timelines", action: "update_timelines", icon: "pi pi-calendar" }
        ],
        tips: [
          "Average response time: 3-7 business days",
          "Consider escalation after 14 days",
          "Keep evidence readily available"
        ]
      },
      completed: {
        title: "Resolved Cases Archive",
        description: "Successfully resolved infringement cases and takedown requests.",
        quickActions: [
          { label: "Generate Report", action: "generate_report", icon: "pi pi-file-pdf" },
          { label: "Archive Old Cases", action: "archive_old", icon: "pi pi-archive" },
          { label: "Analyze Success Metrics", action: "analyze_metrics", icon: "pi pi-chart-bar", severity: "success" }
        ],
        tips: [
          "Review success patterns for future optimization",
          "Archive cases older than 90 days",
          "Use data to improve detection algorithms"
        ]
      }
    };
    
    return guidanceMap[laneId] || {
      title: "Workflow Lane",
      description: "Manage tasks in this workflow stage.",
      quickActions: [],
      tips: []
    };
  };

  const guidance = getLaneGuidance(lane.id);
  const selectedInLane = lane.tasks.filter(task => selectedTasks.includes(task.id)).length;

  // Calculate progress metrics for the lane
  const getProgressMetrics = () => {
    const total = lane.tasks.length;
    if (total === 0) return { progress: 0, statusText: "No tasks" };

    switch (lane.id) {
      case 'new_detection':
        const highConfidence = lane.tasks.filter(t => t.confidence > 90).length;
        const progress = total > 0 ? Math.round((highConfidence / total) * 100) : 0;
        return { progress, statusText: `${highConfidence} high-confidence of ${total} total` };
      
      case 'in_progress':
        const recent = lane.tasks.filter(t => {
          const daysSince = (new Date().getTime() - t.lastUpdated.getTime()) / (1000 * 60 * 60 * 24);
          return daysSince < 7;
        }).length;
        const progressPercent = total > 0 ? Math.round((recent / total) * 100) : 0;
        return { progress: progressPercent, statusText: `${recent} recent updates of ${total} active` };
      
      case 'awaiting_response':
        const overdue = lane.tasks.filter(t => {
          const daysSince = (new Date().getTime() - t.lastUpdated.getTime()) / (1000 * 60 * 60 * 24);
          return daysSince > 7;
        }).length;
        const overduePercent = total > 0 ? Math.round((overdue / total) * 100) : 0;
        return { progress: 100 - overduePercent, statusText: `${overdue} overdue of ${total} pending` };
      
      default:
        return { progress: 100, statusText: `${total} completed` };
    }
  };

  const { progress, statusText } = getProgressMetrics();

  const handleLaneQuickAction = async (action: string) => {
    const laneTaskIds = lane.tasks.map(t => t.id);
    
    switch (action) {
      case 'auto_approve_high':
        const highConfidenceTasks = lane.tasks.filter(t => t.confidence > 90).map(t => t.id);
        if (highConfidenceTasks.length > 0) {
          await onTaskAction(highConfidenceTasks[0], 'batch_approve_high_confidence');
        }
        break;
      case 'auto_reject_low':
        const lowConfidenceTasks = lane.tasks.filter(t => t.confidence < 60).map(t => t.id);
        if (lowConfidenceTasks.length > 0) {
          await onTaskAction(lowConfidenceTasks[0], 'batch_reject_low_confidence');
        }
        break;
      default:
        if (laneTaskIds.length > 0) {
          await onTaskAction(laneTaskIds[0], action);
        }
    }
  };

  return (
    <Card className={`workflow-lane border-top-3 border-${lane.color}-500 h-full`}>
      {/* Enhanced Lane Header with Progress */}
      <div className="lane-header">
        <div className="flex align-items-center justify-content-between mb-2">
          <div className="flex align-items-center gap-2">
            <i className={`${lane.icon} text-${lane.color}-500 text-lg`} />
            <div>
              <div className="font-semibold text-base">{lane.title}</div>
              <div className="text-600 text-sm">{lane.subtitle}</div>
            </div>
          </div>
          <div className="flex align-items-center gap-2">
            {selectedInLane > 0 && (
              <Badge value={`${selectedInLane} selected`} severity="info" />
            )}
            <Badge value={lane.tasks.length} severity={lane.color as any} />
          </div>
        </div>

        {/* Progress Bar */}
        <div className="progress-section mb-2">
          <div className="flex align-items-center justify-content-between mb-1">
            <span className="text-xs text-600">{statusText}</span>
            <span className="text-xs text-600">{progress}%</span>
          </div>
          <ProgressBar 
            value={progress} 
            className="h-1rem"
            pt={{
              value: {
                style: {
                  background: lane.color === 'orange' ? 'var(--orange-500)' :
                            lane.color === 'blue' ? 'var(--blue-500)' :
                            lane.color === 'purple' ? 'var(--purple-500)' :
                            'var(--green-500)'
                }
              }
            }}
          />
        </div>

        {/* Guidance Panel (collapsible) */}
        {showGuidance && guidance.quickActions.length > 0 && (
          <Panel 
            header={guidance.title}
            toggleable
            collapsed={!showGuidance}
            onToggle={() => setShowGuidance(!showGuidance)}
            className="lane-guidance mb-3"
            pt={{
              header: { className: "p-2" },
              content: { className: "p-2" }
            }}
          >
            <div className="text-sm text-600 mb-2">{guidance.description}</div>
            
            {/* Quick Actions */}
            <div className="quick-actions-grid mb-2">
              {guidance.quickActions.map((quickAction, index) => (
                <Button
                  key={index}
                  label={quickAction.label}
                  icon={quickAction.icon}
                  size="small"
                  outlined
                  severity={quickAction.severity as any}
                  className="w-full mb-1"
                  onClick={() => handleLaneQuickAction(quickAction.action)}
                  disabled={lane.tasks.length === 0}
                />
              ))}
            </div>

            {/* Tips */}
            {guidance.tips.length > 0 && (
              <div className="tips-section">
                <div className="text-xs font-semibold text-600 mb-1">💡 Tips:</div>
                {guidance.tips.map((tip, index) => (
                  <div key={index} className="text-xs text-600 mb-1">• {tip}</div>
                ))}
              </div>
            )}
          </Panel>
        )}
      </div>
      
      {/* Tasks List */}
      <div className="lane-tasks" style={{ maxHeight: '600px', overflowY: 'auto' }}>
        {lane.tasks.map((task) => (
          <TaskCard
            key={task.id}
            task={task}
            onAction={onTaskAction}
            onSelect={onTaskSelect}
            selected={selectedTasks.includes(task.id)}
            showBatchSelect={lane.showBatchActions}
          />
        ))}
        
        {/* Empty State with Guidance */}
        {lane.tasks.length === 0 && (
          <div className="empty-lane">
            <div className="text-center py-6">
              <i className={`${lane.icon} text-6xl text-${lane.color}-300 mb-3`} />
              <div className="font-semibold text-lg mb-2">No tasks in {lane.title}</div>
              <div className="text-600 text-sm mb-3">
                {lane.id === 'new_detection' && "Great! No new infringements detected."}
                {lane.id === 'in_progress' && "No takedown requests are currently being processed."}
                {lane.id === 'awaiting_response' && "No pending responses from platforms."}
                {lane.id === 'completed' && "No completed cases to show."}
              </div>
              {lane.id === 'new_detection' && (
                <div className="text-xs text-500">
                  New detections will appear here as our AI monitors your protected content.
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </Card>
  );
};

// Enhanced TaskCard with full contextual information
const TaskCard: React.FC<{
  task: WorkbenchTask;
  onAction: (taskId: string, action: string) => void;
  onSelect: (taskId: string, selected: boolean) => void;
  selected: boolean;
  showBatchSelect: boolean;
}> = ({ task, onAction, onSelect, selected, showBatchSelect }) => {
  const [expanded, setExpanded] = useState(false);
  const [showThumbnails, setShowThumbnails] = useState(false);

  const getConfidenceColor = (confidence: number) => {
    if (confidence > 90) return 'success';
    if (confidence > 70) return 'warning';
    return 'danger';
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical': return 'danger';
      case 'high': return 'warning';
      case 'medium': return 'info';
      case 'low': return 'secondary';
      default: return 'info';
    }
  };

  const getEstimatedImpactIcon = (impact: string) => {
    switch (impact) {
      case 'high': return 'pi pi-exclamation-triangle';
      case 'medium': return 'pi pi-info-circle';
      case 'low': return 'pi pi-minus-circle';
      default: return 'pi pi-info-circle';
    }
  };

  const formatDate = (date: Date) => {
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);

    if (diffHours < 1) return 'Just now';
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const cardClasses = [
    'task-card',
    'mb-3',
    selected ? 'selected' : '',
    `task-priority-${task.priority}`,
    task.confidence > 90 ? 'confidence-high' : 
    task.confidence > 70 ? 'confidence-medium' : 'confidence-low'
  ].filter(Boolean).join(' ');

  return (
    <Card className={cardClasses}>
      <div className="task-content">
        {/* Header with selection and key metrics */}
        <div className="task-header flex align-items-start gap-2 mb-2">
          {showBatchSelect && (
            <Checkbox
              checked={selected}
              onChange={(e) => onSelect(task.id, e.checked || false)}
              className="mt-1"
            />
          )}
          
          <div className="flex-1">
            {/* Priority and confidence indicators */}
            <div className="flex align-items-center justify-content-between mb-2">
              <div className="flex align-items-center gap-2">
                <Tag 
                  value={`${task.confidence}%`} 
                  severity={getConfidenceColor(task.confidence)}
                  icon="pi pi-chart-line"
                />
                <Tag 
                  value={task.priority.toUpperCase()} 
                  severity={getPriorityColor(task.priority)}
                />
                <i 
                  className={`${getEstimatedImpactIcon(task.estimatedImpact)} text-${task.estimatedImpact === 'high' ? 'red' : task.estimatedImpact === 'medium' ? 'orange' : 'blue'}-500`}
                  title={`Estimated impact: ${task.estimatedImpact}`}
                />
              </div>
              <div className="text-xs text-600">
                {formatDate(task.detectedAt)}
              </div>
            </div>

            {/* Content preview */}
            <div className="task-content-preview mb-2">
              <div className="font-semibold text-sm mb-1 line-height-3">{task.title}</div>
              <div className="text-600 text-xs line-height-3">{task.description}</div>
            </div>

            {/* Platform and engagement info */}
            <div className="flex align-items-center justify-content-between mb-2">
              <div className="flex align-items-center gap-2">
                <div className={`platform-icon platform-${task.platform.toLowerCase()}`}>
                  <i className={task.platformIcon} />
                </div>
                <span className="text-sm font-medium">{task.platform}</span>
                <Chip 
                  label={task.profileName} 
                  className="text-xs p-chip-sm"
                />
              </div>
              {task.metadata.engagement && (
                <div className="flex align-items-center gap-2 text-xs">
                  {task.metadata.engagement.views && (
                    <span title="Views">
                      <i className="pi pi-eye" /> {task.metadata.engagement.views.toLocaleString()}
                    </span>
                  )}
                  {task.metadata.engagement.likes && (
                    <span title="Likes" className="text-red-500">
                      <i className="pi pi-heart" /> {task.metadata.engagement.likes}
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* AI Reasoning (collapsible) */}
        {task.aiReasoning && (
          <div className="ai-suggestion mb-2">
            <div className="flex align-items-center gap-2 mb-1">
              <i className="pi pi-brain text-blue-500" />
              <span className="font-semibold text-blue-700">AI Analysis</span>
              <Button
                icon={expanded ? "pi pi-chevron-up" : "pi pi-chevron-down"}
                className="p-button-text p-button-sm"
                onClick={() => setExpanded(!expanded)}
                style={{ padding: '0.25rem' }}
              />
            </div>
            {expanded && (
              <div className="text-xs line-height-3 mt-2">
                {task.aiReasoning}
              </div>
            )}
          </div>
        )}

        {/* Thumbnails preview (expandable) */}
        {task.thumbnail && (
          <div className="thumbnail-section mb-2">
            <div className="flex align-items-center gap-2 mb-1">
              <span className="text-xs text-600">Content Preview</span>
              <Button
                icon="pi pi-images"
                label={showThumbnails ? "Hide" : "Show"}
                className="p-button-text p-button-sm"
                onClick={() => setShowThumbnails(!showThumbnails)}
                style={{ padding: '0.25rem 0.5rem', fontSize: '0.7rem' }}
              />
            </div>
            {showThumbnails && (
              <div className="flex gap-2">
                <img 
                  src={task.thumbnail} 
                  alt="Infringing content"
                  className="thumbnail-preview border-round"
                  style={{ width: '60px', height: '60px', objectFit: 'cover' }}
                />
                {task.originalContentUrl && (
                  <>
                    <div className="flex align-items-center">
                      <i className="pi pi-arrow-right text-600" />
                    </div>
                    <img 
                      src={task.originalContentUrl} 
                      alt="Original content"
                      className="thumbnail-preview border-round"
                      style={{ width: '60px', height: '60px', objectFit: 'cover' }}
                    />
                  </>
                )}
              </div>
            )}
          </div>
        )}

        {/* Takedown status if exists */}
        {task.takedownRequest && (
          <div className="takedown-status mb-2 p-2 border-round" style={{ background: 'var(--blue-50)', border: '1px solid var(--blue-200)' }}>
            <div className="flex align-items-center gap-2">
              <i className="pi pi-file text-blue-600" />
              <span className="text-xs text-blue-700 font-medium">
                Takedown: {task.takedownRequest.status.toUpperCase()}
              </span>
              {task.takedownRequest.sentAt && (
                <span className="text-xs text-600">
                  Sent {formatDate(task.takedownRequest.sentAt)}
                </span>
              )}
            </div>
          </div>
        )}

        {/* Tags */}
        {task.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-2">
            {task.tags.slice(0, 3).map((tag, index) => (
              <Chip 
                key={index}
                label={tag} 
                className="text-xs p-chip-sm"
                style={{ fontSize: '0.65rem', padding: '0.2rem 0.4rem' }}
              />
            ))}
            {task.tags.length > 3 && (
              <Chip 
                label={`+${task.tags.length - 3}`} 
                className="text-xs p-chip-sm"
                style={{ fontSize: '0.65rem', padding: '0.2rem 0.4rem' }}
              />
            )}
          </div>
        )}

        {/* Action buttons with contextual actions */}
        <div className="task-actions">
          <div className="flex gap-1">
            {/* Primary suggested action */}
            {task.suggestedAction === 'auto_approve' && (
              <Button 
                label="Quick Approve" 
                icon="pi pi-check"
                size="small" 
                className="flex-1"
                onClick={() => onAction(task.id, 'approve')}
                severity="success"
              />
            )}
            {task.suggestedAction === 'batch_process' && (
              <Button 
                label="Add to Batch" 
                icon="pi pi-plus"
                size="small" 
                className="flex-1"
                onClick={() => onAction(task.id, 'add_to_batch')}
              />
            )}
            {task.suggestedAction === 'auto_reject' && (
              <Button 
                label="Mark False Positive" 
                icon="pi pi-times"
                size="small" 
                className="flex-1"
                onClick={() => onAction(task.id, 'reject')}
                severity="secondary"
              />
            )}
            
            {/* Secondary actions */}
            <Button 
              icon="pi pi-eye" 
              size="small" 
              outlined
              onClick={() => onAction(task.id, 'review')}
              tooltip="Review Details"
              className="p-button-sm"
            />
            <Button 
              icon="pi pi-external-link" 
              size="small" 
              outlined
              onClick={() => window.open(task.infringingUrl, '_blank')}
              tooltip="View Content"
              className="p-button-sm"
            />
          </div>
          
          {/* Manual takedown option for medium confidence */}
          {task.confidence > 60 && task.confidence < 90 && !task.takedownRequest && (
            <div className="mt-2">
              <Button 
                label="Send Takedown Request" 
                icon="pi pi-send"
                size="small" 
                className="w-full"
                severity="warning"
                onClick={() => onAction(task.id, 'send_takedown')}
              />
            </div>
          )}
        </div>
      </div>
    </Card>
  );
};

const PriorityListView: React.FC<{
  tasks: WorkbenchTask[];
  onTaskAction: (taskId: string, action: string) => void;
  onTaskSelect: (taskId: string, selected: boolean) => void;
  selectedTasks: string[];
}> = ({ tasks }) => {
  return <div>Priority List View - To be implemented</div>;
};

const QuickActionsView: React.FC<{
  tasks: WorkbenchTask[];
  onBatchAction: (taskIds: string[], action: string) => void;
  onTaskAction: (taskId: string, action: string) => void;
}> = ({ tasks, onBatchAction, onTaskAction }) => {
  const [processing, setProcessing] = useState(false);

  // Categorize tasks for quick actions
  const highConfidenceTasks = tasks.filter(t => t.confidence > 90);
  const autoApproveTasks = tasks.filter(t => t.suggestedAction === 'auto_approve');
  const batchProcessTasks = tasks.filter(t => t.suggestedAction === 'batch_process');
  const criticalTasks = tasks.filter(t => t.priority === 'critical');

  // Platform-specific groupings
  const platformGroups = tasks.reduce((acc, task) => {
    acc[task.platform] = acc[task.platform] || [];
    acc[task.platform].push(task);
    return acc;
  }, {} as Record<string, WorkbenchTask[]>);

  const handleOneClickAction = async (actionType: string, taskIds: string[]) => {
    setProcessing(true);
    try {
      switch (actionType) {
        case 'approve_all_high_confidence':
          await onBatchAction(taskIds, 'approve');
          break;
        case 'auto_takedown_critical':
          await onBatchAction(taskIds, 'takedown');
          break;
        case 'batch_platform':
          await onBatchAction(taskIds, 'takedown');
          break;
        default:
          if (taskIds.length === 1) {
            await onTaskAction(taskIds[0], actionType);
          }
      }
    } finally {
      setProcessing(false);
    }
  };

  const getConfidenceIcon = (confidence: number) => {
    if (confidence > 95) return { icon: 'pi pi-star-fill', color: 'text-yellow-500' };
    if (confidence > 90) return { icon: 'pi pi-check-circle', color: 'text-green-500' };
    return { icon: 'pi pi-exclamation-circle', color: 'text-orange-500' };
  };

  const getImpactColor = (impact: string) => {
    switch (impact) {
      case 'high': return 'red';
      case 'medium': return 'orange';
      case 'low': return 'blue';
      default: return 'gray';
    }
  };

  if (tasks.length === 0) {
    return (
      <div className="quick-actions-empty">
        <Card className="text-center p-6">
          <i className="pi pi-bolt text-6xl text-primary-300 mb-4" />
          <h3 className="text-2xl font-semibold mb-2">No Quick Actions Available</h3>
          <p className="text-600 text-lg">
            All tasks require manual review. Check the workflow lanes for tasks that need attention.
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div className="quick-actions-view">
      {/* One-Click Action Cards */}
      <div className="grid mb-4">
        {/* High Confidence Auto-Approve */}
        {highConfidenceTasks.length > 0 && (
          <div className="col-12 md:col-6 xl:col-4">
            <Card className="quick-action-card h-full border-left-3 border-green-500">
              <div className="flex align-items-start gap-3">
                <div className="quick-action-icon bg-green-100 text-green-600">
                  <i className="pi pi-check-circle text-2xl" />
                </div>
                <div className="flex-1">
                  <div className="flex align-items-center gap-2 mb-2">
                    <h4 className="font-semibold text-green-700 m-0">High Confidence Matches</h4>
                    <Badge value={highConfidenceTasks.length} severity="success" />
                  </div>
                  <p className="text-600 text-sm mb-3 line-height-3">
                    {highConfidenceTasks.length} cases with &gt;90% confidence ready for immediate approval
                  </p>
                  
                  {/* Preview of top tasks */}
                  <div className="mb-3">
                    {highConfidenceTasks.slice(0, 3).map((task, index) => (
                      <div key={task.id} className="flex align-items-center gap-2 mb-1">
                        <div className={`platform-icon platform-${task.platform.toLowerCase()}`}>
                          <i className={task.platformIcon} />
                        </div>
                        <span className="text-xs text-600 flex-1">{task.title}</span>
                        <Tag value={`${task.confidence}%`} severity="success" className="text-xs" />
                      </div>
                    ))}
                    {highConfidenceTasks.length > 3 && (
                      <div className="text-xs text-500 mt-2">
                        +{highConfidenceTasks.length - 3} more cases
                      </div>
                    )}
                  </div>

                  <Button
                    label="Approve All & Generate Takedowns"
                    icon="pi pi-send"
                    className="w-full p-button-success"
                    loading={processing}
                    onClick={() => handleOneClickAction('approve_all_high_confidence', highConfidenceTasks.map(t => t.id))}
                  />
                </div>
              </div>
            </Card>
          </div>
        )}

        {/* Critical Priority Cases */}
        {criticalTasks.length > 0 && (
          <div className="col-12 md:col-6 xl:col-4">
            <Card className="quick-action-card h-full border-left-3 border-red-500">
              <div className="flex align-items-start gap-3">
                <div className="quick-action-icon bg-red-100 text-red-600">
                  <i className="pi pi-exclamation-triangle text-2xl" />
                </div>
                <div className="flex-1">
                  <div className="flex align-items-center gap-2 mb-2">
                    <h4 className="font-semibold text-red-700 m-0">Critical Priority</h4>
                    <Badge value={criticalTasks.length} severity="danger" />
                  </div>
                  <p className="text-600 text-sm mb-3 line-height-3">
                    Urgent cases requiring immediate takedown action
                  </p>
                  
                  <div className="mb-3">
                    {criticalTasks.slice(0, 2).map((task, index) => (
                      <div key={task.id} className="flex align-items-center gap-2 mb-2">
                        <i className={getConfidenceIcon(task.confidence).icon + ' ' + getConfidenceIcon(task.confidence).color} />
                        <div className="flex-1">
                          <div className="font-semibold text-sm">{task.title}</div>
                          <div className="text-xs text-600">{task.platform} • {task.confidence}% confidence</div>
                        </div>
                        <Tag value={task.estimatedImpact.toUpperCase()} severity="danger" />
                      </div>
                    ))}
                  </div>

                  <Button
                    label="Process Critical Cases"
                    icon="pi pi-flash"
                    severity="danger"
                    className="w-full"
                    loading={processing}
                    onClick={() => handleOneClickAction('auto_takedown_critical', criticalTasks.map(t => t.id))}
                  />
                </div>
              </div>
            </Card>
          </div>
        )}

        {/* Platform Batch Processing */}
        {Object.entries(platformGroups)
          .filter(([platform, tasks]) => tasks.length >= 3)
          .slice(0, 2)
          .map(([platform, platformTasks]) => (
            <div key={platform} className="col-12 md:col-6 xl:col-4">
              <Card className="quick-action-card h-full border-left-3 border-blue-500">
                <div className="flex align-items-start gap-3">
                  <div className={`platform-icon platform-${platform.toLowerCase()}`} style={{ width: '48px', height: '48px', fontSize: '1.5rem' }}>
                    <i className={platformTasks[0].platformIcon} />
                  </div>
                  <div className="flex-1">
                    <div className="flex align-items-center gap-2 mb-2">
                      <h4 className="font-semibold text-blue-700 m-0 text-capitalize">{platform}</h4>
                      <Badge value={platformTasks.length} severity="info" />
                    </div>
                    <p className="text-600 text-sm mb-3 line-height-3">
                      Multiple similar infringements detected on {platform}
                    </p>
                    
                    {/* Statistics */}
                    <div className="grid mb-3">
                      <div className="col-6">
                        <div className="text-center">
                          <div className="text-lg font-bold text-blue-600">
                            {Math.round(platformTasks.reduce((sum, t) => sum + t.confidence, 0) / platformTasks.length)}%
                          </div>
                          <div className="text-xs text-600">Avg Confidence</div>
                        </div>
                      </div>
                      <div className="col-6">
                        <div className="text-center">
                          <div className="text-lg font-bold text-orange-600">
                            {platformTasks.filter(t => t.priority === 'high' || t.priority === 'critical').length}
                          </div>
                          <div className="text-xs text-600">High Priority</div>
                        </div>
                      </div>
                    </div>

                    <Button
                      label={`Process ${platform} Batch`}
                      icon="pi pi-send"
                      severity="info"
                      className="w-full"
                      loading={processing}
                      onClick={() => handleOneClickAction('batch_platform', platformTasks.map(t => t.id))}
                    />
                  </div>
                </div>
              </Card>
            </div>
          ))
        }
      </div>

      {/* Quick Action Buttons Bar */}
      <Card className="quick-actions-toolbar mb-4">
        <div className="flex align-items-center gap-3 flex-wrap">
          <div className="flex align-items-center gap-2 mr-4">
            <i className="pi pi-bolt text-primary text-xl" />
            <span className="font-semibold">One-Click Actions:</span>
          </div>
          
          {autoApproveTasks.length > 0 && (
            <Button
              label={`Auto-Approve ${autoApproveTasks.length}`}
              icon="pi pi-check"
              size="small"
              severity="success"
              loading={processing}
              onClick={() => handleOneClickAction('approve_all_high_confidence', autoApproveTasks.map(t => t.id))}
            />
          )}

          {batchProcessTasks.length > 0 && (
            <Button
              label={`Batch Process ${batchProcessTasks.length}`}
              icon="pi pi-sitemap"
              size="small"
              loading={processing}
              onClick={() => handleOneClickAction('batch_platform', batchProcessTasks.map(t => t.id))}
            />
          )}

          <Button
            label="Generate All Takedowns"
            icon="pi pi-file"
            size="small"
            severity="warning"
            loading={processing}
            onClick={() => handleOneClickAction('approve_all_high_confidence', tasks.filter(t => t.confidence > 80).map(t => t.id))}
          />
        </div>
      </Card>

      {/* Detailed Tasks List for Quick Actions */}
      <Card title="Tasks Ready for Quick Processing">
        <div className="grid">
          {tasks.slice(0, 12).map((task) => (
            <div key={task.id} className="col-12 md:col-6 xl:col-4 mb-3">
              <Card className="task-quick-card h-full">
                <div className="flex align-items-start gap-3">
                  <div className={`platform-icon platform-${task.platform.toLowerCase()}`}>
                    <i className={task.platformIcon} />
                  </div>
                  <div className="flex-1">
                    <div className="flex align-items-center gap-2 mb-1">
                      <Tag value={`${task.confidence}%`} severity={task.confidence > 90 ? 'success' : 'warning'} />
                      <Tag value={task.priority.toUpperCase()} severity={task.priority === 'critical' ? 'danger' : 'info'} />
                    </div>
                    <div className="font-semibold text-sm mb-1 line-height-3">{task.title}</div>
                    <div className="text-xs text-600 mb-2">{task.platform} • {task.profileName}</div>
                    
                    {task.suggestedAction === 'auto_approve' && (
                      <Button
                        label="Quick Approve"
                        icon="pi pi-check"
                        size="small"
                        className="w-full p-button-success p-button-sm"
                        loading={processing}
                        onClick={() => handleOneClickAction('approve', [task.id])}
                      />
                    )}
                    
                    {task.suggestedAction === 'batch_process' && (
                      <Button
                        label="Add to Batch"
                        icon="pi pi-plus"
                        size="small"
                        className="w-full p-button-sm"
                        loading={processing}
                        onClick={() => handleOneClickAction('add_to_batch', [task.id])}
                      />
                    )}
                  </div>
                </div>
              </Card>
            </div>
          ))}
        </div>
        
        {tasks.length > 12 && (
          <div className="text-center mt-4">
            <Button
              label={`Show ${tasks.length - 12} More Tasks`}
              icon="pi pi-angle-down"
              link
            />
          </div>
        )}
      </Card>
    </div>
  );
};

export default ContentProtectionWorkbench;