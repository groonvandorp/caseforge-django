#!/usr/bin/env python3
"""
Migration script to copy documents from the original FastAPI SQLite database
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

from core.models import ProcessNode, NodeDocument, User

def migrate_documents():
    """Migrate documents from original database to Django database"""
    
    # Path to original database
    original_db_path = Path(__file__).parent.parent / "db" / "onwell.sqlite"
    
    if not original_db_path.exists():
        print(f"Original database not found at: {original_db_path}")
        return False
    
    # Connect to original database
    orig_conn = sqlite3.connect(original_db_path)
    orig_conn.row_factory = sqlite3.Row  # Enable column access by name
    
    try:
        # Get a default user (create admin if doesn't exist)
        user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'first_name': 'Admin',
                'last_name': 'User',
                'is_staff': True,
                'is_superuser': True
            }
        )
        
        if created:
            user.set_password('admin123')
            user.save()
            print(f"Created admin user")
        
        # Document type mapping from original to Django
        doc_type_mapping = {
            'agent_markdown': 'process_details',
            'usecase_spec_markdown': 'usecase_spec',
            'research_summary': 'research_summary',
            'flow_mermaid': 'process_details'  # Also treat flow diagrams as process details
        }
        
        # Query to get all documents with node information
        query = """
        SELECT nd.id, nd.node_id, nd.doc_type, nd.title, nd.content, nd.created_at,
               pn.code, pn.name as node_name
        FROM node_document nd
        JOIN process_node pn ON nd.node_id = pn.id
        WHERE nd.doc_type IN ('agent_markdown', 'usecase_spec_markdown', 'research_summary', 'flow_mermaid')
        ORDER BY pn.code, nd.doc_type
        """
        
        cursor = orig_conn.execute(query)
        documents = cursor.fetchall()
        
        migrated_count = 0
        skipped_count = 0
        
        for doc in documents:
            # Find corresponding Django ProcessNode by code (get first match if multiple)
            try:
                django_node = ProcessNode.objects.filter(code=doc['code']).first()
                if not django_node:
                    print(f"Warning: Node {doc['code']} not found in Django database")
                    skipped_count += 1
                    continue
            except Exception as e:
                print(f"Error finding node {doc['code']}: {e}")
                skipped_count += 1
                continue
            
            # Map document type
            django_doc_type = doc_type_mapping.get(doc['doc_type'], doc['doc_type'])
            
            # Check if document already exists
            existing_doc = NodeDocument.objects.filter(
                node=django_node,
                document_type=django_doc_type
            ).first()
            
            if existing_doc:
                print(f"Document already exists for {doc['code']} ({django_doc_type}), skipping")
                skipped_count += 1
                continue
            
            # Create Django NodeDocument
            django_doc = NodeDocument.objects.create(
                node=django_node,
                user=user,
                document_type=django_doc_type,
                title=doc['title'] or f"{django_doc_type.title()}: {doc['node_name']}",
                content=doc['content'] or "",
                created_at=doc['created_at']
            )
            
            print(f"Migrated: {doc['code']} - {django_doc_type} ({len(doc['content'] or '')} chars)")
            migrated_count += 1
        
        print(f"\nMigration complete:")
        print(f"- Migrated: {migrated_count} documents")
        print(f"- Skipped: {skipped_count} documents")
        
        return True
        
    except Exception as e:
        print(f"Error during migration: {e}")
        return False
        
    finally:
        orig_conn.close()

if __name__ == "__main__":
    print("Starting document migration from original FastAPI database...")
    success = migrate_documents()
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed!")
        sys.exit(1)