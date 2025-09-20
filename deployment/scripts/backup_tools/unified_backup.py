#!/usr/bin/env python3
"""
Unified backup solution for CaseForge - works for both development and production deployments.

This script auto-detects the environment (SQLite dev vs PostgreSQL production) and
creates appropriate backups with consistent structure.
"""

import os
import sys
import json
import subprocess
import shutil
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

def detect_environment():
    """Detect if we're running in development or production environment."""
    if Path("deployment/docker/docker-compose.production.yml").exists():
        return "production"
    elif Path("db.sqlite3").exists():
        return "development"
    else:
        return "unknown"

def create_backup_directory():
    """Create timestamped backup directory."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(f"database_backups/backup_{timestamp}")
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir, timestamp

def backup_development(backup_dir):
    """Backup SQLite development database."""
    print("🔧 Development environment detected")
    print("📁 Backing up SQLite database...")

    db_file = Path("db.sqlite3")
    if not db_file.exists():
        print("❌ SQLite database not found")
        return False

    # Copy database file
    shutil.copy2(db_file, backup_dir / "db.sqlite3")

    # Create compressed version
    subprocess.run([
        "gzip", "-c", str(db_file)
    ], stdout=open(backup_dir / "db.sqlite3.gz", "wb"))

    # Export JSON fixtures
    print("📊 Exporting Django fixtures...")
    subprocess.run([
        "python", "manage.py", "dumpdata",
        "--exclude=contenttypes", "--exclude=auth.permission",
        "--output", str(backup_dir / "full_database.json"),
        "--indent", "2"
    ])

    return True

def backup_production(backup_dir):
    """Backup PostgreSQL production database."""
    print("🏭 Production environment detected")
    print("📁 Backing up PostgreSQL database...")

    # Check if production containers are running
    result = subprocess.run([
        "docker-compose", "-f", "deployment/docker/docker-compose.production.yml",
        "ps", "-q", "db"
    ], capture_output=True, text=True)

    if not result.stdout.strip():
        print("❌ Production database container not running")
        return False

    # Create PostgreSQL dump
    subprocess.run([
        "docker-compose", "-f", "deployment/docker/docker-compose.production.yml",
        "exec", "-T", "db", "pg_dump", "-U", "postgres", "caseforge"
    ], stdout=open(backup_dir / "database.sql", "w"))

    # Create compressed version
    subprocess.run([
        "gzip", "-c", str(backup_dir / "database.sql")
    ], stdout=open(backup_dir / "database.sql.gz", "wb"))

    # Export Django fixtures from production
    print("📊 Exporting Django fixtures from production...")
    subprocess.run([
        "docker-compose", "-f", "deployment/docker/docker-compose.production.yml",
        "exec", "-T", "web", "python", "manage.py", "dumpdata",
        "--exclude=contenttypes", "--exclude=auth.permission",
        "--indent", "2"
    ], stdout=open(backup_dir / "full_database.json", "w"))

    # Backup media files
    print("📁 Backing up media files...")
    subprocess.run([
        "docker-compose", "-f", "deployment/docker/docker-compose.production.yml",
        "run", "--rm", "-v", f"{backup_dir.absolute()}:/backup",
        "web", "cp", "-r", "/app/media", "/backup/"
    ])

    return True

def create_backup_summary(backup_dir, timestamp, environment, success):
    """Create backup summary and restore instructions."""

    # Count files and calculate sizes
    files = list(backup_dir.glob("*"))
    total_size = sum(f.stat().st_size for f in files if f.is_file())

    summary = {
        "backup_timestamp": timestamp,
        "environment": environment,
        "success": success,
        "total_files": len(files),
        "total_size_mb": round(total_size / (1024*1024), 2),
        "files": [f.name for f in files],
        "created_at": datetime.now().isoformat()
    }

    # Save summary
    with open(backup_dir / "backup_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    # Create restore script
    restore_script = f"""#!/usr/bin/env python3
\"\"\"
Restore script for backup {timestamp}
Environment: {environment}
\"\"\"

import subprocess
import sys
from pathlib import Path

def restore_{environment}():
    \"\"\"Restore {environment} backup.\"\"\"
    backup_dir = Path(__file__).parent

    if "{environment}" == "development":
        print("🔧 Restoring development database...")

        # Stop any running Django server
        print("⚠️  Please stop the Django development server before restoring")

        # Restore database
        if (backup_dir / "db.sqlite3").exists():
            subprocess.run(["cp", str(backup_dir / "db.sqlite3"), "db.sqlite3"])
            print("✅ SQLite database restored")
        else:
            print("❌ SQLite backup not found")

    elif "{environment}" == "production":
        print("🏭 Restoring production database...")

        # Restore PostgreSQL
        if (backup_dir / "database.sql").exists():
            print("📥 Restoring PostgreSQL database...")
            subprocess.run([
                "docker-compose", "-f", "deployment/docker/docker-compose.production.yml",
                "exec", "-T", "db", "psql", "-U", "postgres", "caseforge"
            ], stdin=open(backup_dir / "database.sql"))
            print("✅ PostgreSQL database restored")

        # Restore media files
        if (backup_dir / "media").exists():
            print("📁 Restoring media files...")
            subprocess.run([
                "docker-compose", "-f", "deployment/docker/docker-compose.production.yml",
                "run", "--rm", "-v", f"{{backup_dir.absolute()}}:/backup",
                "web", "cp", "-r", "/backup/media/.", "/app/media/"
            ])
            print("✅ Media files restored")

    print("🎉 Restore completed!")

if __name__ == "__main__":
    restore_{environment}()
"""

    with open(backup_dir / "restore.py", "w") as f:
        f.write(restore_script)

    # Make restore script executable
    os.chmod(backup_dir / "restore.py", 0o755)

    return summary

def main():
    """Main backup function."""
    print("🗄️ CaseForge Unified Backup System")
    print("=" * 50)

    # Detect environment
    environment = detect_environment()
    print(f"🔍 Environment: {environment}")

    if environment == "unknown":
        print("❌ Could not detect environment. Please run from project root.")
        sys.exit(1)

    # Create backup directory
    backup_dir, timestamp = create_backup_directory()
    print(f"📁 Backup directory: {backup_dir}")

    # Perform backup based on environment
    if environment == "development":
        success = backup_development(backup_dir)
    elif environment == "production":
        success = backup_production(backup_dir)

    # Create summary
    summary = create_backup_summary(backup_dir, timestamp, environment, success)

    # Report results
    print("\n📈 Backup Summary:")
    print(f"  🕐 Timestamp: {timestamp}")
    print(f"  🏷️  Environment: {environment}")
    print(f"  📊 Files: {summary['total_files']}")
    print(f"  💾 Size: {summary['total_size_mb']} MB")
    print(f"  ✅ Success: {success}")
    print(f"  📁 Location: {backup_dir}")

    if success:
        print(f"\n🔄 To restore this backup:")
        print(f"   cd {backup_dir}")
        print(f"   python restore.py")

    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)