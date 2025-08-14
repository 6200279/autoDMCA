# Task Completion Checklist

## When a Development Task is Complete

### Frontend Development
1. **Code Quality Checks**
   ```bash
   npm run lint              # ESLint validation
   npx tsc --noEmit         # TypeScript type checking
   npm run build            # Ensure production build works
   ```

2. **Manual Testing**
   - Test component functionality in browser
   - Verify responsive design on mobile/desktop
   - Check accessibility (keyboard navigation, screen readers)
   - Validate form submissions and error handling

3. **Integration Testing** 
   - Verify API integration with backend endpoints
   - Test WebSocket connections if applicable
   - Confirm proper error handling for network failures

### Backend Development  
1. **Code Quality Checks**
   ```bash
   black src/               # Format code
   isort src/               # Sort imports
   mypy src/                # Type checking
   ruff src/                # Linting
   ```

2. **Testing**
   ```bash
   python -m pytest        # Run all tests
   pytest --cov=src/autodmca --cov-report=html  # Coverage report
   ```

3. **Manual Validation**
   - Test API endpoints manually or with tools
   - Verify database migrations if applicable
   - Check log outputs for errors

### General Completion Steps
1. **Version Control**
   - Commit changes with descriptive messages
   - Ensure all files are tracked in git
   - Only commit when explicitly requested by user

2. **Documentation**
   - Update relevant documentation if changes affect public APIs
   - Add code comments for complex business logic
   - Update memory files if architectural changes were made

3. **Performance Considerations**
   - Check for potential memory leaks or performance issues
   - Verify proper error handling and user feedback
   - Ensure security best practices are followed

## Never Commit Without User Request
**IMPORTANT**: Never run `git commit` or `git push` unless explicitly requested by the user. Always run quality checks but wait for explicit commit instructions.