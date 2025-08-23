# Content Protection Browser Extension

A cross-browser extension that allows users to quickly report infringing content and scan pages for their copyrighted material directly from their browser.

## Features

### Core Functionality
- **Right-click Reporting**: Context menu options to report images, links, and pages
- **Quick Page Scanning**: Analyze pages for potential content matches
- **Image Collection**: Gather images from pages for analysis
- **Real-time Notifications**: Instant feedback on actions and results
- **Keyboard Shortcuts**: Fast access to common functions

### Context Menu Options
- Report image as infringement
- Report link as infringement  
- Report page as infringement
- Scan page for your content
- Quick content scan

### Popup Interface
- Current page information and statistics
- Quick action buttons
- Detailed reporting form
- Authentication status
- Links to main dashboard

### Keyboard Shortcuts
- `Ctrl+Shift+P` - Quick scan
- `Ctrl+Shift+R` - Report current page
- `Ctrl+Shift+I` - Collect images

## Browser Support

### Chrome (Manifest V3)
- Chrome 88+
- Uses service workers for background tasks
- Modern Chrome extension APIs

### Firefox (WebExtensions/Manifest V2)
- Firefox 91+
- Compatible with WebExtensions API
- Cross-browser API compatibility layer

## Installation

### Development Setup

1. **Chrome Development**:
   ```bash
   # Load extension in Chrome
   1. Open chrome://extensions/
   2. Enable "Developer mode"
   3. Click "Load unpacked"
   4. Select the chrome/ directory
   ```

2. **Firefox Development**:
   ```bash
   # Load extension in Firefox
   1. Open about:debugging
   2. Click "This Firefox"
   3. Click "Load Temporary Add-on"
   4. Select manifest.json from firefox/ directory
   ```

### Production Deployment

1. **Chrome Web Store**:
   - Package the chrome/ directory
   - Submit to Chrome Web Store
   - Follow Chrome store guidelines

2. **Firefox Add-ons**:
   - Package the firefox/ directory
   - Submit to addons.mozilla.org
   - Follow Firefox review process

## Project Structure

```
browser-extension/
├── chrome/                 # Chrome-specific files
│   └── manifest.json      # Chrome Manifest V3
├── firefox/               # Firefox-specific files
│   └── manifest.json      # Firefox Manifest V2
├── shared/                # Shared code
│   ├── background.js      # Chrome background script
│   ├── firefox-background.js # Firefox background script
│   ├── content.js         # Content script (cross-browser)
│   ├── content.css        # Content styles
│   ├── popup.html         # Extension popup
│   ├── popup.js           # Popup functionality
│   └── utils.js           # Shared utilities
├── icons/                 # Extension icons
│   ├── icon-16.png
│   ├── icon-32.png
│   ├── icon-48.png
│   └── icon-128.png
└── README.md
```

## Configuration

### API Endpoints
Update these in the background and popup scripts:
- Development: `http://localhost:8000/api/v1`
- Production: `https://api.autodmca.com/api/v1`

### Host Permissions
The extension requires permissions for:
- Local development server
- Production API endpoints
- All websites (for content analysis)

## API Integration

### Authentication
- Uses JWT tokens stored in extension storage
- Integrates with main platform authentication
- Redirects to dashboard for login when needed

### Backend Endpoints Used
- `GET /profiles` - Get user profiles
- `POST /scanning/scan/url` - Submit URLs for analysis
- Authentication endpoints for token validation

## Security Considerations

### Data Handling
- No sensitive data stored permanently
- Authentication tokens encrypted in storage
- HTTPS only for API communications
- Input sanitization on all user data

### Permissions
- Minimal required permissions
- Explicit user consent for each action
- No data collection without user knowledge

## Development

### Prerequisites
- Node.js 16+ (for development tools)
- Chrome 88+ or Firefox 91+
- AutoDMCA backend running locally

### Local Development
1. Start the backend server: `http://localhost:8000`
2. Start the frontend: `http://localhost:3000`
3. Load extension in browser (see Installation)
4. Test functionality on various websites

### Testing
- Test on different website types
- Verify cross-browser compatibility
- Test authentication flow
- Validate API integrations

## Deployment Checklist

- [ ] Icons created for all required sizes
- [ ] Manifest files reviewed and updated
- [ ] API endpoints configured for production
- [ ] Cross-browser testing completed
- [ ] Store listings prepared
- [ ] Privacy policy and permissions documented
- [ ] Version numbers updated
- [ ] Build process automated

## Privacy & Permissions

### Required Permissions
- **activeTab**: Access current tab for content analysis
- **storage**: Store authentication and preferences
- **contextMenus**: Add right-click menu options
- **notifications**: Show operation feedback
- **host permissions**: Access API endpoints

### Data Collection
- Only collects URLs and content metadata explicitly requested by user
- No tracking or analytics data collected
- Authentication handled by main platform
- All data processing complies with privacy regulations

## Support & Troubleshooting

### Common Issues
1. **Authentication Required**: Click extension icon and log in
2. **No Profiles Found**: Create a profile in the main dashboard
3. **API Errors**: Check internet connection and backend status
4. **Context Menu Missing**: Reload extension or refresh page

### Debug Mode
Enable debug logging by adding `?debug=true` to any page or setting `NODE_ENV=development`.

### Error Reporting
Errors are logged locally and can be exported via the extension's options page.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Test across browsers
4. Submit pull request with detailed description

## License

This extension is part of the AutoDMCA Content Protection Platform.

## Version History

### v1.0.0 (Current)
- Initial release
- Chrome and Firefox support
- Core reporting and scanning features
- Cross-browser compatibility
- Integration with AutoDMCA API

---

For more information, visit the [AutoDMCA Documentation](https://docs.autodmca.com) or contact support.