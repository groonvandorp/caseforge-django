#!/usr/bin/env python3
"""
Migration script to copy use case candidates from the original FastAPI SQLite database
to the Django database.
"""

import os
import sys
import django
import sqlite3
from pathlib import Path

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'caseforge.settings')
django.setup()

from core.models import ProcessNode, NodeUsecaseCandidate, User

def migrate_usecases():
    """Migrate use case candidates from original database to Django database"""
    
    # Path to original database
    original_db_path = Path(__file__).parent.parent / "db" / "onwell.sqlite"
    
    if not original_db_path.exists():
        print(f"Original database not found at: {original_db_path}")
        return False
    
    # Connect to original database
    orig_conn = sqlite3.connect(original_db_path)
    orig_conn.row_factory = sqlite3.Row  # Enable column access by name
    
    try:
        # Get the gruhno user
        user = User.objects.get(email='gruhno@gmail.com')
        print(f"Using user: {user.username}")
        
        # Query to get all use case candidates with node information
        query = """
        SELECT nuc.id, nuc.node_id, nuc.candidate_uid, nuc.title, nuc.problem, 
               nuc.approach, nuc.value, nuc.feasibility, nuc.risks, nuc.meta_json, nuc.created_at,
               pn.code, pn.name as node_name
        FROM node_usecase_candidate nuc
        JOIN process_node pn ON nuc.node_id = pn.id
        ORDER BY pn.code, nuc.created_at
        """
        
        cursor = orig_conn.execute(query)
        candidates = cursor.fetchall()
        
        migrated_count = 0
        skipped_count = 0
        
        for candidate in candidates:
            # Find corresponding Django ProcessNode by code
            try:
                django_node = ProcessNode.objects.filter(code=candidate['code']).first()
                if not django_node:
                    print(f"Warning: Node {candidate['code']} not found in Django database")
                    skipped_count += 1
                    continue
            except Exception as e:
                print(f"Error finding node {candidate['code']}: {e}")
                skipped_count += 1
                continue
            
            # Check if candidate already exists
            existing_candidate = NodeUsecaseCandidate.objects.filter(
                candidate_uid=candidate['candidate_uid']
            ).first()
            
            if existing_candidate:
                print(f"Candidate {candidate['candidate_uid']} already exists, skipping")
                skipped_count += 1
                continue
            
            # Create description from problem and approach
            description = f"**Problem:** {candidate['problem'] or ''}\n\n**Approach:** {candidate['approach'] or ''}"
            impact_assessment = candidate['value'] or candidate['feasibility'] or ""
            
            # Try to extract complexity score from risks or set a default
            complexity_score = None
            if candidate['risks']:
                # Simple heuristic: longer risks text = higher complexity
                complexity_score = min(10, max(1, len(candidate['risks']) // 100 + 3))
            
            # Create Django NodeUsecaseCandidate
            django_candidate = NodeUsecaseCandidate.objects.create(
                node=django_node,
                user=user,
                candidate_uid=candidate['candidate_uid'],
                title=candidate['title'] or f"Use Case for {candidate['node_name']}",
                description=description,
                impact_assessment=impact_assessment,
                complexity_score=complexity_score,
                meta_json=candidate['meta_json'] if candidate['meta_json'] else {},
                created_at=candidate['created_at']
            )
            
            print(f"Migrated: {candidate['code']} - {candidate['title'][:50]}{'...' if len(candidate['title'] or '') > 50 else ''}")
            migrated_count += 1
        
        print(f"\nUse case migration complete:")
        print(f"- Migrated: {migrated_count} use case candidates")
        print(f"- Skipped: {skipped_count} use case candidates")
        
        return True
        
    except Exception as e:
        print(f"Error during migration: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        orig_conn.close()

if __name__ == "__main__":
    print("Starting use case candidate migration from original FastAPI database...")
    success = migrate_usecases()
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed!")
        sys.exit(1)