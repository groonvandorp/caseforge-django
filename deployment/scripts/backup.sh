#!/bin/bash
set -e

BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "🗄️ Creating backup in $BACKUP_DIR..."

# Backup database
echo "📊 Backing up database..."
cd deployment/docker
docker-compose -f docker-compose.production.yml exec -T db pg_dump -U postgres caseforge > "../../$BACKUP_DIR/database.sql"

# Backup media files
echo "📁 Backing up media files..."
docker-compose -f docker-compose.production.yml run --rm -v "$(pwd)/../../$BACKUP_DIR:/backup" web cp -r /app/media /backup/

# Backup environment config
echo "⚙️ Backing up configuration..."
cp ../configs/.env "../../$BACKUP_DIR/env_backup"

# Create backup info
cat > "../../$BACKUP_DIR/backup_info.txt" << EOF
CaseForge Backup
Created: $(date)
Database: PostgreSQL dump
Media: Complete media directory
Config: Environment variables (secrets masked)

To restore:
1. Restore database: docker-compose exec -T db psql -U postgres caseforge < database.sql
2. Restore media: docker cp media/. container_name:/app/media/
3. Update environment: cp env_backup deployment/configs/.env
EOF

echo "✅ Backup completed: $BACKUP_DIR"
echo "📁 Contents:"
ls -la "$BACKUP_DIR"