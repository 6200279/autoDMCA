#!/bin/bash
# Secure entrypoint script for Content Protection Platform

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Security: Validate environment variables
required_vars=(
    "DATABASE_URL"
    "REDIS_URL"
    "SECRET_KEY"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var:-}" ]; then
        echo "ERROR: Required environment variable $var is not set"
        exit 1
    fi
done

# Security: Validate SECRET_KEY strength
if [ ${#SECRET_KEY} -lt 32 ]; then
    echo "ERROR: SECRET_KEY must be at least 32 characters long"
    exit 1
fi

if [ "$SECRET_KEY" = "dev-secret-key-change-in-production" ]; then
    echo "ERROR: Default SECRET_KEY detected. Change SECRET_KEY in production!"
    exit 1
fi

# Security: Set secure file permissions on startup
umask 027

# Security: Check if running as root (should not happen with our Dockerfile)
if [ "$(id -u)" -eq 0 ]; then
    echo "WARNING: Running as root user is not recommended for security"
fi

# Security: Log startup information
echo "Starting Content Protection Platform..."
echo "Python version: $(python --version)"
echo "User: $(whoami)"
echo "Working directory: $(pwd)"
echo "Environment: ${ENVIRONMENT:-development}"

# Security: Run database migrations securely
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    echo "Running database migrations..."
    python -m alembic upgrade head
fi

# Security: Start the application
exec "$@"