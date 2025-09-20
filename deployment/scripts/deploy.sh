#!/bin/bash
set -e

echo "🚀 Starting CaseForge deployment..."

# Check if .env file exists
if [ ! -f "deployment/configs/.env" ]; then
    echo "❌ Error: deployment/configs/.env file not found!"
    echo "Please copy deployment/configs/.env.production to deployment/configs/.env and configure it."
    exit 1
fi

# Load environment variables
export $(cat deployment/configs/.env | grep -v '^#' | xargs)

# Validate required environment variables
required_vars=(
    "SECRET_KEY"
    "POSTGRES_PASSWORD"
    "OPENAI_API_KEY"
    "ALLOWED_HOSTS"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Error: $var is not set in .env file"
        exit 1
    fi
done

echo "✅ Environment variables validated"

# Build and start services
echo "🔨 Building Docker images..."
cd deployment/docker
docker-compose -f docker-compose.production.yml build

echo "🗄️ Starting database..."
docker-compose -f docker-compose.production.yml up -d db redis

echo "⏳ Waiting for database to be ready..."
sleep 10

echo "🔄 Running database migrations..."
docker-compose -f docker-compose.production.yml run --rm web python manage.py migrate

echo "👤 Creating superuser (if needed)..."
docker-compose -f docker-compose.production.yml run --rm web python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print("Superuser 'admin' created with password 'admin123'")
else:
    print("Superuser 'admin' already exists")
EOF

echo "📦 Collecting static files..."
docker-compose -f docker-compose.production.yml run --rm web python manage.py collectstatic --noinput

echo "🚀 Starting all services..."
docker-compose -f docker-compose.production.yml up -d

echo "✅ Deployment complete!"
echo ""
echo "🌐 Application should be available at:"
echo "   http://localhost (if running locally)"
echo "   http://${ALLOWED_HOSTS%,*} (if deployed remotely)"
echo ""
echo "🔧 Admin interface:"
echo "   http://localhost/admin"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo "📊 To view logs:"
echo "   docker-compose -f deployment/docker/docker-compose.production.yml logs -f"
echo ""
echo "🛑 To stop services:"
echo "   docker-compose -f deployment/docker/docker-compose.production.yml down"