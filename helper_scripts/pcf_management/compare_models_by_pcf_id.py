#!/usr/bin/env python3
"""
Compare APQC Life Science and Cross Industry models by PCF ID to find identical nodes.
"""

import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'caseforge.settings')
django.setup()

from core.models import ProcessModel, ProcessModelVersion, ProcessNode, NodeAttribute

def get_nodes_with_pcf_ids(model_key):
    """Get all nodes with their PCF IDs for a specific model."""
    nodes = ProcessNode.objects.filter(
        model_version__model__model_key=model_key,
        model_version__is_current=True
    ).select_related('model_version', 'model_version__model')
    
    nodes_with_pcf = []
    for node in nodes:
        # Try to get PCF ID from attributes
        pcf_id_attr = NodeAttribute.objects.filter(
            node=node, 
            key__in=['PCF_ID', 'pcf_id', 'PCF ID']
        ).first()
        
        pcf_id = pcf_id_attr.value if pcf_id_attr else None
        
        nodes_with_pcf.append({
            'node': node,
            'pcf_id': pcf_id,
            'code': node.code,
            'name': node.name,
            'description': node.description,
            'level': node.level
        })
    
    return nodes_with_pcf

def main():
    print("Comparing APQC Life Science and Cross Industry models by PCF ID...")
    
    # Get nodes from both models
    print("\n1. Loading Life Science nodes...")
    ls_nodes = get_nodes_with_pcf_ids('apqc_pcf_lifescience')
    ls_with_pcf = [n for n in ls_nodes if n['pcf_id']]
    print(f"   Total nodes: {len(ls_nodes)}, with PCF ID: {len(ls_with_pcf)}")
    
    print("\n2. Loading Cross Industry nodes...")
    ci_nodes = get_nodes_with_pcf_ids('apqc_pcf')
    ci_with_pcf = [n for n in ci_nodes if n['pcf_id']]
    print(f"   Total nodes: {len(ci_nodes)}, with PCF ID: {len(ci_with_pcf)}")
    
    # Create PCF ID mappings
    ls_by_pcf = {n['pcf_id']: n for n in ls_with_pcf}
    ci_by_pcf = {n['pcf_id']: n for n in ci_with_pcf}
    
    # Find matching PCF IDs
    common_pcf_ids = set(ls_by_pcf.keys()) & set(ci_by_pcf.keys())
    
    print(f"\n3. Analysis Results:")
    print(f"   Common PCF IDs found: {len(common_pcf_ids)}")
    
    if len(common_pcf_ids) == 0:
        print("\n   No PCF IDs stored in node attributes.")
        print("   The PCF IDs might not have been imported or stored differently.")
        
        # Show sample nodes from each model
        print(f"\n   Sample Life Science nodes:")
        for node in ls_nodes[:5]:
            attrs = NodeAttribute.objects.filter(node=node['node'])
            attr_info = f" ({len(attrs)} attributes)" if attrs.exists() else " (no attributes)"
            print(f"     {node['code']}: {node['name']}{attr_info}")
            
        print(f"\n   Sample Cross Industry nodes:")
        for node in ci_nodes[:5]:
            attrs = NodeAttribute.objects.filter(node=node['node'])
            attr_info = f" ({len(attrs)} attributes)" if attrs.exists() else " (no attributes)"
            print(f"     {node['code']}: {node['name']}{attr_info}")
    else:
        print(f"\n4. Identical nodes by PCF ID:")
        identical_count = 0
        similar_count = 0
        
        for pcf_id in sorted(common_pcf_ids):
            ls_node = ls_by_pcf[pcf_id]
            ci_node = ci_by_pcf[pcf_id]
            
            # Compare names and descriptions
            name_match = ls_node['name'].strip() == ci_node['name'].strip()
            desc_match = (ls_node['description'] or '').strip() == (ci_node['description'] or '').strip()
            
            if name_match and desc_match:
                identical_count += 1
                match_type = "IDENTICAL"
            elif name_match:
                similar_count += 1
                match_type = "SAME_NAME"
            else:
                match_type = "DIFFERENT"
            
            print(f"\n   PCF ID {pcf_id} - {match_type}")
            print(f"     LS: {ls_node['code']} - {ls_node['name']}")
            print(f"     CI: {ci_node['code']} - {ci_node['name']}")
            
            if not name_match and len(common_pcf_ids) <= 10:
                print(f"       Names differ!")
        
        print(f"\n5. Summary:")
        print(f"   Total matching PCF IDs: {len(common_pcf_ids)}")
        print(f"   Identical nodes (name + description): {identical_count}")
        print(f"   Similar nodes (same name, different description): {similar_count}")
        print(f"   Different nodes: {len(common_pcf_ids) - identical_count - similar_count}")

if __name__ == "__main__":
    main()