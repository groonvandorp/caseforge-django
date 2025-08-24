# CaseForge Django - Production Ready

Django port of CaseForge with modern architecture for production deployment.

## Key Improvements

- **Django REST Framework** → Better API documentation, serialization, permissions
- **PostgreSQL-first** → Production database with proper migrations  
- **Celery + Redis** → Async AI processing, better scalability
- **Modern Frontend** → React/TypeScript with Material-UI
- **Production Infrastructure** → Docker Compose, logging, monitoring

## Quick Start

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Environment
cp .env.example .env
# Edit .env with your API keys

# Database
docker-compose up -d db redis
python manage.py migrate
python manage.py createsuperuser

# Run
python manage.py runserver
```

## Development

```bash
# Full stack with Docker
docker-compose up

# Run tests
python manage.py test

# Format code
make format

# Lint
make lint
```

## Migration from FastAPI

This Django port maintains API compatibility while adding:
- Django Admin interface for content management
- Better security and CSRF protection
- Async task processing with Celery
- Production-ready logging and monitoring
- Comprehensive test framework

## Production Deployment

Ready for deployment on:
- Google Cloud Run
- AWS ECS/Fargate  
- Kubernetes
- Traditional servers

See deployment documentation for specific instructions.