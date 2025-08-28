// High-Impact Automation Service
// Implements intelligent automation to reduce user workload by 80%+

import { WorkbenchTask } from '../components/workbench/ContentProtectionWorkbench';

export interface AutomationConfig {
  // Auto-approval settings
  autoApproveEnabled: boolean;
  autoApproveThreshold: number; // 0-100 confidence
  autoRejectThreshold: number; // Below this confidence
  
  // Auto-movement settings
  autoMoveEnabled: boolean;
  autoEscalateHours: number; // Hours before escalation
  
  // Batch processing settings
  smartGroupingEnabled: boolean;
  minGroupSize: number;
  
  // Learning preferences
  learnFromUserActions: boolean;
  adaptiveThresholds: boolean;
  
  // Time-based rules
  businessHoursOnly: boolean;
  weekendProcessing: boolean;
  
  // Platform-specific settings
  platformRules: Record<string, PlatformRule>;
}

export interface PlatformRule {
  platform: string;
  autoApproveThreshold: number;
  responseTimeoutHours: number;
  autoEscalate: boolean;
  preferredTemplate: string;
}

export interface SmartGrouping {
  id: string;
  reason: string;
  confidence: number;
  taskIds: string[];
  suggestedAction: string;
  commonAttributes: {
    platform?: string;
    profile?: string;
    contentType?: string;
    timeRange?: string;
    similarity?: number;
  };
}

export interface ActionRequired {
  priority: 'urgent' | 'high' | 'medium' | 'low';
  reason: string;
  taskIds: string[];
  suggestedAction: string;
  deadline?: Date;
}

class AutomationService {
  private config: AutomationConfig = {
    autoApproveEnabled: true,
    autoApproveThreshold: 90,
    autoRejectThreshold: 40,
    autoMoveEnabled: true,
    autoEscalateHours: 48,
    smartGroupingEnabled: true,
    minGroupSize: 3,
    learnFromUserActions: true,
    adaptiveThresholds: true,
    businessHoursOnly: false,
    weekendProcessing: true,
    platformRules: {
      'YouTube': {
        platform: 'YouTube',
        autoApproveThreshold: 85,
        responseTimeoutHours: 24,
        autoEscalate: true,
        preferredTemplate: 'youtube_standard'
      },
      'Instagram': {
        platform: 'Instagram',
        autoApproveThreshold: 90,
        responseTimeoutHours: 48,
        autoEscalate: true,
        preferredTemplate: 'meta_platform'
      },
      'TikTok': {
        platform: 'TikTok',
        autoApproveThreshold: 88,
        responseTimeoutHours: 36,
        autoEscalate: true,
        preferredTemplate: 'tiktok_copyright'
      }
    }
  };

  private userPatterns: Map<string, number> = new Map();
  private falsePositiveRate: Map<string, number> = new Map();

  // Auto-move cards between Kanban lanes based on AI confidence + response times
  autoMoveTasks(tasks: WorkbenchTask[]): WorkbenchTask[] {
    if (!this.config.autoMoveEnabled) return tasks;

    return tasks.map(task => {
      const updatedTask = { ...task };
      const hoursSinceDetection = (Date.now() - task.detectedAt.getTime()) / (1000 * 60 * 60);
      
      // Auto-approve high confidence tasks
      if (task.type === 'new_detection' && task.confidence >= this.config.autoApproveThreshold) {
        updatedTask.type = 'in_progress';
        updatedTask.suggestedAction = 'auto_approve';
      }
      
      // Auto-reject low confidence tasks
      if (task.type === 'new_detection' && task.confidence < this.config.autoRejectThreshold) {
        updatedTask.type = 'completed';
        updatedTask.suggestedAction = 'auto_reject';
      }
      
      // Auto-escalate stalled tasks
      if (task.type === 'awaiting_response' && hoursSinceDetection > this.config.autoEscalateHours) {
        updatedTask.priority = 'critical';
        updatedTask.suggestedAction = 'manual_review';
      }
      
      // Platform-specific rules
      const platformRule = this.config.platformRules[task.platform];
      if (platformRule) {
        if (task.confidence >= platformRule.autoApproveThreshold && task.type === 'new_detection') {
          updatedTask.type = 'in_progress';
          updatedTask.suggestedAction = 'auto_approve';
        }
        
        if (task.type === 'awaiting_response' && hoursSinceDetection > platformRule.responseTimeoutHours) {
          if (platformRule.autoEscalate) {
            updatedTask.priority = 'critical';
          }
        }
      }
      
      return updatedTask;
    });
  }

  // Smart grouping suggestions for batch processing
  findSmartGroupings(tasks: WorkbenchTask[]): SmartGrouping[] {
    if (!this.config.smartGroupingEnabled) return [];
    
    const groupings: SmartGrouping[] = [];
    
    // Group by platform and confidence
    const platformGroups = this.groupByPlatform(tasks);
    for (const [platform, platformTasks] of Object.entries(platformGroups)) {
      if (platformTasks.length >= this.config.minGroupSize) {
        const highConfidenceTasks = platformTasks.filter(t => t.confidence >= 80);
        if (highConfidenceTasks.length >= this.config.minGroupSize) {
          groupings.push({
            id: `platform-${platform}-high`,
            reason: `${highConfidenceTasks.length} high-confidence ${platform} infringements`,
            confidence: 95,
            taskIds: highConfidenceTasks.map(t => t.id),
            suggestedAction: 'batch_takedown',
            commonAttributes: {
              platform,
              similarity: this.calculateAverageSimilarity(highConfidenceTasks)
            }
          });
        }
      }
    }
    
    // Group by profile
    const profileGroups = this.groupByProfile(tasks);
    for (const [profile, profileTasks] of Object.entries(profileGroups)) {
      if (profileTasks.length >= this.config.minGroupSize) {
        groupings.push({
          id: `profile-${profile}`,
          reason: `${profileTasks.length} infringements for ${profile}`,
          confidence: 90,
          taskIds: profileTasks.map(t => t.id),
          suggestedAction: 'batch_review',
          commonAttributes: {
            profile,
            contentType: this.getMostCommonContentType(profileTasks)
          }
        });
      }
    }
    
    // Group by time proximity (likely from same upload batch)
    const timeGroups = this.groupByTimeProximity(tasks);
    for (const group of timeGroups) {
      if (group.length >= this.config.minGroupSize) {
        groupings.push({
          id: `time-${Date.now()}`,
          reason: `${group.length} infringements detected within same time window`,
          confidence: 85,
          taskIds: group.map(t => t.id),
          suggestedAction: 'batch_process',
          commonAttributes: {
            timeRange: 'recent_batch'
          }
        });
      }
    }
    
    // Group by similarity score for potential duplicate sources
    const similarityGroups = this.groupBySimilarity(tasks);
    for (const group of similarityGroups) {
      if (group.length >= this.config.minGroupSize) {
        groupings.push({
          id: `similar-${Date.now()}`,
          reason: `${group.length} highly similar infringements (likely same source)`,
          confidence: 92,
          taskIds: group.map(t => t.id),
          suggestedAction: 'batch_takedown',
          commonAttributes: {
            similarity: this.calculateAverageSimilarity(group)
          }
        });
      }
    }
    
    return groupings.sort((a, b) => b.confidence - a.confidence);
  }

  // Get only action-required items
  getActionRequiredItems(tasks: WorkbenchTask[]): ActionRequired[] {
    const actionItems: ActionRequired[] = [];
    
    // Critical items needing immediate attention
    const criticalTasks = tasks.filter(t => 
      t.priority === 'critical' && 
      t.type === 'new_detection'
    );
    if (criticalTasks.length > 0) {
      actionItems.push({
        priority: 'urgent',
        reason: `${criticalTasks.length} critical infringements need immediate review`,
        taskIds: criticalTasks.map(t => t.id),
        suggestedAction: 'immediate_review'
      });
    }
    
    // Tasks approaching deadline
    const approachingDeadline = tasks.filter(t => {
      if (t.takedownRequest?.expectedResponseDate) {
        const hoursUntilDeadline = (new Date(t.takedownRequest.expectedResponseDate).getTime() - Date.now()) / (1000 * 60 * 60);
        return hoursUntilDeadline < 24 && hoursUntilDeadline > 0;
      }
      return false;
    });
    if (approachingDeadline.length > 0) {
      actionItems.push({
        priority: 'high',
        reason: `${approachingDeadline.length} takedowns approaching response deadline`,
        taskIds: approachingDeadline.map(t => t.id),
        suggestedAction: 'follow_up',
        deadline: approachingDeadline[0].takedownRequest?.expectedResponseDate 
          ? new Date(approachingDeadline[0].takedownRequest.expectedResponseDate)
          : undefined
      });
    }
    
    // Medium confidence tasks needing human review
    const needsReview = tasks.filter(t => 
      t.confidence >= 60 && 
      t.confidence < 80 && 
      t.type === 'new_detection'
    );
    if (needsReview.length > 0) {
      actionItems.push({
        priority: 'medium',
        reason: `${needsReview.length} medium-confidence detections need review`,
        taskIds: needsReview.map(t => t.id),
        suggestedAction: 'manual_review'
      });
    }
    
    // Batch opportunities
    const batchOpportunities = this.findSmartGroupings(tasks);
    for (const group of batchOpportunities.slice(0, 3)) {
      actionItems.push({
        priority: 'low',
        reason: group.reason,
        taskIds: group.taskIds,
        suggestedAction: group.suggestedAction
      });
    }
    
    return actionItems;
  }

  // Learn from user actions to adjust thresholds
  learnFromAction(task: WorkbenchTask, action: string) {
    if (!this.config.learnFromUserActions) return;
    
    const key = `${task.platform}-${task.metadata.contentType}`;
    const currentPattern = this.userPatterns.get(key) || 0;
    
    if (action === 'approve' && task.confidence < this.config.autoApproveThreshold) {
      // User approved a lower confidence task, consider lowering threshold
      this.userPatterns.set(key, currentPattern + 1);
      if (currentPattern > 5) {
        this.adjustThreshold('approve', -2);
      }
    } else if (action === 'reject' && task.confidence > this.config.autoRejectThreshold) {
      // User rejected a higher confidence task, consider raising reject threshold
      this.userPatterns.set(key, currentPattern - 1);
      if (currentPattern < -5) {
        this.adjustThreshold('reject', 2);
      }
    }
    
    // Track false positive rates
    if (action === 'reject') {
      const fpRate = this.falsePositiveRate.get(task.platform) || 0;
      this.falsePositiveRate.set(task.platform, fpRate + 1);
    }
  }

  // Smart template selection based on infringement type
  selectSmartTemplate(task: WorkbenchTask): string {
    const platformRule = this.config.platformRules[task.platform];
    
    if (platformRule?.preferredTemplate) {
      return platformRule.preferredTemplate;
    }
    
    // Content type specific templates
    const contentTemplates: Record<string, string> = {
      'image': 'dmca_image_standard',
      'video': 'dmca_video_standard',
      'audio': 'dmca_audio_standard',
      'text': 'dmca_text_standard'
    };
    
    return contentTemplates[task.metadata.contentType] || 'dmca_generic';
  }

  // Get daily digest summary
  getDailyDigest(tasks: WorkbenchTask[]): string {
    const actionRequired = this.getActionRequiredItems(tasks);
    const urgent = actionRequired.filter(a => a.priority === 'urgent').length;
    const high = actionRequired.filter(a => a.priority === 'high').length;
    const medium = actionRequired.filter(a => a.priority === 'medium').length;
    
    if (urgent === 0 && high === 0 && medium === 0) {
      return "✅ All systems running smoothly. No action required today.";
    }
    
    let digest = `📋 ${urgent + high + medium} items need your attention today:\n`;
    if (urgent > 0) digest += `🔴 ${urgent} urgent items\n`;
    if (high > 0) digest += `🟡 ${high} high priority items\n`;
    if (medium > 0) digest += `🔵 ${medium} medium priority items\n`;
    
    return digest;
  }

  // Progressive disclosure level
  getUIComplexityLevel(userExperience: number): 'basic' | 'intermediate' | 'advanced' {
    if (userExperience < 10) return 'basic';
    if (userExperience < 50) return 'intermediate';
    return 'advanced';
  }

  // Private helper methods
  private groupByPlatform(tasks: WorkbenchTask[]): Record<string, WorkbenchTask[]> {
    return tasks.reduce((acc, task) => {
      acc[task.platform] = acc[task.platform] || [];
      acc[task.platform].push(task);
      return acc;
    }, {} as Record<string, WorkbenchTask[]>);
  }

  private groupByProfile(tasks: WorkbenchTask[]): Record<string, WorkbenchTask[]> {
    return tasks.reduce((acc, task) => {
      acc[task.profileName] = acc[task.profileName] || [];
      acc[task.profileName].push(task);
      return acc;
    }, {} as Record<string, WorkbenchTask[]>);
  }

  private groupByTimeProximity(tasks: WorkbenchTask[], windowHours = 2): WorkbenchTask[][] {
    const sorted = [...tasks].sort((a, b) => a.detectedAt.getTime() - b.detectedAt.getTime());
    const groups: WorkbenchTask[][] = [];
    let currentGroup: WorkbenchTask[] = [];
    
    for (const task of sorted) {
      if (currentGroup.length === 0) {
        currentGroup.push(task);
      } else {
        const lastTask = currentGroup[currentGroup.length - 1];
        const hoursDiff = (task.detectedAt.getTime() - lastTask.detectedAt.getTime()) / (1000 * 60 * 60);
        
        if (hoursDiff <= windowHours) {
          currentGroup.push(task);
        } else {
          if (currentGroup.length >= this.config.minGroupSize) {
            groups.push(currentGroup);
          }
          currentGroup = [task];
        }
      }
    }
    
    if (currentGroup.length >= this.config.minGroupSize) {
      groups.push(currentGroup);
    }
    
    return groups;
  }

  private groupBySimilarity(tasks: WorkbenchTask[], threshold = 85): WorkbenchTask[][] {
    const groups: WorkbenchTask[][] = [];
    const processed = new Set<string>();
    
    for (const task of tasks) {
      if (processed.has(task.id)) continue;
      
      const similar = tasks.filter(t => {
        if (t.id === task.id || processed.has(t.id)) return false;
        if (!task.metadata.similarity || !t.metadata.similarity) return false;
        return Math.abs(task.metadata.similarity - t.metadata.similarity) < 10;
      });
      
      if (similar.length >= this.config.minGroupSize - 1) {
        const group = [task, ...similar];
        groups.push(group);
        group.forEach(t => processed.add(t.id));
      }
    }
    
    return groups;
  }

  private calculateAverageSimilarity(tasks: WorkbenchTask[]): number {
    const similarities = tasks
      .map(t => t.metadata.similarity)
      .filter(s => s !== undefined) as number[];
    
    if (similarities.length === 0) return 0;
    return similarities.reduce((a, b) => a + b, 0) / similarities.length;
  }

  private getMostCommonContentType(tasks: WorkbenchTask[]): string {
    const counts = tasks.reduce((acc, task) => {
      acc[task.metadata.contentType] = (acc[task.metadata.contentType] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);
    
    return Object.entries(counts)
      .sort(([, a], [, b]) => b - a)[0]?.[0] || 'unknown';
  }

  private adjustThreshold(type: 'approve' | 'reject', delta: number) {
    if (!this.config.adaptiveThresholds) return;
    
    if (type === 'approve') {
      this.config.autoApproveThreshold = Math.max(70, Math.min(95, this.config.autoApproveThreshold + delta));
    } else {
      this.config.autoRejectThreshold = Math.max(20, Math.min(50, this.config.autoRejectThreshold + delta));
    }
  }

  // Configuration management
  updateConfig(updates: Partial<AutomationConfig>) {
    this.config = { ...this.config, ...updates };
    localStorage.setItem('automationConfig', JSON.stringify(this.config));
  }

  loadConfig() {
    const saved = localStorage.getItem('automationConfig');
    if (saved) {
      this.config = { ...this.config, ...JSON.parse(saved) };
    }
  }
}

export const automationService = new AutomationService();