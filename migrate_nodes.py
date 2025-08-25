#!/usr/bin/env python3
"""
Migration script to copy process nodes from the original FastAPI SQLite database
to the Django database, ensuring descriptions are properly migrated.
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

from core.models import ProcessModel, ProcessModelVersion, ProcessNode, User

def migrate_nodes():
    """Migrate process nodes from original database to Django database"""
    
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
        
        # First, get all process models and versions
        models_query = """
        SELECT pm.id, pm.model_key, pm.name, pm.description, pm.created_at,
               pmv.id as version_id, pmv.version_label, pmv.external_reference,
               pmv.notes, pmv.effective_date, pmv.is_current
        FROM process_model pm
        JOIN process_model_version pmv ON pm.id = pmv.model_id
        ORDER BY pm.model_key, pmv.effective_date
        """
        
        models_cursor = orig_conn.execute(models_query)
        models_data = models_cursor.fetchall()
        
        # Migrate models and versions first
        model_version_map = {}  # original_version_id -> django_version_id
        
        for model_data in models_data:
            # Create or get ProcessModel
            django_model, created = ProcessModel.objects.get_or_create(
                model_key=model_data['model_key'],
                defaults={
                    'name': model_data['name'],
                    'description': model_data['description'] or '',
                    'created_at': model_data['created_at']
                }
            )
            
            if created:
                print(f"Created model: {django_model.model_key}")
            
            # Create or get ProcessModelVersion
            django_version, created = ProcessModelVersion.objects.get_or_create(
                model=django_model,
                version_label=model_data['version_label'],
                defaults={
                    'external_reference': model_data['external_reference'] or '',
                    'notes': model_data['notes'] or '',
                    'effective_date': model_data['effective_date'],
                    'is_current': bool(model_data['is_current'])
                }
            )
            
            if created:
                print(f"Created version: {django_version.version_label} for {django_model.model_key}")
            
            model_version_map[model_data['version_id']] = django_version.id
        
        # Now migrate process nodes
        nodes_query = """
        SELECT id, model_version_id, parent_id, code, name, description,
               level, display_order, materialized_path
        FROM process_node
        ORDER BY model_version_id, level, display_order
        """
        
        nodes_cursor = orig_conn.execute(nodes_query)
        nodes_data = nodes_cursor.fetchall()
        
        migrated_count = 0
        skipped_count = 0
        node_id_map = {}  # original_node_id -> django_node_id
        
        # Process nodes in multiple passes to handle parent references
        remaining_nodes = list(nodes_data)
        max_passes = 10
        current_pass = 0
        
        while remaining_nodes and current_pass < max_passes:
            current_pass += 1
            processed_in_this_pass = []
            
            print(f"Pass {current_pass}: Processing {len(remaining_nodes)} remaining nodes")
            
            for node_data in remaining_nodes:
                # Check if we have the model version
                if node_data['model_version_id'] not in model_version_map:
                    print(f"Warning: Model version {node_data['model_version_id']} not found for node {node_data['code']}")
                    processed_in_this_pass.append(node_data)
                    skipped_count += 1
                    continue
                
                # Check if parent exists (if needed)
                parent_node = None
                if node_data['parent_id']:
                    if node_data['parent_id'] not in node_id_map:
                        # Parent not processed yet, skip for now
                        continue
                    try:
                        parent_node = ProcessNode.objects.get(id=node_id_map[node_data['parent_id']])
                    except ProcessNode.DoesNotExist:
                        print(f"Warning: Parent node {node_data['parent_id']} not found for node {node_data['code']}")
                        processed_in_this_pass.append(node_data)
                        skipped_count += 1
                        continue
                
                # Check if node already exists
                django_version = ProcessModelVersion.objects.get(id=model_version_map[node_data['model_version_id']])
                existing_node = ProcessNode.objects.filter(
                    model_version=django_version,
                    code=node_data['code']
                ).first()
                
                if existing_node:
                    print(f"Node {node_data['code']} already exists, updating description")
                    existing_node.description = node_data['description'] or ''
                    existing_node.save()
                    node_id_map[node_data['id']] = existing_node.id
                    processed_in_this_pass.append(node_data)
                    continue
                
                # Create new ProcessNode
                try:
                    django_node = ProcessNode.objects.create(
                        model_version=django_version,
                        parent=parent_node,
                        code=node_data['code'],
                        name=node_data['name'] or '',
                        description=node_data['description'] or '',
                        level=node_data['level'],
                        display_order=node_data['display_order'],
                        materialized_path=node_data['materialized_path'] or ''
                    )
                    
                    node_id_map[node_data['id']] = django_node.id
                    migrated_count += 1
                    processed_in_this_pass.append(node_data)
                    
                    print(f"Migrated: {node_data['code']} - {node_data['name']} (description: {bool(node_data['description'])})")
                    
                except Exception as e:
                    print(f"Error creating node {node_data['code']}: {e}")
                    processed_in_this_pass.append(node_data)
                    skipped_count += 1
            
            # Remove processed nodes from remaining list
            remaining_nodes = [node for node in remaining_nodes if node not in processed_in_this_pass]
        
        if remaining_nodes:
            print(f"Warning: {len(remaining_nodes)} nodes could not be processed after {max_passes} passes")
            for node in remaining_nodes:
                print(f"  - {node['code']}: {node['name']}")
            skipped_count += len(remaining_nodes)
        
        print(f"\nProcess node migration complete:")
        print(f"- Migrated: {migrated_count} nodes")
        print(f"- Skipped: {skipped_count} nodes")
        
        return True
        
    except Exception as e:
        print(f"Error during migration: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        orig_conn.close()

if __name__ == "__main__":
    print("Starting process node migration from original FastAPI database...")
    success = migrate_nodes()
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed!")
        sys.exit(1)