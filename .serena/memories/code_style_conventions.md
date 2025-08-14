# Code Style and Conventions

## Python Backend Style
- **Line Length**: 100 characters (configured in pyproject.toml)
- **Formatter**: Black with isort for import sorting
- **Type Hints**: Required for all functions (mypy strict mode)
- **Linting**: Ruff with comprehensive rule set
- **Docstrings**: Expected for public functions and classes
- **Imports**: Organized with isort, grouped: standard library, third-party, local
- **Naming**: snake_case for variables/functions, PascalCase for classes

## Frontend (React/TypeScript) Style  
- **Framework**: React 18 with TypeScript
- **UI Components**: PrimeReact (recently migrated from Material-UI)
- **File Naming**: PascalCase for components (.tsx), camelCase for utilities (.ts)
- **Component Structure**: Functional components with hooks
- **State Management**: React Query for server state, Context API for local state
- **Form Handling**: React Hook Form with Yup validation
- **Styling**: PrimeReact themes with PrimeFlex utility classes

## Project Structure Patterns
- **Backend**: Domain-driven structure (models/, services/, templates/, utils/)
- **Frontend**: Feature-based structure (components/, pages/, services/, types/)
- **Separation of Concerns**: Clear API layer, reusable components, type-safe interfaces
- **Error Handling**: Consistent error boundaries and user feedback patterns

## TypeScript Conventions
- **Interfaces**: PascalCase with descriptive names
- **Enums**: PascalCase for enum names, UPPER_CASE for values
- **Types**: Prefer interfaces over types for object shapes
- **Generics**: Single letter naming (T, K, V) or descriptive names

## API Integration Patterns
- **HTTP Client**: Axios with interceptors for authentication
- **API Services**: Grouped by feature (dashboardApi, submissionApi, etc.)
- **Response Types**: Strongly typed with TypeScript interfaces
- **Error Handling**: Centralized error handling with user-friendly messages