#!/usr/bin/env python3
"""
Find identical nodes between Cross Industry and Retail models based on:
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
    print("🔍 Finding identical nodes between Cross Industry and Retail...")
    print("=" * 70)
    
    # Get nodes from both models
    ci_nodes = get_nodes_with_pcf_ids('apqc_pcf')
    retail_nodes = get_nodes_with_pcf_ids('apqc_pcf_retail')
    
    print(f"📊 Cross Industry nodes with PCF IDs: {len(ci_nodes)}")
    print(f"📊 Retail nodes with PCF IDs: {len(retail_nodes)}")
    
    # Create lookup dictionary for Retail nodes
    retail_lookup = {}
    for retail_data in retail_nodes:
        key = (retail_data['pcf_id'], retail_data['name'], retail_data['description'])
        retail_lookup[key] = retail_data
    
    # Find matches
    matches = []
    for ci_data in ci_nodes:
        key = (ci_data['pcf_id'], ci_data['name'], ci_data['description'])
        if key in retail_lookup:
            retail_data = retail_lookup[key]
            matches.append({
                'pcf_id': ci_data['pcf_id'],
                'name': ci_data['name'],
                'description': ci_data['description'],
                'ci_node': ci_data['node'],
                'retail_node': retail_data['node'],
                'ci_code': ci_data['code'],
                'retail_code': retail_data['code'],
                'level': ci_data['level']
            })
    
    print(f"\n🎯 Found {len(matches)} identical nodes!")
    print(f"   Matching criteria: PCF ID + name + description")
    print(f"   Match rate: {len(matches)/len(ci_nodes)*100:.1f}% of Cross Industry nodes")
    
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
        print(f"      CI: {match['ci_code']} | Retail: {match['retail_code']}")
    
    if len(matches) > 10:
        print(f"   ... and {len(matches) - 10} more")
    
    return matches

def analyze_copy_potential(matches):
    """Analyze what can be copied from CI to Retail."""
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
            # Check if Retail node already has details
            retail_node = match['retail_node']
            retail_has_details = NodeDocument.objects.filter(
                node=retail_node,
                document_type='process_details'
            ).exists()
            
            if not retail_has_details:
                ci_nodes_with_details.append(match)
    
    print(f"📄 CI nodes with process details (can copy to Retail): {len(ci_nodes_with_details)}")
    
    # Check usecase candidates
    ci_nodes_with_usecases = []
    for match in matches:
        ci_node = match['ci_node']
        usecase_count = ci_node.usecase_candidates.count()
        
        if usecase_count > 0:
            retail_node = match['retail_node']
            retail_usecase_count = retail_node.usecase_candidates.count()
            
            if retail_usecase_count == 0:
                ci_nodes_with_usecases.append({
                    **match,
                    'usecase_count': usecase_count
                })
    
    print(f"💡 CI nodes with AI usecase candidates (can copy to Retail): {len(ci_nodes_with_usecases)}")
    
    # Show some examples
    if ci_nodes_with_details:
        print(f"\n📋 Sample process details to copy:")
        for i, match in enumerate(ci_nodes_with_details[:5]):
            print(f"   {i+1}. PCF {match['pcf_id']}: {match['name']}")
    
    if ci_nodes_with_usecases:
        print(f"\n📋 Sample usecase candidates to copy:")
        for i, match in enumerate(ci_nodes_with_usecases[:5]):
            print(f"   {i+1}. PCF {match['pcf_id']}: {match['name']} ({match['usecase_count']} candidates)")
        
        # Calculate total candidates
        total_candidates = sum(match['usecase_count'] for match in ci_nodes_with_usecases)
        print(f"\n📊 Total AI usecase candidates to copy: {total_candidates}")
    
    return ci_nodes_with_details, ci_nodes_with_usecases

def main():
    """Main execution function."""
    print("🚀 PCF ID-BASED NODE MATCHING: CROSS INDUSTRY → RETAIL")
    print("=" * 70)
    print("✅ Using CORRECT matching criteria:")
    print("   1. Same PCF ID (5-digit number)")
    print("   2. Same name")  
    print("   3. Same description")
    print("❌ NOT using hierarchical codes (1.1.1.1)")
    
    matches = find_pcf_id_matches()
    
    if matches:
        details_matches, usecase_matches = analyze_copy_potential(matches)
        
        print(f"\n🎉 SUMMARY:")
        print(f"   Total identical nodes (CI ↔ Retail): {len(matches)}")
        print(f"   Ready for process details copy: {len(details_matches)}")
        print(f"   Ready for usecase candidates copy: {len(usecase_matches)}")
        
        if usecase_matches:
            total_candidates = sum(match['usecase_count'] for match in usecase_matches)
            print(f"   Total usecase candidates to copy: {total_candidates}")
    else:
        print("❌ No matches found!")

if __name__ == "__main__":
    main()