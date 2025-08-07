# AutoDMCA Content Scanning Engine

A comprehensive Python-based content scanning engine that automatically monitors the internet for copyright infringement, uses AI-powered content matching, and processes DMCA takedown requests.

## Features

### 🔍 **Advanced Content Discovery**
- **Search Engine Integration**: Google Custom Search and Bing Search APIs
- **Piracy Site Crawling**: Specialized crawlers for known piracy sites and forums
- **Proxy Support**: Built-in proxy rotation and anti-detection measures
- **Rate Limiting**: Intelligent rate limiting to respect API limits and avoid blocking

### 🤖 **AI-Powered Content Matching**
- **Face Recognition**: OpenCV and face_recognition library integration
- **Perceptual Image Hashing**: Detect similar/duplicate images even with modifications
- **Content Fingerprinting**: Multiple hash algorithms (pHash, aHash, dHash, wHash)
- **Text Pattern Matching**: Smart keyword and username variation matching

### ⚖️ **Automated DMCA Processing**
- **Queue-Based Processing**: Redis-backed DMCA request queue
- **Template System**: Professional DMCA notice templates
- **Contact Resolution**: Automatic hosting provider contact lookup
- **Multi-Channel Delivery**: Email and web form submission support
- **Status Tracking**: Complete lifecycle tracking of takedown requests

### 🕐 **Background Task Scheduling**
- **APScheduler Integration**: Robust task scheduling with Redis persistence
- **Multiple Scan Types**: Full scans, quick scans, priority scans
- **Retry Logic**: Intelligent retry mechanisms with exponential backoff
- **Health Monitoring**: System health checks and maintenance tasks

### 📧 **Notification System**
- **Multi-Channel Notifications**: Email, webhooks, and API callbacks
- **SendGrid Integration**: Professional email delivery
- **Alert Levels**: Configurable notification priorities
- **Queue Management**: Reliable notification delivery with retry logic

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys and configuration
```

## Quick Start

```python
import asyncio
from scanning.scanner import ContentScanner
from scanning.config import ScannerConfig, ScannerSettings

async def main():
    # Configure scanner
    settings = ScannerSettings(
        google_api_key="your-api-key",
        google_search_engine_id="your-search-engine-id",
        bing_api_key="your-bing-key",
        redis_url="redis://localhost:6379/0"
    )
    
    scanner = ContentScanner(ScannerConfig(settings=settings))
    await scanner.initialize()
    
    try:
        # Add person to monitor
        success = await scanner.add_person(
            person_id="creator_123",
            reference_images=["path/to/reference.jpg"],
            usernames=["creator_username"],
            email="creator@example.com"
        )
        
        # Trigger immediate scan
        task_id = await scanner.trigger_immediate_scan("creator_123")
        print(f"Scan started: {task_id}")
        
    finally:
        await scanner.close()

asyncio.run(main())
```

## Key Components

### 1. Search Engine Integration
- Google Custom Search API support
- Bing Search API integration
- Concurrent search across multiple engines
- Smart result aggregation and deduplication

### 2. Web Crawling with Proxy Support
- Advanced web crawler with anti-detection
- Proxy rotation and health checking
- Cloudflare bypass capabilities
- Rate limiting per domain

### 3. Face Recognition System
- OpenCV-based face detection
- face_recognition library integration
- Reference image management
- Confidence scoring and matching

### 4. Image Hashing
- Multiple perceptual hash algorithms
- Duplicate detection with modifications
- Color histogram matching
- Wavelet-based hashing

### 5. DMCA Processing Queue
- Redis-backed queue system
- Professional DMCA notice templates
- Automatic contact resolution
- Status tracking and retry logic

### 6. Task Scheduling
- APScheduler with Redis persistence
- Multiple scan types and priorities
- Health monitoring and maintenance
- Concurrent task execution

## File Structure

```
C:\Users\stijn\autoDMCA\
├── scanning/
│   ├── __init__.py
│   ├── config.py                    # Configuration management
│   ├── scanner.py                   # Main ContentScanner class
│   │
│   ├── crawlers/                    # Web crawling components
│   │   ├── __init__.py
│   │   ├── search_engine_api.py     # Google/Bing API integration
│   │   ├── web_crawler.py           # Advanced web crawler
│   │   └── piracy_crawler.py        # Specialized piracy site crawler
│   │
│   ├── processors/                  # AI content processing
│   │   ├── __init__.py
│   │   ├── face_recognition_processor.py  # Face recognition
│   │   ├── image_hash_processor.py        # Image hashing
│   │   └── content_matcher.py             # Content matching coordinator
│   │
│   ├── queue/                       # DMCA processing
│   │   ├── __init__.py
│   │   ├── dmca_queue.py            # DMCA request queue
│   │   └── notification_sender.py   # Notification system
│   │
│   └── scheduler/                   # Task scheduling
│       ├── __init__.py
│       ├── scan_scheduler.py        # APScheduler integration
│       └── task_manager.py          # Task coordination
│
├── tests/                           # Comprehensive test suite
│   ├── __init__.py
│   ├── conftest.py                  # Pytest configuration
│   ├── test_face_recognition.py
│   ├── test_scanner.py
│   ├── test_task_manager.py
│   └── pytest.ini
│
├── requirements.txt                 # Python dependencies
├── example_usage.py                 # Usage examples
└── SCANNER_README.md               # This file
```

## Testing

The scanning engine includes comprehensive tests:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=scanning --cov-report=html

# Run specific test categories
pytest -m "unit"        # Unit tests only
pytest -m "not slow"    # Skip slow integration tests
```

Test coverage includes:
- Face recognition processing
- Image hashing algorithms
- Content matching logic
- Task scheduling system
- DMCA queue processing
- Error handling scenarios

## Configuration Options

### Core Settings
- `google_api_key`: Google Custom Search API key
- `bing_api_key`: Bing Search API key
- `redis_url`: Redis connection string
- `database_url`: PostgreSQL connection string

### Rate Limiting
- `requests_per_minute`: API request rate limit
- `concurrent_requests`: Maximum concurrent requests
- `proxy_enabled`: Enable proxy rotation

### AI Processing
- `face_recognition_tolerance`: Face matching sensitivity
- `similarity_threshold`: Image similarity threshold
- `hash_size`: Perceptual hash size

### DMCA Processing
- `dmca_sender_email`: Sender email for notices
- `dmca_sender_name`: Legal entity name
- `sendgrid_api_key`: SendGrid API key

## Performance Considerations

### Scalability Features
- **Async/Await**: Non-blocking I/O operations
- **Connection Pooling**: Efficient HTTP connection reuse
- **Redis Queuing**: Distributed task processing
- **Proxy Rotation**: Load distribution
- **Rate Limiting**: API compliance

### Resource Usage
- **Memory**: Efficient image processing with cleanup
- **CPU**: Optimized AI algorithms
- **Network**: Smart request batching and caching
- **Storage**: Minimal disk usage with temp file cleanup

## Security Features

### Privacy Protection
- **Encrypted Storage**: Sensitive data encryption at rest
- **Proxy Support**: IP address protection
- **Anonymous DMCA**: File on behalf of users
- **Data Export**: GDPR compliance support

### Anti-Detection
- **User-Agent Rotation**: Varied browser signatures
- **Request Timing**: Human-like browsing patterns
- **Cloudflare Bypass**: Advanced anti-bot evasion
- **Proxy Cycling**: IP address rotation

## Integration Examples

### Basic Usage
```python
# Simple scanning setup
scanner = ContentScanner()
await scanner.initialize()

# Add person for monitoring
await scanner.add_person(
    person_id="user123",
    reference_images=["photo.jpg"],
    usernames=["username"],
    email="user@example.com"
)
```

### Advanced Configuration
```python
# Custom configuration
settings = ScannerSettings(
    face_recognition_tolerance=0.7,
    similarity_threshold=0.9,
    requests_per_minute=120,
    proxy_enabled=True
)

config = ScannerConfig(settings=settings)
scanner = ContentScanner(config)
```

### Manual Scanning
```python
# Scan specific URL
matches = await scanner.manual_scan_url(
    "https://suspicious-site.com/content",
    person_id="user123"
)

# Check match quality
for match in matches:
    if match.is_positive_match:
        print(f"Match confidence: {match.confidence_score:.2%}")
```

## Production Deployment

### Requirements
- Python 3.8+
- Redis server
- PostgreSQL database
- Adequate memory for image processing (4GB+ recommended)

### Environment Setup
```bash
# Production environment variables
export SCANNER_LOG_LEVEL=INFO
export SCANNER_REDIS_URL=redis://prod-redis:6379/0
export SCANNER_DATABASE_URL=postgresql://user:pass@prod-db/autodmca
export SCANNER_PROXY_ENABLED=true
```

### Monitoring
- Health check endpoints
- Structured JSON logging
- Performance metrics
- Error tracking integration

This scanning engine provides a robust foundation for automated content protection, combining advanced AI techniques with reliable infrastructure for production use.