#!/usr/bin/env python3

"""
Fix the parent-child relationships in the Life Science model.
The issue: 1.1, 1.2, etc. should be children of 1.0, but they're currently root nodes.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'caseforge.settings')
django.setup()

from core.models import ProcessNode, ProcessModel

def fix_lifescience_hierarchy():
    print("Fixing Life Science model hierarchy...")
    
    # Get the Life Science model
    model = ProcessModel.objects.get(model_key='apqc_pcf_lifescience')
    version = model.versions.filter(is_current=True).first()
    
    if not version:
        print("No current version found for Life Science model")
        return
    
    print(f"Working with model version: {version}")
    
    # Fix the hierarchy for each major category (1-13)
    for major_num in range(1, 14):
        root_code = f"{major_num}.0"
        
        # Find the .0 root node
        root_node = ProcessNode.objects.filter(
            model_version=version,
            code=root_code
        ).first()
        
        if not root_node:
            print(f"Root node {root_code} not found, skipping...")
            continue
            
        print(f"\nProcessing {root_code}: {root_node.name}")
        
        # Find all child nodes that should belong to this root
        child_nodes = ProcessNode.objects.filter(
            model_version=version,
            code__startswith=f"{major_num}.",
            parent=None,  # Currently orphaned
            level=1  # Currently at wrong level
        ).exclude(code=root_code)  # Don't include the root itself
        
        children_fixed = 0
        for child in child_nodes:
            # Check if this should really be a child (e.g., 1.1, 1.2 but not 10.1, 11.1)
            parts = child.code.split('.')
            if len(parts) == 2 and parts[0] == str(major_num):
                print(f"  Fixing {child.code}: {child.name}")
                child.parent = root_node
                child.level = 2  # Should be level 2, not level 1
                child.save()
                children_fixed += 1
        
        print(f"  Fixed {children_fixed} children for {root_code}")
        
        # Verify the fix
        actual_children = root_node.children.count()
        print(f"  {root_code} now has {actual_children} children, is_leaf: {root_node.is_leaf}")

if __name__ == '__main__':
    fix_lifescience_hierarchy()
    print("\nHierarchy fix completed!")