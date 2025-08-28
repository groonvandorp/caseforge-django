#!/usr/bin/env python
"""
Identify nodes that failed in the use case candidates batch processing.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "caseforge.settings")
django.setup()

from core.models import ProcessNode, ProcessModelVersion, NodeUsecaseCandidate

# Get model version
model_version = ProcessModelVersion.objects.filter(
    model__model_key='apqc_pcf',
    is_current=True
).first()

if not model_version:
    print("❌ Model not found")
    sys.exit(1)

# Get all leaf nodes
all_nodes = ProcessNode.objects.filter(model_version=model_version)
leaf_nodes = [node for node in all_nodes if node.is_leaf]

print(f"Total leaf nodes: {len(leaf_nodes)}")

# Get nodes with successful batch-generated use cases
nodes_with_usecases = set(
    NodeUsecaseCandidate.objects.filter(
        node__model_version=model_version,
        meta_json__generated_by='batch_api'
    ).values_list('node_id', flat=True)
)

print(f"Nodes with use cases: {len(nodes_with_usecases)}")

# Find failed nodes
failed_node_ids = []
for node in leaf_nodes:
    if node.id not in nodes_with_usecases:
        failed_node_ids.append(node.id)

print(f"Failed nodes: {len(failed_node_ids)}")

# Write failed node IDs to file
output_file = 'batch_usecase_candidates/failed_node_ids.txt'
with open(output_file, 'w') as f:
    for node_id in failed_node_ids:
        f.write(f"{node_id}\n")

print(f"Failed node IDs written to: {output_file}")

# Show some examples
print("\nFirst 10 failed nodes:")
for i, node_id in enumerate(failed_node_ids[:10]):
    node = ProcessNode.objects.get(id=node_id)
    print(f"  {node.id}: [{node.code}] {node.name}")