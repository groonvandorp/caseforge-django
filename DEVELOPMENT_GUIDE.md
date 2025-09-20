# CaseForge Development Guide

**Complete guide for developing, deploying, and maintaining the CaseForge process model-driven AI use case generation system.**

---

## 📋 Project Overview

**CaseForge** is an enterprise Django application that enables AI-driven analysis and optimization of business processes using the APQC Process Classification Framework (PCF). The system generates process details, identifies waste patterns using TIMWOOD+ methodology, and recommends AI use cases for process improvement.

### Key Capabilities
- **Process Model Management**: APQC PCF support for Cross Industry, Life Science, and Retail
- **AI Content Generation**: Batch processing for process details, waste analysis, and use case recommendations
- **Semantic Search**: Vector embeddings for intelligent process and use case discovery
- **TIMWOOD+ Waste Analysis**: 12 waste types analysis across process hierarchies
- **Technology Recommendations**: AI-driven technology matching for implementation

---

## 🏗️ System Architecture

### Core Components
```
┌─ Frontend (React + MUI) ──┐     ┌─ Backend (Django + DRF) ──┐
│  • Composer View          │────▶│  • Process Model API      │
│  • Build Advisor          │     │  • Waste Analysis API     │
│  • Technology Search      │     │  • Use Case Management    │
└───────────────────────────┘     └───────────────────────────┘
                                              │
                        ┌─────────────────────┼─────────────────────┐
                        ▼                     ▼                     ▼
              ┌─ Database Layer ─┐   ┌─ Batch Processing ─┐   ┌─ AI Services ─┐
              │  • PostgreSQL     │   │  • OpenAI Batch API │   │  • GPT-5 Model │
              │  • SQLite (dev)   │   │  • Embedding Gen.   │   │  • Embeddings  │
              │  • Vector Storage │   │  • Result Proc.     │   │  • Token Mgmt  │
              └───────────────────┘   └─────────────────────┘   └────────────────┘
```

### Data Flow
```
Process Models → Process Details → Waste Analysis → Use Case Generation → Technology Matching
      ↓               ↓                ↓                    ↓                    ↓
   PCF Import    AI Description    TIMWOOD+ Types      AI Candidates      Technology DB
```

---

## 📁 Project Structure

### Organized Codebase
```
caseforge/
├── 📄 manage.py                      # Django management
├── 📄 requirements.txt               # Python dependencies
├── 📄 .env.example                   # Environment template
├── 📄 DEVELOPMENT_GUIDE.md          # This comprehensive guide
│
├── 📁 core/                          # Django application core
│   ├── models.py                     # Data models (ProcessNode, NodeDocument, etc.)
│   ├── admin.py                      # Django admin interface
│   └── migrations/                   # Database schema migrations
│
├── 📁 api/                           # REST API layer
│   ├── views.py                      # API endpoints
│   ├── serializers.py               # Data serialization
│   ├── urls.py                       # URL routing
│   └── services.py                   # Business logic
│
├── 📁 frontend/                      # React application
│   ├── src/components/               # React components
│   ├── src/services/                 # API client
│   └── package.json                  # Node dependencies
│
├── 📁 batch_*/                       # Batch processing systems (organized)
│   ├── batch_waste_by_type/         # ⭐ Current waste analysis
│   ├── batch_waste_embeddings/      # Document embeddings
│   ├── batch_process_details/       # Process descriptions
│   ├── batch_usecase_candidates/    # AI use case generation
│   ├── batch_embeddings/            # General embeddings
│   └── batch_processing/            # Utilities
│
├── 📁 db_management/                 # Database operations (organized)
│   ├── imports/                     # Model imports & population
│   ├── migrations/                  # Data structure migrations
│   ├── data_sync/                   # Cross-model data copying
│   └── utilities/                   # Analysis & debugging tools
│
├── 📁 deployment/                    # Deployment infrastructure (organized)
│   ├── docker/                      # Docker configurations
│   ├── configs/                     # Environment templates
│   ├── scripts/                     # Automation scripts
│   └── README.md                    # Deployment guide
│
├── 📁 database_backups/             # Backup system (organized)
│   ├── backup_YYYYMMDD_HHMMSS/     # Timestamped backups
│   └── README.md                    # Backup documentation
│
├── 📁 services/                     # External services & integrations
│   └── mcp/                        # Model Context Protocol server
│
└── 📁 docs/                         # Comprehensive documentation
    ├── systems/                     # System documentation
    ├── services/                    # Service documentation
    ├── workflows/                   # Process workflows
    └── api/                         # API documentation
```

---

## 🚀 Quick Start

### Development Setup
```bash
# 1. Clone and setup
git clone <repository>
cd caseforge
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# 2. Install dependencies
pip install -r requirements.txt
cd frontend && npm install && cd ..

# 3. Configure environment
cp .env.example .env
# Edit .env with your settings (OpenAI API key, etc.)

# 4. Setup database
python manage.py migrate
python manage.py createsuperuser

# 5. Start development servers
python manage.py runserver &          # Django backend (port 8000)
cd frontend && npm start              # React frontend (port 3000)
```

### Production Deployment
```bash
# Quick production deployment
cp deployment/configs/.env.production deployment/configs/.env
# Edit .env with production values
./deployment/scripts/deploy.sh
```

---

## 💼 Core Workflows

### 1. Process Model Management

#### Import APQC Models
```bash
# Import Life Science model
cd db_management/imports/
python import_lifescience_model.py

# Populate technology data
python populate_initial_technologies.py
```

#### Cross-Model Data Sync
```bash
# Copy data between models using PCF IDs
cd db_management/data_sync/
python copy_process_details_pcf_based.py
python copy_usecase_candidates_pcf_based.py
```

### 2. AI Content Generation

#### Complete Waste Analysis Workflow
```bash
# 1. Generate process details (prerequisite)
cd batch_process_details/
python batch_generate_process_details.py

# 2. Generate waste analysis by type (current approach)
cd ../batch_waste_by_type/
python test_waste_by_type.py           # Test with 2 processes × 3 waste types
python batch_generate_waste_by_type.py # Full generation (12 types per process)
python monitor_waste_by_type.py        # Monitor progress

# 3. Generate embeddings for search
cd ../batch_waste_embeddings/
python batch_generate_waste_embeddings.py --auto-poll
python monitor_waste_embeddings.py
```

#### Use Case Generation Workflow
```bash
# Generate AI use case candidates
cd batch_usecase_candidates/
python batch_generate_usecase_candidates.py
python batch_generate_usecase_specs.py
python monitor_usecase_batch.py

# Generate use case embeddings
cd ../batch_embeddings/
python batch_generate_usecase_embeddings.py
```

### 3. Backup & Recovery

#### Create Backups
```bash
# Unified backup (auto-detects environment)
./deployment/scripts/backup_wrapper.sh

# View backups
ls -la database_backups/

# Restore from backup
cd database_backups/backup_20250828_144129/
python restore.py
```

---

## 🔧 Key Technologies

### Backend Stack
- **Django 4.2+**: Web framework with ORM
- **Django REST Framework**: API layer
- **PostgreSQL**: Production database
- **SQLite**: Development database
- **Celery**: Background task processing
- **Redis**: Cache and message broker

### Frontend Stack
- **React 18**: User interface framework
- **Material-UI (MUI)**: Component library
- **TypeScript**: Type-safe JavaScript
- **Axios**: HTTP client for API calls

### AI & Processing
- **OpenAI GPT-5**: Text generation model
- **OpenAI Embeddings**: Semantic search (text-embedding-3-small)
- **OpenAI Batch API**: Cost-effective bulk processing
- **Vector Search**: Semantic similarity matching

### Infrastructure
- **Docker**: Containerization
- **Docker Compose**: Multi-service orchestration
- **Nginx**: Reverse proxy and static file serving
- **Gunicorn**: WSGI HTTP server

---

## 📊 Data Models

### Core Models

#### ProcessNode
```python
# Hierarchical process structure
ProcessNode.objects.filter(model_version__model__model_key='apqc_pcf')
ProcessNode.objects.filter(level=5, is_leaf=True)  # Leaf nodes
```

#### NodeDocument
```python
# AI-generated content storage
NodeDocument.objects.filter(document_type='process_details')
NodeDocument.objects.filter(document_type__startswith='waste_')  # 12 waste types
NodeDocument.objects.filter(document_type='usecase_spec')
```

#### Embeddings
```python
# Semantic search support
NodeEmbedding.objects.all()                    # Process embeddings
NodeDocumentEmbedding.objects.all()            # Document embeddings
```

### TIMWOOD+ Waste Types
1. **Transportation** (`waste_transportation`)
2. **Inventory** (`waste_inventory`)
3. **Motion** (`waste_motion`)
4. **Waiting** (`waste_waiting`)
5. **Overprocessing** (`waste_overprocessing`)
6. **Overproduction** (`waste_overproduction`)
7. **Defects** (`waste_defects`)
8. **Skills Underutilization** (`waste_skills`)
9. **Digital Waste** (`waste_digital`)
10. **Knowledge Waste** (`waste_knowledge`)
11. **Compliance Waste** (`waste_compliance`)
12. **Communication Waste** (`waste_communication`)

---

## 🔍 API Endpoints

### Process Management
```
GET  /api/process-models/                    # List process models
GET  /api/nodes/{id}/                        # Get process node
GET  /api/nodes/{id}/children/               # Get child nodes
POST /api/nodes/{id}/bookmark/               # Bookmark node
```

### Content & Search
```
GET  /api/nodes/{id}/documents/              # Get node documents
GET  /api/search/semantic/                   # Semantic search
GET  /api/search/processes/                  # Process search
POST /api/generate/process-details/          # Generate process details
```

### Build Advisor
```
GET  /api/build-advice/{use_case_id}/        # Get technology recommendations
GET  /api/technology-landscape/              # Get technology catalog
GET  /api/technologies/                      # Search technologies
```

---

## 🚨 Troubleshooting

### Common Development Issues

1. **Django Server Won't Start**
   ```bash
   # Check database connectivity
   python manage.py check --database default

   # Apply pending migrations
   python manage.py migrate
   ```

2. **OpenAI Batch Processing Fails**
   ```bash
   # Check API key configuration
   python manage.py shell -c "from core.models import AdminSettings; print(AdminSettings.get_setting('openai_api_key')[:10])"

   # Verify batch input format
   cd batch_waste_by_type/batch_waste_by_type/
   head -5 input_*.jsonl
   ```

3. **Frontend Build Errors**
   ```bash
   cd frontend/
   rm -rf node_modules/ package-lock.json
   npm install
   npm start
   ```

4. **Database Migration Issues**
   ```bash
   # Reset migrations (development only)
   python manage.py migrate core zero
   rm core/migrations/000*.py
   python manage.py makemigrations
   python manage.py migrate
   ```

### Production Issues

1. **Container Health Checks**
   ```bash
   docker-compose -f deployment/docker/docker-compose.production.yml ps
   docker-compose logs web
   ```

2. **Database Performance**
   ```bash
   # Check database size
   docker-compose exec db psql -U postgres -c "SELECT pg_size_pretty(pg_database_size('caseforge'));"

   # Monitor active connections
   docker-compose exec db psql -U postgres -c "SELECT * FROM pg_stat_activity;"
   ```

3. **Storage Monitoring**
   ```bash
   # Check disk usage
   df -h
   du -sh database_backups/
   docker system df
   ```

---

## 📈 Performance Optimization

### Database Optimization
```python
# Use select_related for foreign keys
nodes = ProcessNode.objects.select_related('model_version__model')

# Use prefetch_related for reverse foreign keys
nodes = ProcessNode.objects.prefetch_related('documents')

# Database indexes on commonly queried fields
# See core/models.py for index definitions
```

### Batch Processing Optimization
```bash
# Optimize batch sizes for cost/speed balance
# Small: 50-100 requests (testing)
# Medium: 500-1000 requests (typical)
# Large: 2000+ requests (full processing)

# Monitor token usage
python manage.py shell -c "
from core.models import NodeDocument
docs = NodeDocument.objects.filter(document_type__startswith='waste_')
total_content = sum(len(doc.content) for doc in docs)
print(f'Total content: ~{total_content//1000}K characters')
"
```

### Caching Strategy
```python
# Redis caching for expensive queries
from django.core.cache import cache

# Cache node hierarchies
cache.set('node_children_{}'.format(node_id), children, 3600)

# Cache search results
cache.set('search_{}_{}'.format(query_hash, page), results, 1800)
```

---

## 🔐 Security Best Practices

### Environment Security
```bash
# Never commit secrets
echo ".env" >> .gitignore
echo "*.key" >> .gitignore

# Use strong secret keys
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Secure file permissions
chmod 600 .env
chmod 700 deployment/scripts/*.sh
```

### API Security
```python
# Authentication required for sensitive endpoints
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])

# Rate limiting for API endpoints
from django_ratelimit.decorators import ratelimit
@ratelimit(key='ip', rate='100/h')
```

### Production Security
```yaml
# HTTPS enforcement in nginx.conf
server {
    listen 443 ssl;
    ssl_certificate /etc/ssl/certs/cert.pem;
    ssl_certificate_key /etc/ssl/private/key.pem;
}

# Security headers
add_header X-Content-Type-Options nosniff;
add_header X-Frame-Options DENY;
add_header X-XSS-Protection "1; mode=block";
```

---

## 🔗 Documentation Links

### System Documentation
- [📊 Batch Processing Systems](docs/systems/batch-processing.md)
- [🗄️ Database Backup Systems](docs/systems/database-backup.md)
- [🔗 MCP Server Integration](docs/services/mcp-server.md)
- [🚀 Deployment Guide](deployment/README.md)

### External References
- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [APQC Process Classification Framework](https://www.apqc.org/expertise/process-classification-framework)

---

## 🆘 Support & Maintenance

### Regular Maintenance Tasks
```bash
# Weekly tasks
./deployment/scripts/backup_wrapper.sh      # Create backup
docker system prune -f                      # Clean Docker resources
find database_backups/ -mtime +30 -delete   # Clean old backups

# Monthly tasks
python manage.py check --deploy             # Security check
pip list --outdated                         # Check dependency updates
npm audit                                   # Frontend security audit
```

### Monitoring Health
```bash
# Application health
curl -f http://localhost:8000/api/health/ || echo "API DOWN"

# Database health
python manage.py shell -c "from django.db import connection; connection.ensure_connection(); print('DB OK')"

# Background tasks
docker-compose logs celery | tail -10
```

### Emergency Procedures
1. **Service Down**: Check logs, restart containers, verify configuration
2. **Data Loss**: Restore from latest backup using auto-generated restore scripts
3. **Performance Issues**: Check database queries, review cache usage, monitor resource utilization
4. **Security Incident**: Rotate secrets, review access logs, update dependencies

---

## 🚀 Future Roadmap

### Planned Enhancements
- **MCP Server Integration**: Model Context Protocol for external tool integration
- **Advanced Analytics**: Process optimization recommendations using AI insights
- **Real-time Collaboration**: Multi-user process analysis and annotation
- **API Rate Limiting**: Enhanced rate limiting and quota management
- **Automated Testing**: Comprehensive test suite for batch processing systems

### Scalability Improvements
- **Microservices Architecture**: Split into specialized services
- **Kubernetes Deployment**: Container orchestration for production scale
- **Multi-tenant Support**: Organization-based data isolation
- **Advanced Caching**: Redis Cluster for distributed caching

---

**📚 Keep this guide updated as the system evolves. Happy coding! 🎉**