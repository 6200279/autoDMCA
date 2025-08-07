#!/bin/bash

# Content Protection Platform Setup Script

set -e

echo "🚀 Setting up Content Protection Platform..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is required but not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is required but not installed. Please install Docker Compose first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    
    # Generate a secure secret key
    SECRET_KEY=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
    sed -i "s/your_super_secure_secret_key_here_at_least_32_chars/$SECRET_KEY/" .env
    
    echo "⚠️  Please update the .env file with your actual configuration values"
    echo "   Especially database passwords, email settings, and API keys"
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p backend/app/db/migrations/versions
mkdir -p uploads
mkdir -p nginx/ssl
mkdir -p logs

# Set proper permissions
chmod +x scripts/*.sh
chmod 755 uploads

# Build and start services
echo "🔨 Building and starting Docker services..."
docker-compose up -d --build

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
sleep 10

# Run database migrations
echo "🔄 Running database migrations..."
docker-compose exec backend alembic upgrade head

# Create superuser (optional)
read -p "Do you want to create a superuser account? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker-compose exec backend python -c "
from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.db.models.user import User
from app.db.models.subscription import Subscription, SubscriptionPlan
import asyncio

async def create_superuser():
    db = SessionLocal()
    
    email = input('Enter superuser email: ')
    password = input('Enter superuser password: ')
    full_name = input('Enter full name: ')
    
    hashed_password = get_password_hash(password)
    
    user = User(
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
        is_superuser=True,
        is_active=True,
        is_verified=True
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create enterprise subscription for superuser
    subscription = Subscription(
        user_id=user.id,
        plan=SubscriptionPlan.ENTERPRISE,
        max_protected_profiles=999,
        max_monthly_scans=999999,
        max_takedown_requests=999,
        ai_face_recognition=True,
        priority_support=True,
        custom_branding=True,
        api_access=True
    )
    
    db.add(subscription)
    db.commit()
    
    print(f'✅ Superuser {email} created successfully!')
    db.close()

asyncio.run(create_superuser())
"
fi

echo ""
echo "🎉 Setup complete! Your Content Protection Platform is ready."
echo ""
echo "🌐 Access your application:"
echo "   Frontend: http://localhost:3000"
echo "   Backend API: http://localhost:8000"
echo "   API Documentation: http://localhost:8000/docs"
echo ""
echo "📋 Next steps:"
echo "   1. Update your .env file with production values"
echo "   2. Configure your email settings for DMCA notices"
echo "   3. Set up Stripe for billing (if using paid features)"
echo "   4. Review the README.md for detailed documentation"
echo ""
echo "🐛 To view logs: docker-compose logs -f"
echo "🛑 To stop services: docker-compose down"