# Smart Onboarding System

An intelligent onboarding system that minimizes user input and automatically configures the content protection platform based on detected patterns using AI-powered analysis.

## Features

### 🚀 Intelligent Configuration
- **Industry Presets**: Pre-configured settings for photographers, musicians, authors, filmmakers, designers, influencers, and software developers
- **AI Content Analysis**: Automatically analyzes uploaded samples to detect content type, style, and optimal protection settings
- **Smart Platform Discovery**: Auto-detects platforms from social media handles
- **Keyword Generation**: AI-powered keyword suggestion based on content analysis and industry patterns

### 🎯 Progressive Flow
1. **Industry Selection**: Quick preset selection or skip to content upload
2. **Content Analysis**: Upload samples for AI-powered analysis
3. **Configuration Preview**: Review auto-generated settings with one-click customization
4. **Final Setup**: Confirm settings and activate protection

### 🔧 Automation Features
- **Content Type Detection**: Analyzes images, videos, and audio to determine content style and subjects
- **Platform Auto-Discovery**: Scans social handles to find existing content and suggest monitoring platforms
- **Risk Assessment**: Evaluates content vulnerability and recommends protection levels
- **Smart Exclusions**: Generates appropriate exclusion terms based on industry and content type

## Usage

### Basic Implementation

```tsx
import { SmartOnboarding } from '../components/onboarding';
import type { OnboardingConfiguration } from '../types/api';

function MyComponent() {
  const handleOnboardingComplete = (config: OnboardingConfiguration) => {
    // Save configuration to backend
    console.log('Configuration:', config);
    // Initialize monitoring with settings
    // Redirect to dashboard
  };

  const handleSkip = () => {
    // Use default settings or show traditional setup
    console.log('Onboarding skipped');
  };

  return (
    <SmartOnboarding 
      onComplete={handleOnboardingComplete}
      onSkip={handleSkip}
    />
  );
}
```

### With Demo Container

```tsx
import { SmartOnboardingDemo } from '../components/onboarding';

// Pre-built demo component with dialog wrapper
function App() {
  return <SmartOnboardingDemo />;
}
```

## Configuration Object

The `OnboardingConfiguration` object returned contains:

```typescript
interface OnboardingConfiguration {
  industry?: string;              // Selected industry preset
  contentTypes: string[];         // Detected/selected content types
  platforms: string[];           // Platforms to monitor
  keywords: string[];             // Generated monitoring keywords
  exclusions: string[];           // Terms to exclude from monitoring
  scanFrequency: string;          // How often to scan (daily/weekly/monthly)
  priority: string;               // Protection priority level
  watermarkEnabled: boolean;      // Enable watermark protection
  autoTakedown: boolean;          // Auto-send takedown requests
  socialHandles: Record<string, string>; // Connected social media accounts
  contentSamples: File[];         // Uploaded sample files
  customSettings: Record<string, any>; // Additional custom configuration
}
```

## Industry Presets

### Photographer
- **Content Types**: Photography, visual art
- **Platforms**: Instagram, Facebook, Pinterest, Getty Images, Shutterstock
- **Keywords**: photography, photo, image, portrait, wedding, commercial
- **Watermarking**: Recommended
- **Scan Frequency**: Daily

### Musician
- **Content Types**: Audio, music, performance
- **Platforms**: Spotify, SoundCloud, YouTube, Apple Music, Bandcamp
- **Keywords**: music, song, album, track, audio, performance
- **Watermarking**: Not recommended
- **Scan Frequency**: Weekly

### Author/Writer
- **Content Types**: Text, literature, articles
- **Platforms**: Amazon KDP, Medium, WordPress, Scribd, Academia
- **Keywords**: book, article, story, manuscript, writing, text
- **Watermarking**: Not applicable
- **Scan Frequency**: Weekly

### Filmmaker
- **Content Types**: Video, film, documentary
- **Platforms**: YouTube, Vimeo, Netflix, Amazon Prime, Hulu
- **Keywords**: video, film, movie, documentary, production, cinema
- **Watermarking**: Recommended
- **Scan Frequency**: Daily

### Graphic Designer
- **Content Types**: Design, graphics, branding
- **Platforms**: Behance, Dribbble, 99designs, Fiverr, Upwork
- **Keywords**: design, logo, graphic, brand, identity, artwork
- **Watermarking**: Recommended
- **Scan Frequency**: Daily

### Content Creator/Influencer
- **Content Types**: Social media, personal brand, lifestyle
- **Platforms**: Instagram, TikTok, YouTube, Twitter, OnlyFans
- **Keywords**: content, brand, influencer, social, lifestyle, personal
- **Watermarking**: Recommended
- **Scan Frequency**: Daily
- **Priority**: Very High

### Software Developer
- **Content Types**: Software, code, applications
- **Platforms**: GitHub, Stack Overflow, Product Hunt, App Store, Google Play
- **Keywords**: software, app, application, code, program, tool
- **Watermarking**: Not applicable
- **Scan Frequency**: Weekly

## AI Analysis Features

### Content Detection
- **Image Analysis**: Detects style, subjects, color palettes, and technical quality
- **Video Analysis**: Identifies type, duration, quality, and production style  
- **Audio Analysis**: Determines genre, tempo, instruments, and production quality

### Smart Recommendations
- **Platform Suggestions**: Based on content type and existing social presence
- **Keyword Generation**: Industry-specific and content-derived terms
- **Risk Assessment**: Evaluates content vulnerability and protection needs
- **Automation Settings**: Recommends optimal scan frequency and takedown rules

## Customization

### Theme Integration
The component uses PrimeReact's theming system and CSS custom properties:

```css
/* Industry card colors */
.industry-card.selected {
  border-color: var(--primary-color);
}

/* Analysis results */
.analysis-results {
  border-left: 4px solid var(--green-500);
}

/* Progress indicators */
.step-indicator.active {
  color: var(--primary-color);
}
```

### Custom Analysis Backend
Override the `analyzeContent` function to connect to your own AI analysis service:

```tsx
const customAnalyzeContent = async (files: File[]): Promise<AnalysisResult> => {
  const formData = new FormData();
  files.forEach(file => formData.append('files', file));
  
  const response = await fetch('/api/analyze-content', {
    method: 'POST',
    body: formData
  });
  
  return response.json();
};
```

## Accessibility

- **Keyboard Navigation**: Full keyboard support for all interactive elements
- **Screen Readers**: Proper ARIA labels and semantic HTML
- **Color Contrast**: Meets WCAG 2.1 AA standards
- **Focus Management**: Clear focus indicators and logical tab order

## Performance

- **Lazy Loading**: Components are code-split for optimal loading
- **File Upload**: Handles large file uploads with progress indication
- **Memory Management**: Properly cleans up file references and event listeners
- **Responsive Design**: Optimized for all device sizes

## Testing

The component includes:
- Unit tests for core functionality
- Integration tests for the onboarding flow
- Accessibility tests for screen reader compatibility
- Performance tests for large file handling

## Browser Support

- Chrome/Chromium 80+
- Firefox 75+
- Safari 13+
- Edge 80+

## Dependencies

- React 18+
- PrimeReact 10+
- TypeScript 4.5+
- Modern browser with File API support

## Development

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Run tests
npm run test

# Build for production
npm run build
```

## Contributing

When contributing to the SmartOnboarding system:

1. Follow the existing TypeScript patterns
2. Add appropriate ARIA labels for accessibility
3. Include unit tests for new features
4. Update industry presets in the constants file
5. Maintain responsive design principles