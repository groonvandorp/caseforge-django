#!/usr/bin/env python3
"""
Capture current software state for database backup correlation.
Run this before creating database backups to document the code state.
"""

import os
import sys
import subprocess
import json
from datetime import datetime

def run_command(cmd):
    """Run a shell command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=os.getcwd())
        return result.stdout.strip() if result.returncode == 0 else f"Error: {result.stderr.strip()}"
    except Exception as e:
        return f"Error: {str(e)}"

def capture_git_state():
    """Capture current git repository state"""
    return {
        'current_commit': run_command('git rev-parse HEAD'),
        'current_commit_short': run_command('git rev-parse --short HEAD'),
        'current_branch': run_command('git rev-parse --abbrev-ref HEAD'),
        'commit_message': run_command('git log -1 --pretty=%B'),
        'commit_author': run_command('git log -1 --pretty=%an'),
        'commit_date': run_command('git log -1 --pretty=%cd'),
        'uncommitted_changes': len(run_command('git status --porcelain').split('\n')) > 1,
        'recent_commits': [
            line for line in run_command('git log --oneline -10').split('\n') if line
        ],
        'remote_status': run_command('git status -b --porcelain=v1 | head -1')
    }

def capture_django_state():
    """Capture Django migrations and settings state"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'caseforge.settings')
    
    try:
        import django
        django.setup()
        
        from django.core.management import call_command
        from io import StringIO
        
        # Capture migration status
        migration_output = StringIO()
        call_command('showmigrations', format='plan', stdout=migration_output)
        migrations = migration_output.getvalue()
        
        return {
            'migrations_status': migrations,
            'django_version': django.get_version(),
            'debug_mode': os.environ.get('DEBUG', 'False'),
            'database_engine': 'sqlite3'  # From our settings
        }
    except Exception as e:
        return {'error': f'Could not capture Django state: {str(e)}'}

def capture_environment():
    """Capture Python and system environment"""
    return {
        'python_version': sys.version,
        'working_directory': os.getcwd(),
        'virtual_env': os.environ.get('VIRTUAL_ENV', 'Not activated'),
        'timestamp': datetime.now().isoformat(),
        'platform': run_command('uname -a')
    }

def generate_state_summary():
    """Generate a comprehensive software state summary"""
    state = {
        'capture_timestamp': datetime.now().isoformat(),
        'git': capture_git_state(),
        'django': capture_django_state(),
        'environment': capture_environment()
    }
    
    return state

def save_state_to_backup(backup_dir, state_data):
    """Save state information to a backup directory"""
    state_file = os.path.join(backup_dir, 'software_state.json')
    md_file = os.path.join(backup_dir, 'SOFTWARE_STATE.md')
    
    # Save JSON version
    with open(state_file, 'w') as f:
        json.dump(state_data, f, indent=2)
    
    # Create human-readable markdown
    git = state_data['git']
    django = state_data['django']
    env = state_data['environment']
    
    md_content = f"""# Database Backup Software State

**Backup Created**: {state_data['capture_timestamp']}

## Git Repository State

**Current Commit**: {git['current_commit_short']}
**Commit Message**: "{git['commit_message'].strip()}"
**Branch**: {git['current_branch']}
**Author**: {git['commit_author']}
**Date**: {git['commit_date']}
**Uncommitted Changes**: {'Yes ⚠️' if git['uncommitted_changes'] else 'No ✅'}

### Recent Commits:
```
{chr(10).join(git['recent_commits'][:5])}
```

## Django State

**Version**: {django.get('django_version', 'Unknown')}
**Debug Mode**: {django.get('debug_mode', 'Unknown')}

### Migration Status:
```
{django.get('migrations_status', 'Could not capture')}
```

## Environment

**Python**: {env['python_version'].split()[0]}
**Platform**: {env['platform']}
**Virtual Env**: {env['virtual_env']}
**Working Dir**: {env['working_directory']}

## Verification Commands

To verify this backup matches your code state:

```bash
# Check git commit
git log --oneline -1
# Should show: {git['current_commit_short']} {git['commit_message'].strip()}

# Check migration status
python manage.py showmigrations core

# Check Django version
python -c "import django; print(django.get_version())"
# Should show: {django.get('django_version', 'Unknown')}
```

---
*Software state captured automatically by capture_software_state.py*
"""
    
    with open(md_file, 'w') as f:
        f.write(md_content)
    
    return state_file, md_file

def main():
    """Main function"""
    print("📋 Capturing current software state...")
    
    state = generate_state_summary()
    
    # If backup directory is provided as argument, save there
    if len(sys.argv) > 1:
        backup_dir = sys.argv[1]
        if os.path.exists(backup_dir):
            json_file, md_file = save_state_to_backup(backup_dir, state)
            print(f"✅ State saved to: {json_file}")
            print(f"✅ Readable version: {md_file}")
        else:
            print(f"❌ Backup directory not found: {backup_dir}")
            return 1
    else:
        # Just print the state
        print("🔍 Current Software State:")
        print(f"   Git: {state['git']['current_commit_short']} - {state['git']['commit_message'].strip()}")
        print(f"   Branch: {state['git']['current_branch']}")
        print(f"   Django: {state['django'].get('django_version', 'Unknown')}")
        print(f"   Uncommitted: {'Yes' if state['git']['uncommitted_changes'] else 'No'}")
        
        # Save to current directory
        with open('current_software_state.json', 'w') as f:
            json.dump(state, f, indent=2)
        print("📁 State saved to: current_software_state.json")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())