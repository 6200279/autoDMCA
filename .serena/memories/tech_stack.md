# Technology Stack

## Backend (Python)
- **Framework**: FastAPI with async/await support
- **Models**: Pydantic for data validation, SQLAlchemy for ORM
- **Email**: SendGrid API + SMTP fallback
- **WHOIS**: python-whois with custom enhancements
- **Templates**: Jinja2 with legal compliance validation
- **Caching**: Redis with automatic TTL management
- **Rate Limiting**: Token bucket algorithm with backoff
- **Testing**: pytest with asyncio and mocking

## Frontend (React) 
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **UI Framework**: PrimeReact (migrated from Material-UI)
- **State Management**: React Query (TanStack Query)
- **Form Management**: React Hook Form with Yup validation
- **Charts**: Chart.js with react-chartjs-2
- **File Upload**: React Dropzone
- **Date Handling**: date-fns
- **WebSocket**: Socket.io-client
- **HTTP Client**: Axios
- **Routing**: React Router v6

## Infrastructure
- **Database**: PostgreSQL with Redis caching
- **Queue**: Redis-based task queue
- **Email**: SendGrid for primary delivery
- **APIs**: Google/Bing search APIs for delisting
- **Security**: JWT tokens, bcrypt hashing, input sanitization

## Development Tools
- **Python**: Black, isort, mypy, ruff for code quality
- **Frontend**: ESLint, TypeScript compiler
- **Testing**: pytest for backend, standard React testing for frontend
- **Version Control**: Git with standard workflow