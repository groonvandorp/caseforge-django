# CaseForge Database Backup Systems

This document provides comprehensive documentation for the database backup and recovery systems in the CaseForge application.

## 📋 Overview

CaseForge implements a multi-layered backup strategy supporting both development (SQLite) and production (PostgreSQL) environments with automated backup creation, verification, and recovery procedures.

## 🏗️ Architecture

### Backup Strategy
```
Development (SQLite) → File Copy + JSON Export + Compression
Production (PostgreSQL) → SQL Dump + JSON Export + Media Backup + Compression
```

### Backup Types
- **Full Database Backups**: Complete data export
- **Incremental Snapshots**: Quick state captures
- **Media File Backups**: User-uploaded content (production)
- **Configuration Backups**: Environment and settings

## 📁 Organized Structure

### Primary Backup Directory: `database_backups/`
```
database_backups/
├── README.md                           # Comprehensive backup documentation
├── backup_20250828_144129/            # Timestamped backup directories
│   ├── backup_summary.json            # Backup metadata and validation
│   ├── restore.py                     # Auto-generated restore script
│   ├── db.sqlite3                     # SQLite database (development)
│   ├── db.sqlite3.gz                  # Compressed SQLite
│   ├── database.sql                   # PostgreSQL dump (production)
│   ├── database.sql.gz                # Compressed PostgreSQL
│   ├── full_database.json             # Django fixtures export
│   ├── core_models.json              # Core models export
│   ├── auth_users.json               # User data export
│   ├── media/                        # Media files (production)
│   ├── software_state.json          # System state snapshot
│   └── SOFTWARE_STATE.md            # Human-readable state report
└── latest -> backup_20250828_144129/ # Symlink to most recent (future)
```

### Backup Scripts: `deployment/scripts/backup_tools/`
```
deployment/scripts/backup_tools/
├── unified_backup.py          # ⭐ Smart auto-detecting backup
├── backup_database.py         # Original comprehensive SQLite backup
└── capture_software_state.py  # System state capture utility
```

### Integration Scripts: `deployment/scripts/`
```
deployment/scripts/
├── backup_wrapper.sh          # ⭐ Main backup entry point
├── backup.sh                  # Production Docker backup
└── deploy.sh                  # Deployment with backup integration
```

## 🚀 Backup Methods

### 1. Unified Backup (Recommended)
**Auto-detects environment and creates appropriate backup**

```bash
# Main entry point - works everywhere
./deployment/scripts/backup_wrapper.sh

# Direct execution
python deployment/scripts/backup_tools/unified_backup.py
```

**Features**:
- **Smart Detection**: Automatically detects dev/prod environment
- **Universal Compatibility**: Single script for all environments
- **Auto-Restore**: Generates restoration script per backup
- **Comprehensive Logging**: JSON summary with validation

### 2. Environment-Specific Backups

#### Development (SQLite)
```bash
# Original comprehensive backup
python db_management/utilities/backup_database.py

# Quick unified backup
python deployment/scripts/backup_tools/unified_backup.py
```

**Creates**:
- SQLite file copy + compressed version
- Django fixtures export (JSON)
- Core models export
- User data export
- Software state snapshot

#### Production (PostgreSQL + Docker)
```bash
# Docker-integrated backup
./deployment/scripts/backup.sh

# Unified backup
python deployment/scripts/backup_tools/unified_backup.py
```

**Creates**:
- PostgreSQL SQL dump + compressed version
- Django fixtures export
- Complete media files directory
- Container volume backups

## 📊 Backup Contents

### Data Included ✅
- **Process Models**: APQC PCF (Cross Industry, Life Science, Retail)
- **Process Hierarchy**: Complete node structure with relationships
- **AI-Generated Content**:
  - Process details descriptions
  - Waste analysis (12 TIMWOOD+ types per process)
  - AI use case candidates and specifications
  - Process embeddings and document embeddings
- **User Data**: Accounts, bookmarks, portfolios, settings
- **System Configuration**: Admin settings, model access, technology inventory
- **Media Files**: Uploaded content (production environments)

### Data Excluded ❌
- **Temporary Data**: Sessions, cache, logs
- **System Files**: Virtual environment, compiled code
- **Secrets**: API keys (backed up as placeholders)
- **Large Dependencies**: Node modules, Python packages

## 🔧 Backup Validation & Verification

### Automated Validation
Each backup includes:
```json
{
  "backup_timestamp": "20250828_144129",
  "environment": "development",
  "success": true,
  "total_files": 8,
  "total_size_mb": 892.3,
  "files": ["db.sqlite3", "db.sqlite3.gz", "full_database.json", ...],
  "created_at": "2025-08-28T14:41:29.123456"
}
```

### Integrity Checks
- **File Count Verification**: Expected vs actual files
- **Size Validation**: Reasonable size ranges per environment
- **Format Validation**: JSON syntax, SQL dump integrity
- **Compression Verification**: Archive integrity tests

### Test Restore (Dry Run)
```bash
# Test restoration without applying changes
cd database_backups/backup_20250828_144129/
python restore.py --dry-run  # (future feature)
```

## 🔄 Restore Procedures

### Auto-Generated Restore Scripts
Each backup creates a custom restore script tailored to its environment:

```bash
# Navigate to specific backup
cd database_backups/backup_20250828_144129/

# Execute auto-generated restore
python restore.py
```

### Manual Restore Procedures

#### Development Restore
```bash
# 1. Stop Django development server
pkill -f "manage.py runserver"

# 2. Backup current database (safety)
cp db.sqlite3 db.sqlite3.before_restore

# 3. Restore database
cp database_backups/backup_YYYYMMDD_HHMMSS/db.sqlite3 ./

# 4. Restart Django server
python manage.py runserver
```

#### Production Restore
```bash
# 1. Stop application containers
docker-compose -f deployment/docker/docker-compose.production.yml down

# 2. Create safety backup
./deployment/scripts/backup_wrapper.sh

# 3. Restore database
docker-compose -f deployment/docker/docker-compose.production.yml up -d db
cat database_backups/backup_YYYYMMDD_HHMMSS/database.sql | \
  docker-compose exec -T db psql -U postgres caseforge

# 4. Restore media files (if needed)
docker cp database_backups/backup_YYYYMMDD_HHMMSS/media/. \
  $(docker-compose ps -q web):/app/media/

# 5. Restart all services
docker-compose -f deployment/docker/docker-compose.production.yml up -d
```

## 📈 Backup Schedule & Retention

### Current Manual Schedule
- **Before Deployments**: Always create backup
- **After Major Data Generation**: AI batch processing completion
- **Before Database Migrations**: Schema change safety
- **Weekly Maintenance**: Regular data protection

### Recommended Automated Schedule
```bash
# Crontab entries (future implementation)
0 2 * * *     # Daily at 2:00 AM UTC
0 1 * * 0     # Weekly on Sunday at 1:00 AM UTC
0 0 1 * *     # Monthly on 1st at midnight UTC
```

### Retention Policy
- **Development**: Last 10 backups (~7-14 days)
- **Production**:
  - Daily: 30 days
  - Weekly: 3 months
  - Monthly: 1 year

### Cleanup Automation
```bash
# Remove old backups (manual for now)
find database_backups/ -name "backup_*" -mtime +30 -exec rm -rf {} \;

# Keep only latest 10 backups
ls -1t database_backups/backup_* | tail -n +11 | xargs rm -rf
```

## 🔍 Monitoring & Health Checks

### Backup Health Dashboard
```bash
# View all backups
ls -lat database_backups/

# Check backup sizes
du -sh database_backups/backup_*/

# Verify recent backup integrity
cat database_backups/backup_$(ls -1t database_backups/ | head -1)/backup_summary.json
```

### Backup Success Monitoring
```bash
# Check if backup completed successfully
python -c "
import json
with open('database_backups/backup_LATEST/backup_summary.json') as f:
    data = json.load(f)
    print(f'Success: {data[\"success\"]}, Size: {data[\"total_size_mb\"]} MB')
"
```

### Storage Monitoring
```bash
# Check backup storage usage
df -h database_backups/
du -sh database_backups/

# Alert if storage > 80%
df database_backups/ | awk 'NR==2 {if($5+0 > 80) print "WARNING: Backup storage " $5 " full"}'
```

## 🛡️ Security & Compliance

### Data Protection
- **Local Storage**: Backups stored locally by default
- **Access Control**: File system permissions restrict access
- **Encryption Ready**: Prepared for encryption in transit/rest
- **Audit Trail**: Detailed logging of backup operations

### Sensitive Data Handling
- **API Keys**: Masked in backup summaries
- **User Passwords**: Django hashed passwords only
- **Personal Data**: Process data is business-focused, minimal PII

### Compliance Considerations
- **Data Retention**: Configurable retention policies
- **Access Logging**: Backup creation and restoration logged
- **Recovery Testing**: Regular restore verification procedures

## 🚨 Disaster Recovery

### Recovery Time Objectives (RTO)
- **Development**: < 30 minutes (local restore)
- **Production**: < 2 hours (includes container restart)

### Recovery Point Objectives (RPO)
- **Development**: 24 hours (daily backup)
- **Production**: 4 hours (6x daily backup recommended)

### Disaster Scenarios

#### 1. Database Corruption
```bash
# Immediate response
./deployment/scripts/backup_wrapper.sh  # Create current state backup
cd database_backups/backup_LATEST/
python restore.py                       # Restore last known good
```

#### 2. Complete System Loss
```bash
# Recovery procedure
git clone <repository>                  # Restore codebase
cd database_backups/backup_LATEST/
python restore.py                       # Restore data
./deployment/scripts/deploy.sh          # Redeploy application
```

#### 3. Partial Data Loss
```bash
# Selective restoration using Django fixtures
python manage.py loaddata database_backups/backup_LATEST/core_models.json
python manage.py loaddata database_backups/backup_LATEST/auth_users.json
```

## 🔗 Integration Points

### Deployment Integration
- **Pre-deployment Backup**: Automatic backup before deployment
- **Rollback Support**: Quick restoration for deployment failures
- **CI/CD Pipeline**: Backup verification in automated testing

### Monitoring Integration
- **Health Checks**: Backup success/failure monitoring
- **Alerting**: Storage capacity and backup age alerts
- **Dashboards**: Backup status in system monitoring

### Application Integration
- **Admin Interface**: Backup status and manual triggers
- **API Endpoints**: Backup management via REST API
- **User Notifications**: Backup completion notifications

## 📊 Performance Metrics

### Typical Backup Sizes
- **Development (SQLite)**: 300-700 MB
  - Database: 300-400 MB
  - JSON exports: 200-300 MB
  - Compressed: ~150-200 MB

- **Production (PostgreSQL)**: 500MB - 2GB+
  - Database dump: 400-800 MB
  - Media files: Variable (100MB - 10GB+)
  - Compressed: 50-70% size reduction

### Performance Benchmarks
- **SQLite Backup**: 2-5 minutes
- **PostgreSQL Backup**: 5-15 minutes
- **Media File Backup**: Depends on volume (1GB/minute typical)
- **Compression**: 3-5x speed improvement on restoration

## 🔧 Troubleshooting

### Common Issues

1. **Backup Script Permission Denied**
   ```bash
   chmod +x deployment/scripts/backup_wrapper.sh
   chmod +x deployment/scripts/backup_tools/unified_backup.py
   ```

2. **Database Locked During Backup**
   ```bash
   # Stop Django development server
   pkill -f "manage.py runserver"
   # Then retry backup
   ```

3. **Production Container Not Running**
   ```bash
   docker-compose -f deployment/docker/docker-compose.production.yml ps
   docker-compose -f deployment/docker/docker-compose.production.yml up -d db
   ```

4. **Backup Directory Full**
   ```bash
   # Clean old backups
   find database_backups/ -name "backup_*" -mtime +7 -exec rm -rf {} \;
   ```

5. **Restore Fails - Target Database Busy**
   ```bash
   # Development: Stop Django server
   pkill -f "manage.py runserver"

   # Production: Stop application containers
   docker-compose -f deployment/docker/docker-compose.production.yml stop web celery
   ```

### Debug Tools
```bash
# Check backup integrity
python -c "
import json, os
backup_dir = 'database_backups/backup_LATEST/'
with open(backup_dir + 'backup_summary.json') as f:
    data = json.load(f)
    for file in data['files']:
        path = backup_dir + file
        exists = os.path.exists(path)
        size = os.path.getsize(path) if exists else 0
        print(f'{file}: {\"OK\" if exists else \"MISSING\"} ({size} bytes)')
"

# Test database connectivity
python manage.py shell -c "from django.db import connection; connection.ensure_connection(); print('Database OK')"

# Check disk space
df -h database_backups/
```

## 📚 Related Documentation

- [Batch Processing Systems](./batch-processing.md)
- [Deployment Guide](../deployment/README.md)
- [Django Database Documentation](https://docs.djangoproject.com/en/4.2/topics/db/)
- [PostgreSQL Backup Best Practices](https://www.postgresql.org/docs/current/backup.html)

---

## 🆘 Emergency Recovery

For critical backup/restore situations:
1. **Stay Calm**: Multiple backup formats provide redundancy
2. **Assess Damage**: Identify what data is affected
3. **Choose Recovery Method**: Auto-restore vs manual procedures
4. **Verify Recovery**: Test application functionality after restore
5. **Document Incident**: Record what happened and how it was resolved

**Emergency Contacts**: Development team with backup timestamp and error details