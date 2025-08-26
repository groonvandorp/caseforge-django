#!/usr/bin/env python
"""
Script to populate model_key metadata for existing NodeUsecaseCandidate records
"""
import os
import sys
import django

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'caseforge.settings')
django.setup()

from core.models import NodeUsecaseCandidate

def populate_usecase_metadata():
    """
    Populate model_key metadata for all existing NodeUsecaseCandidate records
    """
    print("Starting metadata population for NodeUsecaseCandidate records...")
    
    # Get all usecase candidates
    candidates = NodeUsecaseCandidate.objects.select_related(
        'node__model_version__model'
    ).all()
    
    print(f"Found {candidates.count()} usecase candidates to update")
    
    updated_count = 0
    
    for candidate in candidates:
        try:
            # Get the model key from the node relationship
            model_key = candidate.node.model_version.model.model_key
            
            # Handle meta_json - it might be a string, dict, or None
            meta_json = candidate.meta_json
            if meta_json is None:
                meta_json = {}
            elif isinstance(meta_json, str):
                # Try to parse as JSON, or create new dict if parsing fails
                try:
                    import json
                    meta_json = json.loads(meta_json)
                except (json.JSONDecodeError, ValueError):
                    meta_json = {}
            elif not isinstance(meta_json, dict):
                meta_json = {}
            
            # Add metadata if it doesn't exist
            if 'metadata' not in meta_json:
                meta_json['metadata'] = {}
            
            # Set the model_key in metadata
            meta_json['metadata']['model_key'] = model_key
            
            # Update the record
            candidate.meta_json = meta_json
            candidate.save()
            
            updated_count += 1
            
            if updated_count % 50 == 0:
                print(f"Updated {updated_count} candidates...")
                
        except Exception as e:
            print(f"Error updating candidate {candidate.id}: {e}")
            continue
    
    print(f"Successfully updated {updated_count} out of {candidates.count()} usecase candidates")
    
    # Show breakdown by model
    print("\nBreakdown by model:")
    models = {}
    for candidate in NodeUsecaseCandidate.objects.select_related('node__model_version__model').all():
        try:
            model_key = candidate.node.model_version.model.model_key
            models[model_key] = models.get(model_key, 0) + 1
        except:
            models['unknown'] = models.get('unknown', 0) + 1
    
    for model_key, count in models.items():
        print(f"  {model_key}: {count} candidates")

if __name__ == '__main__':
    populate_usecase_metadata()