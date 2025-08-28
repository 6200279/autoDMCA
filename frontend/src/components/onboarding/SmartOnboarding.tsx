import React, { useState, useCallback, useRef, useEffect } from 'react';
import { Card } from 'primereact/card';
import { Button } from 'primereact/button';
import { ProgressBar } from 'primereact/progressbar';
import { Dropdown } from 'primereact/dropdown';
import { InputText } from 'primereact/inputtext';
import { InputTextarea } from 'primereact/inputtextarea';
import { FileUpload } from 'primereact/fileupload';
import { Chip } from 'primereact/chip';
import { Toast } from 'primereact/toast';
import { Panel } from 'primereact/panel';
import { Badge } from 'primereact/badge';
import { Divider } from 'primereact/divider';
import { Tag } from 'primereact/tag';
import { SelectButton } from 'primereact/selectbutton';
import { MultiSelect } from 'primereact/multiselect';
import { Slider } from 'primereact/slider';
import { Checkbox } from 'primereact/checkbox';
import { TabView, TabPanel } from 'primereact/tabview';
import type { OnboardingConfiguration, AnalysisResult, IndustryPreset } from '../../types/api';
import './SmartOnboarding.css';

// Industry preset configurations
const INDUSTRY_PRESETS = {
  photographer: {
    name: 'Photographer',
    icon: 'pi-camera',
    description: 'Professional photography and visual content',
    contentTypes: ['photography', 'visual_art'],
    defaultKeywords: ['photography', 'photo', 'image', 'portrait', 'wedding', 'commercial'],
    exclusions: ['stock photo', 'free image', 'creative commons'],
    platforms: ['Instagram', 'Facebook', 'Pinterest', 'Getty Images', 'Shutterstock'],
    scanFrequency: 'daily',
    priority: 'high',
    watermarkRecommended: true
  },
  musician: {
    name: 'Musician',
    icon: 'pi-volume-up',
    description: 'Music production, audio content, and performances',
    contentTypes: ['audio', 'music', 'performance'],
    defaultKeywords: ['music', 'song', 'album', 'track', 'audio', 'performance'],
    exclusions: ['cover song', 'remix', 'sample'],
    platforms: ['Spotify', 'SoundCloud', 'YouTube', 'Apple Music', 'Bandcamp'],
    scanFrequency: 'weekly',
    priority: 'medium',
    watermarkRecommended: false
  },
  author: {
    name: 'Author/Writer',
    icon: 'pi-book',
    description: 'Written content, books, articles, and manuscripts',
    contentTypes: ['text', 'literature', 'articles'],
    defaultKeywords: ['book', 'article', 'story', 'manuscript', 'writing', 'text'],
    exclusions: ['quote', 'excerpt', 'fair use'],
    platforms: ['Amazon KDP', 'Medium', 'WordPress', 'Scribd', 'Academia'],
    scanFrequency: 'weekly',
    priority: 'medium',
    watermarkRecommended: false
  },
  filmmaker: {
    name: 'Filmmaker',
    icon: 'pi-video',
    description: 'Video content, films, documentaries, and productions',
    contentTypes: ['video', 'film', 'documentary'],
    defaultKeywords: ['video', 'film', 'movie', 'documentary', 'production', 'cinema'],
    exclusions: ['trailer', 'clip', 'fair use'],
    platforms: ['YouTube', 'Vimeo', 'Netflix', 'Amazon Prime', 'Hulu'],
    scanFrequency: 'daily',
    priority: 'high',
    watermarkRecommended: true
  },
  designer: {
    name: 'Graphic Designer',
    icon: 'pi-palette',
    description: 'Graphic design, logos, branding, and visual identity',
    contentTypes: ['design', 'graphics', 'branding'],
    defaultKeywords: ['design', 'logo', 'graphic', 'brand', 'identity', 'artwork'],
    exclusions: ['template', 'stock design', 'free resource'],
    platforms: ['Behance', 'Dribbble', '99designs', 'Fiverr', 'Upwork'],
    scanFrequency: 'daily',
    priority: 'high',
    watermarkRecommended: true
  },
  influencer: {
    name: 'Content Creator/Influencer',
    icon: 'pi-users',
    description: 'Social media content, personal brand, and digital influence',
    contentTypes: ['social_media', 'personal_brand', 'lifestyle'],
    defaultKeywords: ['content', 'brand', 'influencer', 'social', 'lifestyle', 'personal'],
    exclusions: ['fan content', 'user generated', 'tribute'],
    platforms: ['Instagram', 'TikTok', 'YouTube', 'Twitter', 'OnlyFans'],
    scanFrequency: 'daily',
    priority: 'very_high',
    watermarkRecommended: true
  },
  software: {
    name: 'Software Developer',
    icon: 'pi-code',
    description: 'Software products, applications, and digital tools',
    contentTypes: ['software', 'code', 'applications'],
    defaultKeywords: ['software', 'app', 'application', 'code', 'program', 'tool'],
    exclusions: ['open source', 'free software', 'demo'],
    platforms: ['GitHub', 'Stack Overflow', 'Product Hunt', 'App Store', 'Google Play'],
    scanFrequency: 'weekly',
    priority: 'medium',
    watermarkRecommended: false
  }
};

const CONTENT_ANALYSIS_RESULTS = {
  photography: {
    detectedStyle: 'Professional Portrait Photography',
    subjects: ['people', 'portraits', 'professional headshots'],
    colorPalette: ['warm tones', 'neutral backgrounds'],
    technicalMetrics: { resolution: 'High (>4K)', lighting: 'Professional', composition: 'Rule of thirds' }
  },
  music: {
    detectedGenre: 'Electronic/Pop',
    tempo: '120-128 BPM',
    instruments: ['synthesizer', 'drums', 'vocal'],
    production: 'Studio quality'
  },
  video: {
    detectedType: 'Cinematic/Documentary',
    duration: 'Medium form (5-15 min)',
    quality: '4K HDR',
    style: 'Professional cinematography'
  }
};

interface SmartOnboardingProps {
  onComplete: (config: OnboardingConfiguration) => void;
  onSkip: () => void;
}

const SmartOnboarding: React.FC<SmartOnboardingProps> = ({ onComplete, onSkip }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResults, setAnalysisResults] = useState<AnalysisResult | null>(null);
  const [configuration, setConfiguration] = useState<OnboardingConfiguration>({
    contentTypes: [],
    platforms: [],
    keywords: [],
    exclusions: [],
    scanFrequency: 'weekly',
    priority: 'medium',
    watermarkEnabled: false,
    autoTakedown: false,
    socialHandles: {},
    contentSamples: [],
    customSettings: {}
  });
  const [selectedIndustry, setSelectedIndustry] = useState<string>('');
  const [detectedPlatforms, setDetectedPlatforms] = useState<string[]>([]);
  const [socialHandles, setSocialHandles] = useState<Record<string, string>>({});
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [isCustomizing, setIsCustomizing] = useState(false);
  
  const toast = useRef<Toast>(null);

  const steps = [
    { label: 'Industry Selection', icon: 'pi-briefcase' },
    { label: 'Content Analysis', icon: 'pi-search' },
    { label: 'Configuration Preview', icon: 'pi-eye' },
    { label: 'Final Setup', icon: 'pi-check' }
  ];

  // Simulate content analysis with AI-like intelligence
  const analyzeContent = useCallback(async (files: File[]): Promise<AnalysisResult> => {
    setIsAnalyzing(true);
    
    // Simulate processing time
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    const fileTypes = files.map(f => f.type.split('/')[0]);
    const hasImages = fileTypes.includes('image');
    const hasVideos = fileTypes.includes('video');
    const hasAudio = fileTypes.includes('audio');
    
    let contentType = 'mixed';
    let suggestedKeywords: string[] = [];
    let detectedPlatforms: string[] = [];
    
    if (hasImages && !hasVideos && !hasAudio) {
      contentType = 'photography';
      suggestedKeywords = ['photo', 'image', 'photography', 'visual', 'art', 'creative'];
      detectedPlatforms = ['Instagram', 'Pinterest', 'Flickr', 'Behance'];
    } else if (hasVideos) {
      contentType = 'video';
      suggestedKeywords = ['video', 'film', 'content', 'visual', 'media', 'production'];
      detectedPlatforms = ['YouTube', 'Vimeo', 'TikTok', 'Instagram'];
    } else if (hasAudio) {
      contentType = 'music';
      suggestedKeywords = ['music', 'audio', 'song', 'sound', 'track', 'composition'];
      detectedPlatforms = ['Spotify', 'SoundCloud', 'YouTube', 'Apple Music'];
    }
    
    setIsAnalyzing(false);
    
    return {
      contentType,
      confidence: 0.85 + Math.random() * 0.1,
      suggestedKeywords,
      detectedPlatforms,
      riskAssessment: contentType === 'photography' ? 'High' : 'Medium',
      recommendations: [
        'Enable daily monitoring for high-value content',
        'Set up automated takedown for confirmed matches',
        'Use watermarking for visual content',
        'Monitor social media platforms closely'
      ]
    };
  }, []);

  // Auto-discover platforms from social handles
  const discoverPlatformsFromHandles = useCallback((handles: Record<string, string>) => {
    const platforms: string[] = [];
    Object.keys(handles).forEach(platform => {
      if (handles[platform]?.trim()) {
        platforms.push(platform);
      }
    });
    setDetectedPlatforms(platforms);
    return platforms;
  }, []);

  // Generate configuration based on industry and analysis
  const generateConfiguration = useCallback(() => {
    const preset = selectedIndustry ? INDUSTRY_PRESETS[selectedIndustry as keyof typeof INDUSTRY_PRESETS] : null;
    const analyzedPlatforms = analysisResults?.detectedPlatforms || [];
    const socialPlatforms = discoverPlatformsFromHandles(socialHandles);
    
    const newConfig: OnboardingConfiguration = {
      industry: selectedIndustry,
      contentTypes: preset?.contentTypes || (analysisResults ? [analysisResults.contentType] : []),
      platforms: [...new Set([...analyzedPlatforms, ...socialPlatforms, ...(preset?.platforms || [])])],
      keywords: [...new Set([...(preset?.defaultKeywords || []), ...(analysisResults?.suggestedKeywords || [])])],
      exclusions: preset?.exclusions || ['free', 'sample', 'demo'],
      scanFrequency: preset?.scanFrequency || 'weekly',
      priority: preset?.priority || 'medium',
      watermarkEnabled: preset?.watermarkRecommended || analysisResults?.contentType === 'photography',
      autoTakedown: analysisResults?.riskAssessment === 'High',
      socialHandles,
      contentSamples: uploadedFiles,
      customSettings: {}
    };
    
    setConfiguration(newConfig);
    return newConfig;
  }, [selectedIndustry, analysisResults, socialHandles, uploadedFiles, discoverPlatformsFromHandles]);

  // Handle file upload and analysis
  const handleFileUpload = useCallback(async (event: any) => {
    const files = Array.from(event.files) as File[];
    setUploadedFiles(files);
    
    if (files.length > 0) {
      toast.current?.show({
        severity: 'info',
        summary: 'Analyzing Content',
        detail: 'AI is analyzing your content to suggest optimal settings...',
        life: 3000
      });
      
      try {
        const result = await analyzeContent(files);
        setAnalysisResults(result);
        toast.current?.show({
          severity: 'success',
          summary: 'Analysis Complete',
          detail: `Detected ${result.contentType} content with ${Math.round(result.confidence * 100)}% confidence`,
          life: 5000
        });
      } catch (error) {
        toast.current?.show({
          severity: 'error',
          summary: 'Analysis Failed',
          detail: 'Could not analyze content. Using default settings.',
          life: 5000
        });
      }
    }
  }, [analyzeContent]);

  // Handle social handle input
  const handleSocialHandleChange = useCallback((platform: string, handle: string) => {
    const newHandles = { ...socialHandles, [platform]: handle };
    setSocialHandles(newHandles);
    discoverPlatformsFromHandles(newHandles);
  }, [socialHandles, discoverPlatformsFromHandles]);

  // Navigate steps
  const nextStep = () => {
    if (currentStep === 1 && uploadedFiles.length === 0 && !selectedIndustry) {
      toast.current?.show({
        severity: 'warn',
        summary: 'Missing Information',
        detail: 'Please select an industry or upload content samples for analysis.',
        life: 3000
      });
      return;
    }
    
    if (currentStep === 1) {
      generateConfiguration();
    }
    
    setCurrentStep(prev => Math.min(prev + 1, steps.length - 1));
  };

  const prevStep = () => {
    setCurrentStep(prev => Math.max(prev - 1, 0));
  };

  const completeOnboarding = () => {
    const finalConfig = generateConfiguration();
    toast.current?.show({
      severity: 'success',
      summary: 'Setup Complete',
      detail: 'Your content protection is now active!',
      life: 5000
    });
    onComplete(finalConfig);
  };

  // Render industry selection step
  const renderIndustrySelection = () => (
    <div className="industry-selection">
      <div className="text-center mb-4">
        <h3>What type of content do you create?</h3>
        <p className="text-muted-color">Select your industry for optimized protection settings, or skip to upload samples.</p>
      </div>
      
      <div className="industry-grid">
        {Object.entries(INDUSTRY_PRESETS).map(([key, preset]) => (
          <Card 
            key={key}
            className={`industry-card ${selectedIndustry === key ? 'selected' : ''}`}
            onClick={() => setSelectedIndustry(selectedIndustry === key ? '' : key)}
          >
            <div className="text-center">
              <i className={`pi ${preset.icon} industry-icon`}></i>
              <h4>{preset.name}</h4>
              <p className="text-sm text-muted-color">{preset.description}</p>
              {selectedIndustry === key && (
                <div className="preset-preview mt-2">
                  <Badge value={`${preset.defaultKeywords.length} keywords`} className="mr-2" />
                  <Badge value={`${preset.platforms.length} platforms`} />
                </div>
              )}
            </div>
          </Card>
        ))}
      </div>
      
      <Divider className="my-4" />
      
      <div className="text-center">
        <p className="text-muted-color mb-3">Or skip industry selection and let AI analyze your content</p>
        <Button label="Skip to Content Upload" icon="pi pi-arrow-right" className="p-button-text" onClick={nextStep} />
      </div>
    </div>
  );

  // Render content analysis step
  const renderContentAnalysis = () => (
    <div className="content-analysis">
      <div className="text-center mb-4">
        <h3>Upload Sample Content</h3>
        <p className="text-muted-color">Upload examples of your content for AI-powered analysis and automatic configuration.</p>
      </div>

      <Card className="upload-section mb-4">
        <FileUpload
          name="content"
          multiple
          accept="image/*,video/*,audio/*"
          maxFileSize={50000000}
          customUpload
          uploadHandler={handleFileUpload}
          emptyTemplate={
            <div className="text-center p-4">
              <i className="pi pi-cloud-upload" style={{ fontSize: '3rem', color: 'var(--primary-color)' }}></i>
              <p className="mt-2 mb-0">Drag and drop files here, or click to browse</p>
              <p className="text-sm text-muted-color">Supports images, videos, and audio files (max 50MB each)</p>
            </div>
          }
        />
        
        {uploadedFiles.length > 0 && (
          <div className="uploaded-files mt-3">
            <h5>Uploaded Files ({uploadedFiles.length})</h5>
            <div className="file-chips">
              {uploadedFiles.map((file, index) => (
                <Chip key={index} label={file.name} className="mr-2 mb-2" />
              ))}
            </div>
          </div>
        )}
      </Card>

      {isAnalyzing && (
        <Card className="analysis-progress mb-4">
          <div className="text-center p-3">
            <i className="pi pi-spinner pi-spin" style={{ fontSize: '2rem' }}></i>
            <p className="mt-2 mb-2">AI is analyzing your content...</p>
            <ProgressBar mode="indeterminate" style={{ height: '6px' }} />
          </div>
        </Card>
      )}

      {analysisResults && (
        <Card className="analysis-results mb-4">
          <h5>Analysis Results</h5>
          <div className="grid">
            <div className="col-12 md:col-6">
              <div className="analysis-metric">
                <label>Content Type</label>
                <div className="flex align-items-center">
                  <Tag value={analysisResults.contentType} severity="info" className="mr-2" />
                  <span>{Math.round(analysisResults.confidence * 100)}% confidence</span>
                </div>
              </div>
            </div>
            <div className="col-12 md:col-6">
              <div className="analysis-metric">
                <label>Risk Assessment</label>
                <Badge 
                  value={analysisResults.riskAssessment} 
                  severity={analysisResults.riskAssessment === 'High' ? 'danger' : 'warning'} 
                />
              </div>
            </div>
            <div className="col-12">
              <label>Suggested Keywords</label>
              <div className="keyword-chips">
                {analysisResults.suggestedKeywords.map((keyword, index) => (
                  <Chip key={index} label={keyword} className="mr-2 mb-2" />
                ))}
              </div>
            </div>
            <div className="col-12">
              <label>Recommended Platforms</label>
              <div className="platform-chips">
                {analysisResults.detectedPlatforms.map((platform, index) => (
                  <Chip key={index} label={platform} className="mr-2 mb-2" />
                ))}
              </div>
            </div>
          </div>
        </Card>
      )}

      <Card className="social-handles-section">
        <h5>Social Media Handles (Optional)</h5>
        <p className="text-muted-color text-sm mb-3">Add your social media handles to auto-detect additional platforms to monitor.</p>
        
        <div className="grid">
          {['Instagram', 'Twitter', 'TikTok', 'YouTube', 'LinkedIn', 'OnlyFans'].map(platform => (
            <div key={platform} className="col-12 md:col-6">
              <label htmlFor={platform.toLowerCase()}>{platform}</label>
              <InputText
                id={platform.toLowerCase()}
                placeholder={`@your${platform.toLowerCase()}handle`}
                value={socialHandles[platform] || ''}
                onChange={(e) => handleSocialHandleChange(platform, e.target.value)}
                className="w-full"
              />
            </div>
          ))}
        </div>
        
        {detectedPlatforms.length > 0 && (
          <div className="mt-3">
            <label>Detected Active Platforms</label>
            <div className="platform-chips">
              {detectedPlatforms.map((platform, index) => (
                <Tag key={index} value={platform} severity="success" className="mr-2" />
              ))}
            </div>
          </div>
        )}
      </Card>
    </div>
  );

  // Render configuration preview
  const renderConfigurationPreview = () => {
    const config = generateConfiguration();
    
    return (
      <div className="configuration-preview">
        <div className="text-center mb-4">
          <h3>Generated Configuration</h3>
          <p className="text-muted-color">Review your automatically configured protection settings. You can customize these later.</p>
        </div>

        <TabView>
          <TabPanel header="Content Protection" leftIcon="pi pi-shield">
            <div className="config-section">
              <h5>Content Types</h5>
              <div className="value-chips mb-3">
                {config.contentTypes.map((type, index) => (
                  <Chip key={index} label={type} className="mr-2 mb-2" />
                ))}
              </div>

              <h5>Keywords ({config.keywords.length})</h5>
              <div className="value-chips mb-3">
                {config.keywords.slice(0, 8).map((keyword, index) => (
                  <Chip key={index} label={keyword} className="mr-2 mb-2" />
                ))}
                {config.keywords.length > 8 && (
                  <Chip label={`+${config.keywords.length - 8} more`} className="p-chip-outlined" />
                )}
              </div>

              <h5>Exclusions</h5>
              <div className="value-chips mb-3">
                {config.exclusions.map((exclusion, index) => (
                  <Chip key={index} label={exclusion} className="mr-2 mb-2 p-chip-outlined" />
                ))}
              </div>
            </div>
          </TabPanel>

          <TabPanel header="Monitoring" leftIcon="pi pi-eye">
            <div className="config-section">
              <div className="grid">
                <div className="col-12 md:col-6">
                  <label>Scan Frequency</label>
                  <Tag value={config.scanFrequency} severity="info" className="w-full block text-center" />
                </div>
                <div className="col-12 md:col-6">
                  <label>Priority Level</label>
                  <Tag 
                    value={config.priority} 
                    severity={config.priority === 'high' ? 'danger' : config.priority === 'medium' ? 'warning' : 'success'} 
                    className="w-full block text-center"
                  />
                </div>
              </div>

              <h5 className="mt-4">Monitored Platforms ({config.platforms.length})</h5>
              <div className="value-chips mb-3">
                {config.platforms.map((platform, index) => (
                  <Chip key={index} label={platform} className="mr-2 mb-2" />
                ))}
              </div>

              <div className="grid mt-4">
                <div className="col-12 md:col-6">
                  <div className="flex align-items-center">
                    <Checkbox 
                      checked={config.watermarkEnabled} 
                      readOnly 
                      className="mr-2"
                    />
                    <label>Watermark Protection</label>
                  </div>
                </div>
                <div className="col-12 md:col-6">
                  <div className="flex align-items-center">
                    <Checkbox 
                      checked={config.autoTakedown} 
                      readOnly 
                      className="mr-2"
                    />
                    <label>Auto Takedown</label>
                  </div>
                </div>
              </div>
            </div>
          </TabPanel>

          <TabPanel header="Social Media" leftIcon="pi pi-users">
            <div className="config-section">
              <h5>Connected Accounts</h5>
              {Object.keys(config.socialHandles).length === 0 ? (
                <p className="text-muted-color">No social media accounts configured</p>
              ) : (
                <div className="social-accounts">
                  {Object.entries(config.socialHandles).map(([platform, handle]) => (
                    handle && (
                      <div key={platform} className="social-account-item flex align-items-center mb-2">
                        <i className="pi pi-check-circle text-green-500 mr-2"></i>
                        <span className="font-semibold mr-2">{platform}:</span>
                        <span>{handle}</span>
                      </div>
                    )
                  ))}
                </div>
              )}
            </div>
          </TabPanel>
        </TabView>

        <div className="text-center mt-4">
          <Button 
            label="Customize Settings" 
            icon="pi pi-cog" 
            className="p-button-outlined mr-2"
            onClick={() => setIsCustomizing(!isCustomizing)}
          />
          <Button 
            label="Use These Settings" 
            icon="pi pi-check" 
            onClick={nextStep}
          />
        </div>

        {isCustomizing && (
          <Card className="customization-panel mt-4">
            <h5>Quick Customization</h5>
            <div className="grid">
              <div className="col-12 md:col-6">
                <label>Scan Frequency</label>
                <Dropdown
                  value={configuration.scanFrequency}
                  options={[
                    { label: 'Daily', value: 'daily' },
                    { label: 'Weekly', value: 'weekly' },
                    { label: 'Monthly', value: 'monthly' }
                  ]}
                  onChange={(e) => setConfiguration(prev => ({ ...prev, scanFrequency: e.value }))}
                  className="w-full"
                />
              </div>
              <div className="col-12 md:col-6">
                <label>Priority Level</label>
                <SelectButton
                  value={configuration.priority}
                  options={[
                    { label: 'Low', value: 'low' },
                    { label: 'Medium', value: 'medium' },
                    { label: 'High', value: 'high' }
                  ]}
                  onChange={(e) => setConfiguration(prev => ({ ...prev, priority: e.value }))}
                  className="w-full"
                />
              </div>
            </div>
          </Card>
        )}
      </div>
    );
  };

  // Render final setup step
  const renderFinalSetup = () => (
    <div className="final-setup text-center">
      <div className="mb-4">
        <i className="pi pi-check-circle" style={{ fontSize: '4rem', color: 'var(--green-500)' }}></i>
        <h3 className="mt-3">Setup Complete!</h3>
        <p className="text-muted-color">Your content protection system is ready to activate.</p>
      </div>

      <Card className="setup-summary mb-4">
        <h5>Protection Summary</h5>
        <div className="grid text-left">
          <div className="col-12 md:col-4">
            <div className="summary-stat">
              <span className="stat-number">{configuration.platforms.length}</span>
              <span className="stat-label">Platforms Monitored</span>
            </div>
          </div>
          <div className="col-12 md:col-4">
            <div className="summary-stat">
              <span className="stat-number">{configuration.keywords.length}</span>
              <span className="stat-label">Keywords Tracked</span>
            </div>
          </div>
          <div className="col-12 md:col-4">
            <div className="summary-stat">
              <span className="stat-number">{configuration.scanFrequency}</span>
              <span className="stat-label">Scan Frequency</span>
            </div>
          </div>
        </div>
      </Card>

      <div className="activation-options">
        <Button 
          label="Activate Protection Now" 
          icon="pi pi-play" 
          size="large"
          onClick={completeOnboarding}
          className="mr-3"
        />
        <Button 
          label="Review Settings" 
          icon="pi pi-arrow-left" 
          className="p-button-outlined"
          onClick={prevStep}
        />
      </div>
    </div>
  );

  return (
    <div className="smart-onboarding">
      <Toast ref={toast} />
      
      {/* Header */}
      <div className="onboarding-header text-center mb-4">
        <h2>Smart Content Protection Setup</h2>
        <p className="text-muted-color">AI-powered configuration that learns from your content</p>
        <Button 
          label="Skip Setup" 
          className="p-button-text p-button-sm"
          icon="pi pi-times"
          onClick={onSkip}
        />
      </div>

      {/* Progress */}
      <div className="progress-section mb-4">
        <ProgressBar value={(currentStep / (steps.length - 1)) * 100} className="mb-3" />
        <div className="step-indicators">
          {steps.map((step, index) => (
            <div key={index} className={`step-indicator ${index <= currentStep ? 'active' : ''}`}>
              <i className={`pi ${step.icon}`}></i>
              <span>{step.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Content */}
      <Card className="onboarding-content">
        {currentStep === 0 && renderIndustrySelection()}
        {currentStep === 1 && renderContentAnalysis()}
        {currentStep === 2 && renderConfigurationPreview()}
        {currentStep === 3 && renderFinalSetup()}
      </Card>

      {/* Navigation */}
      {currentStep < 3 && (
        <div className="onboarding-navigation text-center mt-4">
          <Button 
            label="Back" 
            icon="pi pi-arrow-left" 
            className="p-button-outlined mr-2"
            onClick={prevStep}
            disabled={currentStep === 0}
          />
          <Button 
            label={currentStep === 2 ? "Complete Setup" : "Next"} 
            icon="pi pi-arrow-right" 
            iconPos="right"
            onClick={nextStep}
            disabled={isAnalyzing}
          />
        </div>
      )}
    </div>
  );
};

export default SmartOnboarding;