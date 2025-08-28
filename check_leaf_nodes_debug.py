#!/usr/bin/env python
"""
Debug leaf node detection for PCF model
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "caseforge.settings")
django.setup()

from core.models import ProcessNode, ProcessModelVersion

def main():
    # Get the PCF model version
    version = ProcessModelVersion.objects.filter(
        model__model_key='apqc_pcf', 
        is_current=True
    ).first()

    if not version:
        print("PCF model not found!")
        return

    # Count nodes using the is_leaf property
    all_nodes = ProcessNode.objects.filter(model_version=version)
    
    print("Checking nodes using is_leaf property...")
    leaf_count = 0
    non_leaf_count = 0
    
    # Sample some nodes
    samples_leaf = []
    samples_non_leaf = []
    
    for node in all_nodes:
        if node.is_leaf:
            leaf_count += 1
            if len(samples_leaf) < 5:
                samples_leaf.append(node)
        else:
            non_leaf_count += 1
            if len(samples_non_leaf) < 5:
                samples_non_leaf.append(node)
    
    print(f"\nResults using is_leaf property:")
    print(f"  Leaf nodes: {leaf_count}")
    print(f"  Non-leaf nodes: {non_leaf_count}")
    print(f"  Total: {leaf_count + non_leaf_count}")
    
    # Get level distribution for leaf nodes
    level_counts = {}
    for node in all_nodes:
        if node.is_leaf:
            level = node.level
            level_counts[level] = level_counts.get(level, 0) + 1
    
    print(f"\nLeaf nodes by level:")
    for level in sorted(level_counts.keys()):
        print(f"  Level {level}: {level_counts[level]} nodes")
    
    print(f"\nSample leaf nodes:")
    for node in samples_leaf[:5]:
        print(f"  [{node.code}] {node.name} (Level {node.level})")
    
    print(f"\nSample non-leaf nodes:")
    for node in samples_non_leaf[:5]:
        print(f"  [{node.code}] {node.name} (Level {node.level})")
        
    # Cost calculation
    if leaf_count > 0:
        avg_input_tokens = 800
        avg_output_tokens = 700
        total_input_tokens = leaf_count * avg_input_tokens
        total_output_tokens = leaf_count * avg_output_tokens
        
        input_cost = (total_input_tokens / 1_000_000) * 1.25
        output_cost = (total_output_tokens / 1_000_000) * 5.00
        total_cost = input_cost + output_cost
        
        print(f'\n=== Cost Estimate for OpenAI Batch API ===')
        print(f'  Leaf nodes to process: {leaf_count}')
        print(f'  Est. tokens per node: {avg_input_tokens + avg_output_tokens}')
        print(f'  Total tokens: {(total_input_tokens + total_output_tokens):,}')
        print(f'  Estimated cost (batch pricing): ${total_cost:.2f}')

if __name__ == '__main__':
    main()