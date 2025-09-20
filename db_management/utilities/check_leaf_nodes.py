#!/usr/bin/env python
"""
Check leaf node statistics for PCF model
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "caseforge.settings")
django.setup()

from core.models import ProcessNode, ProcessModelVersion
from django.db.models import Count

def main():
    # Get the PCF model version
    version = ProcessModelVersion.objects.filter(
        model__model_key='apqc_pcf', 
        is_current=True
    ).first()

    if not version:
        print("PCF model not found!")
        return

    # Count all nodes
    total_nodes = ProcessNode.objects.filter(model_version=version).count()
    
    # Find leaf nodes (nodes that have no children)
    parent_ids = ProcessNode.objects.filter(
        model_version=version
    ).values_list('parent_id', flat=True).distinct()
    
    leaf_nodes = ProcessNode.objects.filter(
        model_version=version
    ).exclude(id__in=parent_ids)
    
    leaf_nodes_count = leaf_nodes.count()
    nodes_with_children_count = total_nodes - leaf_nodes_count
    
    # Get level distribution
    level_dist = leaf_nodes.values('level').annotate(count=Count('id')).order_by('level')
    
    print(f'PCF Model Statistics:')
    print(f'  Total nodes: {total_nodes}')
    print(f'  Leaf nodes: {leaf_nodes_count}')
    print(f'  Non-leaf (parent) nodes: {nodes_with_children_count}')
    print(f'\nLeaf nodes by level:')
    for item in level_dist:
        print(f'    Level {item["level"]}: {item["count"]} nodes')
    
    # Estimate tokens and cost
    avg_input_tokens = 800  # Prompt with context
    avg_output_tokens = 700  # Generated content
    total_input_tokens = leaf_nodes_count * avg_input_tokens
    total_output_tokens = leaf_nodes_count * avg_output_tokens
    
    # Batch API pricing (50% discount from regular pricing)
    # Regular: Input $2.50/1M, Output $10.00/1M
    # Batch: Input $1.25/1M, Output $5.00/1M
    input_cost = (total_input_tokens / 1_000_000) * 1.25
    output_cost = (total_output_tokens / 1_000_000) * 5.00
    total_cost = input_cost + output_cost
    
    print(f'\n=== Cost Estimate for OpenAI Batch API ===')
    print(f'  Nodes to process: {leaf_nodes_count}')
    print(f'  Est. input tokens per node: {avg_input_tokens}')
    print(f'  Est. output tokens per node: {avg_output_tokens}')
    print(f'  Total input tokens: {total_input_tokens:,}')
    print(f'  Total output tokens: {total_output_tokens:,}')
    print(f'\n  Batch API Pricing (50% discount):')
    print(f'    Input cost: ${input_cost:.2f}')
    print(f'    Output cost: ${output_cost:.2f}')
    print(f'    TOTAL COST: ${total_cost:.2f}')
    print(f'\n  Processing time: ~24 hours (batch queue)')
    
    # Sample a few leaf nodes
    print(f'\nSample leaf nodes:')
    for node in leaf_nodes[:5]:
        print(f'  [{node.code}] {node.name} (Level {node.level})')

if __name__ == '__main__':
    main()