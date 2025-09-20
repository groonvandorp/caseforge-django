#!/bin/bash
set -e

echo "🗄️ CaseForge Backup System"
echo "=========================="

# Change to project root
cd "$(dirname "$0")/../.."

# Check if unified backup script exists
if [ ! -f "deployment/scripts/backup_tools/unified_backup.py" ]; then
    echo "❌ Unified backup script not found!"
    exit 1
fi

# Run the unified backup
echo "🚀 Starting unified backup..."
python deployment/scripts/backup_tools/unified_backup.py

# Check if backup was successful
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Backup completed successfully!"
    echo ""
    echo "📁 Backup location: database_backups/"
    echo "📋 View backups: ls -la database_backups/"
    echo "🔄 To restore: cd database_backups/backup_YYYYMMDD_HHMMSS/ && python restore.py"
    echo ""
    echo "📚 For more information, see: database_backups/README.md"
else
    echo ""
    echo "❌ Backup failed!"
    echo "📋 Check the output above for error details"
    exit 1
fi