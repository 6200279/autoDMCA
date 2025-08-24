# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the AutoDMCA system - a comprehensive DMCA takedown automation platform with creator anonymity protection. It consists of:

1. **Python Backend** - DMCA processing engine using FastAPI, SQLAlchemy, and asynchronous services
2. **React Frontend** - Modern dashboard built with Vite, TypeScript, and PrimeReact
3. **Mock API Server** - Development server (`dashboard_mock_api.py`) for testing frontend without full backend

## Critical Architecture Decisions

### Frontend-Backend Communication
- Frontend runs on port 3000-3005 (Vite auto-selects available port)
- Mock API runs on port 8080 (previously was scattered across 8000, 8001, 19001)
- Real backend API (when available) runs on port 8001
- WebSocket connections default to `ws://localhost:8000/ws`
- CORS is configured to allow localhost ports 3000-3006

### Environment Variables
**Important:** The frontend uses Vite, not Create React App. Use `import.meta.env` instead of `process.env`:
- `import.meta.env.DEV` instead of `process.env.NODE_ENV === 'development'`
- `import.meta.env.PROD` instead of `process.env.NODE_ENV === 'production'`
- `import.meta.env.VITE_*` for custom environment variables

### Authentication Flow
- Uses JWT tokens stored in localStorage
- Mock API accepts any credentials and returns mock tokens
- AuthProvider must wrap all components that use `useAuth()`
- Router must wrap AuthProvider (not the other way around)

## Common Development Commands

### Frontend Development
```bash
cd frontend
npm install                    # Install dependencies
npm run dev                    # Start dev server (auto-selects port)
npm run build                 # Build for production
npm run preview              # Preview production build
npm run lint                 # Run ESLint
npm run type-check           # Check TypeScript types
npm run test                 # Run tests with Vitest
npm run test:coverage        # Run tests with coverage
```

### Backend Development
```bash
# Python DMCA Engine
pip install -r requirements.txt     # Install Python dependencies
pytest                              # Run all tests
pytest tests/unit/test_models.py -v # Run specific test file
pytest --cov=src/autodmca          # Run with coverage

# Mock API Server (for frontend development)
python dashboard_mock_api.py       # Runs on port 8080
```

### Docker Development
```bash
docker-compose -f docker-compose.local.yml up    # Start all services
docker-compose -f docker-compose.local.yml down  # Stop all services
```

## Key File Locations

### Frontend
- `frontend/src/App.tsx` - Main app component with routing structure
- `frontend/src/types/api.ts` - TypeScript interfaces (watch for duplicates!)
- `frontend/src/services/api.ts` - API client configuration
- `frontend/src/contexts/AuthContext.tsx` - Authentication state management
- `frontend/vite.config.ts` - Vite configuration including CSP headers

### Backend
- `src/autodmca/services/dmca_service.py` - Main DMCA orchestration
- `src/autodmca/models/` - Pydantic and SQLAlchemy models
- `dashboard_mock_api.py` - Mock API for frontend development
- `backend/app/api/v1/endpoints/` - FastAPI endpoints

## Common Issues and Solutions

### Blank Page on Frontend
1. Check browser console for `process is not defined` errors - replace with `import.meta.env`
2. Verify AuthProvider wraps components using `useAuth()`
3. Ensure Router wraps AuthProvider in App.tsx

### CORS Errors
1. Check that mock API includes current frontend port in CORS origins
2. Verify API URL matches in `frontend/src/services/api.ts`
3. Restart mock API after changing CORS configuration

### TypeScript Errors
- Check `frontend/src/types/api.ts` for duplicate interface definitions
- Ensure DMCA types are imported from `./dmca` not redefined
- SystemHealth interface should support both 'down' and 'critical' status values

### Port Conflicts
- Frontend: Vite auto-increments from 3000 if port is in use
- Mock API: Currently hardcoded to 8080 in `dashboard_mock_api.py`
- Update CORS origins in mock API when frontend port changes

## Testing Strategy

### Frontend Testing
- Unit tests use Vitest with React Testing Library
- E2E tests use Playwright
- Mock API provides test data without requiring full backend

### Backend Testing
- Unit tests for models, services, and templates
- Integration tests for DMCA workflow
- Mock external services (SendGrid, WHOIS) for testing

## Security Considerations

- Never commit real API keys or tokens
- Use environment variables for sensitive configuration
- Frontend CSP headers configured in vite.config.ts
- DMCA agent credentials should be anonymized for creator protection

## Database Schema

The system uses PostgreSQL with these key tables:
- `creators` - Creator profiles with anonymity settings
- `takedown_requests` - DMCA takedown tracking
- `hosting_providers` - Cached WHOIS data
- `dmca_agents` - Legal representatives
- `email_logs` - Email dispatch tracking

## Performance Notes

- Frontend uses code splitting with React.lazy()
- API responses are cached with React Query
- Redis used for backend caching and rate limiting
- WebSocket for real-time updates

## Deployment Considerations

- Frontend builds to `frontend/dist/`
- Static assets use content hashing for cache busting
- Service worker enabled in production for offline support
- Environment-specific configs in `.env` files (not committed)