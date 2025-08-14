# Suggested Development Commands

## Backend (Python) Commands
```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest
pytest --cov=src/autodmca --cov-report=html  # With coverage

# Code quality checks
black src/                    # Format code
isort src/                    # Sort imports  
mypy src/                     # Type checking
ruff src/                     # Linting

# Run examples
python examples/basic_usage.py
python examples/advanced_features.py
```

## Frontend (React) Commands  
```bash
# Install dependencies
npm install

# Development server
npm run dev                   # Start dev server on http://localhost:3000

# Build and preview
npm run build                 # Production build
npm run preview              # Preview production build

# Code quality
npm run lint                 # Run ESLint
npx tsc --noEmit            # TypeScript type checking (no build output)
```

## Windows System Commands
```cmd
# File operations
dir                          # List directory contents (ls equivalent)
type filename.txt            # Display file contents (cat equivalent)  
cd directory_name            # Change directory
md directory_name            # Create directory (mkdir equivalent)
del filename.txt             # Delete file (rm equivalent)
findstr "pattern" file.txt   # Search in files (grep equivalent)

# Git operations  
git status                   # Check repository status
git add .                    # Stage all changes
git commit -m "message"      # Commit changes
git push                     # Push to remote repository
git pull                     # Pull latest changes
```

## Project Startup Sequence
1. Ensure Python 3.10+ and Node.js 18+ are installed
2. Backend setup: `pip install -r requirements.txt`
3. Frontend setup: `cd frontend && npm install`  
4. Start frontend: `npm run dev`
5. Configure environment variables in `.env` files