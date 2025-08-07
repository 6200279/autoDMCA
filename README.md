# AutoDMCA - Automated DMCA Takedown Processing System

🛡️ **Comprehensive DMCA takedown automation with creator anonymity protection**

A complete system for automating DMCA takedown processes, from generating legally compliant notices to tracking responses and maintaining creator anonymity. Includes both a powerful Python backend and a modern React dashboard for content creators, agencies, and platforms.

## ✨ Features

### 🔧 DMCA Processing Engine (Python Backend)
- **Automated DMCA Notice Generation** - Legally compliant templates following 17 U.S.C. § 512(c)(3)
- **WHOIS Integration** - Automatic hosting provider identification and contact discovery
- **Multi-Channel Email Dispatch** - SendGrid + SMTP fallback with delivery tracking
- **Search Engine Delisting** - Google, Bing, and Yahoo removal request automation
- **Response Processing** - Intelligent handling of acknowledgments, completions, and counter-notices
- **Status Tracking** - Real-time monitoring with automated follow-ups

### 🔒 Privacy & Security
- **Complete Anonymity Protection** - Creator identities remain private
- **DMCA Agent Representation** - Professional legal service acts on behalf of creators
- **Secure Data Handling** - Encrypted storage and secure API communications
- **Input Validation** - Comprehensive sanitization to prevent abuse

### 📊 Dashboard & Analytics (React Frontend)
- Real-time statistics and metrics
- Interactive charts with Chart.js integration
- Platform distribution visualization
- Recent activity timeline
- Performance analytics
- DMCA takedown success tracking

### 🛡️ Content Protection
- URL submission for monitoring
- Bulk upload capabilities
- Automated infringement detection
- Status tracking with filtering
- Counter-notice handling
- Batch processing capabilities

### 📱 Modern Web Interface
- Mobile-first responsive design
- Material-UI component library
- Dark/light theme support
- Real-time WebSocket updates
- Accessible design (WCAG compliant)

### ⚙️ Advanced Capabilities
- **Batch Processing** - Handle hundreds of takedowns simultaneously
- **Performance Analytics** - Track success rates and hosting provider compliance
- **Counter-Notice Handling** - Complete DMCA 512(g) counter-notice processing
- **Template Customization** - Flexible notice templates with legal validation
- **Rate Limiting & Caching** - Efficient API usage with Redis support

## 🚀 Technology Stack

### Backend (Python)
- **Framework**: FastAPI with async/await support
- **Models**: Pydantic for data validation, SQLAlchemy for ORM
- **Email**: SendGrid API + SMTP fallback
- **WHOIS**: python-whois with custom enhancements
- **Templates**: Jinja2 with legal compliance validation
- **Caching**: Redis with automatic TTL management
- **Rate Limiting**: Token bucket algorithm with backoff
- **Testing**: pytest with asyncio and mocking

### Frontend (React)
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **UI Framework**: Material-UI (MUI) v5
- **State Management**: React Query (TanStack Query)
- **Form Management**: React Hook Form with Yup validation
- **Charts**: Chart.js with react-chartjs-2
- **File Upload**: React Dropzone
- **Date Handling**: date-fns
- **Notifications**: notistack
- **WebSocket**: Socket.io-client
- **HTTP Client**: Axios
- **Routing**: React Router v6

### Infrastructure
- **Database**: PostgreSQL with Redis caching
- **Queue**: Redis-based task queue
- **Email**: SendGrid for primary delivery
- **APIs**: Google/Bing search APIs for delisting
- **Security**: JWT tokens, bcrypt hashing, input sanitization

## 📁 Project Structure

```
autodmca/
├── src/autodmca/           # Python DMCA Processing Engine
│   ├── models/             # Data models (Pydantic + SQLAlchemy)
│   │   ├── takedown.py     # TakedownRequest, CreatorProfile models
│   │   └── hosting.py      # HostingProvider, DMCAAgent models
│   ├── services/           # Core processing services
│   │   ├── dmca_service.py       # Main orchestration service
│   │   ├── whois_service.py      # Domain/hosting provider lookup
│   │   ├── email_service.py      # SendGrid + SMTP email dispatch
│   │   ├── search_delisting_service.py  # Google/Bing delisting
│   │   └── response_handler.py   # Email response processing
│   ├── templates/          # DMCA notice templates
│   │   ├── dmca_notice.py        # Legal notice templates
│   │   └── template_renderer.py  # Jinja2 rendering engine
│   └── utils/              # Utilities and helpers
│       ├── security.py     # Anonymity protection
│       ├── validators.py   # Email/URL validation
│       ├── cache.py        # Redis caching layer
│       └── rate_limiter.py # API rate limiting
├── frontend/src/           # React Dashboard Frontend
│   ├── components/         # Reusable UI components
│   ├── pages/             # Page components
│   │   ├── Dashboard/     # Analytics and overview
│   │   ├── Infringements/ # Takedown management
│   │   ├── Submission/    # Content submission
│   │   └── Settings/      # Configuration
│   ├── services/          # API integration
│   └── types/             # TypeScript definitions
├── examples/              # Usage examples
│   ├── basic_usage.py     # Getting started guide
│   └── advanced_features.py # Advanced capabilities
├── tests/                 # Comprehensive test suite
│   ├── unit/              # Unit tests for all components
│   └── integration/       # Integration tests
└── docs/                  # Documentation
```

## 🚀 Quick Start

### Prerequisites
- Python 3.10+ 
- Node.js 18+ 
- PostgreSQL 12+
- Redis 6+

### Backend Setup (DMCA Processing Engine)

1. Clone and setup Python environment:
```bash
git clone <repository-url>
cd autoDMCA

# Install Python dependencies
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and database connections
```

3. Basic Python usage:
```python
import asyncio
from src.autodmca import DMCAService, TakedownRequest, CreatorProfile, InfringementData

async def main():
    # Setup DMCA agent
    from src.autodmca.models.hosting import DMCAAgent
    
    agent = DMCAAgent(
        name="Your Legal Service",
        email="dmca@yourlegalservice.com",
        address_line1="123 Legal Ave",
        city="Legal City", 
        state_province="CA",
        postal_code="90210",
        country="USA"
    )
    
    # Create services
    dmca_service = DMCAService.create_default(agent)
    
    # Create creator profile (with anonymity)
    creator = CreatorProfile(
        public_name="Creative Artist",  # Pseudonym
        email="artist@example.com",
        use_anonymity=True  # Enable privacy protection
        # ... address and other details
    )
    
    # Define infringement
    infringement = InfringementData(
        infringing_url="https://pirate-site.com/stolen-content.jpg",
        description="Unauthorized use of my copyrighted work",
        original_work_title="My Original Artwork",
        original_work_description="Original digital artwork",
        content_type="image"
    )
    
    # Create and process takedown
    takedown = TakedownRequest(
        creator_id="user-123",
        creator_profile=creator,
        infringement_data=infringement
    )
    
    # Process automatically (WHOIS → Notice → Email → Search Delisting)
    result = await dmca_service.process_takedown_request(takedown)
    
    if result['success']:
        print(f"✅ Takedown processed! Status: {takedown.status}")
        print(f"📧 Email sent to: {result['hosting_provider']}")

# Run the example
asyncio.run(main())
```

### Frontend Setup (Dashboard)

1. Install Node.js dependencies:
```bash
npm install
```

2. Configure frontend environment:
```bash
cp frontend/.env.example frontend/.env
# Edit with API endpoints
```

3. Start development server:
```bash
npm run dev
```

4. Open your browser to `http://localhost:3000`

## 📊 Key Features Implemented

✅ **Complete DMCA Processing Pipeline**
1. **Generates compliant DMCA notices** from customizable templates
2. **Identifies hosting providers** via comprehensive WHOIS lookup  
3. **Sends notices via email** using SendGrid/SMTP with tracking
4. **Submits Google/Bing delisting requests** for search removal
5. **Tracks takedown status** with automated follow-ups
6. **Handles responses** including counter-notices and confirmations
7. **Maintains anonymity** for creators using agent representation

✅ **Advanced Capabilities**
- **Batch Processing** - Handle hundreds of takedowns simultaneously
- **Counter-Notice Processing** - Complete DMCA 512(g) compliance
- **Response Classification** - AI-powered email response analysis
- **Performance Analytics** - Track hosting provider compliance rates
- **Template Validation** - Ensure legal compliance of all notices
- **Rate Limiting** - Prevent API abuse and respect service limits

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Run all Python tests
pytest

# Run specific test categories  
pytest tests/unit/test_models.py -v          # Model validation tests
pytest tests/unit/test_services.py -v       # Service functionality tests
pytest tests/unit/test_templates.py -v      # Template rendering tests

# Run with coverage
pytest --cov=src/autodmca --cov-report=html

# Frontend tests
npm run test
npm run test:coverage
```

## 🔒 Legal & Compliance

### DMCA Compliance
- ✅ Follows 17 U.S.C. § 512(c)(3) requirements
- ✅ Includes all required legal elements
- ✅ Proper perjury statements and signatures  
- ✅ Counter-notice handling per 512(g)

### Privacy Protection
- ✅ Creator anonymity maintained
- ✅ Agent-based representation
- ✅ Secure data handling
- ✅ GDPR considerations

### Legal Disclaimer
This software is provided for legitimate copyright enforcement. Users are responsible for:
- Ensuring they own or control the copyrighted material
- Providing accurate information in takedown requests
- Complying with applicable laws and regulations
- Understanding that false claims may result in liability under 17 U.S.C. § 512(f)

## 🛠️ Implementation Status

This is a **complete, production-ready implementation** including:

✅ **Models & Data Structures** - Complete validation and type safety  
✅ **WHOIS Lookup Service** - Domain resolution and hosting provider identification  
✅ **Email Dispatch Service** - SendGrid + SMTP with delivery tracking  
✅ **Search Delisting Service** - Google/Bing removal requests  
✅ **DMCA Orchestration** - End-to-end workflow automation  
✅ **Response Handling** - Email processing and counter-notice support  
✅ **Anonymity Protection** - Complete privacy and security features  
✅ **Template System** - Legally compliant DMCA notice generation  
✅ **Comprehensive Tests** - Unit tests for all components  
✅ **Documentation & Examples** - Complete usage guides  

## Available Scripts

### Backend (Python)
- `python -m pytest` - Run test suite
- `python examples/basic_usage.py` - Basic usage example
- `python examples/advanced_features.py` - Advanced features demo

### Frontend (React)
- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint
- `npm run type-check` - Run TypeScript compiler

## Authentication Flow

The application uses a token-based authentication system:

1. User logs in with credentials
2. API returns JWT token and user data
3. Token is stored in localStorage
4. All subsequent API calls include the Bearer token
5. WebSocket connection is established with the token
6. Automatic token refresh on expiry

## API Integration

The app integrates with a REST API for:

- User authentication and profile management
- Content submission and monitoring
- Infringement detection and management
- Statistics and analytics data
- Account settings and preferences

Example API endpoints:
- `POST /api/auth/login` - User authentication
- `GET /api/dashboard/stats` - Dashboard statistics
- `GET /api/infringements` - Infringement list
- `POST /api/submissions` - Submit URLs for monitoring

## WebSocket Integration

Real-time updates are handled via WebSocket connections:

- Infringement detection notifications
- Status update alerts
- System-wide announcements
- Live dashboard updates

## Responsive Design

The application is fully responsive with:

- Mobile-first CSS approach
- Flexible grid layouts
- Touch-friendly interface elements
- Optimized navigation for small screens
- Adaptive typography and spacing

## Accessibility Features

- Semantic HTML structure
- ARIA labels and roles
- Keyboard navigation support
- Focus management
- Screen reader compatibility
- High contrast theme support
- Reduced motion preferences

## Performance Optimizations

- Code splitting with React.lazy()
- Image optimization and lazy loading
- Efficient re-rendering with React.memo()
- Query caching with React Query
- Bundle size optimization
- Service worker for caching (production)

## Security Features

- XSS protection
- CSRF protection
- Secure token storage
- Input validation and sanitization
- Rate limiting awareness
- Secure HTTP headers

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+
- Mobile browsers (iOS Safari, Chrome Mobile)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation wiki

## Deployment

### Production Build
```bash
npm run build
```

### Docker Deployment
```bash
docker build -t contentguard-frontend .
docker run -p 3000:80 contentguard-frontend
```

### Environment Variables for Production
- `REACT_APP_API_BASE_URL` - Production API URL
- `REACT_APP_WS_URL` - Production WebSocket URL
- `REACT_APP_ENABLE_ANALYTICS` - Enable Google Analytics
- `REACT_APP_SENTRY_DSN` - Error tracking (optional)