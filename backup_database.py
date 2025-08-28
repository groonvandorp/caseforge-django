#!/usr/bin/env python3
"""
Comprehensive database backup solution for the APQC PCF Django project.
Creates multiple backup formats and includes data verification.
"""

import os
import sys
import shutil
import sqlite3
import django
import gzip
import json
import subprocess
from datetime import datetime
from pathlib import Path

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'caseforge.settings')
django.setup()

from django.core.management import call_command
from django.conf import settings
from core.models import ProcessModel, ProcessNode, NodeAttribute, NodeDocument, NodeUsecaseCandidate

def create_backup_directory():
    """Create timestamped backup directory."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(f"database_backups/backup_{timestamp}")
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir

def backup_sqlite_file(backup_dir):
    """Create direct copy of SQLite database file."""
    print("📁 Creating SQLite file backup...")
    
    db_path = Path(settings.DATABASES['default']['NAME'])
    if not db_path.exists():
        print(f"❌ Database file not found: {db_path}")
        return False
    
    # Create compressed backup
    backup_file = backup_dir / "db.sqlite3"
    compressed_backup = backup_dir / "db.sqlite3.gz"
    
    # Copy original file
    shutil.copy2(db_path, backup_file)
    
    # Create compressed version
    with open(backup_file, 'rb') as f_in:
        with gzip.open(compressed_backup, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    
    # Get file sizes
    original_size = db_path.stat().st_size
    compressed_size = compressed_backup.stat().st_size
    
    print(f"   ✅ SQLite backup created: {backup_file}")
    print(f"   ✅ Compressed backup: {compressed_backup}")
    print(f"   📊 Original: {original_size:,} bytes, Compressed: {compressed_size:,} bytes ({compressed_size/original_size*100:.1f}%)")
    
    return True

def backup_django_data(backup_dir):
    """Create Django data fixtures (JSON format)."""
    print("📋 Creating Django data backup...")
    
    try:
        # Full database dump
        fixtures_file = backup_dir / "full_database.json"
        with open(fixtures_file, 'w') as f:
            call_command('dumpdata', stdout=f, indent=2)
        
        print(f"   ✅ Django fixtures created: {fixtures_file}")
        
        # Create model-specific backups for key data
        model_backups = [
            ('core', backup_dir / "core_models.json"),
            ('auth', backup_dir / "auth_users.json"),
        ]
        
        for app_name, backup_file in model_backups:
            try:
                with open(backup_file, 'w') as f:
                    call_command('dumpdata', app_name, stdout=f, indent=2)
                print(f"   ✅ {app_name} backup: {backup_file}")
            except Exception as e:
                print(f"   ⚠️  Failed to backup {app_name}: {e}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Django backup failed: {e}")
        return False

def create_data_summary(backup_dir):
    """Create a summary of the data being backed up."""
    print("📊 Creating data summary...")
    
    try:
        summary = {
            "backup_timestamp": datetime.now().isoformat(),
            "database_stats": {},
            "pcf_models": {},
            "content_summary": {}
        }
        
        # Model counts
        models = ProcessModel.objects.all()
        for model in models:
            current_version = model.versions.filter(is_current=True).first()
            if current_version:
                node_count = current_version.nodes.count()
                details_count = NodeDocument.objects.filter(
                    node__model_version=current_version,
                    document_type='process_details'
                ).count()
                candidates_count = NodeUsecaseCandidate.objects.filter(
                    node__model_version=current_version
                ).count()
                pcf_id_count = NodeAttribute.objects.filter(
                    node__model_version=current_version,
                    key='pcf_id'
                ).count()
                
                summary["pcf_models"][model.model_key] = {
                    "name": model.name,
                    "version": current_version.version_label,
                    "nodes": node_count,
                    "process_details": details_count,
                    "ai_candidates": candidates_count,
                    "pcf_ids": pcf_id_count,
                    "pcf_coverage": f"{pcf_id_count/node_count*100:.1f}%" if node_count > 0 else "0%"
                }
        
        # Overall totals
        summary["content_summary"] = {
            "total_process_models": ProcessModel.objects.count(),
            "total_nodes": ProcessNode.objects.count(),
            "total_process_details": NodeDocument.objects.filter(document_type='process_details').count(),
            "total_ai_candidates": NodeUsecaseCandidate.objects.count(),
            "total_pcf_ids": NodeAttribute.objects.filter(key='pcf_id').count(),
        }
        
        # Save summary
        summary_file = backup_dir / "backup_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"   ✅ Data summary created: {summary_file}")
        
        # Print summary to console
        print("\n📊 BACKUP CONTENT SUMMARY:")
        print("=" * 50)
        for model_key, data in summary["pcf_models"].items():
            print(f"🏷️  {data['name']} ({data['version']}):")
            print(f"   Nodes: {data['nodes']}")
            print(f"   Process Details: {data['process_details']}")
            print(f"   AI Candidates: {data['ai_candidates']}")
            print(f"   PCF IDs: {data['pcf_ids']} ({data['pcf_coverage']})")
        
        print(f"\n🎯 GRAND TOTALS:")
        print(f"   Models: {summary['content_summary']['total_process_models']}")
        print(f"   Nodes: {summary['content_summary']['total_nodes']}")
        print(f"   Process Details: {summary['content_summary']['total_process_details']}")
        print(f"   AI Candidates: {summary['content_summary']['total_ai_candidates']}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Summary creation failed: {e}")
        return False

def create_restore_script(backup_dir):
    """Create a script to restore from this backup."""
    print("📝 Creating restore script...")
    
    restore_script = backup_dir / "restore_backup.py"
    
    script_content = f'''#!/usr/bin/env python3
"""
Restore script for database backup created on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

import os
import sys
import shutil
import gzip
from pathlib import Path

def restore_from_sqlite():
    """Restore from SQLite backup."""
    print("🔄 Restoring from SQLite backup...")
    
    # Paths
    current_db = Path("db.sqlite3")
    backup_db = Path("{backup_dir.name}/db.sqlite3")
    compressed_backup = Path("{backup_dir.name}/db.sqlite3.gz")
    
    # Create backup of current db if it exists
    if current_db.exists():
        backup_current = f"db.sqlite3.backup_{{datetime.now().strftime('%Y%m%d_%H%M%S')}}"
        shutil.move(current_db, backup_current)
        print(f"   Current database backed up as: {{backup_current}}")
    
    # Restore from backup
    if backup_db.exists():
        shutil.copy2(backup_db, current_db)
        print(f"   ✅ Database restored from: {{backup_db}}")
    elif compressed_backup.exists():
        with gzip.open(compressed_backup, 'rb') as f_in:
            with open(current_db, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        print(f"   ✅ Database restored from compressed backup: {{compressed_backup}}")
    else:
        print("   ❌ No backup file found!")
        return False
    
    return True

def restore_from_fixtures():
    """Restore from Django fixtures."""
    print("🔄 Restoring from Django fixtures...")
    print("⚠️  This requires Django environment setup")
    print("   Run: python manage.py loaddata {backup_dir.name}/full_database.json")

if __name__ == "__main__":
    print("🚀 DATABASE RESTORE UTILITY")
    print("=" * 40)
    print("Choose restore method:")
    print("1. SQLite file restore (recommended)")
    print("2. Django fixtures restore")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        restore_from_sqlite()
    elif choice == "2":
        restore_from_fixtures()
    else:
        print("❌ Invalid choice!")
'''
    
    with open(restore_script, 'w') as f:
        f.write(script_content)
    
    # Make executable
    os.chmod(restore_script, 0o755)
    
    print(f"   ✅ Restore script created: {restore_script}")
    return True

def main():
    """Main backup function."""
    print("🚀 APQC PCF DATABASE BACKUP UTILITY")
    print("=" * 50)
    print(f"🕐 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create backup directory
    backup_dir = create_backup_directory()
    print(f"📁 Backup directory: {backup_dir}")
    
    success_count = 0
    total_operations = 5
    
    # 1. SQLite file backup
    if backup_sqlite_file(backup_dir):
        success_count += 1
    
    # 2. Django data backup
    if backup_django_data(backup_dir):
        success_count += 1
    
    # 3. Data summary
    if create_data_summary(backup_dir):
        success_count += 1
    
    # 4. Software state capture
    print("📋 Capturing software state...")
    try:
        subprocess.run([sys.executable, 'capture_software_state.py', backup_dir], check=True)
        print("   ✅ Software state captured")
        success_count += 1
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Software state capture failed: {e}")
    except Exception as e:
        print(f"   ❌ Software state error: {e}")
    
    # 5. Restore script
    if create_restore_script(backup_dir):
        success_count += 1
    
    # Summary
    print("\n" + "=" * 50)
    print("🎯 BACKUP COMPLETE!")
    print("=" * 50)
    print(f"📁 Backup location: {backup_dir.absolute()}")
    print(f"✅ Successfully completed: {success_count}/{total_operations} operations")
    print(f"🕐 Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if success_count == total_operations:
        print("\n🎉 All backup operations completed successfully!")
        print("\n📋 Backup contains:")
        print("   • db.sqlite3 - Direct SQLite file copy")
        print("   • db.sqlite3.gz - Compressed SQLite backup")  
        print("   • full_database.json - Django fixtures")
        print("   • backup_summary.json - Data statistics")
        print("   • restore_backup.py - Restoration script")
    else:
        print(f"\n⚠️  {total_operations - success_count} operations failed - check output above")
    
    return success_count == total_operations

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)