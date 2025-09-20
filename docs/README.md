# CaseForge Documentation Hub

Welcome to the comprehensive documentation for the CaseForge process model-driven AI system.

## 📚 Documentation Structure

### 🎯 **Main Guides**
- **[📖 DEVELOPMENT_GUIDE.md](../DEVELOPMENT_GUIDE.md)** - **START HERE**: Complete development guide with quick start, workflows, and troubleshooting

### 🔧 **System Documentation**
- **[📊 Batch Processing Systems](systems/batch-processing.md)** - AI content generation, TIMWOOD+ waste analysis, embeddings
- **[🗄️ Database Backup Systems](systems/database-backup.md)** - Comprehensive backup, recovery, and disaster planning
- **[🔗 MCP Server Integration](services/mcp-server.md)** - Claude Desktop integration, natural language process queries

### 🚀 **Operational Guides**
- **[🚀 Deployment Guide](../deployment/README.md)** - Docker, production deployment, infrastructure
- **[🗄️ Backup Guide](../database_backups/README.md)** - Backup operations, restoration procedures

## 🏗️ System Overview

**CaseForge** enables AI-driven business process analysis and optimization using:
- **APQC Process Classification Framework** (Cross Industry, Life Science, Retail)
- **TIMWOOD+ Waste Analysis** (12 waste types per process)
- **AI Use Case Generation** (GPT-5 powered recommendations)
- **Semantic Search** (Vector embeddings for intelligent discovery)

## 🚀 Quick Navigation

### I want to...
- **🏃 Get started developing** → [DEVELOPMENT_GUIDE.md](../DEVELOPMENT_GUIDE.md#quick-start)
- **📊 Run batch AI processing** → [Batch Processing Guide](systems/batch-processing.md#workflow-examples)
- **🗄️ Backup the database** → [Database Backup Guide](systems/database-backup.md#backup-methods)
- **🚀 Deploy to production** → [Deployment Guide](../deployment/README.md#production-deployment)
- **🔧 Troubleshoot issues** → [Development Guide - Troubleshooting](../DEVELOPMENT_GUIDE.md#troubleshooting)
- **🔗 Set up Claude Desktop integration** → [MCP Server Guide](services/mcp-server.md#quick-start)

### I work with...
- **🔬 Process Analysis** → [Batch Processing - Waste Analysis](systems/batch-processing.md#batch_waste_by_type-current-system)
- **🤖 AI Content Generation** → [Batch Processing - Workflows](systems/batch-processing.md#workflow-examples)
- **🔗 Claude Desktop/MCP** → [MCP Server Integration](services/mcp-server.md)
- **💾 Data Management** → [Database Backup Systems](systems/database-backup.md)
- **🐳 DevOps/Infrastructure** → [Deployment Guide](../deployment/README.md)

## 📁 Codebase Organization

```
caseforge/
├── 📄 DEVELOPMENT_GUIDE.md          # 🎯 Main development guide
├── 📁 docs/                         # 📚 This documentation hub
│   ├── systems/                     # System-specific documentation
│   ├── services/                    # Service documentation
│   ├── workflows/                   # Process workflows
│   └── api/                         # API documentation
├── 📁 services/                     # External services & integrations
│   └── mcp/                        # Model Context Protocol server
├── 📁 batch_*/                      # AI batch processing (organized)
├── 📁 db_management/                # Database operations (organized)
├── 📁 deployment/                   # Infrastructure & deployment (organized)
└── 📁 database_backups/             # Backup system (organized)
```

## 🔄 Workflows at a Glance

### Complete Waste Analysis
```bash
# 1. Test system
cd batch_waste_by_type/ && python test_waste_by_type.py

# 2. Generate analysis
python batch_generate_waste_by_type.py

# 3. Generate embeddings
cd ../batch_waste_embeddings/ && python batch_generate_waste_embeddings.py
```

### Backup & Deploy
```bash
# 1. Create backup
./deployment/scripts/backup_wrapper.sh

# 2. Deploy to production
./deployment/scripts/deploy.sh
```

## 🎯 Key Features

### ✅ **Batch Processing Systems**
- **TIMWOOD+ Waste Analysis**: 12 waste types per process
- **AI Use Case Generation**: GPT-5 powered recommendations
- **Semantic Embeddings**: Vector search capabilities
- **Cost Optimization**: 50% savings via OpenAI Batch API

### ✅ **Enterprise Backup System**
- **Smart Auto-Detection**: Adapts to dev/prod environments
- **Multiple Formats**: SQLite, PostgreSQL, JSON fixtures
- **Auto-Restore Scripts**: Generated per backup
- **Comprehensive Recovery**: Complete disaster recovery procedures

### ✅ **Production Deployment**
- **Docker Containerization**: Multi-service orchestration
- **Security Hardening**: Non-root users, security headers
- **Scalability**: Multi-worker Gunicorn, Redis clustering
- **Monitoring**: Health checks, logging, alerting

## 🔗 External References

- [Django Documentation](https://docs.djangoproject.com/)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [APQC Process Classification Framework](https://www.apqc.org/expertise/process-classification-framework)
- [Docker Documentation](https://docs.docker.com/)

## 🆘 Getting Help

1. **📖 Check Documentation**: Start with relevant guide above
2. **🔍 Search Issues**: Check troubleshooting sections
3. **📝 Check Logs**: Application and system logs
4. **🤝 Contact Team**: Development team with specific error details

---

**📝 Keep documentation updated as the system evolves!**