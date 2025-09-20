# CaseForge Deployment Guide

This directory contains all deployment configurations and scripts for the CaseForge application.

## 📁 Directory Structure

```
deployment/
├── docker/                    # Docker configurations
│   ├── Dockerfile            # Development Dockerfile
│   ├── Dockerfile.production # Production Dockerfile
│   ├── docker-compose.yml    # Development compose
│   ├── docker-compose.production.yml # Production compose
│   └── nginx.conf            # Nginx configuration
├── configs/                  # Configuration files
│   ├── .env.example         # Environment template
│   ├── .env.production      # Production environment template
│   └── requirements.txt     # Python dependencies
├── scripts/                  # Deployment automation
│   ├── deploy.sh            # Production deployment
│   └── backup.sh            # Backup utility
└── kubernetes/              # K8s configs (future)
```

## 🚀 Quick Start

### Development Deployment

1. **Start development environment:**
   ```bash
   cd deployment/docker
   docker-compose up -d
   ```

2. **Access the application:**
   - Web App: http://localhost:8000
   - Database: localhost:5432
   - Redis: localhost:6379

### Production Deployment

1. **Configure environment:**
   ```bash
   cp deployment/configs/.env.production deployment/configs/.env
   # Edit .env with your production values
   ```

2. **Deploy:**
   ```bash
   ./deployment/scripts/deploy.sh
   ```

3. **Access:**
   - Application: http://your-domain.com
   - Admin: http://your-domain.com/admin

## ⚙️ Configuration

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | `your-secret-key-here` |
| `POSTGRES_PASSWORD` | Database password | `secure-password` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `ALLOWED_HOSTS` | Allowed hostnames | `yourdomain.com,www.yourdomain.com` |

### Optional Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Debug mode | `false` |
| `POSTGRES_DB` | Database name | `caseforge` |
| `POSTGRES_USER` | Database user | `postgres` |
| `EMAIL_HOST` | SMTP server | - |
| `SENTRY_DSN` | Error tracking | - |

## 🐳 Docker Services

### Development Stack
- **web**: Django development server
- **db**: PostgreSQL 15
- **redis**: Redis for caching/queuing
- **celery**: Background task worker

### Production Stack
- **web**: Django with Gunicorn
- **db**: PostgreSQL 15 with persistence
- **redis**: Redis with persistence
- **celery**: Background task worker
- **celery-beat**: Scheduled task scheduler
- **nginx**: Reverse proxy and static file server

## 📊 Monitoring & Maintenance

### Health Checks
- Application: `http://localhost/health/`
- Database: Built into Docker Compose
- Services: `docker-compose ps`

### Logs
```bash
# All services
docker-compose -f deployment/docker/docker-compose.production.yml logs -f

# Specific service
docker-compose -f deployment/docker/docker-compose.production.yml logs -f web
```

### Backups

#### Quick Backup (Recommended)
```bash
# Auto-detects environment and creates appropriate backup
./deployment/scripts/backup_wrapper.sh

# Alternative: Direct Python script
python deployment/scripts/backup_tools/unified_backup.py
```

#### Environment-Specific Backups
```bash
# Development (SQLite)
python db_management/utilities/backup_database.py

# Production (Docker PostgreSQL)
./deployment/scripts/backup.sh
```

#### Backup Locations
```bash
# View all backups
ls -la database_backups/

# View specific backup contents
ls -la database_backups/backup_20250828_144129/

# Restore from backup
cd database_backups/backup_20250828_144129/
python restore.py
```

📚 **Complete backup documentation:** `database_backups/README.md`

### Database Management
```bash
# Enter database shell
docker-compose -f deployment/docker/docker-compose.production.yml exec db psql -U postgres caseforge

# Run migrations
docker-compose -f deployment/docker/docker-compose.production.yml exec web python manage.py migrate

# Create superuser
docker-compose -f deployment/docker/docker-compose.production.yml exec web python manage.py createsuperuser
```

## 🔧 Batch Processing

The application includes several batch processing systems:

### Process Analysis
```bash
# Run from project root
cd batch_waste_by_type/
python test_waste_by_type.py
python monitor_waste_by_type.py
```

### Embedding Generation
```bash
cd batch_waste_embeddings/
python batch_generate_waste_embeddings.py --auto-poll
```

### Database Management
```bash
cd db_management/utilities/
python backup_database.py
```

## 🔐 Security Considerations

### Production Security
- Change default passwords
- Use strong SECRET_KEY
- Configure HTTPS with SSL certificates
- Restrict database access
- Enable authentication on Redis
- Configure firewall rules

### Environment Variables
- Never commit `.env` files
- Use secrets management in production
- Rotate API keys regularly
- Monitor access logs

## 🚨 Troubleshooting

### Common Issues

1. **Database connection failed**
   ```bash
   # Check database status
   docker-compose ps db

   # View database logs
   docker-compose logs db
   ```

2. **Static files not loading**
   ```bash
   # Collect static files
   docker-compose exec web python manage.py collectstatic --noinput
   ```

3. **Celery tasks not processing**
   ```bash
   # Check celery worker logs
   docker-compose logs celery

   # Restart celery
   docker-compose restart celery
   ```

4. **OpenAI API errors**
   - Verify API key in environment
   - Check API quota and billing
   - Monitor rate limits

### Resource Requirements

**Minimum:**
- CPU: 2 cores
- RAM: 4GB
- Storage: 20GB

**Recommended:**
- CPU: 4 cores
- RAM: 8GB
- Storage: 100GB SSD

## 📚 Additional Resources

- [Django Deployment Guide](https://docs.djangoproject.com/en/4.2/howto/deployment/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

## 🆘 Support

For deployment issues:

1. Check application logs
2. Verify environment configuration
3. Consult troubleshooting section
4. Contact development team