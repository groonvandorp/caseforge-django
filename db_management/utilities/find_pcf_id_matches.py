#!/usr/bin/env python3
"""
Find identical nodes between Cross Industry and Life Science models based on:
- Same PCF ID (5-digit number)
- Same name
- Same description

This is the CORRECT matching criteria as specified by the user.
"""

import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'caseforge.settings')
django.setup()

from core.models import ProcessModel, ProcessModelVersion, ProcessNode, NodeAttribute, NodeDocument

def get_nodes_with_pcf_ids(model_key):
    """Get all nodes with PCF IDs for a specific model."""
    nodes = ProcessNode.objects.filter(
        model_version__model__model_key=model_key,
        model_version__is_current=True
    ).select_related('model_version', 'model_version__model')
    
    nodes_with_pcf = []
    for node in nodes:
        # Get PCF ID attribute
        pcf_attr = NodeAttribute.objects.filter(
            node=node,
            key='pcf_id'
        ).first()
        
        if pcf_attr:
            nodes_with_pcf.append({
                'node': node,
                'pcf_id': pcf_attr.value,
                'name': node.name,
                'description': node.description or '',
                'code': node.code,
                'level': node.level
            })
    
    return nodes_with_pcf

def find_pcf_id_matches():
    """Find nodes with identical PCF ID + name + description."""
    print("🔍 Finding identical nodes using PCF ID + name + description matching...")
    print("=" * 70)
    
    # Get nodes from both models
    ci_nodes = get_nodes_with_pcf_ids('apqc_pcf')
    ls_nodes = get_nodes_with_pcf_ids('apqc_pcf_lifescience')
    
    print(f"📊 Cross Industry nodes with PCF IDs: {len(ci_nodes)}")
    print(f"📊 Life Science nodes with PCF IDs: {len(ls_nodes)}")
    
    # Create lookup dictionary for Life Science nodes
    ls_lookup = {}
    for ls_data in ls_nodes:
        key = (ls_data['pcf_id'], ls_data['name'], ls_data['description'])
        ls_lookup[key] = ls_data
    
    # Find matches
    matches = []
    for ci_data in ci_nodes:
        key = (ci_data['pcf_id'], ci_data['name'], ci_data['description'])
        if key in ls_lookup:
            ls_data = ls_lookup[key]
            matches.append({
                'pcf_id': ci_data['pcf_id'],
                'name': ci_data['name'],
                'description': ci_data['description'],
                'ci_node': ci_data['node'],
                'ls_node': ls_data['node'],
                'ci_code': ci_data['code'],
                'ls_code': ls_data['code'],
                'level': ci_data['level']
            })
    
    print(f"\n🎯 Found {len(matches)} identical nodes!")
    print(f"   Matching criteria: PCF ID + name + description")
    
    # Analyze by level
    level_counts = {}
    for match in matches:
        level = match['level']
        level_counts[level] = level_counts.get(level, 0) + 1
    
    print(f"\n📈 Matches by level:")
    for level in sorted(level_counts.keys()):
        print(f"   Level {level}: {level_counts[level]} matches")
    
    # Show sample matches
    print(f"\n📋 Sample matches (first 10):")
    for i, match in enumerate(matches[:10]):
        print(f"   {i+1}. PCF {match['pcf_id']}: {match['name']}")
        print(f"      CI: {match['ci_code']} | LS: {match['ls_code']}")
    
    if len(matches) > 10:
        print(f"   ... and {len(matches) - 10} more")
    
    return matches

def analyze_copy_potential(matches):
    """Analyze what can be copied from CI to LS."""
    print(f"\n🔄 COPY ANALYSIS")
    print("=" * 50)
    
    # Check which CI nodes have process details
    ci_nodes_with_details = []
    for match in matches:
        ci_node = match['ci_node']
        has_details = NodeDocument.objects.filter(
            node=ci_node,
            document_type='process_details'
        ).exists()
        
        if has_details:
            # Check if LS node already has details
            ls_node = match['ls_node']
            ls_has_details = NodeDocument.objects.filter(
                node=ls_node,
                document_type='process_details'
            ).exists()
            
            if not ls_has_details:
                ci_nodes_with_details.append(match)
    
    print(f"📄 CI nodes with process details (can copy): {len(ci_nodes_with_details)}")
    
    # Check usecase candidates
    ci_nodes_with_usecases = []
    for match in matches:
        ci_node = match['ci_node']
        usecase_count = ci_node.usecase_candidates.count()
        
        if usecase_count > 0:
            ls_node = match['ls_node']
            ls_usecase_count = ls_node.usecase_candidates.count()
            
            if ls_usecase_count == 0:
                ci_nodes_with_usecases.append({
                    **match,
                    'usecase_count': usecase_count
                })
    
    print(f"💡 CI nodes with AI usecase candidates (can copy): {len(ci_nodes_with_usecases)}")
    
    # Show some examples
    if ci_nodes_with_details:
        print(f"\n📋 Sample process details to copy:")
        for i, match in enumerate(ci_nodes_with_details[:5]):
            print(f"   {i+1}. PCF {match['pcf_id']}: {match['name']}")
    
    if ci_nodes_with_usecases:
        print(f"\n📋 Sample usecase candidates to copy:")
        for i, match in enumerate(ci_nodes_with_usecases[:5]):
            print(f"   {i+1}. PCF {match['pcf_id']}: {match['name']} ({match['usecase_count']} candidates)")
    
    return ci_nodes_with_details, ci_nodes_with_usecases

def main():
    """Main execution function."""
    print("🚀 PCF ID-BASED NODE MATCHING")
    print("=" * 50)
    print("✅ Using CORRECT matching criteria:")
    print("   1. Same PCF ID (5-digit number)")
    print("   2. Same name")  
    print("   3. Same description")
    print("❌ NOT using hierarchical codes (1.1.1.1)")
    
    matches = find_pcf_id_matches()
    
    if matches:
        details_matches, usecase_matches = analyze_copy_potential(matches)
        
        print(f"\n🎉 SUMMARY:")
        print(f"   Total identical nodes: {len(matches)}")
        print(f"   Ready for process details copy: {len(details_matches)}")
        print(f"   Ready for usecase candidates copy: {len(usecase_matches)}")
    else:
        print("❌ No matches found!")

if __name__ == "__main__":
    main()